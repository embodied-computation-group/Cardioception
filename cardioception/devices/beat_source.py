# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Where the heart beats come from, for tasks that time stimuli on them.

- :class:`LSLBeatSource` finds R peaks online in an ECG arriving over LSL
  (an :class:`~cardioception.devices.LSLRecorder`'s inlet), with
  :class:`~cardioception.devices._online_beats.OnlineRDetector`;
- :class:`VirtualBeatSource` makes up a heart (fixed, simulated or replayed
  periods), for control tasks with an external "heartbeat".

Both satisfy the :class:`BeatSource` protocol and report :class:`Beat`
records on the LSL clock (``pylsl.local_clock``). This module imports neither
pylsl nor PsychToolbox at import time.
"""

import time
from collections import deque
from typing import (
    Any,
    Callable,
    Deque,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Union,
    runtime_checkable,
)

import numpy as np

#: An RR interval longer than this (seconds) is taken for a gap in the
#: signal, not a heartbeat: the anticipated period starts again from scratch.
MAX_RR = 2.0

#: RR intervals averaged into the anticipated period.
PERIOD_BEATS = 3

#: Period, in seconds, assumed before one is known.
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


class Beat(NamedTuple):
    """One heartbeat, real or virtual."""

    #: Time of the R peak, LSL seconds.
    r_time: float
    #: Anticipated period at this beat, seconds; ``None`` until known.
    period: Optional[float]
    #: When the beat became known, LSL seconds: the timestamp of the sample
    #: the detector committed on (for a virtual beat, when it was released).
    #: ``None`` if the source does not say.
    commit_time: Optional[float] = None


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
                i = min(max(found.commit_index - self.n_samples, 0), len(stamps) - 1)
                self._on_beat(found.r_time, found.rr, float(stamps[i]))
            self.n_samples += len(stamps)
            self.last_sample_time = float(stamps[-1])
            if len(stamps) < PULL_CHUNK:
                return
            timeout = 0.0

    def _on_beat(
        self, r_time: float, rr: Optional[float], commit_time: Optional[float] = None
    ) -> None:
        if rr is None or rr > MAX_RR:
            self._rr.clear()
        else:
            self._rr.append(rr)
        self.last_r_time = r_time
        self._pending.append(Beat(r_time, self.period, commit_time))


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
            beat = Beat(self._next_r, self._next_period, now)
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
