# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The PAT engine: scheduling rule, dial, trial rows and beat sources.

Almost everything runs on fakes (a clock set by hand, a beat source fed by
hand, a player that records what it was asked to play), so no sound card or
LSL stream is needed. The replay test feeds a recorded biosignalsplux ECG
through ``LSLBeatSource`` and skips when the file is missing; the live tone
test skips when no audio device opens.
"""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from cardioception.PAT.engine import (
    DEFAULT_PERIOD,
    Beat,
    BeatSource,
    LSLBeatSource,
    PhaseEngine,
    VirtualBeatSource,
    simulated_periods,
)

XDF = Path(
    r"C:\Users\stim\Desktop\cannabodies\plux-lsl\data\sub-test\ses-hrd20"
    r"\sub-test_ses-hrd20_task-hrd_physio.xdf"
)

# -- fakes ---------------------------------------------------------------------


class FakeClock:
    """A clock set by hand; ``step`` seconds are added on every reading."""

    def __init__(self, t=100.0, step=0.0):
        self.t = t
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


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
    assert "Confidence" not in row
    # Every tone has its onset once end_trial returns.
    assert all(np.isfinite(t["Onset"]) for t in engine.tones)
    kinds = outlet.kinds()
    for kind in ("trial_start", "beat", "tone_scheduled", "tone_onset", "dial"):
        assert kind in kinds
    assert kinds.index("press") < kinds.index("trial_end")
    end = outlet.samples[kinds.index("trial_end")][0]
    assert end["Trial"] == 7 and end["ChosenDelayMs"] == pytest.approx(450)


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


# -- VirtualBeatSource ----------------------------------------------------------------


def run_virtual(source, clock, seconds, frame=0.01):
    beats = []
    end = clock.t + seconds
    while clock.t < end:
        clock.t += frame
        for b in source.poll():
            # Never more than one period ahead, never in the past.
            assert clock.t <= b.r_time <= clock.t + 1.6
            beats.append(b)
    return beats


def test_virtual_fixed_period():
    clock = FakeClock(t=10.0)
    source = VirtualBeatSource(1.0, clock=clock)
    assert isinstance(source, BeatSource)
    assert source.virtual
    source.start()
    assert source.period == 1.0
    beats = run_virtual(source, clock, 10.0)
    r = np.array([b.r_time for b in beats])
    assert r[0] == pytest.approx(11.0)  # lead_in
    assert np.allclose(np.diff(r), 1.0)
    assert all(b.period == 1.0 for b in beats)
    # Each beat comes out about one period ahead.
    assert len(beats) == 11  # 11 to 21 s: the last one a period ahead of 20 s
    assert r[-1] <= clock.t + 1.0 + 1e-9


def test_virtual_simulated_within_bounds():
    clock = FakeClock(t=0.0)
    source = VirtualBeatSource("simulated", seed=3, clock=clock)
    beats = run_virtual(source, clock, 120.0)
    r = np.array([b.r_time for b in beats])
    periods = np.array([b.period for b in beats])
    assert np.all((periods >= 0.55) & (periods <= 1.5))
    # A beat's period is the interval to the next one.
    assert np.allclose(np.diff(r), periods[:-1])
    assert 0.8 < periods.mean() < 1.2
    assert periods.std() > 0.005  # it does vary


def test_simulated_periods_reproducible_and_bounded():
    a = [p for p, _ in zip(simulated_periods(seed=1), range(3000))]
    b = [p for p, _ in zip(simulated_periods(seed=1), range(3000))]
    c = [p for p, _ in zip(simulated_periods(seed=2), range(3000))]
    assert a == b and a != c
    a = np.asarray(a)
    assert a.min() >= 0.55 and a.max() <= 1.5
    # RMSSD in a plausible range for a resting heart (ms).
    rmssd = np.sqrt(np.mean(np.diff(a * 1000) ** 2))
    assert 5 < rmssd < 150


def test_virtual_replay_cycles():
    clock = FakeClock(t=0.0)
    seq = [0.8, 1.0, 1.2]
    source = VirtualBeatSource(seq, clock=clock)
    beats = run_virtual(source, clock, 12.0)
    periods = [b.period for b in beats]
    assert periods[:7] == [0.8, 1.0, 1.2, 0.8, 1.0, 1.2, 0.8]


def test_virtual_drops_missed_beats_and_wait_next_beat():
    clock = FakeClock(t=0.0)
    source = VirtualBeatSource(1.0, clock=clock)
    source.poll()  # first beat at 1.0
    clock.t = 20.3  # nobody polled for 20 s
    beats = source.poll()
    assert all(b.r_time >= 20.3 for b in beats)
    assert len(beats) == 1 and beats[0].r_time == pytest.approx(21.0)
    nxt = source.wait_next_beat(20.3)
    assert nxt.r_time == pytest.approx(21.0)
    assert source.wait_next_beat(21.0).r_time == pytest.approx(22.0)


@pytest.mark.parametrize("bad", ["fixed", 0.1, 5.0, [], [1.0, float("nan")], [0.1]])
def test_virtual_rejects_bad_periods(bad):
    with pytest.raises(ValueError):
        VirtualBeatSource(bad)


# -- LSLBeatSource on a recorded ECG ---------------------------------------------------


class FakeInlet:
    """Hands out a recording in 10-sample chunks, as the PLUX bridge pushes them.

    Each pull moves ``clock`` to the newest sample's stamp plus ``transport``.
    """

    def __init__(self, data, stamps, clock, chunk=10, transport=0.005):
        self.data = data
        self.stamps = stamps
        self.clock = clock
        self.chunk = chunk
        self.transport = transport
        self.pos = 0
        self.flushed = 0

    def flush(self):
        self.flushed += 1

    @property
    def exhausted(self):
        return self.pos >= len(self.stamps)

    def pull_chunk(self, timeout=0.0, max_samples=1024):
        n = min(self.chunk, max_samples)
        lo, hi = self.pos, min(self.pos + n, len(self.stamps))
        self.pos = hi
        if lo == hi:
            return [], []
        self.clock.t = float(self.stamps[hi - 1]) + self.transport
        return self.data[lo:hi].tolist(), self.stamps[lo:hi].tolist()


class FakeRecorder:
    def __init__(self, inlet, channel, sfreq=1000.0):
        self.inlet = inlet
        self.channel = channel
        self.sfreq = sfreq


@pytest.fixture(scope="module")
def recorded_ecg():
    """Two columns (a counter, ECG2) and their stamps, plus the offline beats."""
    if not XDF.exists():
        pytest.skip(f"{XDF} not found")
    pyxdf = pytest.importorskip("pyxdf")
    pytest.importorskip("systole")
    from cardioception.devices._beats import detect_beats

    streams, _ = pyxdf.load_xdf(str(XDF))
    plux = next(s for s in streams if s["info"]["name"][0] == "PLUX")
    labels = [c["label"][0] for c in plux["info"]["desc"][0]["channels"][0]["channel"]]
    ecg = np.asarray(plux["time_series"][:, labels.index("ECG2")], dtype=float)
    stamps = np.asarray(plux["time_stamps"], dtype=float)
    data = np.column_stack([np.arange(ecg.size), ecg])
    _, peaks = detect_beats(ecg, 1000, "ecg", 1000)
    return data, stamps, stamps[np.flatnonzero(peaks)]


def test_lsl_beat_source_replay(recorded_ecg):
    data, stamps, offline = recorded_ecg
    clock = FakeClock()
    inlet = FakeInlet(data, stamps, clock)
    source = LSLBeatSource(FakeRecorder(inlet, channel=1))
    assert isinstance(source, BeatSource)
    assert not source.virtual
    assert source.period is None
    source.start()
    assert inlet.flushed == 1
    beats, lags = [], []
    while not inlet.exhausted:
        for b in source.poll():
            beats.append(b)
            lags.append(clock.t - b.r_time)
    r = np.array([b.r_time for b in beats])
    rr = np.diff(r)
    print(
        f"\n{len(beats)} beats online, {offline.size} offline; lag median "
        f"{np.median(lags) * 1000:.1f} ms; RR {rr.min():.3f} to {rr.max():.3f} s"
    )
    # Almost every offline beat (after the warmup) found within 50 ms.
    ref = offline[(offline > stamps[0] + 2.5) & (offline < stamps[-1] - 0.5)]
    nearest = np.min(np.abs(ref[:, None] - r[None, :]), axis=1)
    assert np.mean(nearest < 0.05) > 0.98
    assert abs(len(beats) - ref.size) <= 0.02 * ref.size + 2
    # Periods: None for the first three beats, then the mean of the last 3 RR.
    assert [b.period for b in beats[:3]] == [None, None, None]
    for i in range(3, len(beats)):
        expected = (r[i] - r[i - 3]) / 3
        if np.all(rr[i - 3 : i] <= 2.0):
            assert beats[i].period == pytest.approx(expected)
    periods = np.array([b.period for b in beats[3:] if b.period is not None])
    assert np.all((periods > 0.4) & (periods < 1.6))
    assert source.period == pytest.approx(periods[-1])
    assert source.last_r_time == r[-1]
    assert np.median(lags) < 0.08


@pytest.mark.parametrize("chunk", [10, 1024])
def test_lsl_beat_source_commit_times(recorded_ecg, chunk):
    """Each beat carries the stamp of its commit sample, however late it is pulled.

    With 1024-sample chunks a beat can be pulled up to a second after it was
    committed; its commit time must not move.
    """
    data, stamps, _ = recorded_ecg
    n = 30_000
    clock = FakeClock()
    inlet = FakeInlet(data[:n], stamps[:n], clock, chunk=chunk)
    source = LSLBeatSource(FakeRecorder(inlet, channel=1))
    beats = []
    while not inlet.exhausted:
        beats += source.poll()
    commit = np.array([b.commit_time for b in beats])
    r = np.array([b.r_time for b in beats])
    assert np.all(np.isin(commit, stamps[:n]))
    lag = commit - r
    assert np.all(lag > 0) and np.all(lag < 0.25)
    print(f"\nchunk {chunk}: commit lag median {np.median(lag) * 1000:.1f} ms")


def test_lsl_commit_times_do_not_depend_on_chunking(recorded_ecg):
    data, stamps, _ = recorded_ecg
    n = 30_000
    out = []
    for chunk in (7, 1024):
        clock = FakeClock()
        inlet = FakeInlet(data[:n], stamps[:n], clock, chunk=chunk)
        source = LSLBeatSource(FakeRecorder(inlet, channel=1))
        beats = []
        while not inlet.exhausted:
            beats += source.poll()
        out.append([(b.r_time, b.commit_time) for b in beats])
    assert out[0] == out[1]


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


def test_lsl_beat_source_wait_next_beat(recorded_ecg):
    data, stamps, _ = recorded_ecg
    clock = FakeClock()
    inlet = FakeInlet(data[:20000], stamps[:20000], clock)
    source = LSLBeatSource(FakeRecorder(inlet, channel=1))
    after = stamps[10000]
    beat = source.wait_next_beat(after, timeout=5.0)
    assert beat is not None and after < beat.r_time < after + 2.0
    # The beats found while waiting still come out of poll, in order.
    polled = source.poll()
    assert beat in polled
    assert all(np.diff([b.r_time for b in polled]) > 0)
    # Past the end of the signal: nothing, after the timeout.
    assert source.wait_next_beat(stamps[19999] + 10, timeout=0.05) is None


def test_lsl_beat_source_gap_resets_period():
    clock = FakeClock()
    source = LSLBeatSource(FakeRecorder(FakeInlet(np.zeros((0, 2)), [], clock), 1))
    for r, rr in [(1.0, None), (2.0, 1.0), (3.0, 1.0), (4.0, 1.0)]:
        source._on_beat(r, rr)
    assert source.period == pytest.approx(1.0)
    source._on_beat(30.0, 26.0)  # a 26 s hole in the signal
    assert source.period is None


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


# -- the real sound card -------------------------------------------------------------


@pytest.fixture(scope="module")
def player():
    pytest.importorskip("psychtoolbox")
    pytest.importorskip("pylsl")
    from cardioception.PAT.engine import TonePlayer

    try:
        p = TonePlayer(volume=0.05, vib_volume=0.05)
    except Exception as err:  # no device, or it would not open
        pytest.skip(f"No audio device opened: {err}")
    yield p
    p.close()


def wait_onsets(player, handles, seconds=3.0):
    import time

    found = {}
    end = time.perf_counter() + seconds
    while len(found) < len(handles) and time.perf_counter() < end:
        found.update(player.poll_onsets())
        time.sleep(0.002)
    return found


def test_tone_player_onsets(player):
    import pylsl

    now = pylsl.local_clock()
    whens = [now + 0.1 + 0.35 * i for i in range(4)]
    handles = [player.schedule(w, "tone") for w in whens]
    # A vibration at the same moment as a tone: they overlap, both play.
    handles.append(player.schedule(whens[1], "vibration"))
    found = wait_onsets(player, handles)
    assert set(found) == set(handles)
    errors = [found[h] - w for h, w in zip(handles, whens + [whens[1]])]
    assert np.all(np.abs(errors) < 0.005), errors


def test_tone_player_stop_all(player):
    import pylsl

    h = player.schedule(pylsl.local_clock() + 1.0, "tone")
    player.stop_all()
    found = wait_onsets(player, [h], seconds=0.5)
    assert math.isnan(found[h])
    assert not player.busy
