# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The real-time part of the PAT: heartbeats in, tones out at the dialled phase.

Three pieces, each replaceable for testing:

- a beat source: :class:`LSLBeatSource` finds R peaks in an ECG arriving over
  LSL, :class:`VirtualBeatSource` makes up a heart for the exteroceptive task;
- a :class:`TonePlayer`, which plays a tone (left channel) or a 50 Hz
  vibration burst (right channel) at a scheduled time and reports when it
  actually started;
- the :class:`PhaseEngine`, which on every beat reads the dial, works out when
  the tone is due and schedules it, logs every tone, and pushes one JSON marker
  per event to an LSL outlet.

All times are seconds on the LSL clock (``pylsl.local_clock``), the clock
LabRecorder writes, so the ECG and the markers line up in the XDF file.

Scheduling, on each beat ``b``::

    delay  = phase / 360 * b.period         (relative mode)
           = min(dial_ms / 1000, b.period)  (absolute mode)
    target = b.r_time + delay - latency_bias

If ``target`` is at least ``audio_lead`` away the tone is scheduled there
(anchor ``real``). Otherwise it is too late for this cycle and goes one period
later (anchor ``predicted``), timed from the beat just seen and the
anticipated period. A tone less than ``min_tone_gap`` after the previous one
is skipped, as the original firmware's double-beep guard does.

``latency_bias`` stands for what the recordings cannot see: the ECG is
stamped when it reaches the PC, tens of milliseconds after the heart beat,
and the sound leaves the speaker some milliseconds after the onset the audio
driver reports. Subtracting it from every target puts the tone where the
participant would hear it if those delays were zero.

This module imports no PsychoPy. ``pylsl`` and ``psychtoolbox`` are imported
inside the classes that need them, so it imports on a machine with neither.
"""

import json
import math
import time
from collections import deque
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
    runtime_checkable,
)

import numpy as np

#: Scheduling modes of :class:`PhaseEngine`.
MODES = ("relative", "absolute")

#: Sound kinds :class:`TonePlayer` can play.
KINDS = ("tone", "vibration")

#: Seconds :meth:`PhaseEngine.end_trial` waits for the R after the press.
NEXT_BEAT_TIMEOUT = 3.0

#: An RR interval longer than this (seconds) is taken for a gap in the
#: signal, not a heartbeat: the anticipated period starts again from scratch.
MAX_RR = 2.0

#: RR intervals averaged into the anticipated period.
PERIOD_BEATS = 3

#: Period, in seconds, used to wrap the absolute dial before one is known.
DEFAULT_PERIOD = 1.0

Clock = Callable[[], float]


def default_clock() -> Clock:
    """``pylsl.local_clock``, or PsychToolbox's ``GetSecs`` without pylsl.

    On Windows both read QueryPerformanceCounter from the same origin.
    """
    try:
        import pylsl

        return pylsl.local_clock
    except ImportError:  # pragma: no cover - pylsl is there wherever LSL is
        import psychtoolbox as ptb

        return ptb.GetSecs


def _json_safe(value: Any) -> Any:
    """NaN and infinities as ``null``, numpy scalars as Python ones."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


# -- beats ---------------------------------------------------------------------


class Beat(NamedTuple):
    """One heartbeat, real or virtual."""

    #: Time of the R peak, LSL seconds.
    r_time: float
    #: Anticipated period at this beat, seconds; ``None`` until known.
    period: Optional[float]


@runtime_checkable
class BeatSource(Protocol):
    """Anything that tells the engine when the heart beats."""

    def start(self) -> None:
        """Begin delivering beats."""

    def poll(self) -> List[Beat]:
        """Beats since the last call, oldest first. Never blocks."""

    def stop(self) -> None:
        """Stop delivering beats."""

    @property
    def period(self) -> Optional[float]:
        """The current anticipated period in seconds, ``None`` if unknown."""


class LSLBeatSource:
    """R peaks found online in the ECG of an :class:`~cardioception.devices.LSLRecorder`.

    Pulls the recorder's inlet and feeds the samples of its channel to an
    :class:`~cardioception.devices._online_beats.OnlineRDetector`. The
    anticipated period is the mean of the last 3 RR intervals; an interval
    longer than :data:`MAX_RR` is taken for a gap in the signal and starts the
    count again.

    While this source is in use it is the only reader of the inlet: do not
    call the recorder's ``read``, ``readInWaiting`` or ``waitBeat`` at the
    same time, they would take samples the detector never sees.

    Parameters
    ----------
    recorder :
        A connected :class:`~cardioception.devices.LSLRecorder` (anything with
        ``inlet``, ``channel`` and ``sfreq``).
    detector :
        An ``OnlineRDetector``; one is made for the recorder's rate if omitted.
    """

    #: This source follows a real heart.
    virtual = False

    def __init__(self, recorder: Any, detector: Any = None):
        if detector is None:
            from cardioception.devices._online_beats import OnlineRDetector

            detector = OnlineRDetector(sfreq=recorder.sfreq)
        self.recorder = recorder
        self.detector = detector
        self.last_r_time: Optional[float] = None
        self._rr: Deque[float] = deque(maxlen=PERIOD_BEATS)
        self._pending: List[Beat] = []
        self._started = False
        #: Samples fed to the detector since :meth:`start`.
        self.n_samples = 0
        #: Clock time at which the last sample arrived.
        self.last_sample_time: Optional[float] = None

    @property
    def period(self) -> Optional[float]:
        if len(self._rr) < PERIOD_BEATS:
            return None
        return sum(self._rr) / PERIOD_BEATS

    def start(self) -> None:
        """Drop what the inlet holds and start detecting from now.

        Does nothing if already started: the detector needs about 2 s of
        signal and 3 beats before it knows the period, so it is kept running
        across trials.
        """
        if self._started:
            return
        self.recorder.inlet.flush()
        self.detector.reset()
        self._rr.clear()
        self._pending = []
        self.last_r_time = None
        self.n_samples = 0
        self._started = True

    def stop(self) -> None:
        """Stop; the next :meth:`start` begins afresh. The recorder stays open."""
        self._started = False

    def poll(self) -> List[Beat]:
        """Beats committed since the last call."""
        if not self._started:
            self.start()
        self._pull(timeout=0.0)
        beats, self._pending = self._pending, []
        return beats

    def wait_next_beat(self, after: float, timeout: float = 3.0) -> Optional[Beat]:
        """Block until a beat with ``r_time > after`` is found, or ``timeout`` s pass.

        The beats found while waiting are still returned by the next
        :meth:`poll`, so nothing is lost for the marker stream.
        """
        if not self._started:
            self.start()
        deadline = time.perf_counter() + timeout
        while True:
            for beat in self._pending:
                if beat.r_time > after:
                    return beat
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return None
            self._pull(timeout=min(0.01, remaining))

    def _pull(self, timeout: float) -> None:
        """Feed everything the inlet holds to the detector."""
        from cardioception.devices.lsl import PULL_CHUNK

        inlet, ch = self.recorder.inlet, self.recorder.channel
        while True:
            samples, stamps = inlet.pull_chunk(timeout=timeout, max_samples=PULL_CHUNK)
            if not stamps:
                return
            x = np.asarray(samples, dtype=float)[:, ch]
            for found in self.detector.process(x, stamps):
                self._on_beat(found.r_time, found.rr)
            self.n_samples += len(stamps)
            self.last_sample_time = float(stamps[-1])
            if len(stamps) < PULL_CHUNK:
                return
            timeout = 0.0

    def _on_beat(self, r_time: float, rr: Optional[float]) -> None:
        if rr is None or rr > MAX_RR:
            self._rr.clear()
        else:
            self._rr.append(rr)
        self.last_r_time = r_time
        self._pending.append(Beat(r_time, self.period))


def simulated_periods(seed: Optional[int] = None) -> Iterator[float]:
    """The PAT-ECG firmware's simulated heart, in seconds, forever.

    A baseline drawn between 900 and 1100 ms plus four first-order
    autoregressive components (high, low and very low frequency, and noise)
    driven by uniform noise, clamped to 550 to 1500 ms and averaged over 3
    beats, as in ``firmware_2026.ino``.
    """
    rng = np.random.default_rng(seed)
    base = 900.0 + float(rng.integers(0, 201))
    # (AR coefficient, noise amplitude in ms) for HF, LF, VLF and noise.
    components = ((0.92, 65.0), (0.985, 18.0), (0.996, 6.0), (0.90, 10.0))
    state = [0.0] * len(components)
    last: Deque[float] = deque(maxlen=3)
    while True:
        for i, (coef, amp) in enumerate(components):
            state[i] = coef * state[i] + (rng.random() * 2.0 - 1.0) * amp
        last.append(min(max(base + sum(state), 550.0), 1500.0))
        if len(last) == 3:
            yield sum(last) / 3 / 1000.0


class VirtualBeatSource:
    """Beats known in advance, for the exteroceptive task.

    :meth:`poll` returns each beat one period before it happens (as soon as
    the previous virtual beat is due), so the engine can schedule the
    vibration at the beat itself and the tone after it. A beat's ``period``
    is the interval to the next virtual beat, which is known exactly.

    Parameters
    ----------
    period :
        ``"simulated"`` for the firmware's simulated heart (see
        :func:`simulated_periods`), a number for a fixed period in seconds,
        or a sequence of periods in seconds to replay (repeated when it runs
        out), e.g. the participant's own RR intervals.
    seed :
        Seed of the simulated heart.
    clock :
        The clock beats are timed on; ``pylsl.local_clock`` by default.
    lead_in :
        Seconds from :meth:`start` to the first beat.
    """

    #: The engine schedules a vibration on each beat of this source.
    virtual = True

    def __init__(
        self,
        period: Union[str, float, Sequence[float]] = "simulated",
        seed: Optional[int] = None,
        clock: Optional[Clock] = None,
        lead_in: float = 1.0,
    ):
        if isinstance(period, str):
            if period != "simulated":
                raise ValueError(
                    f"period should be 'simulated', seconds, or a sequence of "
                    f"seconds, got {period!r}"
                )
        elif isinstance(period, (int, float)):
            if not 0.25 <= period <= 3.0:
                raise ValueError(f"A period of {period} s is not a heartbeat.")
        else:
            values = np.asarray(period, dtype=float).ravel()
            if values.size == 0 or not np.all(np.isfinite(values)):
                raise ValueError("The periods to replay should be finite numbers.")
            if values.min() < 0.25 or values.max() > 3.0:
                raise ValueError(
                    "The periods to replay should be seconds between 0.25 and 3."
                )
        self._spec = period
        self.seed = seed
        self.clock = clock or default_clock()
        self.lead_in = lead_in
        self._periods: Iterator[float] = iter(())
        self._next_r: Optional[float] = None
        self._next_period = DEFAULT_PERIOD
        self._last_period: Optional[float] = None
        self._emitted: Deque[Beat] = deque(maxlen=8)
        self.last_r_time: Optional[float] = None

    def _make_periods(self) -> Iterator[float]:
        spec = self._spec
        if isinstance(spec, str):
            return simulated_periods(self.seed)
        if isinstance(spec, (int, float)):
            return _repeat([float(spec)])
        return _repeat([float(v) for v in np.asarray(spec, dtype=float).ravel()])

    @property
    def period(self) -> Optional[float]:
        if self._last_period is not None:
            return self._last_period
        return self._next_period if self._next_r is not None else None

    def start(self) -> None:
        """Start the heart: the first beat comes ``lead_in`` seconds from now.

        Does nothing if already started, so the heart keeps beating across
        trials.
        """
        if self._next_r is not None:
            return
        self._periods = self._make_periods()
        self._next_period = next(self._periods)
        self._next_r = self.clock() + self.lead_in

    def stop(self) -> None:
        """Stop the heart; the next :meth:`start` begins a new series."""
        self._next_r = None
        self._last_period = None
        self._emitted.clear()

    def poll(self) -> List[Beat]:
        """The beats due within one period from now.

        Beats that were due while nobody polled are dropped, not returned
        late.
        """
        if self._next_r is None:
            self.start()
        assert self._next_r is not None
        now = self.clock()
        beats = []
        while self._next_r - now <= (self._last_period or self._next_period):
            beat = Beat(self._next_r, self._next_period)
            if beat.r_time >= now:
                beats.append(beat)
            self._emitted.append(beat)
            self.last_r_time = beat.r_time
            self._last_period = self._next_period
            self._next_r += self._next_period
            self._next_period = next(self._periods)
        return beats

    def wait_next_beat(self, after: float, timeout: float = 3.0) -> Optional[Beat]:
        """The first beat after ``after``; virtual beats are known, so no wait."""
        if self._next_r is None:
            return None
        for beat in self._emitted:
            if beat.r_time > after:
                return beat
        return Beat(self._next_r, self._next_period)


def _repeat(values: List[float]) -> Iterator[float]:
    while True:
        yield from values


# -- sound ---------------------------------------------------------------------


def _burst(
    freq: float, duration: float, ramp: float, volume: float, fs: float
) -> np.ndarray:
    """A sine burst with raised-cosine ramps, mono float32."""
    n = max(int(round(duration * fs)), 1)
    x = volume * np.sin(2 * np.pi * freq * np.arange(n) / fs)
    r = min(int(round(ramp * fs)), n // 2)
    if r > 0:
        window = 0.5 * (1 - np.cos(np.pi * np.arange(r) / r))
        x[:r] *= window
        x[-r:] *= window[::-1]
    return x.astype(np.float32)


def ptb_minus_clock(clock: Clock, n: int = 50) -> float:
    """Offset of PsychToolbox's ``GetSecs`` from ``clock``, median of ``n`` readings.

    Each reading takes ``clock`` either side of ``GetSecs`` and uses the
    midpoint, so the cost of the calls does not bias the offset.
    """
    import psychtoolbox as ptb

    offsets = []
    for _ in range(n):
        a = clock()
        g = ptb.GetSecs()
        b = clock()
        offsets.append(g - (a + b) / 2)
    return float(np.median(offsets))


class _Track:
    """One PsychPortAudio slave: a queue of starts of one sound."""

    def __init__(self, slave: Any, duration: float):
        self.slave = slave
        self.duration = duration
        self.queue: List[Tuple[float, int]] = []  # (when on GetSecs, handle)
        self.active: Optional[Tuple[float, int]] = None
        self.onset = 0.0
        self.started_at = 0.0


class TonePlayer:
    """Tones and vibration bursts at scheduled times, through PsychPortAudio.

    One stereo output at latency class 1, kept running for the whole session
    (a master stream with two slaves), so starts are sample-accurate and the
    Windows audio endpoint never has to wake up. The tone plays on the left
    channel, the vibration burst on the right one, so the exteroceptive task
    can drive a tactor through an amplifier from the same jack. Tone and
    vibration can overlap in time.

    :meth:`schedule` and :meth:`poll_onsets` take and return times on
    ``clock`` (the LSL clock by default); the offset to ``GetSecs`` is
    measured once at start.

    Parameters
    ----------
    freq, duration, ramp, volume :
        The tone: Hz, seconds, seconds of raised-cosine ramp at each end,
        amplitude 0 to 1.
    vib_freq, vib_duration, vib_volume :
        The vibration burst, likewise (same ramp).
    device :
        PsychPortAudio output device index; the system default if omitted.
    clock :
        The clock of ``when`` and of the reported onsets.
    """

    def __init__(
        self,
        freq: float = 1000.0,
        duration: float = 0.03,
        ramp: float = 0.005,
        volume: float = 0.5,
        vib_freq: float = 50.0,
        vib_duration: float = 0.05,
        vib_volume: float = 1.0,
        device: Optional[int] = None,
        clock: Optional[Clock] = None,
    ):
        for name, value in (("volume", volume), ("vib_volume", vib_volume)):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} should be between 0 and 1, got {value}")
        import psychtoolbox as ptb
        from psychtoolbox import audio

        audio.verbosity(1)
        self._ptb = ptb
        self.clock = clock or default_clock()
        self.offset = ptb_minus_clock(self.clock)
        # Mode 1 + 8: playback, as a master that slaves mix into.
        self.master = audio.Stream(
            device_id=[] if device is None else device,
            mode=1 + 8,
            latency_class=1,
            freq=[],
            channels=2,
        )
        self.master.run_mode = 1
        status = self.master.status
        self.fs = float(status["SampleRate"])
        self.device = int(status["OutDeviceIndex"])
        # Run forever, from now; slaves are mixed in when started.
        self.master.start(repetitions=0, when=0, wait_for_start=1)
        tone = _burst(freq, duration, ramp, volume, self.fs)
        vib = _burst(vib_freq, vib_duration, ramp, vib_volume, self.fs)
        self._tracks: Dict[str, _Track] = {}
        for kind, left, right, dur in (
            ("tone", tone, np.zeros_like(tone), duration),
            ("vibration", np.zeros_like(vib), vib, vib_duration),
        ):
            slave = audio.Slave(self.master.handle, mode=1, channels=2)
            slave.fill_buffer(np.column_stack([left, right]))
            self._tracks[kind] = _Track(slave, dur)
        self._next_handle = 0
        self._done: List[Tuple[int, float]] = []
        self._closed = False
        # Let the endpoint settle before the first real start.
        time.sleep(0.2)

    @property
    def busy(self) -> bool:
        """Whether any sound is waiting or playing."""
        return any(t.active is not None or t.queue for t in self._tracks.values())

    def schedule(self, when: float, kind: str = "tone") -> int:
        """Play ``kind`` at ``when`` (clock seconds). Returns a handle.

        The onset is reported by :meth:`poll_onsets` under that handle. Sounds
        of one kind play one after the other in time order; a sound whose
        time has passed by the time its turn comes plays at once (and its
        onset says so).
        """
        if kind not in self._tracks:
            raise ValueError(f"kind should be one of {KINDS}, got {kind!r}")
        handle = self._next_handle
        self._next_handle += 1
        track = self._tracks[kind]
        track.queue.append((when + self.offset, handle))
        track.queue.sort()
        self._advance(track)
        return handle

    def poll_onsets(self) -> List[Tuple[int, float]]:
        """``(handle, onset)`` of the sounds that have finished since the last call.

        ``onset`` is when PsychPortAudio says the first sample reached the
        output, on ``clock``; NaN if it gave none (e.g. stopped before it
        started).
        """
        for track in self._tracks.values():
            self._advance(track)
        done, self._done = self._done, []
        return done

    def _advance(self, track: _Track) -> None:
        """Finish the playing sound if it is over, then start the next one."""
        now = self._ptb.GetSecs()
        if track.active is not None:
            when, handle = track.active
            status = track.slave.status
            # Until this sound starts, StartTime can still hold the last one's.
            if status["StartTime"] > when - 0.05:
                track.onset = status["StartTime"]
            # State 1 is waiting for ``when``, 2 playing, 0 stopped. Right
            # after a start the state can still read 0, hence the time check.
            finished = status["State"] == 0 and now > max(when, track.started_at)
            if finished or now > when + track.duration + 1.0:
                start_time = track.slave.stop()[0]
                if not track.onset and start_time > when - 0.05:
                    track.onset = start_time
                onset = track.onset - self.offset if track.onset else math.nan
                self._done.append((handle, onset))
                track.active = None
        if track.active is None and track.queue:
            when, handle = track.queue.pop(0)
            track.onset = 0.0
            track.started_at = now
            track.slave.start(repetitions=1, when=when, wait_for_start=0)
            track.active = (when, handle)

    def stop_all(self) -> None:
        """Stop everything playing or waiting. Their onsets are still reported.

        A sound that had started keeps its onset, the others report NaN.
        """
        now = self._ptb.GetSecs()
        for track in self._tracks.values():
            if track.active is not None:
                when, handle = track.active
                status = track.slave.status
                start_time = track.slave.stop()[0]
                onset = 0.0
                for candidate in (status["StartTime"], start_time):
                    if when - 0.05 < candidate <= now:
                        onset = candidate
                self._done.append((handle, onset - self.offset if onset else math.nan))
                track.active = None
            self._done.extend((handle, math.nan) for _, handle in track.queue)
            track.queue = []

    def close(self) -> None:
        """Stop and release the audio device."""
        if self._closed:
            return
        self._closed = True
        try:
            self.stop_all()
        except Exception:
            pass
        # Slaves first: closing the master closes them under their feet.
        for track in self._tracks.values():
            track.slave.close()
        try:
            self.master.stop()
        except Exception:
            pass
        self.master.close()


# -- the engine ----------------------------------------------------------------


class PhaseEngine:
    """Play one tone per heartbeat at the phase set with the dial.

    Call :meth:`start_trial`, then :meth:`poll` every frame and :meth:`nudge`
    whenever the dial moves; :meth:`stop_tones` at the press, and
    :meth:`end_trial` for the trial's row. See the module docstring for the
    scheduling rule.

    The dial is kept as a phase in degrees in relative mode (it wraps at
    360) and as a delay in ms in absolute mode (it wraps at the anticipated
    period, and the delay used for a beat is clamped to that beat's period).
    Each trial starts with the dial at the trial's start phase.

    With a virtual source (``source.virtual`` true, the exteroceptive task)
    each beat also gets a vibration burst at ``r_time - latency_bias``,
    anchor ``virtual``.

    Parameters
    ----------
    source :
        A :class:`BeatSource`.
    player :
        A :class:`TonePlayer`, or anything with ``schedule(when, kind)`` and
        ``poll_onsets()``.
    mode :
        ``"relative"`` or ``"absolute"``.
    latency_bias :
        Seconds subtracted from every target (see the module docstring).
    audio_lead :
        Least time, in seconds, between scheduling a sound and its target.
    min_tone_gap :
        A tone less than this many seconds after the previous one is skipped.
    outlet :
        A pylsl ``StreamOutlet`` of one string channel for the JSON markers,
        or ``None`` for none.
    clock :
        The clock beats and tones are timed on; ``pylsl.local_clock`` by
        default.
    """

    def __init__(
        self,
        source: BeatSource,
        player: Any,
        mode: str,
        latency_bias: float = 0.05,
        audio_lead: float = 0.05,
        min_tone_gap: float = 0.3,
        outlet: Any = None,
        clock: Optional[Clock] = None,
    ):
        if mode not in MODES:
            raise ValueError(f"mode should be one of {MODES}, got {mode!r}")
        if audio_lead < 0 or min_tone_gap < 0:
            raise ValueError("audio_lead and min_tone_gap should not be negative.")
        self.source = source
        self.player = player
        self.mode = mode
        self.latency_bias = float(latency_bias)
        self.audio_lead = float(audio_lead)
        self.min_tone_gap = float(min_tone_gap)
        self.outlet = outlet
        self.clock = clock or default_clock()
        self.extero = bool(getattr(source, "virtual", False))

        self._phase = 0.0  # degrees, relative mode
        self._delay_ms = 0.0  # ms, absolute mode
        self._known_period: Optional[float] = None
        self._tones: List[dict] = []
        self._waiting: Dict[int, dict] = {}  # handle -> tone row without onset
        self._beats: Deque[Beat] = deque(maxlen=64)
        self._last_target: Optional[float] = None
        self._last_vib_target: Optional[float] = None
        self._started = False
        self._scheduling = False
        self.trial: Optional[int] = None
        self.block = ""
        self.start_phase_deg = math.nan
        self._trial_start = math.nan
        self._press: Optional[float] = None
        self._press_wall = math.nan
        self._dial_at_press: Tuple[float, float] = (math.nan, math.nan)
        self._n_moves = 0
        #: Tones of the current trial: ``real``, ``predicted``, ``skipped``.
        self.counts = {"real": 0, "predicted": 0, "skipped": 0}

    # -- markers ---------------------------------------------------------------

    def mark(self, kind: str, stamp: float = 0.0, **fields: Any) -> None:
        """Push one JSON marker ``{"kind": kind, ...}``.

        ``stamp`` is its LSL time; 0 means now. Public so the task can push
        the ``confidence`` marker through the same outlet.
        """
        self._push(kind, stamp, fields)

    def _push(self, kind: str, stamp: float, fields: Dict[str, Any]) -> None:
        if self.outlet is None:
            return
        payload = _json_safe({"kind": kind, **fields})
        self.outlet.push_sample([json.dumps(payload)], stamp)

    # -- the dial --------------------------------------------------------------

    @property
    def _period(self) -> Optional[float]:
        period = self.source.period
        if period is not None:
            self._known_period = period
        return self._known_period

    @property
    def phase_deg(self) -> float:
        """The dial as a phase, degrees in [0, 360); NaN in absolute mode
        while no period is known."""
        if self.mode == "relative":
            return self._phase
        period = self._period
        if period is None:
            return math.nan
        return (self._delay_ms / (period * 1000.0) * 360.0) % 360.0

    @property
    def delay_ms(self) -> float:
        """The dial as ms after the R-wave; NaN in relative mode while no
        period is known."""
        if self.mode == "absolute":
            return self._delay_ms
        period = self._period
        if period is None:
            return math.nan
        return self._phase / 360.0 * period * 1000.0

    def _set_phase(self, phase_deg: float) -> None:
        phase_deg = float(phase_deg) % 360.0
        if self.mode == "relative":
            self._phase = phase_deg
        else:
            period = self._period or DEFAULT_PERIOD
            self._delay_ms = phase_deg / 360.0 * period * 1000.0

    def nudge(self, notches: float, gain_deg: float, gain_ms: float) -> None:
        """Turn the dial by ``notches`` (negative turns back).

        Relative mode moves ``notches * gain_deg`` degrees, wrapping at 360;
        absolute mode ``notches * gain_ms`` ms, wrapping at the anticipated
        period.
        """
        if not notches:
            return
        if self.mode == "relative":
            self._phase = (self._phase + notches * gain_deg) % 360.0
        else:
            period_ms = (self._period or DEFAULT_PERIOD) * 1000.0
            self._delay_ms = (self._delay_ms + notches * gain_ms) % period_ms
        self._n_moves += 1
        self.mark(
            "dial",
            trial=self.trial,
            notches=notches,
            phase_deg=self.phase_deg,
            delay_ms=self.delay_ms,
        )

    # -- trials ----------------------------------------------------------------

    def start_trial(self, trial: int, start_phase_deg: float, block: str = "") -> None:
        """Set the dial to ``start_phase_deg`` and start playing tones.

        Beats that arrived since the last poll (e.g. during the confidence
        rating) are logged but get no tone. ``block`` (``"practice"`` or
        ``"main"``) only labels the tone rows and markers.
        """
        if not self._started:
            self.source.start()
            self._started = True
        self._scheduling = False
        self.poll()  # catch up, without tones
        self.trial = trial
        self.block = block
        self.start_phase_deg = float(start_phase_deg)
        self._set_phase(start_phase_deg)
        self._n_moves = 0
        self._press = None
        self._press_wall = math.nan
        self._dial_at_press = (math.nan, math.nan)
        self.counts = {"real": 0, "predicted": 0, "skipped": 0}
        self._trial_start = self.clock()
        self._scheduling = True
        self.mark(
            "trial_start",
            self._trial_start,
            trial=trial,
            block=block,
            mode=self.mode,
            extero=self.extero,
            start_phase_deg=self.start_phase_deg,
            phase_deg=self.phase_deg,
            delay_ms=self.delay_ms,
        )

    def poll(self) -> None:
        """Pull new beats, schedule their tones, collect onsets. Call every frame."""
        beats = self.source.poll()
        for beat in beats:
            self._on_beat(beat, self.clock())
        for handle, onset in self.player.poll_onsets():
            self._on_onset(handle, onset)

    def stop_tones(self) -> None:
        """The press: no more tones are scheduled. Those already scheduled play."""
        if self._press is not None:
            return
        self._press = self.clock()
        self._press_wall = time.time()
        self._scheduling = False
        self._dial_at_press = (self.phase_deg, self.delay_ms)
        self.mark(
            "press",
            self._press,
            trial=self.trial,
            phase_deg=self._dial_at_press[0],
            delay_ms=self._dial_at_press[1],
        )

    def end_trial(self) -> dict:
        """The trial's row of ``final.txt`` (all but the confidence columns).

        Calls :meth:`stop_tones` if that has not been done, then keeps
        polling until the R-wave after the press has arrived (at most
        :data:`NEXT_BEAT_TIMEOUT` s after the press) and every tone scheduled
        has reported its onset, so the tone rows are complete on return.

        ``ChosenDelayMs`` and ``ChosenPhaseDeg`` are the dial at the press,
        converted with the anticipated period of the last beat before it
        (``AnticipatedPeriodMs``); in absolute mode the delay is clamped to
        that period, as it would have been for the next tone.
        ``ObservedPeriodMs`` is the RR interval containing the press.
        """
        self.stop_tones()
        assert self._press is not None
        press = self._press
        beat_deadline = press + NEXT_BEAT_TIMEOUT
        tone_deadline = self._tone_deadline()
        while True:
            self.poll()
            now = self.clock()
            have_next = self._next_beat_after(press) is not None
            tones_done = not self._waiting
            if (have_next or now > beat_deadline) and (
                tones_done or now > tone_deadline
            ):
                break
            time.sleep(0.002)

        last = self._last_beat_before(press)
        nxt = self._next_beat_after(press)
        last_r = last.r_time if last is not None else math.nan
        anticipated = (
            last.period if last is not None and last.period is not None else None
        )
        if anticipated is None:
            anticipated = self._period
        observed = (
            (nxt.r_time - last_r) * 1000.0
            if nxt is not None and last is not None
            else math.nan
        )
        phase, delay = self._dial_at_press
        if anticipated is not None:
            period_ms = anticipated * 1000.0
            if self.mode == "relative":
                delay = phase / 360.0 * period_ms
            else:
                delay = min(self._delay_ms, period_ms)
                phase = delay / period_ms * 360.0 % 360.0
        row = {
            "Trial": self.trial,
            "Block": self.block,
            "Mode": self.mode,
            "Extero": self.extero,
            "StartPhaseDeg": self.start_phase_deg,
            "ChosenPhaseDeg": phase,
            "ChosenDelayMs": delay,
            "AnticipatedPeriodMs": (
                anticipated * 1000.0 if anticipated is not None else math.nan
            ),
            "ObservedPeriodMs": observed,
            "LastRTime": last_r,
            "PressTime": press,
            "WallTime": self._press_wall,
            "nTonesReal": self.counts["real"],
            "nTonesPredicted": self.counts["predicted"],
            "nTonesSkipped": self.counts["skipped"],
            "TrialDuration": press - self._trial_start,
            "nDialMoves": self._n_moves,
        }
        self._push("trial_end", 0.0, row)
        return row

    @property
    def tones(self) -> List[dict]:
        """Every tone and vibration scheduled so far, as ``tones.txt`` rows."""
        return self._tones

    def close(self) -> None:
        """Stop the source and release the audio device."""
        self._scheduling = False
        try:
            self.source.stop()
        finally:
            close = getattr(self.player, "close", None)
            if close is not None:
                close()

    # -- internals -------------------------------------------------------------

    def _delay_for(self, period: float) -> Tuple[float, float, float]:
        """(delay s, phase deg, delay ms) of the dial for a beat of ``period``."""
        if self.mode == "relative":
            delay = self._phase / 360.0 * period
            return delay, self._phase, delay * 1000.0
        delay = min(self._delay_ms / 1000.0, period)
        return delay, delay / period * 360.0 % 360.0, delay * 1000.0

    def _on_beat(self, beat: Beat, now: float) -> None:
        previous = self._beats[-1] if self._beats else None
        rr = beat.r_time - previous.r_time if previous is not None else None
        self._beats.append(beat)
        if beat.period is not None:
            self._known_period = beat.period
        self.mark(
            "beat",
            now,
            trial=self.trial,
            r_time=beat.r_time,
            rr=rr,
            period=beat.period,
        )
        if not self._scheduling or beat.period is None:
            return
        if self.extero:
            target = beat.r_time - self.latency_bias
            if target - now >= self.audio_lead:
                self._schedule(beat, target, "virtual", "vibration", 0.0, 0.0, now)
            else:
                self.mark(
                    "tone_skipped",
                    trial=self.trial,
                    sound="vibration",
                    r_time=beat.r_time,
                    target=target,
                    reason="late",
                )
        delay, phase, delay_ms = self._delay_for(beat.period)
        target = beat.r_time + delay - self.latency_bias
        anchor = "real"
        if target - now < self.audio_lead:
            target += beat.period
            anchor = "predicted"
        reason = None
        if target - now < self.audio_lead:
            reason = "late"
        elif (
            self._last_target is not None
            and target - self._last_target < self.min_tone_gap
        ):
            reason = "gap"
        if reason is not None:
            self.counts["skipped"] += 1
            self.mark(
                "tone_skipped",
                trial=self.trial,
                sound="tone",
                r_time=beat.r_time,
                period=beat.period,
                phase_deg=phase,
                target=target,
                anchor=anchor,
                reason=reason,
            )
            return
        self._last_target = target
        self.counts[anchor] += 1
        self._schedule(beat, target, anchor, "tone", phase, delay_ms, now)

    def _schedule(
        self,
        beat: Beat,
        target: float,
        anchor: str,
        kind: str,
        phase: float,
        delay_ms: float,
        now: float,
    ) -> None:
        handle = self.player.schedule(target, kind)
        row = {
            "Trial": self.trial,
            "Block": self.block,
            "RTime": beat.r_time,
            "PeriodS": beat.period,
            "PhaseDeg": phase,
            "DelayMs": delay_ms,
            "Target": target,
            "Anchor": anchor,
            "Onset": math.nan,
            "Kind": kind,
        }
        self._tones.append(row)
        self._waiting[handle] = row
        self.mark(
            "tone_scheduled",
            now,
            trial=self.trial,
            sound=kind,
            r_time=beat.r_time,
            period=beat.period,
            phase_deg=phase,
            delay_ms=delay_ms,
            target=target,
            anchor=anchor,
            lead=target - now,
        )

    def _on_onset(self, handle: int, onset: float) -> None:
        row = self._waiting.pop(handle, None)
        if row is None:
            return
        row["Onset"] = onset
        self.mark(
            "tone_onset",
            onset if math.isfinite(onset) else 0.0,
            trial=row["Trial"],
            sound=row["Kind"],
            target=row["Target"],
            onset=onset,
            phase_deg=row["PhaseDeg"],
            anchor=row["Anchor"],
        )

    def _tone_deadline(self) -> float:
        """When every tone waiting for its onset should have reported it."""
        if not self._waiting:
            return -math.inf
        latest = max(row["Target"] for row in self._waiting.values())
        return min(latest + 0.5, self.clock() + NEXT_BEAT_TIMEOUT)

    def _last_beat_before(self, t: float) -> Optional[Beat]:
        for beat in reversed(self._beats):
            if beat.r_time <= t:
                return beat
        return None

    def _next_beat_after(self, t: float) -> Optional[Beat]:
        found = None
        for beat in reversed(self._beats):
            if beat.r_time > t:
                found = beat
            else:
                break
        return found
