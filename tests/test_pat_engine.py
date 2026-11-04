# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The PAT engine: scheduling rule, dial, trial rows and markers.

Everything runs on fakes (a clock set by hand, a beat source fed by hand, a
player that records what it was asked to play), so no sound card or LSL
stream is needed. Two tests run the engine on a recorded ECG through
``LSLBeatSource`` and skip when the file is missing. The beat sources and the
player have their own tests, in test_beat_source.py and test_tone_player.py.
"""

import json
import math

import numpy as np
import pytest

# Shared fakes and the recorded-ECG fixture; pytest puts tests/ on the path.
from test_beat_source import FakeClock, FakeInlet, FakeRecorder
from test_beat_source import recorded_ecg as _recorded_ecg

from cardioception.PAT.engine import (
    DEFAULT_PERIOD,
    Beat,
    LSLBeatSource,
    PhaseEngine,
    VirtualBeatSource,
)

recorded_ecg = _recorded_ecg

# -- fakes ---------------------------------------------------------------------


class FakeSource:
    """Beats handed over by the test."""

    virtual = False

    def __init__(self, period=1.0):
        self.period = period
        self.queue = []
        self.started = 0
        self.stopped = 0

    def feed(self, *beats):
        self.queue.extend(beats)

    def start(self):
        self.started += 1

    def poll(self):
        beats, self.queue = self.queue, []
        return beats

    def stop(self):
        self.stopped += 1


class FakeVirtualSource(FakeSource):
    virtual = True


class FakePlayer:
    """Records schedules; reports an onset 1 ms late once the clock passes it."""

    def __init__(self, clock, error=0.001):
        self.clock = clock
        self.error = error
        self.scheduled = []  # (handle, when, kind)
        self.reported = set()
        self.closed = False

    def schedule(self, when, kind="tone"):
        handle = len(self.scheduled)
        self.scheduled.append((handle, when, kind))
        return handle

    def poll_onsets(self):
        now = self.clock.t
        done = []
        for handle, when, _ in self.scheduled:
            if handle not in self.reported and when <= now:
                self.reported.add(handle)
                done.append((handle, when + self.error))
        return done

    def close(self):
        self.closed = True

    @property
    def tones(self):
        return [(w, k) for _, w, k in self.scheduled if k == "tone"]


class FakeOutlet:
    def __init__(self):
        self.samples = []

    def push_sample(self, sample, stamp=0.0):
        (text,) = sample
        self.samples.append((json.loads(text), stamp))

    def kinds(self):
        return [m["kind"] for m, _ in self.samples]


def make_engine(mode="relative", virtual=False, period=1.0, **kwargs):
    clock = FakeClock()
    source = (FakeVirtualSource if virtual else FakeSource)(period)
    player = FakePlayer(clock)
    outlet = FakeOutlet()
    engine = PhaseEngine(source, player, mode, outlet=outlet, clock=clock, **kwargs)
    return engine, source, player, clock, outlet


def beat_now(engine, source, clock, r_time, period=1.0, lag=0.02):
    """A beat at ``r_time``, seen ``lag`` s later."""
    clock.t = r_time + lag
    source.feed(Beat(r_time, period))
    engine.poll()


# -- scheduling rule -------------------------------------------------------------


def test_relative_real_anchor():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 180)
    beat_now(engine, source, clock, 100.0)
    ((when, kind),) = player.tones
    assert kind == "tone"
    assert when == pytest.approx(100.0 + 0.5 - 0.05)
    row = engine.tones[-1]
    assert row["Anchor"] == "real"
    assert row["PhaseDeg"] == 180
    assert row["DelayMs"] == pytest.approx(500)
    assert row["RTime"] == 100.0 and row["PeriodS"] == 1.0
    assert engine.counts == {"real": 1, "predicted": 0, "skipped": 0}


def test_relative_predicted_anchor():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 0)
    beat_now(engine, source, clock, 100.0, period=0.8)
    ((when, _),) = player.tones
    # r - bias is already past: one anticipated period later.
    assert when == pytest.approx(100.0 + 0.8 - 0.05)
    assert engine.tones[-1]["Anchor"] == "predicted"
    assert engine.counts["predicted"] == 1


def test_audio_lead_boundary():
    # Target exactly audio_lead away is still real (binary-exact numbers).
    engine, source, player, clock, _ = make_engine(latency_bias=0.0, audio_lead=0.0625)
    engine.start_trial(1, 45)  # 0.125 s of a 1 s period
    clock.t = 100.0625
    source.feed(Beat(100.0, 1.0))
    engine.poll()
    assert engine.tones[-1]["Anchor"] == "real"
    # A hair later it is predicted.
    clock.t = 101.0626
    source.feed(Beat(101.0, 1.0))
    engine.poll()
    assert engine.tones[-1]["Anchor"] == "predicted"


@pytest.mark.parametrize("bias", [0.0, 0.05, 0.08])
def test_latency_bias_shifts_target(bias):
    engine, source, player, clock, _ = make_engine(latency_bias=bias)
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, 100.0)
    ((when, _),) = player.tones
    assert when == pytest.approx(100.25 - bias)
    assert engine.tones[-1]["Target"] == pytest.approx(100.25 - bias)
    # The logged dial is the delay without the bias.
    assert engine.tones[-1]["DelayMs"] == pytest.approx(250)


def test_min_tone_gap():
    engine, source, player, clock, outlet = make_engine(latency_bias=0.0)
    engine.start_trial(1, 180)
    beat_now(engine, source, clock, 100.0)  # tone at 100.5
    # A beat 0.25 s later (an artefact, say) would put a tone at 100.75.
    beat_now(engine, source, clock, 100.25)
    assert len(player.tones) == 1
    assert engine.counts["skipped"] == 1
    skipped = [m for m, _ in outlet.samples if m["kind"] == "tone_skipped"]
    assert skipped[-1]["reason"] == "gap"
    # The next real beat is fine: 101.5 is a period after 100.5.
    beat_now(engine, source, clock, 101.0)
    assert len(player.tones) == 2
    # A target before the last one is skipped too.
    engine.nudge(-9, 10.0, 25.0)  # 180 - 90 = 90 degrees
    beat_now(engine, source, clock, 101.2)  # 101.45 < 101.5 + 0.3
    assert len(player.tones) == 2
    assert engine.counts["skipped"] == 2


def test_min_tone_gap_zero_allows_close_tones():
    engine, source, player, clock, _ = make_engine(min_tone_gap=0.0, latency_bias=0)
    engine.start_trial(1, 180)
    beat_now(engine, source, clock, 100.0)
    beat_now(engine, source, clock, 100.3)
    assert len(player.tones) == 2


def test_absolute_mode_delay_and_clamp():
    engine, source, player, clock, _ = make_engine("absolute", period=1.0)
    engine.start_trial(1, 90)  # 250 ms of a 1 s period
    assert engine.delay_ms == pytest.approx(250)
    beat_now(engine, source, clock, 100.0)
    assert player.tones[-1][0] == pytest.approx(100.25 - 0.05)
    # Turn to 900 ms; the next beat's period is only 0.6 s: clamped.
    engine.nudge(26, 10.0, 25.0)  # 250 + 650 = 900
    assert engine.delay_ms == pytest.approx(900)
    beat_now(engine, source, clock, 101.0, period=0.6)
    row = engine.tones[-1]
    assert row["Target"] == pytest.approx(101.0 + 0.6 - 0.05)
    assert row["DelayMs"] == pytest.approx(600)
    assert row["Anchor"] == "real"
    # The dial itself is not changed by the clamp.
    assert engine.delay_ms == pytest.approx(900)


def test_absolute_mode_delay_ignores_period_changes():
    engine, source, player, clock, _ = make_engine("absolute", period=1.0)
    engine.start_trial(1, 72)  # 200 ms
    beat_now(engine, source, clock, 100.0, period=1.0)
    beat_now(engine, source, clock, 101.0, period=0.7)
    first, second = engine.tones
    assert first["DelayMs"] == pytest.approx(200)
    assert second["DelayMs"] == pytest.approx(200)
    assert second["PhaseDeg"] == pytest.approx(200 / 700 * 360)


def test_no_tone_until_period_known():
    engine, source, player, clock, outlet = make_engine(period=None)
    engine.start_trial(1, 180)
    beat_now(engine, source, clock, 100.0, period=None)
    assert player.scheduled == []
    assert "beat" in outlet.kinds()
    assert math.isnan(engine.delay_ms)
    assert engine.phase_deg == 180


# -- the dial ----------------------------------------------------------------------


def test_relative_dial_wraps_at_360():
    engine, *_ = make_engine()
    engine.start_trial(1, 350)
    engine.nudge(2, 10.0, 25.0)
    assert engine.phase_deg == pytest.approx(10)
    engine.nudge(-2, 10.0, 25.0)
    assert engine.phase_deg == pytest.approx(350)
    engine.start_trial(2, 0)
    engine.nudge(-1, 5.0, 25.0)
    assert engine.phase_deg == pytest.approx(355)
    assert engine.delay_ms == pytest.approx(355 / 360 * 1000)


def test_absolute_dial_wraps_at_period():
    engine, source, *_ = make_engine("absolute", period=0.8)
    engine.start_trial(1, 0)
    assert engine.delay_ms == 0
    engine.nudge(-1, 10.0, 25.0)
    assert engine.delay_ms == pytest.approx(775)
    engine.nudge(2, 10.0, 25.0)
    assert engine.delay_ms == pytest.approx(25)
    assert engine.phase_deg == pytest.approx(25 / 800 * 360)


def test_absolute_dial_clamps_before_wrapping():
    """A dial at 950 ms, then the period shrinks to 900 ms."""
    engine, source, player, clock, outlet = make_engine("absolute", period=1.0)
    engine.start_trial(1, 0)
    engine.nudge(38, 10.0, 25.0)
    assert engine.delay_ms == pytest.approx(950)
    source.period = 0.9
    # It reads as what the scheduler plays: the full period, phase 0.
    assert engine.delay_ms == pytest.approx(900)
    assert engine.phase_deg == pytest.approx(0)
    beat_now(engine, source, clock, 100.0, period=0.9)
    tone = engine.tones[-1]
    assert tone["Target"] == pytest.approx(100.0 + 0.9 - 0.05)
    assert tone["PhaseDeg"] == pytest.approx(0) and tone["DelayMs"] == 900
    # One notch on from there is 25 ms, not (950 + 25) % 900 = 75 ms.
    engine.nudge(1, 10.0, 25.0)
    assert engine.delay_ms == pytest.approx(25)
    dial = [m for m, _ in outlet.samples if m["kind"] == "dial"][-1]
    assert dial["delay_ms"] == pytest.approx(25)
    assert dial["phase_deg"] == pytest.approx(10)
    # Back at 950 and pressed while the period is 900: the press marker and
    # the row agree with the scheduler.
    source.period = 1.0
    engine.nudge(37, 10.0, 25.0)
    assert engine.delay_ms == pytest.approx(950)
    source.period = 0.9
    clock.t = 100.5
    engine.stop_tones()
    press = [m for m, _ in outlet.samples if m["kind"] == "press"][-1]
    assert press["delay_ms"] == pytest.approx(900)
    assert press["phase_deg"] == pytest.approx(0)
    source.feed(Beat(100.9, 0.9))
    clock.t = 101.0
    row = engine.end_trial()
    assert row["ChosenDelayMs"] == pytest.approx(900)
    assert row["ChosenPhaseDeg"] == pytest.approx(0)


def test_nudge_counts_moves_and_marks():
    engine, source, player, clock, outlet = make_engine()
    engine.start_trial(1, 0)
    engine.nudge(0, 10.0, 25.0)  # no movement: not a move
    engine.nudge(1, 10.0, 25.0)
    engine.nudge(-3, 10.0, 25.0)
    dial = [m for m, _ in outlet.samples if m["kind"] == "dial"]
    assert [d["notches"] for d in dial] == [1, -3]
    assert dial[-1]["phase_deg"] == pytest.approx(340)
    source.feed(Beat(clock.t - 0.5, 1.0), Beat(clock.t + 0.5, 1.0))
    assert engine.end_trial()["nDialMoves"] == 2


# -- start phases and trials --------------------------------------------------------


@pytest.mark.parametrize("start", [0, 90, 180, 270, 360, -90])
def test_start_phase_relative(start):
    engine, *_ = make_engine()
    engine.start_trial(1, start)
    assert engine.phase_deg == pytest.approx(start % 360)


@pytest.mark.parametrize("start", [0, 90, 180, 270])
def test_start_phase_absolute(start):
    engine, *_ = make_engine("absolute", period=0.8)
    engine.start_trial(1, start)
    assert engine.delay_ms == pytest.approx(start / 360 * 800)
    assert engine.phase_deg == pytest.approx(start)


def test_start_phase_absolute_without_period():
    engine, *_ = make_engine("absolute", period=None)
    engine.start_trial(1, 180)
    assert engine.delay_ms == pytest.approx(180 / 360 * DEFAULT_PERIOD * 1000)
    assert math.isnan(engine.phase_deg)


def test_start_trial_resets_dial_and_counts():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 90)
    engine.nudge(4, 10.0, 25.0)
    beat_now(engine, source, clock, 100.0)
    engine.start_trial(2, 270)
    assert engine.phase_deg == 270
    assert engine.counts == {"real": 0, "predicted": 0, "skipped": 0}
    assert source.started == 1  # the source keeps running across trials


def test_beats_waiting_at_start_get_no_tone():
    engine, source, player, clock, outlet = make_engine()
    engine.start_trial(1, 180)
    engine.stop_tones()
    # Beats during the confidence rating, polled only at the next start.
    source.feed(Beat(100.0, 1.0), Beat(101.0, 1.0))
    clock.t = 101.02
    engine.start_trial(2, 180)
    assert player.scheduled == []
    assert outlet.kinds().count("beat") == 2


def test_stop_tones_stops_scheduling_but_tones_play():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 270)
    beat_now(engine, source, clock, 100.0)  # tone at 100.70
    engine.stop_tones()
    beat_now(engine, source, clock, 101.0)  # no tone
    assert len(player.tones) == 1
    clock.t = 100.75
    engine.poll()
    assert engine.tones[0]["Onset"] == pytest.approx(100.701)


def test_end_trial_fields():
    engine, source, player, clock, outlet = make_engine(latency_bias=0.05)
    engine.start_trial(7, 90, block="main")
    start = clock.t
    for r, p in [(100.0, 1.0), (101.0, 0.9), (101.9, 0.9)]:
        beat_now(engine, source, clock, r, period=p)
    engine.nudge(9, 10.0, 25.0)  # 90 + 90 = 180
    clock.t = 102.5
    engine.poll()
    engine.stop_tones()
    # The next R comes 0.95 s after the last one, and the last tone's onset.
    clock.t = 102.9
    source.feed(Beat(102.85, 0.92))
    row = engine.end_trial()
    assert row["Trial"] == 7 and row["Block"] == "main"
    assert row["TrialStatus"] == "ok"
    assert row["Mode"] == "relative" and row["Extero"] is False
    assert row["StartPhaseDeg"] == 90
    assert row["ChosenPhaseDeg"] == pytest.approx(180)
    assert row["AnticipatedPeriodMs"] == pytest.approx(900)
    assert row["ChosenDelayMs"] == pytest.approx(450)
    assert row["LastRTime"] == 101.9
    assert row["ObservedPeriodMs"] == pytest.approx(950)
    assert row["PressTime"] == 102.5
    assert row["TrialDuration"] == pytest.approx(102.5 - start)
    assert row["nTonesReal"] == 3
    assert row["nTonesPredicted"] == 0
    assert row["nTonesSkipped"] == 0
    assert row["nDialMoves"] == 1
    assert isinstance(row["WallTime"], float)
    # The last tone before the press was timed from 101.9 at 90 degrees, before
    # the dial moved to 180: what was heard is not what was chosen.
    assert row["LastToneAnchor"] == "real"
    assert row["LastToneRTime"] == 101.9
    assert row["LastToneDelayMs"] == pytest.approx(225)
    assert [t["ToneIndex"] for t in engine.tones] == [1, 2, 3]
    assert row["LastToneIndex"] == 3
    assert "Confidence" not in row
    # Every tone has its onset once end_trial returns.
    assert all(np.isfinite(t["Onset"]) for t in engine.tones)
    kinds = outlet.kinds()
    for kind in ("trial_start", "beat", "tone_scheduled", "tone_onset", "dial"):
        assert kind in kinds
    assert kinds.index("press") < kinds.index("trial_end")
    end = outlet.samples[kinds.index("trial_end")][0]
    assert end["Trial"] == 7 and end["ChosenDelayMs"] == pytest.approx(450)


def test_predicted_tone_delay_is_measured_from_its_own_r_wave():
    """At phase 0 the tone is predicted from the R before, and the heart is
    slower than predicted: the tone sounds 50 ms before the R it was meant
    for, while the dial says 0 ms."""
    engine, source, player, clock, outlet = make_engine(latency_bias=0.05)
    engine.start_trial(1, 0)
    beat_now(engine, source, clock, 100.0, period=0.8)  # tone at 100.75
    (tone,) = engine.tones
    assert tone["Anchor"] == "predicted"
    beat_now(engine, source, clock, 100.85, period=0.82)  # its R, 50 ms late
    clock.t = 101.0
    engine.poll()
    engine.stop_tones()
    source.feed(Beat(101.67, 0.82))
    clock.t = 101.7
    row = engine.end_trial()
    assert row["ChosenDelayMs"] == pytest.approx(0)
    # The last tone heard before the press is the first one (the second, timed
    # from 100.85, sounds at 101.62, after the press).
    assert row["LastToneIndex"] == tone["ToneIndex"] == 1
    assert row["LastToneAnchor"] == "predicted"
    assert row["LastToneRTime"] == 100.0
    assert row["LastToneDelayMs"] == pytest.approx(-50, abs=1e-6)
    scheduled = [m for m, _ in outlet.samples if m["kind"] == "tone_scheduled"]
    assert [m["tone"] for m in scheduled] == [1, 2]


def test_predicted_tone_delay_without_its_r_wave():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 0)
    beat_now(engine, source, clock, 100.0, period=0.8)
    clock.t = 100.9  # the tone has played, its R never came
    engine.stop_tones()
    clock.step = 0.05
    row = engine.end_trial()
    assert row["LastToneAnchor"] == "predicted"
    assert math.isnan(row["LastToneDelayMs"])


def test_no_tone_before_the_press():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 270)
    beat_now(engine, source, clock, 100.0)  # tone at 100.70
    engine.stop_tones()  # at 100.02
    source.feed(Beat(101.0, 1.0))
    clock.t = 101.1
    row = engine.end_trial()
    assert math.isnan(row["LastToneIndex"]) and row["LastToneAnchor"] == ""
    assert math.isnan(row["LastToneDelayMs"])


def test_end_trial_absolute_clamps_chosen_delay():
    engine, source, player, clock, _ = make_engine("absolute", period=1.0)
    engine.start_trial(1, 0)
    engine.nudge(36, 10.0, 25.0)  # 900 ms
    beat_now(engine, source, clock, 100.0, period=0.7)
    engine.stop_tones()
    source.feed(Beat(100.7, 0.7))
    clock.t = 100.8
    row = engine.end_trial()
    assert row["ChosenDelayMs"] == pytest.approx(700)
    assert row["ChosenPhaseDeg"] == pytest.approx(0)


def test_end_trial_without_next_beat():
    engine, source, player, clock, _ = make_engine()
    clock.step = 0.05  # time runs on, the heart does not
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, clock.t)
    engine.stop_tones()
    row = engine.end_trial()
    assert math.isnan(row["ObservedPeriodMs"])
    assert np.isfinite(row["LastRTime"])


def test_press_long_after_the_last_beat_is_stale():
    """The ECG drops out: the press comes 2.5 periods after the last R."""
    engine, source, player, clock, outlet = make_engine()
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, 100.0, period=0.8)
    clock.t = 102.0
    engine.stop_tones()
    clock.t = 103.0  # no next beat either; tones have played
    clock.step = 0.05
    row = engine.end_trial()
    assert row["TrialStatus"] == "stale"
    assert math.isnan(row["AnticipatedPeriodMs"])
    # Relative mode: the phase is the dial, the delay needs a period.
    assert row["ChosenPhaseDeg"] == pytest.approx(90)
    assert math.isnan(row["ChosenDelayMs"])
    end = [m for m, _ in outlet.samples if m["kind"] == "trial_end"][-1]
    assert end["TrialStatus"] == "stale"


def test_press_within_one_and_a_half_periods_is_ok():
    engine, source, player, clock, _ = make_engine()
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, 100.0, period=0.8)
    clock.t = 101.19  # 1.49 periods after the R
    engine.stop_tones()
    source.feed(Beat(101.3, 0.8))
    clock.t = 101.4
    row = engine.end_trial()
    assert row["TrialStatus"] == "ok"
    assert row["AnticipatedPeriodMs"] == pytest.approx(800)


def test_stale_in_absolute_mode_keeps_the_delay():
    engine, source, player, clock, _ = make_engine("absolute", period=1.0)
    engine.start_trial(1, 90)  # 250 ms
    beat_now(engine, source, clock, 100.0, period=1.0)
    clock.t = 103.0
    engine.stop_tones()
    clock.step = 0.05
    row = engine.end_trial()
    assert row["TrialStatus"] == "stale"
    assert row["ChosenDelayMs"] == pytest.approx(250)
    assert math.isnan(row["ChosenPhaseDeg"])


def test_timeout_has_no_choice():
    engine, source, player, clock, outlet = make_engine()
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, 100.0)
    engine.stop_tones("timeout")
    source.feed(Beat(101.0, 1.0))
    clock.t = 101.1
    row = engine.end_trial()
    assert row["TrialStatus"] == "timeout"
    assert math.isnan(row["ChosenPhaseDeg"]) and math.isnan(row["ChosenDelayMs"])
    kinds = outlet.kinds()
    assert "timeout" in kinds and "press" not in kinds
    # The next trial is a normal one again.
    engine.start_trial(2, 90)
    beat_now(engine, source, clock, 102.0)
    engine.stop_tones()
    source.feed(Beat(103.0, 1.0))
    clock.t = 103.1
    assert engine.end_trial()["TrialStatus"] == "ok"


def test_abort_marker_is_not_a_press():
    engine, source, player, clock, outlet = make_engine()
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, 100.0)
    engine.stop_tones("abort")
    engine.stop_tones()  # only the first call of a trial counts
    kinds = outlet.kinds()
    assert kinds.count("abort") == 1 and "press" not in kinds
    abort = [m for m, _ in outlet.samples if m["kind"] == "abort"][0]
    assert abort["trial"] == 1


def test_stop_tones_rejects_an_unknown_reason():
    engine, *_ = make_engine()
    engine.start_trial(1, 0)
    with pytest.raises(ValueError, match="reason"):
        engine.stop_tones("lunch")


def test_markers_are_valid_json_without_nan():
    engine, source, player, clock, outlet = make_engine(period=None)
    engine.start_trial(1, 90)
    beat_now(engine, source, clock, 100.0, period=None)
    engine.mark("confidence", trial=1, rating=7, rt=1.2)
    for message, stamp in outlet.samples:
        assert "kind" in message
        assert "NaN" not in json.dumps(message)
    assert outlet.kinds()[-1] == "confidence"


def test_beat_marker_stamped_with_commit_time():
    engine, source, player, clock, outlet = make_engine()
    engine.start_trial(1, 180)
    # Detected at 100.02 but pulled only at 107 (nobody polled).
    clock.t = 107.0
    source.feed(Beat(100.0, 1.0, 100.02))
    engine.poll()
    message, stamp = [m for m in outlet.samples if m[0]["kind"] == "beat"][-1]
    assert stamp == 100.02
    assert message["commit_time"] == 100.02
    assert message["seen_time"] == 107.0
    # A source that gives no commit time: stamped when seen.
    source.feed(Beat(108.0, 1.0))
    clock.t = 108.02
    engine.poll()
    message, stamp = [m for m in outlet.samples if m[0]["kind"] == "beat"][-1]
    assert stamp == message["commit_time"] == 108.02


def test_idle_poll_detects_without_tones():
    engine, source, player, clock, outlet = make_engine()
    # Before any trial: beats are marked, no tones, the source is started.
    beat_now(engine, source, clock, 100.0)
    clock.t = 100.02
    source.feed(Beat(100.0, 1.0, 100.02))
    engine.idle_poll()
    assert source.started == 1
    assert outlet.kinds().count("beat") == 2
    assert player.scheduled == []
    # Inside a trial, idle_poll schedules nothing, and poll still does.
    engine.start_trial(1, 180)
    source.feed(Beat(101.0, 1.0, 101.02))
    clock.t = 101.02
    engine.idle_poll()
    assert player.scheduled == []
    beat_now(engine, source, clock, 102.0)
    assert len(player.tones) == 1
    # After the press, between trials: onsets still collected.
    engine.stop_tones()
    clock.t = 103.0
    engine.idle_poll()
    assert np.isfinite(engine.tones[-1]["Onset"])
    assert source.started == 1


def test_close_stops_source_and_player():
    engine, source, player, *_ = make_engine()
    engine.start_trial(1, 0)
    engine.close()
    assert source.stopped == 1 and player.closed


def test_bad_mode():
    with pytest.raises(ValueError, match="mode"):
        PhaseEngine(FakeSource(), FakePlayer(FakeClock()), "phase")


# -- exteroceptive task ----------------------------------------------------------------


def test_extero_schedules_vibration_and_tone():
    engine, source, player, clock, _ = make_engine(virtual=True)
    assert engine.extero
    engine.start_trial(1, 90)
    # A virtual beat a period in the future.
    clock.t = 100.0
    source.feed(Beat(101.0, 1.0))
    engine.poll()
    kinds = {k: w for _, w, k in player.scheduled}
    assert kinds["vibration"] == pytest.approx(101.0 - 0.05)
    assert kinds["tone"] == pytest.approx(101.25 - 0.05)
    by_kind = {t["Kind"]: t for t in engine.tones}
    assert by_kind["vibration"]["Anchor"] == "virtual"
    assert by_kind["tone"]["Anchor"] == "real"
    # Only the tone counts as a tone.
    assert engine.counts == {"real": 1, "predicted": 0, "skipped": 0}


def test_extero_with_virtual_source_end_to_end():
    clock = FakeClock(t=50.0)
    source = VirtualBeatSource(0.8, clock=clock)
    player = FakePlayer(clock)
    engine = PhaseEngine(source, player, "relative", clock=clock)
    engine.start_trial(1, 180)
    for _ in range(400):  # 4 s at 10 ms frames
        clock.t += 0.01
        engine.poll()
    engine.stop_tones()
    clock.step = 0.01  # time runs on while end_trial waits for the last tones
    row = engine.end_trial()
    vib = [w for _, w, k in player.scheduled if k == "vibration"]
    tones = [w for _, w, k in player.scheduled if k == "tone"]
    assert len(vib) >= 4 and len(tones) >= 4
    assert np.allclose(np.diff(vib), 0.8)
    # Each tone half a period after its vibration.
    for v in vib:
        assert np.min(np.abs(np.asarray(tones) - (v + 0.4))) < 1e-9
    assert row["Extero"] is True
    assert row["AnticipatedPeriodMs"] == pytest.approx(800)
    assert row["ObservedPeriodMs"] == pytest.approx(800)


# -- LSLBeatSource on a recorded ECG ---------------------------------------------------


def test_engine_marks_late_beats_at_commit_time(recorded_ecg):
    """Ten unpolled seconds (a rating screen), then start_trial catches up."""
    data, stamps, _ = recorded_ecg
    n = 30_000
    clock = FakeClock()
    inlet = FakeInlet(data[:n], stamps[:n], clock, chunk=10)
    source = LSLBeatSource(FakeRecorder(inlet, channel=1))
    outlet = FakeOutlet()
    engine = PhaseEngine(
        source, FakePlayer(clock), "relative", outlet=outlet, clock=clock
    )
    engine.start_trial(1, 90)
    while clock.t < stamps[0] + 10:
        engine.poll()
    engine.stop_tones()
    # The next pulls happen 10 s after the samples arrived, in big chunks.
    inlet.chunk = 1024
    inlet.transport = 10.0
    engine.start_trial(2, 90)
    for _ in range(5):
        engine.idle_poll()
    beats = [(m, t) for m, t in outlet.samples if m["kind"] == "beat"]
    late = [(m, t) for m, t in beats if m["seen_time"] - m["commit_time"] > 1.0]
    assert late, "the catch-up should have found beats from the unpolled seconds"
    for message, stamp in beats:
        assert stamp == message["commit_time"]
        assert 0 < stamp - message["r_time"] < 0.25


def test_engine_on_recorded_ecg(recorded_ecg):
    """The whole loop on 60 s of the recording, with a fake player."""
    data, stamps, _ = recorded_ecg
    n = 60_000
    clock = FakeClock()
    inlet = FakeInlet(data[:n], stamps[:n], clock)
    source = LSLBeatSource(FakeRecorder(inlet, channel=1))
    player = FakePlayer(clock)
    outlet = FakeOutlet()
    engine = PhaseEngine(source, player, "relative", outlet=outlet, clock=clock)
    engine.start_trial(1, 0)
    phases = [0, 90, 180, 270]
    while not inlet.exhausted:
        engine.poll()
        # Move a quarter turn every ~10 s of signal.
        k = int((clock.t - stamps[0]) // 10) % 4
        if engine.phase_deg != phases[k]:
            engine.nudge((phases[k] - engine.phase_deg) / 10, 10.0, 25.0)
    tones = [t for t in engine.tones if t["Kind"] == "tone"]
    anchors = [t["Anchor"] for t in tones]
    print(
        f"\n{len(tones)} tones: {anchors.count('real')} real, "
        f"{anchors.count('predicted')} predicted, {engine.counts['skipped']} skipped"
    )
    assert len(tones) > 40
    for t in tones:
        expected = t["RTime"] + t["PhaseDeg"] / 360 * t["PeriodS"] - 0.05
        if t["Anchor"] == "predicted":
            expected += t["PeriodS"]
        assert t["Target"] == pytest.approx(expected)
    # Phase 0 is always too late for the beat just seen; 180 never is.
    assert all(t["Anchor"] == "predicted" for t in tones if t["PhaseDeg"] == 0)
    assert all(t["Anchor"] == "real" for t in tones if t["PhaseDeg"] == 180)
    assert np.all(np.diff([w for w, _ in player.tones]) >= 0.3 - 1e-9)
