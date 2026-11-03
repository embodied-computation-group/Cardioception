# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""One trial's stimulus: a train of tones, each a set delay after its own R-wave.

:class:`TrainScheduler` watches a beat source and, for each new beat, schedules
a tone on the audio device at the R-wave time plus the trial's delay. It codes
against two small protocols, :class:`BeatSource` and :class:`TonePlayer`, which
the LSL beat source and the PsychPortAudio tone player of the PAT task satisfy
unchanged, and which tests satisfy with fakes.

Units: every time here is seconds on the beat source's clock (LSL
``local_clock`` in a real session), and the clock passed to the scheduler must
be the same one. A requested delay is in engine units, ms on the absolute axis
and a fraction of the anticipated interbeat interval on the phase axis; only
:attr:`TrainResult.realized_corrected` is given back in engine units, ready for
:meth:`~cardioception.HSD.psi.SynchronyPsi.update`.

The rules, per beat:

- The target is ``r_time + delay`` (absolute) or ``r_time + fraction * period``
  (phase), where ``period`` is the source's anticipated interbeat interval at
  that beat.
- If the target is less than ``audio_lead`` away, the tone cannot be scheduled
  in time. The beat is skipped and counted. It is never re-anchored on the
  predicted next beat, because that adds the error of the RR prediction to the
  delay.
- If the delay is more than ``max_fraction`` of the period, the tone would land
  near the next R-wave. The train is aborted, so that the task can draw a
  delay with a tighter ceiling. A beat that carries no anticipated period is
  checked against the observed RR interval instead; with neither, it is
  skipped as ``"no_period"``.
- A tone the device reports no onset for (NaN) does not count: another beat
  is tried in its place.

The train ends when ``n_tones`` tones have played, after ``max_beats`` beats,
or at the deadline. The deadline is ``timeout_s``, or, when the period is
known at the start, long enough for ``max_beats + 1`` beats plus the delay if
that is later, so that a slow heart is not taken for a timeout.
"""

import math
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    runtime_checkable,
)

from ._constants import AUDIO_LEAD, AXES, MAX_PERIOD_FRACTION, N_TONES

#: Seconds of float error forgiven in the floor and ceiling checks, so that a
#: delay drawn exactly on a bound is not refused by rounding.
TOLERANCE = 1e-9

# -- protocols -----------------------------------------------------------------


class BeatEvent(Protocol):
    """One detected heartbeat: anything with these two attributes."""

    @property
    def r_time(self) -> float:
        """Time of the R peak, seconds on the source clock."""

    @property
    def period(self) -> Optional[float]:
        """Anticipated interbeat interval at this beat, seconds, or ``None``."""


@runtime_checkable
class BeatSource(Protocol):
    """Anything that reports heartbeats as they are detected."""

    def start(self) -> None:
        """Begin delivering beats. Does nothing if already started."""

    def poll(self) -> Sequence[BeatEvent]:
        """Beats detected since the last call. Never blocks."""

    def stop(self) -> None:
        """Stop delivering beats."""

    @property
    def period(self) -> Optional[float]:
        """Anticipated interbeat interval in seconds, ``None`` until known."""


@runtime_checkable
class TonePlayer(Protocol):
    """Anything that plays a sound at a given clock time."""

    def schedule(self, when: float, kind: str = "tone") -> int:
        """Play ``kind`` at ``when`` (clock seconds). Returns a handle."""

    def poll_onsets(self) -> List[Tuple[int, float]]:
        """``(handle, onset)`` of sounds finished since the last call.

        ``onset`` is NaN when the device reported none.
        """

    @property
    def busy(self) -> bool:
        """Whether any sound is waiting or playing."""

    def stop_all(self) -> None:
        """Stop everything; the onsets of stopped sounds are still reported."""

    def close(self) -> None:
        """Release the device."""


class Clock(Protocol):
    """A callable returning the current time in seconds."""

    def __call__(self) -> float:
        """Seconds, on the same clock as the beat source."""


#: ``marker(kind, stamp, **fields)`` pushes one JSON marker. ``stamp`` is the
#: clock time it refers to (0.0 for "now").
Marker = Callable[..., Any]


# -- results -------------------------------------------------------------------


@dataclass
class ToneRecord:
    """One beat the train tried to put a tone on. Times in seconds."""

    #: Position in the train, counting skipped beats.
    index: int
    #: The R-wave the tone is locked to.
    r_time: float
    #: Anticipated interbeat interval at that beat, or ``None``.
    period: Optional[float]
    #: When the tone was due, or ``None`` if no target could be computed.
    target: Optional[float]
    #: When the device reported the tone started, ``None`` if it did not play.
    onset: Optional[float] = None
    #: ``onset - r_time``.
    realized: Optional[float] = None
    #: ``realized`` as a fraction of the observed interbeat interval, to the
    #: next beat seen during the train. ``None`` when that beat was not seen,
    #: which is usual for the last tone: the train ends before it arrives.
    realized_fraction: Optional[float] = None
    #: True for a beat that got no tone.
    skipped: bool = False
    #: Why it was skipped: ``"late"``, ``"no_period"`` or ``"no_onset"``.
    reason: Optional[str] = None
    #: Seconds between scheduling and the target.
    lead: Optional[float] = None
    #: The player's handle for the tone.
    handle: Optional[int] = None


@dataclass
class TrainResult:
    """What one train delivered."""

    #: The delay asked for, in engine units (ms, or fraction of the period).
    delay: float
    axis: str
    tones: List[ToneRecord] = field(default_factory=list)
    n_delivered: int = 0
    n_skipped: int = 0
    aborted: bool = False
    #: ``"ceiling"``, ``"floor"``, ``"no_period"`` or ``"timeout"``.
    abort_reason: Optional[str] = None
    #: Why the train ended: ``"complete"``, ``"max_beats"``, or the abort
    #: reason.
    end_reason: Optional[str] = None
    #: Mean realized delay over the delivered tones, in seconds (absolute), or
    #: the mean ``realized_fraction`` over the tones whose next beat was seen
    #: (phase). ``None`` if there is nothing to average.
    realized_mean: Optional[float] = None
    #: Mean realized delay plus the bridge lag, in engine units: ms (absolute)
    #: or a fraction of the mean anticipated period of the delivered tones
    #: (phase). This is the value to update the engine with. On the phase axis
    #: it is not ``realized_mean`` plus the lag: one is relative to the
    #: observed interbeat interval, the other to the anticipated one.
    realized_corrected: Optional[float] = None
    #: Clock times the train started and ended.
    started: Optional[float] = None
    ended: Optional[float] = None
    #: Every beat polled during the train: ``r_time``, ``period``, ``seen``
    #: (clock time it was polled) and ``status`` (``"tone"``, ``"skipped"``,
    #: ``"stale"`` for an R-wave before the train started, ``"extra"`` for one
    #: after the train had what it needed).
    beats_seen: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def delivered(self) -> List[ToneRecord]:
        """The tones that played."""
        return [t for t in self.tones if not t.skipped and t.realized is not None]


# -- the scheduler -------------------------------------------------------------


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values))


class TrainScheduler:
    """Play a train of tones locked to successive R-waves.

    Parameters
    ----------
    source :
        A :class:`BeatSource`, kept running across trials by the caller.
    player :
        A :class:`TonePlayer`.
    clock :
        Returns seconds on the source's clock.
    n_tones :
        Tones per train.
    audio_lead :
        Seconds a tone must be scheduled ahead of its target.
    bridge_lag :
        Seconds by which the stamped R-wave trails the true one, added to the
        realized delay before it is handed to the engine.
    marker :
        Optional ``marker(kind, stamp, **fields)`` for the JSON marker stream.
        Kinds are ``beat``, ``tone_scheduled``, ``tone_onset`` and
        ``tone_skipped``. Bind the trial number into it if the stream needs
        one.
    on_frame :
        Optional callable run once after each loop pass that scheduled a tone,
        such as a ``win.flip`` wrapper. Called at most once per tone, so the
        loop is not tied to the screen refresh.
    """

    def __init__(
        self,
        source: BeatSource,
        player: TonePlayer,
        clock: Clock,
        n_tones: int = N_TONES,
        audio_lead: float = AUDIO_LEAD,
        bridge_lag: float = 0.0,
        marker: Optional[Marker] = None,
        on_frame: Optional[Callable[[], Any]] = None,
    ):
        if n_tones < 1:
            raise ValueError("n_tones should be at least 1")
        if audio_lead < 0:
            raise ValueError("audio_lead should not be negative")
        self.source = source
        self.player = player
        self.clock = clock
        self.n_tones = int(n_tones)
        self.audio_lead = float(audio_lead)
        self.bridge_lag = float(bridge_lag)
        self.marker = marker
        self.on_frame = on_frame
        # Kept across trains so the first beat of a train still has an RR.
        self._last_r: Optional[float] = None

    def _mark(self, kind: str, stamp: float, **fields: Any) -> None:
        if self.marker is not None:
            self.marker(kind, stamp, **fields)

    def run(
        self,
        delay: float,
        axis: str,
        min_delay_s: float,
        max_fraction: float = MAX_PERIOD_FRACTION,
        timeout_s: float = 10.0,
        max_beats: Optional[int] = None,
    ) -> TrainResult:
        """Play one train and report what was delivered.

        Parameters
        ----------
        delay :
            In engine units: ms after the R-wave (absolute axis) or a fraction
            of the anticipated period (phase axis).
        axis :
            ``"absolute"`` or ``"phase"``.
        min_delay_s :
            Shortest delay allowed, in seconds. A request below it is refused
            with ``abort_reason="floor"``.
        max_fraction :
            Longest delay allowed, as a fraction of the period at each beat.
        timeout_s :
            Seconds after which the train is aborted with ``"timeout"``. When
            the period is known at the start, the deadline is at least
            ``(max_beats + 1) * period + delay``.
        max_beats :
            Beats to try before giving up on the rest of the train; defaults
            to ``n_tones + 3``.
        """
        if axis not in AXES:
            raise ValueError(f"axis should be one of {AXES}, got {axis!r}")
        if max_beats is None:
            max_beats = self.n_tones + 3
        self.source.start()
        started = self.clock()
        result = TrainResult(delay=float(delay), axis=axis, started=started)

        # Requests that cannot be met whatever the beats do.
        refused: Optional[str] = None
        if axis == "absolute":
            if delay / 1000.0 < min_delay_s - TOLERANCE:
                refused = "floor"
        else:
            period = self.source.period
            if period is None:
                refused = "no_period"
            elif delay > max_fraction + TOLERANCE:
                refused = "ceiling"
            elif delay * period < min_delay_s - TOLERANCE:
                refused = "floor"
        if refused is not None:
            return self._finish(result, {}, refused, aborted=True)

        # Long enough for every beat the train may use at the current rate.
        start_period = self.source.period
        allowed = timeout_s
        if start_period is not None:
            if axis == "absolute":
                start_delay_s = delay / 1000.0
            else:
                start_delay_s = delay * start_period
            allowed = max(timeout_s, (max_beats + 1) * start_period + start_delay_s)
        deadline = started + allowed

        pending: Dict[int, ToneRecord] = {}
        n_beats = 0  # beats that counted towards the train
        n_scheduled = 0  # tones played or still waiting to
        abort: Optional[str] = None

        while True:
            scheduled_now = False
            for beat in self.source.poll():
                now = self.clock()
                period = beat.period if beat.period is not None else self.source.period
                rr = beat.r_time - self._last_r if self._last_r is not None else None
                self._last_r = beat.r_time
                seen: Dict[str, Any] = {
                    "r_time": beat.r_time,
                    "period": period,
                    "seen": now,
                    "status": "extra",
                }
                result.beats_seen.append(seen)
                self._mark("beat", now, r_time=beat.r_time, rr=rr, period=period)

                if beat.r_time < started:
                    seen["status"] = "stale"
                    continue
                if abort is not None or n_scheduled >= self.n_tones:
                    continue
                if n_beats >= max_beats:
                    continue
                n_beats += 1

                record = ToneRecord(
                    index=len(result.tones),
                    r_time=beat.r_time,
                    period=period,
                    target=None,
                )
                # The interval the tone must stay clear of: the anticipated
                # period, or, without one, the RR interval just observed.
                ceiling_period = period if period is not None else rr
                if ceiling_period is None or (axis == "phase" and period is None):
                    self._skip(result, record, seen, now, "no_period")
                    continue
                if axis == "absolute":
                    delay_s = delay / 1000.0
                else:
                    assert period is not None
                    delay_s = delay * period
                if delay_s > max_fraction * ceiling_period + TOLERANCE:
                    abort = "ceiling"
                    continue

                record.target = beat.r_time + delay_s
                record.lead = record.target - now
                if record.lead < self.audio_lead:
                    self._skip(result, record, seen, now, "late")
                    continue

                record.handle = self.player.schedule(record.target, "tone")
                result.tones.append(record)
                pending[record.handle] = record
                seen["status"] = "tone"
                n_scheduled += 1
                scheduled_now = True
                self._mark(
                    "tone_scheduled",
                    now,
                    index=record.index,
                    r_time=record.r_time,
                    period=period,
                    target=record.target,
                    anchor="r",
                    lead=record.lead,
                    delay_ms=delay_s * 1000.0,
                    fraction=delay_s / period if period else None,
                )

            # A tone with no onset did not play: free its place in the train.
            n_scheduled -= self._collect(pending)
            if scheduled_now and self.on_frame is not None:
                self.on_frame()

            if abort is not None:
                break
            if not pending and (n_scheduled >= self.n_tones or n_beats >= max_beats):
                break
            if self.clock() >= deadline:
                abort = "timeout"
                break

        if abort is not None:
            return self._finish(result, pending, abort, aborted=True)
        return self._finish(result, pending, None, aborted=False)

    # -- internals -------------------------------------------------------------

    def _skip(
        self,
        result: TrainResult,
        record: ToneRecord,
        seen: Dict[str, Any],
        now: float,
        reason: str,
    ) -> None:
        record.skipped = True
        record.reason = reason
        result.tones.append(record)
        seen["status"] = "skipped"
        self._mark(
            "tone_skipped",
            now,
            index=record.index,
            r_time=record.r_time,
            period=record.period,
            target=record.target,
            anchor="r",
            reason=reason,
        )

    def _collect(self, pending: Dict[int, ToneRecord]) -> int:
        """Take the onsets reported for tones of this train.

        Returns how many of them came back without an onset.
        """
        failed = 0
        for handle, onset in self.player.poll_onsets():
            record = pending.pop(handle, None)
            if record is None:
                continue  # a tone of an earlier train
            if onset is None or not math.isfinite(onset):
                record.skipped = True
                record.reason = "no_onset"
                failed += 1
            else:
                record.onset = float(onset)
                record.realized = record.onset - record.r_time
            self._mark(
                "tone_onset",
                record.onset if record.onset is not None else 0.0,
                index=record.index,
                r_time=record.r_time,
                target=record.target,
                onset=record.onset,
                anchor="r",
                realized=record.realized,
            )
        return failed

    def _finish(
        self,
        result: TrainResult,
        pending: Dict[int, ToneRecord],
        reason: Optional[str],
        aborted: bool,
    ) -> TrainResult:
        """Stop what is still waiting, then fill in the summary values.

        ``reason`` is the abort reason. For a train that was not aborted it is
        ``None``, and the end reason follows from how many tones played.
        """
        if pending:
            self.player.stop_all()
            self._collect(pending)
            for record in pending.values():
                record.skipped = True
                record.reason = "no_onset"
            pending.clear()

        delivered = result.delivered
        result.n_delivered = len(delivered)
        result.n_skipped = sum(t.skipped for t in result.tones)
        if not aborted:
            complete = result.n_delivered >= self.n_tones
            reason = "complete" if complete else "max_beats"
        result.aborted = aborted
        result.abort_reason = reason if aborted else None
        result.end_reason = reason

        r_times = sorted(b["r_time"] for b in result.beats_seen)
        for record in delivered:
            following = [r for r in r_times if r > record.r_time]
            if following and record.realized is not None:
                interval = following[0] - record.r_time
                record.realized_fraction = record.realized / interval

        if delivered:
            realized = _mean([t.realized for t in delivered if t.realized is not None])
            corrected = realized + self.bridge_lag
            if result.axis == "absolute":
                result.realized_mean = realized
                result.realized_corrected = corrected * 1000.0
            else:
                # Every phase-axis tone had a period: it was needed to time it.
                fractions = [
                    t.realized_fraction
                    for t in delivered
                    if t.realized_fraction is not None
                ]
                periods = [t.period for t in delivered if t.period]
                if fractions:
                    result.realized_mean = _mean(fractions)
                if len(periods) == len(delivered):
                    result.realized_corrected = corrected / _mean(periods)
        result.ended = self.clock()
        return result
