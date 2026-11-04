# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""One trial's stimulus: a train of tones, each a set delay after its own R-wave.

:class:`TrainScheduler` watches a beat source and, for each new beat, schedules
a tone on the audio device at the R-wave time plus the trial's delay, less the
latency bias. It codes against two small protocols, :class:`BeatSource` and
:class:`TonePlayer`, which the shared
:class:`cardioception.devices.beat_source.LSLBeatSource` and
:class:`cardioception.devices.tone_player.TonePlayer` satisfy unchanged
(``cardioception.HSD.parameters`` checks this statically), and which tests
satisfy with fakes.

Units: every time here is seconds on the beat source's clock (LSL
``local_clock`` in a real session), and the clock passed to the scheduler must
be the same one. A requested delay is in engine units, ms on the absolute axis
and a fraction of the anticipated interbeat interval on the phase axis; only
:attr:`TrainResult.realized_corrected` is given back in engine units, ready for
:meth:`~cardioception.HSD.psi.SynchronyPsi.update`.

The rules, per beat:

- The target is ``r_time + delay - latency_bias`` (absolute) or
  ``r_time + fraction * period - latency_bias`` (phase), where ``period`` is
  the source's anticipated interbeat interval at that beat. ``latency_bias``
  stands for the delays the recordings cannot see, the transport before the
  ECG is stamped and the speaker after the reported onset, so that the
  delay is the one the participant hears. The realized delay measured
  against the stamped R-wave is ``latency_bias`` short of it, and
  :attr:`TrainResult.realized_corrected` adds it back.
- If the target is less than ``audio_lead`` away, the tone cannot be scheduled
  in time. The beat is skipped and counted. It is never re-anchored on the
  predicted next beat, because that adds the error of the RR prediction to the
  delay.
- If the delay is more than ``max_fraction`` of the period, the tone would land
  near the next R-wave. Once a tone of the train has been scheduled, the beat
  is skipped as ``"ceiling"`` and the train goes on, so that a period moved
  by respiratory sinus arrhythmia costs one tone rather than the rest of the
  train. Before any tone, the train is aborted instead, so that the task can
  draw a delay with a tighter ceiling without the participant having heard
  anything. A beat that carries no anticipated period is checked against the
  observed RR interval instead; with neither, it is skipped as
  ``"no_period"``.
- A tone the device reports no onset for (NaN) does not count: another beat
  is tried in its place.

Beats polled outside a train, by whoever keeps the source current between
trials, are passed to :meth:`TrainScheduler.observe`. They then still count
for the RR interval of the next beat, and are kept with the next train's
beats, with status ``"between"``.

Markers follow the field names of the PAT dry run, so
``bench/pat_dryrun_report.py`` can read an HSD recording: every ``beat``
carries ``commit_time`` (when the beat became known: the source's
``commit_time`` when it gives one, else when it was polled) and
``seen_time`` (when it was polled), and the tones carry ``anchor="real"``
(every HSD tone is locked to a detected R-wave), ``phase_deg`` and
``delay_ms``, the intended physical position of the tone after its R-wave.
``tone_scheduled`` also carries ``latency``, the time from the beat becoming
known to the tone being scheduled.

While the train runs, the frame hook (a ``win.flip`` and an Escape check, in
the task) is called every ``frame_interval`` seconds whatever the beats do,
and once more right after each tone is scheduled, when the next beat is
furthest away. An experimenter status line is logged every second, and says
``NO BEATS`` once no beat has come for 1.5 anticipated periods (at least
1 s).

The train ends when ``n_tones`` tones have played, after ``max_beats`` beats
(``2 * n_tones`` by default, so a skipped beat is replaced by a later one),
or at the deadline. The deadline is ``timeout_s``, or, when the period is
known at the start, long enough for ``max_beats + 1`` beats plus the delay if
that is later, so that a slow heart is not taken for a timeout.
"""

import math
import time
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

from .._log import get_logger
from ._constants import AUDIO_LEAD, AXES, LATENCY_BIAS, MAX_PERIOD_FRACTION, N_TONES

logger = get_logger()

#: Seconds of float error forgiven in the floor and ceiling checks, so that a
#: delay drawn exactly on a bound is not refused by rounding.
TOLERANCE = 1e-9

#: Seconds between calls of the frame hook during a train, whatever the beats
#: do, so that the screen keeps flipping and Escape is read with no beat
#: coming in.
FRAME_INTERVAL = 0.05

#: Seconds a loop pass that found nothing to do sleeps, so that waiting for
#: a beat does not pin a core. It adds up to this much to the time a beat is
#: seen, well inside the audio lead, provided the sleep is that short. On
#: Windows with Python 3.10 a sleep lasts the system timer period, 15.6 ms
#: by default; importing ``psychopy.core`` loads PsychToolbox, which sets it
#: to 1 ms (measured: 15.5 ms before the import, 1.04 ms after), and every
#: session imports it.
IDLE_SLEEP = 0.001

#: Seconds between the experimenter's status lines during a train.
STATUS_INTERVAL = 1.0

#: Seconds without a beat after which the status line says ``NO BEATS``, at
#: least. With an anticipated period it is 1.5 periods, if that is longer, so
#: that a slow heart is not reported as lost.
NO_BEAT_WARNING = 1.0

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
    #: When the tone was scheduled to start on the clock (the R-wave plus the
    #: delay, less the latency bias), or ``None`` if no target was computed.
    target: Optional[float]
    #: When the device reported the tone started, ``None`` if it did not play.
    #: The PsychToolbox player reports the start time it scheduled, not the
    #: sound, so this equals ``target`` unless the tone started late.
    onset: Optional[float] = None
    #: ``onset - r_time``, as the recordings show it: ``latency_bias`` short
    #: of the physical delay.
    realized: Optional[float] = None
    #: The physical delay, ``realized + latency_bias``, as a fraction of the
    #: observed interbeat interval, to the next beat seen during the train.
    #: ``None`` when that beat was not seen, which is usual for the last tone:
    #: the train ends before it arrives.
    realized_fraction: Optional[float] = None
    #: True for a beat that got no tone.
    skipped: bool = False
    #: Why it was skipped: ``"late"``, ``"ceiling"``, ``"no_period"`` or
    #: ``"no_onset"``.
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
    #: Mean realized delay over the delivered tones, in seconds, as measured
    #: against the stamped R-wave (absolute); or the mean
    #: ``realized_fraction``, which includes the latency bias, over the tones
    #: whose next beat was seen (phase). ``None`` if there is nothing to
    #: average.
    realized_mean: Optional[float] = None
    #: Mean realized delay plus the latency bias, the physical delay, in
    #: engine units: ms (absolute) or a fraction of the mean anticipated
    #: period of the delivered tones (phase). This is the value to update the
    #: engine with. On the phase axis it differs from ``realized_mean``: one
    #: is relative to the anticipated interbeat interval, the other to the
    #: observed one.
    realized_corrected: Optional[float] = None
    #: Clock times the train started and ended.
    started: Optional[float] = None
    ended: Optional[float] = None
    #: Every beat polled during the train, and before it since the previous
    #: train: ``r_time``, ``period``, ``rr`` (seconds since the beat before,
    #: ``None`` for the first), ``commit_time`` (when the source says the beat
    #: became known, ``None`` if it does not say), ``seen`` (clock time it was
    #: polled) and ``status`` (``"tone"``, ``"skipped"``, ``"between"`` for one polled
    #: between trains through :meth:`TrainScheduler.observe`, ``"stale"`` for
    #: an R-wave before the train started, ``"extra"`` for one after the train
    #: had what it needed).
    beats_seen: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def delivered(self) -> List[ToneRecord]:
        """The tones that played."""
        return [t for t in self.tones if not t.skipped and t.realized is not None]


# -- the scheduler -------------------------------------------------------------


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values))


def _phase_deg(delay_s: Optional[float], period: Optional[float]) -> float:
    """A delay after the R-wave as degrees of the period, NaN without one.

    The intended position of the tone, as the PAT dry run reports it: the
    report compares it with the phase measured against the offline R peaks.
    """
    if delay_s is None or not period:
        return math.nan
    return 360.0 * delay_s / period


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
    latency_bias :
        Seconds of physical delay the recordings cannot see: the transport
        before the ECG is stamped plus the speaker after the reported onset.
        Subtracted from every target and added to the realized delay before
        it is handed to the engine.
    marker :
        Optional ``marker(kind, stamp, **fields)`` for the JSON marker stream.
        Kinds are ``beat``, ``tone_scheduled``, ``tone_onset`` and
        ``tone_skipped``, with the field names of the PAT dry run. Bind the
        trial number into it if the stream needs one.
    on_frame :
        Optional callable, such as a ``win.flip`` wrapper that also checks for
        Escape. Called every ``frame_interval`` seconds during a train,
        whether or not beats arrive, and right after each tone is scheduled.
    frame_interval :
        Seconds between calls of ``on_frame``, at most (give or take one loop
        pass and the hook's own duration).
    sleep :
        Called with :data:`IDLE_SLEEP` on a loop pass that polled no beat and
        did not call ``on_frame``. ``time.sleep`` by default; tests on a fake
        clock pass one that moves that clock.
    """

    def __init__(
        self,
        source: BeatSource,
        player: TonePlayer,
        clock: Clock,
        n_tones: int = N_TONES,
        audio_lead: float = AUDIO_LEAD,
        latency_bias: float = LATENCY_BIAS,
        marker: Optional[Marker] = None,
        on_frame: Optional[Callable[[], Any]] = None,
        frame_interval: float = FRAME_INTERVAL,
        sleep: Callable[[float], Any] = time.sleep,
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
        self.latency_bias = float(latency_bias)
        self.marker = marker
        self.on_frame = on_frame
        self.frame_interval = float(frame_interval)
        self.sleep = sleep
        #: Names the train in the status line, such as ``"trial 3"``.
        self.label = ""
        # Kept across trains so the first beat of a train still has an RR.
        self._last_r: Optional[float] = None
        # Clock time the last beat was polled, for the status line.
        self._last_seen: Optional[float] = None
        # Beats observed since the last train, for the next one's record.
        self._between: List[Dict[str, Any]] = []

    def _mark(self, kind: str, stamp: float, **fields: Any) -> None:
        if self.marker is not None:
            self.marker(kind, stamp, **fields)

    def _see(self, beat: BeatEvent, status: str) -> Dict[str, Any]:
        """Record one polled beat, update the last R-wave and mark it."""
        now = self.clock()
        period = beat.period if beat.period is not None else self.source.period
        rr = beat.r_time - self._last_r if self._last_r is not None else None
        self._last_r = beat.r_time
        self._last_seen = now
        commit = getattr(beat, "commit_time", None)
        seen: Dict[str, Any] = {
            "r_time": beat.r_time,
            "period": period,
            "rr": rr,
            "commit_time": commit,
            "seen": now,
            "status": status,
        }
        # Stamped when the beat became known, not when it was pulled, as the
        # PAT task stamps it; the poll time goes alongside.
        self._mark(
            "beat",
            now,
            r_time=beat.r_time,
            rr=rr,
            period=period,
            commit_time=commit if commit is not None else now,
            seen_time=now,
        )
        return seen

    def observe(self, beats: Sequence[BeatEvent]) -> List[Dict[str, Any]]:
        """Take beats polled from the source outside :meth:`run`.

        Whoever keeps the source current between trains passes what it polls
        here, so that the first beat of the next train has the RR interval to
        the beat before it, and so that no beat is lost from the record. The
        beats are marked, kept with status ``"between"``, and added to the
        ``beats_seen`` of the next train. Returns their records.
        """
        records = [self._see(beat, "between") for beat in beats]
        self._between.extend(records)
        return records

    def take_between(self) -> List[Dict[str, Any]]:
        """Beats observed since the last train that no train has taken yet.

        Clears them. For the end of a session, so the last beats are kept.
        """
        records, self._between = self._between, []
        return records

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
            to ``2 * n_tones``.
        """
        if axis not in AXES:
            raise ValueError(f"axis should be one of {AXES}, got {axis!r}")
        if max_beats is None:
            max_beats = 2 * self.n_tones
        self.source.start()
        started = self.clock()
        result = TrainResult(delay=float(delay), axis=axis, started=started)
        result.beats_seen.extend(self.take_between())

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

        last_frame = started
        next_status = started + STATUS_INTERVAL
        pending: Dict[int, ToneRecord] = {}
        n_beats = 0  # beats that counted towards the train
        n_scheduled = 0  # tones played or still waiting to
        any_scheduled = False  # whether the participant may have heard a tone
        abort: Optional[str] = None

        while True:
            scheduled_now = False
            beats = self.source.poll()
            for beat in beats:
                seen = self._see(beat, "extra")
                now, period, rr = seen["seen"], seen["period"], seen["rr"]
                result.beats_seen.append(seen)

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
                    if not any_scheduled:
                        # Nothing heard yet: let the task draw a shorter delay.
                        abort = "ceiling"
                    else:
                        self._skip(result, record, seen, now, "ceiling")
                    continue

                record.target = beat.r_time + delay_s - self.latency_bias
                record.lead = record.target - now
                if record.lead < self.audio_lead:
                    self._skip(result, record, seen, now, "late")
                    continue

                record.handle = self.player.schedule(record.target, "tone")
                result.tones.append(record)
                pending[record.handle] = record
                seen["status"] = "tone"
                n_scheduled += 1
                any_scheduled = True
                scheduled_now = True
                self._mark(
                    "tone_scheduled",
                    now,
                    index=record.index,
                    r_time=record.r_time,
                    period=period,
                    target=record.target,
                    anchor="real",
                    lead=record.lead,
                    delay_ms=delay_s * 1000.0,
                    phase_deg=_phase_deg(delay_s, period),
                    fraction=delay_s / period if period else None,
                    latency=(
                        now - seen["commit_time"]
                        if seen["commit_time"] is not None
                        else None
                    ),
                )

            # A tone with no onset did not play: free its place in the train.
            n_scheduled -= self._collect(pending)
            # On a timer, so that a train with no beats coming in still
            # flips and reads Escape; and right after a tone is scheduled,
            # when the next beat is furthest away.
            now = self.clock()
            frame_due = now - last_frame >= self.frame_interval
            hooked = False
            if self.on_frame is not None and (scheduled_now or frame_due):
                self.on_frame()
                last_frame = self.clock()
                hooked = True
            if now >= next_status:
                n_skipped = sum(t.skipped for t in result.tones)
                self._status(now, started, n_scheduled, n_skipped)
                next_status = now + STATUS_INTERVAL

            if abort is not None:
                break
            if not pending and (n_scheduled >= self.n_tones or n_beats >= max_beats):
                break
            if self.clock() >= deadline:
                abort = "timeout"
                break
            if not beats and not hooked:
                self.sleep(IDLE_SLEEP)

        if abort is not None:
            return self._finish(result, pending, abort, aborted=True)
        return self._finish(result, pending, None, aborted=False)

    # -- internals -------------------------------------------------------------

    def _status(self, now: float, started: float, n_scheduled: int, n_skipped: int):
        """Log one status line for the experimenter, flagging a silent source."""
        period = self.source.period
        hr = f"{60.0 / period:.0f}" if period else "--"
        line = (
            f"  [HSD {self.label}] {now - started:4.1f} s | HR {hr} bpm"
            f" | tones {n_scheduled}/{self.n_tones}, skipped {n_skipped}"
        )
        since = self._last_seen if self._last_seen is not None else started
        silent = now - since
        if silent >= max(NO_BEAT_WARNING, 1.5 * period if period else 0.0):
            logger.warning(f"{line} | NO BEATS (check the ECG) FOR {silent:.0f} s")
        else:
            logger.info(line)

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
            anchor="real",
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
            # The physical delay the target was set for.
            intended = (
                record.target - record.r_time + self.latency_bias
                if record.target is not None
                else None
            )
            self._mark(
                "tone_onset",
                record.onset if record.onset is not None else 0.0,
                index=record.index,
                r_time=record.r_time,
                target=record.target,
                onset=record.onset,
                anchor="real",
                realized=record.realized,
                delay_ms=intended * 1000.0 if intended is not None else math.nan,
                phase_deg=_phase_deg(intended, record.period),
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
                physical = record.realized + self.latency_bias
                record.realized_fraction = physical / interval

        if delivered:
            realized = _mean([t.realized for t in delivered if t.realized is not None])
            corrected = realized + self.latency_bias
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
