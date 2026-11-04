# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Beat sources: the virtual heart, and LSLBeatSource on a recorded ECG.

The recorded ECG is a biosignalsplux chest ECG streamed over LSL: the
committed 60 s excerpt always, and a lab recording when
``CARDIOCEPTION_RECORDINGS`` points at it (see ecg_recordings.py).
The fakes here (clock, inlet, recorder) are also used by test_pat_engine.py.
"""

import numpy as np
import pytest
from ecg_recordings import load

from cardioception.devices.beat_source import (
    BeatSource,
    LSLBeatSource,
    VirtualBeatSource,
    simulated_periods,
)


class FakeClock:
    """A clock set by hand; ``step`` seconds are added on every reading."""

    def __init__(self, t=100.0, step=0.0):
        self.t = t
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


# -- VirtualBeatSource ---------------------------------------------------------


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


# -- LSLBeatSource on a recorded ECG ---------------------------------------------


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


@pytest.fixture(scope="module", params=["excerpt", "hrd20"])
def recorded_ecg(request):
    """Two columns (a counter, the ECG) and their stamps, plus the offline beats."""
    _, ecg, stamps, reference = load(request.param)
    data = np.column_stack([np.arange(ecg.size), ecg])
    return data, stamps, stamps[reference]


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
    beats, lags, rejected = [], [], []
    while not inlet.exhausted:
        for b in source.poll():
            beats.append(b)
            lags.append(clock.t - b.r_time)
            rejected.append(source.n_rejected)
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
    # Periods: None for the first three beats, then the mean of the last 3
    # RR, away from any interval rejected as a missed or extra beat (an extra
    # beat moves the next interval back to the beat before it).
    assert [b.period for b in beats[:3]] == [None, None, None]
    for i in range(3, len(beats)):
        expected = (r[i] - r[i - 3]) / 3
        if np.all(rr[i - 3 : i] <= 2.0) and rejected[i] == rejected[max(i - 4, 0)]:
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


def feed(source, r_times):
    """Hand ``r_times`` to the source as the detector would, with its RR."""
    beats, previous = [], None
    for r in r_times:
        source._on_beat(r, None if previous is None else r - previous, r + 0.03)
        previous = r
        beats.append(source._pending[-1])
    return beats


def test_lsl_beat_source_rejects_missed_and_extra_beats():
    """At 70 bpm, one dropped beat and one T wave taken for a beat leave the
    anticipated period where it was, and each is counted once."""
    clock = FakeClock()
    source = LSLBeatSource(FakeRecorder(FakeInlet(np.zeros((0, 2)), [], clock), 1))
    rr = 60 / 70 + np.random.default_rng(0).uniform(-0.02, 0.02, 40)
    r_times = list(1.0 + np.cumsum(rr))
    missed = r_times.pop(15)
    r_times.insert(28, r_times[27] + 0.3)  # a T wave, 0.3 s after its R
    beats = feed(source, r_times)
    periods = np.array([b.period for b in beats if b.period is not None])
    assert len(periods) == len(beats) - 3
    assert np.all((periods > 0.95 * 60 / 70) & (periods < 1.05 * 60 / 70))
    assert source.n_rejected == 2
    # Every beat is still reported, the extra one included.
    assert [b.r_time for b in beats] == r_times
    assert missed not in r_times
    # Under the old rule (mean of the last three RR whatever they are) the
    # missed beat pushed the period a third high.
    old = np.convolve(np.diff(r_times), np.ones(3) / 3, "valid")
    assert old.max() > 1.25 * 60 / 70


def test_lsl_beat_source_follows_a_real_change_of_rate():
    """A gradual change is followed without rejections, and a rate that jumps
    out of the band for good is learnt again rather than locked out."""
    clock = FakeClock()
    source = LSLBeatSource(FakeRecorder(FakeInlet(np.zeros((0, 2)), [], clock), 1))
    rr = list(np.linspace(1.0, 0.5, 30)) + [0.5] * 5
    feed(source, list(np.cumsum(rr)))
    assert source.n_rejected == 0
    assert source.period == pytest.approx(0.5)

    source = LSLBeatSource(FakeRecorder(FakeInlet(np.zeros((0, 2)), [], clock), 1))
    rr = [0.5] * 10 + [1.0] * 10
    beats = feed(source, list(np.cumsum(rr)))
    assert source.n_rejected == 3
    assert beats[-1].period == pytest.approx(1.0)
