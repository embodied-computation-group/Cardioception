# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The HSD train scheduler, configuration, results row and autopilot.

Pure Python with fakes: no window, no audio device, no LSL.
"""

import json
import math
import unittest

import numpy as np

from cardioception._rng import make_rng
from cardioception.HSD._autopilot import HSDAutopilot
from cardioception.HSD._constants import LATENCY_BIAS, MIN_DELAY_S
from cardioception.HSD._outcome import (
    HSDTrialOutcome,
    posterior_fields,
    train_fields,
    unused_reason,
)
from cardioception.HSD._stimulus import BeatSource, TonePlayer, TrainScheduler
from cardioception.HSD.config import TaskConfig
from cardioception.HSD.simulate import Observer
from cardioception.scales import VAS_0_100


class FakeClock:
    """Settable clock that moves on by ``step`` every time it is read."""

    def __init__(self, now=0.0, step=0.001):
        self.now = float(now)
        self.step = step

    def __call__(self):
        value = self.now
        self.now += self.step
        return value


class FakeBeat:
    def __init__(self, r_time, period, commit_time=None):
        self.r_time = r_time
        self.period = period
        self.commit_time = commit_time


class FakeBeatSource:
    """Scripted beats, each reported once the clock passes ``r_time + latency``."""

    def __init__(self, clock, r_times, period=None, latency=0.02, periods=None):
        self.clock = clock
        self.r_times = list(r_times)
        self.periods = periods
        self.latency = latency if callable(latency) else (lambda i: latency)
        self._period = period
        self._next = 0
        self.started = 0

    @property
    def period(self):
        return self._period

    def start(self):
        self.started += 1

    def stop(self):
        pass

    def poll(self):
        beats = []
        while self._next < len(self.r_times):
            i = self._next
            r_time = self.r_times[i]
            if self.clock.now < r_time + self.latency(i):
                break
            if self.periods is not None:
                self._period = self.periods[i]
            beats.append(FakeBeat(r_time, self._period))
            self._next += 1
        return beats


class FakePlayer:
    """Plays each tone at ``when + onset_error``.

    The onset is reported ``report_delay`` seconds after ``when`` (by default
    as soon as it has happened), or as NaN for a handle in ``nan_handles``.
    :meth:`stop_all` reports the onset of a tone that has already started
    and NaN for one that has not, as the PsychPortAudio player does.
    """

    def __init__(self, clock, onset_error=0.0, report_delay=None, nan_handles=()):
        self.clock = clock
        self.onset_error = onset_error
        self.report_delay = onset_error if report_delay is None else report_delay
        self.nan_handles = set(nan_handles)
        self.scheduled = {}
        self._waiting = {}
        self._handle = 0
        self._stopped = []
        self.stopped = 0

    def _onset(self, handle):
        if handle in self.nan_handles:
            return math.nan
        return self.scheduled[handle] + self.onset_error

    def schedule(self, when, kind="tone"):
        self._handle += 1
        self.scheduled[self._handle] = when
        self._waiting[self._handle] = when + self.report_delay
        return self._handle

    def poll_onsets(self):
        done = [h for h, t in self._waiting.items() if self.clock.now >= t]
        for h in done:
            del self._waiting[h]
        reported = self._stopped + [(h, self._onset(h)) for h in done]
        self._stopped = []
        return reported

    @property
    def busy(self):
        return bool(self._waiting)

    def stop_all(self):
        self.stopped += 1
        for h in self._waiting:
            started = self.clock.now >= self.scheduled[h] + self.onset_error
            self._stopped.append((h, self._onset(h) if started else math.nan))
        self._waiting = {}

    def close(self):
        pass


def setup(
    r_times,
    period=1.0,
    latency=0.02,
    onset_error=0.0,
    start=0.5,
    periods=None,
    player_kwargs=None,
    **kwargs,
):
    clock = FakeClock(now=start)
    source = FakeBeatSource(
        clock, r_times, period=period, latency=latency, periods=periods
    )
    player = FakePlayer(clock, onset_error=onset_error, **(player_kwargs or {}))
    scheduler = TrainScheduler(source, player, clock, **kwargs)
    return clock, source, player, scheduler


BEATS = [1.0 + i for i in range(10)]


class TestTargets(unittest.TestCase):
    def test_absolute_targets_are_r_time_plus_delay(self):
        """On the absolute axis each tone is due ``delay`` ms after its R-wave.

        Less the latency bias: the target is where the tone must start on the
        clock for the participant to hear it ``delay`` after the true R-wave.
        """
        _, _, player, scheduler = setup(BEATS)
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertFalse(result.aborted)
        self.assertEqual(result.end_reason, "complete")
        for tone in result.tones:
            self.assertAlmostEqual(
                tone.target, tone.r_time + 0.2 - LATENCY_BIAS, places=12
            )
            self.assertAlmostEqual(player.scheduled[tone.handle], tone.target)
        self.assertEqual([t.r_time for t in result.tones], BEATS[:5])

    def test_phase_targets_are_r_time_plus_fraction_of_period(self):
        """On the phase axis the delay is the fraction times the beat's period."""
        r_times = [1.0 + 0.8 * i for i in range(10)]
        _, _, _, scheduler = setup(r_times, period=0.8)
        result = scheduler.run(0.4, "phase", min_delay_s=MIN_DELAY_S)
        self.assertFalse(result.aborted)
        self.assertEqual(result.n_delivered, 5)
        for tone in result.tones:
            self.assertAlmostEqual(
                tone.target, tone.r_time + 0.4 * 0.8 - LATENCY_BIAS, places=12
            )
        for tone in result.tones[:-1]:
            self.assertAlmostEqual(tone.realized_fraction, 0.4, places=9)
        self.assertAlmostEqual(result.realized_mean, 0.4, places=9)

    def test_stale_beats_are_ignored(self):
        """An R-wave before the train started is neither used nor counted."""
        _, _, _, scheduler = setup(BEATS, start=1.5)
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(result.beats_seen[0]["status"], "stale")
        self.assertEqual(result.tones[0].r_time, 2.0)
        self.assertEqual(result.n_skipped, 0)


class TestRules(unittest.TestCase):
    def test_late_beat_is_skipped_counted_and_not_reanchored(self):
        """A beat known too late for the audio lead is skipped, not moved.

        The second beat is reported 50 ms after its R-wave. A 130 ms tone,
        less the 50 ms latency bias, is due 80 ms after it, so 30 ms away,
        under the 50 ms lead. The train completes from the later beats, and
        no tone is scheduled off the predicted next beat.
        """
        latency = lambda i: 0.05 if i == 1 else 0.02  # noqa: E731
        _, _, player, scheduler = setup(BEATS, latency=latency)
        result = scheduler.run(130.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertFalse(result.aborted)
        self.assertEqual(result.n_skipped, 1)
        self.assertEqual(result.n_delivered, 5)
        skipped = [t for t in result.tones if t.skipped]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].reason, "late")
        self.assertEqual(skipped[0].r_time, BEATS[1])
        self.assertIsNone(skipped[0].onset)
        self.assertEqual(len(player.scheduled), 5)
        for when in player.scheduled.values():
            self.assertTrue(any(abs(when - (r + 0.08)) < 1e-12 for r in BEATS))
        self.assertNotIn(BEATS[1] + 0.08, list(player.scheduled.values()))

    def test_every_beat_late_ends_after_max_beats(self):
        """With no beat usable the train gives up after ``2 * n_tones`` beats."""
        _, _, player, scheduler = setup(BEATS, latency=0.06)
        result = scheduler.run(130.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertFalse(result.aborted)
        self.assertEqual(result.end_reason, "max_beats")
        self.assertEqual(result.n_skipped, 10)
        self.assertEqual(result.n_delivered, 0)
        self.assertIsNone(result.realized_mean)
        self.assertIsNone(result.realized_corrected)
        self.assertEqual(player.scheduled, {})

    def test_delay_beyond_the_period_ceiling_aborts(self):
        """A 600 ms delay on a 700 ms period is above 0.75 of it: abort."""
        r_times = [1.0 + 0.7 * i for i in range(10)]
        _, _, player, scheduler = setup(r_times, period=0.7)
        result = scheduler.run(600.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "ceiling")
        self.assertEqual(player.scheduled, {})

    def test_phase_axis_without_a_period_aborts(self):
        """The phase axis needs a period before the train can start."""
        _, _, player, scheduler = setup(BEATS, period=None)
        result = scheduler.run(0.4, "phase", min_delay_s=MIN_DELAY_S)
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "no_period")
        self.assertEqual(result.tones, [])
        self.assertEqual(player.scheduled, {})

    def test_delay_below_the_floor_is_refused(self):
        """A request below ``min_delay_s`` is refused before any beat."""
        _, _, _, scheduler = setup(BEATS)
        result = scheduler.run(100.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "floor")

    def test_timeout_aborts(self):
        """Without beats the train ends at ``timeout_s``, flagged as aborted."""
        clock, _, _, scheduler = setup([])
        result = scheduler.run(
            200.0, "absolute", min_delay_s=MIN_DELAY_S, timeout_s=1.0
        )
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "timeout")
        self.assertGreaterEqual(result.ended - result.started, 1.0)

    def test_unknown_axis_raises(self):
        """Only the two axes exist."""
        _, _, _, scheduler = setup(BEATS)
        with self.assertRaises(ValueError):
            scheduler.run(200.0, "degrees", min_delay_s=MIN_DELAY_S)


class TestRealized(unittest.TestCase):
    def test_absolute_corrected_adds_the_latency_bias_in_ms(self):
        """Targets move earlier by the bias; the engine value adds it back.

        With a 30 ms bias and onsets 2 ms late, the stamped delay is 172 ms
        and the physical one 202 ms.
        """
        _, _, _, scheduler = setup(BEATS, onset_error=0.002, latency_bias=0.03)
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        for tone in result.tones:
            self.assertAlmostEqual(tone.target, tone.r_time + 0.17, places=12)
        self.assertAlmostEqual(result.realized_mean, 0.172, places=9)
        self.assertAlmostEqual(result.realized_corrected, 202.0, places=6)

    def test_phase_corrected_is_a_fraction_of_the_period(self):
        """On the phase axis the bias-corrected delay is divided by the period."""
        r_times = [1.0 + 0.8 * i for i in range(10)]
        _, _, _, scheduler = setup(r_times, period=0.8, latency_bias=0.03)
        result = scheduler.run(0.4, "phase", min_delay_s=MIN_DELAY_S)
        self.assertAlmostEqual(result.realized_corrected, 0.4, places=9)
        # The realized fraction carries the bias in its numerator too.
        for tone in result.tones[:-1]:
            self.assertAlmostEqual(tone.realized, 0.29, places=9)
            self.assertAlmostEqual(tone.realized_fraction, 0.4, places=9)

    def test_no_bias_targets_the_stamped_delay(self):
        """``latency_bias=0`` schedules on the stamped R-wave plus the delay."""
        _, _, _, scheduler = setup(BEATS, latency_bias=0.0)
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        for tone in result.tones:
            self.assertAlmostEqual(tone.target, tone.r_time + 0.2, places=12)
        self.assertAlmostEqual(result.realized_corrected, 200.0, places=6)

    def test_tone_records_are_filled(self):
        """Every delivered tone has its onset, realized delay and lead."""
        _, _, _, scheduler = setup(BEATS, onset_error=0.001)
        result = scheduler.run(300.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(result.n_delivered, scheduler.n_tones)
        self.assertEqual(len(result.tones), 5)
        for i, tone in enumerate(result.tones):
            self.assertEqual(tone.index, i)
            self.assertFalse(tone.skipped)
            self.assertIsNone(tone.reason)
            self.assertEqual(tone.period, 1.0)
            self.assertAlmostEqual(tone.onset, tone.target + 0.001)
            # Stamped: 300 ms less the bias, plus the 1 ms onset error.
            self.assertAlmostEqual(tone.realized, 0.251)
            self.assertGreaterEqual(tone.lead, scheduler.audio_lead)
            self.assertIsNotNone(tone.handle)
        for tone in result.tones[:-1]:
            # Physical, over the observed 1 s interval.
            self.assertAlmostEqual(tone.realized_fraction, 0.301)
        # The train ends before the beat after the last tone is seen.
        self.assertIsNone(result.tones[-1].realized_fraction)
        self.assertLess(result.started, result.ended)

    def test_train_fields_put_every_delay_in_engine_units(self):
        """The results row has requested and realized delay in ms alike."""
        _, _, _, scheduler = setup(BEATS)
        fields = train_fields(scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S))
        # Measured against the stamped R-wave, then with the bias added back.
        self.assertAlmostEqual(
            fields["realizedDelay"], 200.0 - LATENCY_BIAS * 1000.0, places=6
        )
        self.assertAlmostEqual(fields["realizedCorrected"], 200.0, places=6)
        self.assertEqual(fields["requestedDelay"], 200.0)
        self.assertEqual(fields["periodMean"], 1.0)


class TestReview(unittest.TestCase):
    """Cases found in review of the first version."""

    def test_phase_realized_mean_uses_observed_intervals_only(self):
        """Realized fractions use the observed RR; the engine value the anticipated.

        The source anticipates 0.9 s while the heart beats every 0.8 s. A
        0.4 fraction is timed at 0.36 s, which is 0.45 of the observed
        interval. The last tone has no observed interval, so it is left out
        of ``realized_mean`` rather than divided by the anticipated period.
        """
        r_times = [1.0 + 0.8 * i for i in range(10)]
        _, _, _, scheduler = setup(r_times, period=0.9)
        result = scheduler.run(0.4, "phase", min_delay_s=MIN_DELAY_S)
        self.assertEqual(result.n_delivered, 5)
        for tone in result.tones[:-1]:
            self.assertAlmostEqual(tone.realized_fraction, 0.45, places=9)
        self.assertIsNone(result.tones[-1].realized_fraction)
        self.assertAlmostEqual(result.realized_mean, 0.45, places=9)
        self.assertAlmostEqual(result.realized_corrected, 0.4, places=9)

    def test_slow_heart_is_not_a_timeout(self):
        """At 40 bpm with two late beats the train outlasts 10 s and still ends.

        Seven beats at 1.5 s take past the old fixed 10 s deadline; the
        deadline now stretches to the beats the train may use.
        """
        r_times = [1.4 + 1.5 * i for i in range(12)]
        latency = lambda i: 0.2 if i in (1, 3) else 0.02  # noqa: E731
        _, _, player, scheduler = setup(r_times, period=1.5, latency=latency)
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertFalse(result.aborted)
        self.assertIn(result.end_reason, ("complete", "max_beats"))
        self.assertEqual(result.n_delivered, 5)
        self.assertEqual(result.n_skipped, 2)
        self.assertGreater(result.ended - result.started, 10.0)
        self.assertEqual(player.stopped, 0)

    def test_absolute_without_period_checks_the_observed_rr(self):
        """With no anticipated period, the ceiling is checked against the RR.

        Beats every 0.5 s and no period: the first beat has no RR to check
        against and is skipped; the second shows 600 ms is past 0.75 of the
        RR, so no tone is scheduled past the next R-wave.
        """
        r_times = [1.0 + 0.5 * i for i in range(10)]
        _, _, player, scheduler = setup(r_times, period=None)
        result = scheduler.run(600.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(player.scheduled, {})
        self.assertEqual(result.n_delivered, 0)
        self.assertEqual(result.tones[0].reason, "no_period")
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "ceiling")

    def test_absolute_without_period_uses_rr_when_it_fits(self):
        """A delay that fits the observed RR is played although no period is known."""
        _, _, _, scheduler = setup(BEATS, period=None)
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(result.end_reason, "complete")
        self.assertEqual(result.n_delivered, 5)
        self.assertEqual(result.n_skipped, 1)

    def test_tone_without_onset_is_replaced(self):
        """A NaN onset frees its place, and the train goes on to a sixth beat."""
        _, _, player, scheduler = setup(BEATS, player_kwargs={"nan_handles": {2}})
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(result.n_delivered, 5)
        self.assertEqual(result.end_reason, "complete")
        self.assertEqual(len(player.scheduled), 6)
        missing = [t for t in result.tones if t.reason == "no_onset"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].handle, 2)

    def test_complete_only_when_every_tone_played(self):
        """With tones lost to NaN and no beats left, the end is ``max_beats``."""
        _, _, _, scheduler = setup(
            BEATS, player_kwargs={"nan_handles": set(range(1, 20))}
        )
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(result.n_delivered, 0)
        self.assertEqual(result.end_reason, "max_beats")
        self.assertFalse(result.aborted)

    def test_top_candidate_survives_a_slightly_early_beat(self):
        """The drawn ceiling leaves room for the next beats to come 7% early.

        Respiratory sinus arrhythmia moved the anticipated period by about 7
        percent within a train on the hardware dry run.
        """
        config = TaskConfig()
        _, high = config.bounds(0.8)
        top = float(max(d for d in config.candidates() if d <= high))
        self.assertGreater(top, 0.75 * 0.8 * 0.93 * 1000.0 - 50.0)
        periods = [0.8 * 0.93] * 10
        r_times = [1.0 + 0.8 * 0.93 * i for i in range(10)]
        _, _, _, scheduler = setup(r_times, period=0.8, periods=periods)
        result = scheduler.run(top, "absolute", min_delay_s=config.minDelay)
        self.assertFalse(result.aborted)
        self.assertEqual(result.n_delivered, 5)

    def test_phase_floor_is_rounded_up(self):
        """A candidate inside the bounds is never refused as below the floor.

        At this period the 0.13 s floor is 0.1250000004 of it, which rounds to
        0.125 at six decimals; the floor must round up, past the 0.125
        candidate.
        """
        period = MIN_DELAY_S / 0.1250000004
        config = TaskConfig(axis="phase")
        low, high = config.bounds(period)
        self.assertGreater(low, 0.125)
        allowed = [d for d in config.candidates() if low <= d <= high]
        self.assertNotIn(0.125, allowed)
        r_times = [1.0 + period * i for i in range(10)]
        for delay in (allowed[0], allowed[-1]):
            _, _, _, scheduler = setup(r_times, period=period)
            result = scheduler.run(float(delay), "phase", min_delay_s=config.minDelay)
            self.assertFalse(result.aborted, delay)

    def test_absolute_ceiling_is_rounded_down(self):
        """The absolute ceiling never rounds up past the margined bound."""
        config = TaskConfig()
        # 0.75 * 0.90 of this period is 500.0000006 ms, which would round to
        # nearest as 500.000001.
        _, high = config.bounds(500.0000006 / 675.0)
        self.assertEqual(high, 500.0)

    def test_mid_train_ceiling_skips_the_beat_and_goes_on(self):
        """A beat whose period trips the ceiling costs one tone, not the train.

        The dry-run case: a 540 ms delay drawn on a 0.8 s period, and the
        anticipated period drops 12.5 percent to 0.7 s on the third beat, so
        540 ms is past 0.75 of it. That beat is skipped as ``"ceiling"`` and
        the next beats complete the train.
        """
        periods = [0.8, 0.8, 0.7, 0.8, 0.8, 0.8, 0.8, 0.8]
        r_times = [1.0 + 0.8 * i for i in range(len(periods))]
        _, _, player, scheduler = setup(r_times, period=0.8, periods=periods)
        result = scheduler.run(540.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertFalse(result.aborted)
        self.assertEqual(result.end_reason, "complete")
        self.assertEqual(result.n_delivered, 5)
        self.assertEqual(result.n_skipped, 1)
        skipped = [t for t in result.tones if t.skipped]
        self.assertEqual([t.reason for t in skipped], ["ceiling"])
        self.assertEqual(skipped[0].r_time, r_times[2])
        self.assertIsNone(skipped[0].target)
        self.assertEqual(len(player.scheduled), 5)

    def test_a_ceiling_before_any_tone_still_aborts(self):
        """Nothing heard yet: the train is refused, for the task to draw again."""
        periods = [0.7, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8]
        r_times = [1.0 + 0.8 * i for i in range(len(periods))]
        _, _, player, scheduler = setup(r_times, period=0.8, periods=periods)
        result = scheduler.run(540.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "ceiling")
        self.assertEqual(player.scheduled, {})

    def test_an_abort_stops_pending_tones(self):
        """An abort collects the onsets of tones that played and stops the rest.

        Two tones are scheduled, then the beats stop and the train times out.
        Both tones have played but neither has been reported; on abort both
        onsets are collected and nothing is left pending on the player.
        """
        _, _, player, scheduler = setup(
            [1.0, 2.0], player_kwargs={"report_delay": 60.0}
        )
        result = scheduler.run(400.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "timeout")
        self.assertEqual(player.stopped, 1)
        self.assertFalse(player.busy)
        first, second = result.tones
        self.assertAlmostEqual(first.onset, 1.4 - LATENCY_BIAS)
        self.assertAlmostEqual(second.onset, 2.4 - LATENCY_BIAS)
        self.assertEqual(result.n_delivered, 2)


class TestHooks(unittest.TestCase):
    def test_markers_carry_the_expected_fields(self):
        """All four marker kinds are pushed, with the PAT dry-run field names."""
        markers = []
        latency = lambda i: 0.05 if i == 1 else 0.02  # noqa: E731
        _, _, _, scheduler = setup(
            BEATS,
            latency=latency,
            marker=lambda kind, stamp, **f: markers.append((kind, stamp, f)),
        )
        scheduler.run(130.0, "absolute", min_delay_s=MIN_DELAY_S)
        kinds = {kind for kind, _, _ in markers}
        self.assertEqual(
            kinds, {"beat", "tone_scheduled", "tone_onset", "tone_skipped"}
        )
        expected = {
            "beat": {"r_time", "rr", "period", "commit_time", "seen_time"},
            "tone_scheduled": {
                "r_time",
                "period",
                "target",
                "anchor",
                "lead",
                "delay_ms",
                "phase_deg",
                "fraction",
                "latency",
            },
            "tone_onset": {
                "r_time",
                "target",
                "onset",
                "anchor",
                "delay_ms",
                "phase_deg",
            },
            "tone_skipped": {"r_time", "period", "target", "anchor", "reason"},
        }
        for kind, stamp, fields in markers:
            self.assertTrue(expected[kind] <= set(fields), kind)
            json.dumps(fields)
            if "anchor" in fields:
                # The report summarizes "real" and "predicted" anchors only.
                self.assertEqual(fields["anchor"], "real")
            if kind == "beat":
                # These fake beats give no commit time, so it is the poll time,
                # from which the report takes the detection lag.
                self.assertEqual(fields["commit_time"], stamp)
                self.assertEqual(fields["seen_time"], stamp)
                self.assertGreaterEqual(fields["commit_time"], fields["r_time"])
            if kind == "tone_scheduled":
                self.assertIsNone(fields["latency"])
                self.assertAlmostEqual(
                    fields["target"], fields["r_time"] + 0.13 - LATENCY_BIAS
                )
            if kind in ("tone_scheduled", "tone_onset"):
                # The intended physical delay, not the biased target.
                self.assertAlmostEqual(fields["delay_ms"], 130.0)
                # The intended phase: 130 ms of a 1 s period.
                self.assertAlmostEqual(fields["phase_deg"], 46.8)
            if kind == "tone_onset":
                self.assertEqual(stamp, fields["onset"])
            if kind == "tone_skipped":
                self.assertEqual(fields["reason"], "late")
        self.assertEqual(sum(k == "tone_onset" for k, _, _ in markers), 5)

    def test_on_frame_runs_at_most_once_per_scheduled_tone(self):
        """The frame hook is not called on every loop pass."""
        calls = []
        _, _, _, scheduler = setup(BEATS, on_frame=lambda: calls.append(1))
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertLessEqual(len(calls), result.n_delivered)
        self.assertGreater(len(calls), 0)

    def test_commit_time_from_the_source_is_kept(self):
        """A beat's own commit time is marked, recorded and timed against."""

        class CommittingSource(FakeBeatSource):
            def poll(self):
                beats = super().poll()
                return [FakeBeat(b.r_time, b.period, b.r_time + 0.015) for b in beats]

        markers = []
        clock = FakeClock(now=0.5)
        source = CommittingSource(clock, BEATS, period=1.0)
        scheduler = TrainScheduler(
            source,
            FakePlayer(clock),
            clock,
            marker=lambda kind, stamp, **f: markers.append((kind, stamp, f)),
        )
        result = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        for beat in result.beats_seen:
            self.assertAlmostEqual(beat["commit_time"], beat["r_time"] + 0.015)
        for kind, stamp, fields in markers:
            if kind == "beat":
                self.assertAlmostEqual(fields["commit_time"], fields["r_time"] + 0.015)
                self.assertGreater(fields["seen_time"], fields["commit_time"])
            if kind == "tone_scheduled":
                # Polled 20 ms after the R-wave, committed 15 ms after it.
                self.assertGreater(fields["latency"], 0.0)
                self.assertLess(fields["latency"], 0.02)

    def test_phase_deg_is_nan_without_a_period(self):
        """A tone on a beat with no anticipated period has no intended phase."""
        markers = []
        _, _, _, scheduler = setup(
            BEATS,
            period=None,
            marker=lambda kind, stamp, **f: markers.append((kind, f)),
        )
        scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        onsets = [f for kind, f in markers if kind == "tone_onset"]
        self.assertGreater(len(onsets), 0)
        for fields in onsets:
            self.assertTrue(math.isnan(fields["phase_deg"]))
            self.assertAlmostEqual(fields["delay_ms"], 200.0)

    def test_fakes_satisfy_the_protocols(self):
        """The fakes stand in for the real classes, so they meet the protocols."""
        clock = FakeClock()
        self.assertIsInstance(FakeBeatSource(clock, BEATS), BeatSource)
        self.assertIsInstance(FakePlayer(clock), TonePlayer)


class TestAutopilot(unittest.TestCase):
    def test_answers_synchronous_at_the_observer_rate(self):
        """Over 2000 draws the "Synchronous" rate is close to ``p_yes``."""
        observer = Observer(mu=250.0, sigma=80.0, floor=0.1, peak=0.9)
        pilot = HSDAutopilot(make_rng(3)[0], observer)
        answers = [pilot.decide(260.0) for _ in range(2000)]
        rate = np.mean([a is not None and a[0] == "Synchronous" for a in answers])
        self.assertAlmostEqual(rate, float(observer.p_yes(260.0)), delta=0.04)
        self.assertEqual(len(pilot.log), 2000)
        self.assertTrue(all(0.4 <= a[1] <= 2.5 for a in answers if a is not None))

    def test_rate_and_advance_are_logged_with_decisions(self):
        """Ratings and advances go through the HRD responder, into one log."""
        observer = Observer(mu=250.0, sigma=80.0, floor=0.1, peak=0.9)
        pilot = HSDAutopilot(make_rng(4)[0], observer, p_miss=0.0)
        pilot.advance()
        value, rt = pilot.rate(0, 100, min_time=0.5, max_wait=5.0)
        self.assertTrue(20 <= value <= 90)
        self.assertGreater(rt, 0.5)
        self.assertEqual([e["event"] for e in pilot.log], ["advance", "rate"])

    def test_misses_return_none(self):
        """With ``p_miss=1`` no decision is given."""
        observer = Observer(mu=250.0, sigma=80.0, floor=0.1, peak=0.9)
        pilot = HSDAutopilot(make_rng(5)[0], observer, p_miss=1.0)
        self.assertIsNone(pilot.decide(250.0))


class TestConfig(unittest.TestCase):
    def test_axis_is_validated(self):
        """An unknown axis is refused at construction."""
        with self.assertRaises(ValueError):
            TaskConfig(axis="degrees")

    def test_tone_must_fit_between_two_r_waves(self):
        """Tones can come one refractory period (0.25 s) apart, and the player
        needs a tone's duration plus 0.05 s between starts."""
        TaskConfig(toneSecs=0.2)
        for bad in (0.0, 0.21, 0.5):
            with self.assertRaisesRegex(ValueError, "toneSecs"):
                TaskConfig(toneSecs=bad)

    def test_absolute_candidates_and_grids(self):
        """Absolute: 80 to 600 ms by 20, ``mu`` grid up to 600 ms."""
        config = TaskConfig()
        delays = config.candidates()
        self.assertEqual(delays[0], 80.0)
        self.assertEqual(delays[-1], 600.0)
        self.assertEqual(delays.size, 27)
        grids = config.grids()
        self.assertEqual(grids["mu"][-1], 600.0)
        self.assertEqual(config.ci_width(), 100.0)
        # The floor is the 130 ms physical floor; candidates below it stay in
        # the grid and are left out per trial.
        self.assertEqual(delays[0], 80.0)
        # The ceiling: 0.75 of the period, less the 0.10 margin.
        self.assertEqual(config.bounds(0.8), (130.0, 540.0))

    def test_phase_candidates_and_grids(self):
        """Phase: 0.10 to 0.90 by 0.025, ``mu`` 0 to 1 and ``sigma`` in fractions."""
        config = TaskConfig(axis="phase")
        delays = config.candidates()
        self.assertAlmostEqual(delays[0], 0.10)
        self.assertAlmostEqual(delays[-1], config.maxPeriodFraction)
        self.assertEqual(delays.size, 27)
        grids = config.grids()
        self.assertEqual(grids["mu"][0], 0.0)
        self.assertAlmostEqual(grids["mu"][-1], 1.0)
        self.assertEqual(grids["mu"].size, 51)
        self.assertAlmostEqual(grids["sigma"][0], 0.03)
        self.assertAlmostEqual(grids["sigma"][-1], 0.5)
        self.assertEqual(config.ci_width(), 0.17)
        low, high = config.bounds(0.8)
        self.assertAlmostEqual(low, 0.1625)
        self.assertEqual(high, 0.75)
        psi = config.engine(make_rng(0)[0])
        delay, _ = psi.next_delay(low, high)
        self.assertTrue(low <= delay <= high)

    def test_min_tones_lies_between_one_and_n_tones(self):
        """A trial cannot need more tones than a train plays."""
        self.assertEqual(TaskConfig().minTones, 3)
        TaskConfig(nTones=3, minTones=3)
        for bad in (0, 6):
            with self.assertRaisesRegex(ValueError, "minTones"):
                TaskConfig(minTones=bad)

    def test_describe_is_json_serializable_and_apply_fills_parameters(self):
        """The manifest entry dumps to JSON; apply copies every field."""
        config = TaskConfig(axis="phase")
        described = json.loads(json.dumps(config.describe()))
        self.assertEqual(described["axis"], "phase")
        self.assertEqual(described["isi"], [0.25, 0.25])
        parameters = {}
        config.apply(parameters)
        self.assertEqual(parameters["allowedKeys"], ["up", "down"])
        self.assertEqual(parameters["nTones"], 5)


class TestOutcome(unittest.TestCase):
    COLUMNS = [
        "Trial",
        "Axis",
        "RequestedDelay",
        "RealizedDelay",
        "RealizedCorrected",
        "nDelivered",
        "nSkipped",
        "Aborted",
        "AbortReason",
        "Explored",
        "Used",
        "UnusedReason",
        "Decision",
        "DecisionRT",
        "Confidence",
        "ConfidenceRT",
        "ConfidenceUnit",
        "Device",
        "ConfidenceScale",
        "ConfidenceLow",
        "ConfidenceHigh",
        "ConfidenceGranularity",
        "ConfidenceLevels",
        "ConfidenceSigned",
        "DecisionProvided",
        "RatingProvided",
        "nTrials",
        "MuMean",
        "MuMedian",
        "MuCILow",
        "MuCIHigh",
        "SigmaMean",
        "SigmaMedian",
        "SigmaCILow",
        "SigmaCIHigh",
        "FloorMean",
        "PeakMean",
        "DetectionEvidence",
        "DetectionBF",
        "PeriodMean",
        "StartTrigger",
        "TrainStart",
        "TrainStop",
        "DecisionStart",
        "ResponseMade",
        "RatingStart",
        "RatingEnds",
        "endTrigger",
    ]

    def test_unused_reason(self):
        """A trial updates the posterior only with minTones tones and a decision."""
        self.assertEqual(unused_reason(0, 3, False), "no_tone")
        self.assertEqual(unused_reason(2, 3, True), "few_tones")
        self.assertEqual(unused_reason(3, 3, False), "no_decision")
        self.assertIsNone(unused_reason(3, 3, True))
        self.assertIsNone(unused_reason(5, 3, True))

    def test_row_has_a_fixed_column_order(self):
        """The order is the documented one, whatever order context is passed in."""
        psi = TaskConfig().engine(make_rng(0)[0])
        psi.update(250.0, True)
        outcome = HSDTrialOutcome(
            trial=0,
            explored=False,
            decision="Synchronous",
            decisionRT=1.0,
            confidence=50.0,
            confidenceRT=1.2,
            respProvided=True,
            ratingProvided=True,
            axis="absolute",
            requestedDelay=240.0,
            realizedDelay=241.0,
            realizedCorrected=241.0,
            nDelivered=5,
            nSkipped=0,
            aborted=False,
            **posterior_fields(psi),
        )
        a = outcome.row(
            Device="keyboard", ConfidenceUnit="0-100", scale=VAS_0_100.describe()
        )
        b = outcome.row(
            nTrials=60,
            scale=VAS_0_100.describe(),
            ConfidenceUnit="0-100",
            Device="keyboard",
        )
        self.assertEqual(list(a), self.COLUMNS)
        self.assertEqual(list(b), self.COLUMNS)
        self.assertIsInstance(b["MuMean"], float)

        outcome.quality = {"nBeats": 7, "MaxLead": 0.2}
        with_quality = list(outcome.row(scale=VAS_0_100.describe()))
        at = self.COLUMNS.index("StartTrigger")
        expected = self.COLUMNS[:at] + ["nBeats", "MaxLead"] + self.COLUMNS[at:]
        self.assertEqual(with_quality, expected)


if __name__ == "__main__":
    unittest.main()


class TestObserve(unittest.TestCase):
    def test_beats_between_trains_keep_the_rr_and_the_record(self):
        """Beats polled between trains are kept, and give the next beat its RR."""
        markers = []
        clock, source, _, scheduler = setup(
            BEATS,
            n_tones=2,
            marker=lambda kind, stamp, **f: markers.append((kind, f)),
        )
        first = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(first.n_delivered, 2)
        # A rating gap of three beats, during which the task polls the source.
        clock.now += 3.0
        between = scheduler.observe(source.poll())
        self.assertEqual(len(between), 3)
        self.assertEqual({b["status"] for b in between}, {"between"})
        for b in between:
            self.assertAlmostEqual(b["rr"], 1.0)
        second = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        self.assertEqual(second.beats_seen[: len(between)], between)
        first_of_train = next(
            b for b in second.beats_seen if b["status"] in ("tone", "skipped")
        )
        self.assertAlmostEqual(first_of_train["rr"], 1.0)
        beat_markers = [f for kind, f in markers if kind == "beat"]
        self.assertEqual(
            len(beat_markers), len(first.beats_seen) + len(second.beats_seen)
        )

    def test_without_observe_the_first_rr_spans_the_gap(self):
        """The case observe exists for: discarded beats stretch the next RR."""
        clock, source, _, scheduler = setup(BEATS, n_tones=2)
        scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        clock.now += 3.0
        source.poll()  # polled and thrown away
        second = scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        first_of_train = next(
            b for b in second.beats_seen if b["status"] in ("tone", "skipped")
        )
        self.assertAlmostEqual(first_of_train["rr"], 4.0)

    def test_take_between_returns_and_clears(self):
        """Beats observed after the last train can still be collected."""
        clock, source, _, scheduler = setup(BEATS, n_tones=1)
        scheduler.run(200.0, "absolute", min_delay_s=MIN_DELAY_S)
        clock.now += 2.0
        scheduler.observe(source.poll())
        left = scheduler.take_between()
        self.assertEqual(len(left), 2)
        self.assertEqual(scheduler.take_between(), [])
