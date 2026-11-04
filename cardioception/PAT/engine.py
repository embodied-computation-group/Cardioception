# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
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

The beat sources and the player are in :mod:`cardioception.devices.beat_source`
and :mod:`cardioception.devices.tone_player`, shared with other tasks, and
re-exported here. This module imports no PsychoPy. ``pylsl`` and ``psychtoolbox`` are imported
inside the classes that need them, so it imports on a machine with neither.
"""

import json
import math
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

# The beat sources and the player live in ``cardioception.devices``, shared
# with other tasks; re-exported here so ``cardioception.PAT.engine`` keeps
# offering them.
from cardioception.devices.beat_source import (  # noqa: F401
    DEFAULT_PERIOD,
    MAX_RR,
    PERIOD_BEATS,
    Beat,
    BeatSource,
    Clock,
    LSLBeatSource,
    VirtualBeatSource,
    default_clock,
    simulated_periods,
)
from cardioception.devices.tone_player import (  # noqa: F401
    KINDS,
    TonePlayer,
    make_tone,
    ptb_minus_clock,
)

__all__ = [
    "MODES",
    "NEXT_BEAT_TIMEOUT",
    "STALE_PERIODS",
    "TRIAL_STATUSES",
    "DEFAULT_PERIOD",
    "MAX_RR",
    "PERIOD_BEATS",
    "KINDS",
    "Beat",
    "BeatSource",
    "Clock",
    "LSLBeatSource",
    "VirtualBeatSource",
    "TonePlayer",
    "PhaseEngine",
    "default_clock",
    "simulated_periods",
    "make_tone",
    "ptb_minus_clock",
]

#: Scheduling modes of :class:`PhaseEngine`.
MODES = ("relative", "absolute")

#: Seconds :meth:`PhaseEngine.end_trial` waits for the R after the press.
NEXT_BEAT_TIMEOUT = 3.0

#: A press more than this many anticipated periods after the last R-wave is
#: ``stale``: the ECG was lost, and the period on the row would be old.
STALE_PERIODS = 1.5

#: Values of ``TrialStatus`` on a trial row. ``ok``: the press came while beats
#: were arriving. ``stale``: the last R-wave before the press is more than
#: :data:`STALE_PERIODS` anticipated periods old. ``timeout``: the trial ended
#: with no press (see ``maxTrialTime`` in the task).
TRIAL_STATUSES = ("ok", "stale", "timeout")

#: How a trial stops: the participant's press, or the task's time limit.
STOP_REASONS = ("press", "timeout")


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
        self._stop_reason = "press"
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
        self.idle_poll()  # catch up, without tones
        self.trial = trial
        self.block = block
        self.start_phase_deg = float(start_phase_deg)
        self._set_phase(start_phase_deg)
        self._n_moves = 0
        self._press = None
        self._press_wall = math.nan
        self._stop_reason = "press"
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
        """Pull new beats, schedule their tones, collect onsets. Call every frame.

        Outside a trial (before :meth:`start_trial`, after :meth:`stop_tones`)
        it schedules nothing, like :meth:`idle_poll`.
        """
        self._poll(schedule=True)

    def idle_poll(self) -> None:
        """Pull and detect beats, push their markers, collect onsets; no tones.

        Cheap; call it every frame of the screens between trials (confidence
        rating, breaks, instructions), so beats are detected as they come
        rather than in a burst at the next :meth:`start_trial`, and the
        detector's period stays current.
        """
        self._poll(schedule=False)

    def _poll(self, schedule: bool) -> None:
        if not self._started:
            self.source.start()
            self._started = True
        scheduling = self._scheduling
        self._scheduling = scheduling and schedule
        try:
            for beat in self.source.poll():
                self._on_beat(beat, self.clock())
            for handle, onset in self.player.poll_onsets():
                self._on_onset(handle, onset)
        finally:
            self._scheduling = scheduling

    def stop_tones(self, reason: str = "press") -> None:
        """The trial stops: no more tones are scheduled. Those already
        scheduled play.

        ``reason`` is ``"press"`` (the participant locked in a choice) or
        ``"timeout"`` (the task's time limit ran out, with no choice), and is
        the kind of the marker pushed. Only the first call of a trial counts.
        """
        if reason not in STOP_REASONS:
            raise ValueError(f"reason should be one of {STOP_REASONS}, got {reason!r}")
        if self._press is not None:
            return
        self._press = self.clock()
        self._press_wall = time.time()
        self._stop_reason = reason
        self._scheduling = False
        self._dial_at_press = (self.phase_deg, self.delay_ms)
        self.mark(
            reason,
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

        The ``LastTone*`` columns describe the last tone of the trial whose
        target came before the press, the tone the participant was matching:
        its ``ToneIndex`` in :attr:`tones`, its ``Anchor``, the R-wave it was
        timed from (``LastToneRTime``) and ``LastToneDelayMs``, the delay it
        was actually played at after the R-wave of its own cycle, with the
        latency bias added back so it reads like ``ChosenDelayMs``. For a
        ``real`` tone that R-wave is the one it was timed from and the delay is
        the dial's. A ``predicted`` tone was timed from the R-wave before, one
        anticipated period ahead, so its delay is measured from the next R-wave
        and differs from the dial's by the error of that prediction; NaN if
        that R-wave never came.

        ``TrialStatus`` (see :data:`TRIAL_STATUSES`) is ``timeout`` when the
        trial was stopped with ``stop_tones("timeout")``, and both chosen
        columns are then NaN. It is ``stale`` when no R-wave came within
        :data:`STALE_PERIODS` anticipated periods before the press: the
        anticipated period is then NaN, and so is whichever chosen column
        needs it (the delay in relative mode, the phase in absolute mode).
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
        stale = (
            last is None
            or anticipated is None
            or press - last_r > STALE_PERIODS * anticipated
        )
        if stale:
            anticipated = None
        phase, delay = self._dial_at_press
        if anticipated is not None:
            period_ms = anticipated * 1000.0
            if self.mode == "relative":
                delay = phase / 360.0 * period_ms
            else:
                delay = min(self._delay_ms, period_ms)
                phase = delay / period_ms * 360.0 % 360.0
        elif self.mode == "relative":
            delay = math.nan
        else:
            phase = math.nan
        status = "stale" if stale else "ok"
        if self._stop_reason == "timeout":
            status = "timeout"
            phase = delay = math.nan
        row = {
            "Trial": self.trial,
            "Block": self.block,
            "TrialStatus": status,
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
            **self._last_tone(press),
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
        """Every tone and vibration scheduled so far, as ``tones.txt`` rows.

        ``ToneIndex`` numbers them from 1 in the order they were scheduled,
        across trials; ``LastToneIndex`` on a trial row refers to it.
        """
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
        # Stamped when the beat became known, not when it was pulled: a beat
        # detected late (nobody polled) still carries its own time.
        commit = beat.commit_time if beat.commit_time is not None else now
        self.mark(
            "beat",
            commit,
            trial=self.trial,
            r_time=beat.r_time,
            commit_time=commit,
            seen_time=now,
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

    def _last_tone(self, press: float) -> Dict[str, Any]:
        """The ``LastTone*`` columns of the trial row (see :meth:`end_trial`)."""
        fields: Dict[str, Any] = {
            "LastToneIndex": math.nan,
            "LastToneAnchor": "",
            "LastToneRTime": math.nan,
            "LastToneDelayMs": math.nan,
        }
        tone = None
        for row in reversed(self._tones):
            if row["Trial"] != self.trial:
                break
            if row["Kind"] == "tone" and row["Target"] <= press:
                tone = row
                break
        if tone is None:
            return fields
        r_cycle: Optional[float] = tone["RTime"]
        if tone["Anchor"] == "predicted":
            nxt = self._next_beat_after(tone["RTime"])
            r_cycle = nxt.r_time if nxt is not None else None
        fields.update(
            LastToneIndex=tone["ToneIndex"],
            LastToneAnchor=tone["Anchor"],
            LastToneRTime=tone["RTime"],
        )
        if r_cycle is not None:
            fields["LastToneDelayMs"] = (
                tone["Target"] + self.latency_bias - r_cycle
            ) * 1000.0
        return fields

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
        index = len(self._tones) + 1
        row = {
            "ToneIndex": index,
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
            tone=index,
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
