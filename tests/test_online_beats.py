# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""OnlineRDetector against the offline detector, and on a synthetic ECG.

The recorded files are a biosignalsplux chest ECG streamed over LSL. They live
outside the repository, and the tests that need them skip when they are
missing.
"""

from pathlib import Path

import numpy as np
import pytest

from cardioception.devices._beats import snap_to_qrs
from cardioception.devices._online_beats import Beat, OnlineRDetector

SFREQ = 1000
DATA = Path(r"C:\Users\stim\Desktop\cannabodies\plux-lsl\data\sub-test")
RECORDINGS = {
    "hrd20": DATA / "ses-hrd20" / "sub-test_ses-hrd20_task-hrd_physio.xdf",
    "lsl07": DATA / "ses-lsl07" / "sub-test_ses-lsl07_task-hrd_physio.xdf",
}

#: Seconds within which an online beat counts as the offline one.
TOLERANCE = 0.05


def in_chunks(detector, samples, stamps, seed=0):
    """Feed the signal in chunks of 1 to 50 samples, as an inlet would."""
    rng = np.random.default_rng(seed)
    beats, start = [], 0
    while start < len(samples):
        stop = start + int(rng.integers(1, 51))
        beats += detector.process(samples[start:stop], stamps[start:stop])
        start = stop
    return beats


def compare(beats, reference, n_samples, warmup=2.0, end=0.5):
    """Sensitivity, PPV, timing errors and lags, in samples.

    Beats in the warmup, which the online detector does not report, and in
    the last ``end`` seconds, which it may not have committed yet, are left
    out of both sides.
    """
    lo, hi = int(warmup * SFREQ), n_samples - int(end * SFREQ)
    online = np.array([b.r_index for b in beats])
    lags = np.array([b.commit_index - b.r_index for b in beats])
    online = online[(online >= lo) & (online < hi)]
    reference = reference[(reference >= lo) & (reference < hi)]
    tol = TOLERANCE * SFREQ
    nearest = np.array([online[np.argmin(np.abs(online - r))] for r in reference])
    errors = nearest - reference
    found = np.abs(errors) <= tol
    true = np.array([np.min(np.abs(reference - b)) <= tol for b in online])
    return {
        "sensitivity": found.mean(),
        "ppv": true.mean(),
        "errors": np.abs(errors[found]),
        "lags": lags,
    }


# -- recorded ECG --------------------------------------------------------------


@pytest.fixture(scope="module", params=sorted(RECORDINGS))
def recording(request):
    """ECG2 of the PLUX stream, its timestamps, and the offline beats."""
    path = RECORDINGS[request.param]
    if not path.exists():
        pytest.skip(f"{path} not found")
    pyxdf = pytest.importorskip("pyxdf")
    pytest.importorskip("systole")
    from cardioception.devices._beats import detect_beats

    streams, _ = pyxdf.load_xdf(str(path))
    plux = next(s for s in streams if s["info"]["name"][0] == "PLUX")
    labels = [c["label"][0] for c in plux["info"]["desc"][0]["channels"][0]["channel"]]
    ecg = np.asarray(plux["time_series"][:, labels.index("ECG2")])
    stamps = np.asarray(plux["time_stamps"])
    _, peaks = detect_beats(ecg.astype(float), SFREQ, "ecg", SFREQ)
    assert peaks.size == ecg.size
    return request.param, ecg, stamps, np.flatnonzero(peaks)


@pytest.fixture(scope="module")
def whole(recording):
    """The online beats with the recording fed as one chunk."""
    _, ecg, stamps, _ = recording
    return OnlineRDetector(SFREQ).process(ecg, stamps)


def test_matches_offline_detector(recording, whole):
    name, ecg, stamps, reference = recording
    result = compare(whole, reference, ecg.size)
    errors, lags = result["errors"], result["lags"]
    print(
        f"\n{name}: sensitivity {result['sensitivity']:.4f}, "
        f"PPV {result['ppv']:.4f}, |error| median {np.median(errors):g} ms, "
        f"p95 {np.percentile(errors, 95):g} ms, lag median {np.median(lags):g} "
        f"ms, p95 {np.percentile(lags, 95):g} ms, max {lags.max()} ms"
    )
    assert result["sensitivity"] > 0.98
    assert result["ppv"] > 0.98
    assert np.median(errors) < 5
    assert np.median(lags) < 80
    for beat in whole:
        assert beat.r_time == stamps[beat.r_index]


def test_chunk_size_does_not_matter(recording, whole):
    _, ecg, stamps, _ = recording
    assert in_chunks(OnlineRDetector(SFREQ), ecg, stamps, seed=1) == whole


def test_polarity_does_not_matter(recording, whole):
    _, ecg, stamps, _ = recording
    inverted = OnlineRDetector(SFREQ).process(-ecg, stamps)
    assert [b.r_index for b in inverted] == [b.r_index for b in whole]


# -- synthetic ECG -------------------------------------------------------------


def synthetic_ecg(r_times, seconds, polarity=1, seed=0):
    """P, Q, R, S and T as Gaussians around given R times, in raw counts.

    With a DC offset, a slow baseline wander larger than the R wave, mains
    hum and a little noise, as a badly attached chest electrode gives.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SFREQ)) / SFREQ
    ecg = np.zeros_like(t)
    for r in r_times:
        for offset, width, height in (
            (-0.16, 0.025, 0.15),  # P
            (-0.02, 0.008, -0.1),  # Q
            (0.0, 0.01, 1.0),  # R
            (0.022, 0.008, -0.3),  # S
            (0.28, 0.05, 0.4),  # T
        ):
            near = np.abs(t - r - offset) < 6 * width
            ecg[near] += height * np.exp(-0.5 * ((t[near] - r - offset) / width) ** 2)
    ecg += 1.5 * np.sin(2 * np.pi * 0.2 * t) + 0.05 * np.sin(2 * np.pi * 50 * t)
    ecg += rng.normal(0, 0.005, t.size)
    return (32768 + polarity * 8000 * ecg).astype(np.int32), t + 1000.0


@pytest.fixture(scope="module")
def r_times():
    """R peaks at a varying rate, from 50 to 140 beats per minute."""
    rr = np.random.default_rng(0).uniform(0.43, 1.2, 100)
    times = 0.5 + np.cumsum(rr)
    return times[times < 59.0]


@pytest.mark.parametrize("polarity", [1, -1])
def test_synthetic(r_times, polarity):
    ecg, stamps = synthetic_ecg(r_times, 60.0, polarity)
    detector = OnlineRDetector(SFREQ)
    beats = detector.process(ecg, stamps)
    truth = np.round(r_times * SFREQ).astype(int)
    result = compare(beats, truth, ecg.size)
    assert result["sensitivity"] == 1.0
    assert result["ppv"] == 1.0
    # Noise and the baseline's slope move the largest sample off the
    # Gaussian's centre, as they would offline: snapped the same way, the
    # beats agree exactly.
    assert result["errors"].max() <= 5
    marks = np.zeros(ecg.size, dtype=bool)
    marks[truth] = True
    snapped = np.flatnonzero(snap_to_qrs(ecg, marks, SFREQ))
    assert compare(beats, snapped, ecg.size)["errors"].max() == 0
    assert result["lags"].max() < 40
    assert detector.polarity == polarity
    assert all(b.r_index >= 2 * SFREQ for b in beats)
    assert in_chunks(OnlineRDetector(SFREQ), ecg, stamps) == beats


def test_rr_and_anticipated_period(r_times):
    ecg, stamps = synthetic_ecg(r_times, 60.0)
    detector = OnlineRDetector(SFREQ)
    beats, periods = [], []
    for start in range(0, ecg.size, 10):
        chunk = slice(start, start + 10)
        for beat in detector.process(ecg[chunk], stamps[chunk]):
            beats.append(beat)
            periods.append(detector.anticipated_period)
    assert all(isinstance(b, Beat) for b in beats)
    assert beats[0].rr is None
    rr = [b.rr for b in beats[1:]]
    assert rr == pytest.approx(np.diff([b.r_time for b in beats]))
    assert detector.rr_history == rr
    assert periods[:3] == [None, None, None]
    for k, period in enumerate(periods[3:], start=3):
        assert period == pytest.approx(np.mean(rr[slice(k - 3, k)]))

    detector.reset()
    assert detector.rr_history == []
    assert detector.anticipated_period is None
    assert detector.process(ecg, stamps) == beats


def test_flat_and_missing_signal():
    """A disconnected lead gives a flat line or NaN; neither is a beat."""
    detector = OnlineRDetector(SFREQ)
    stamps = np.arange(10 * SFREQ) / SFREQ
    assert detector.process(np.full(stamps.size, 32768), stamps) == []
    assert detector.process([np.nan] * 5, stamps[:5] + 10) == []
    assert detector.process([], []) == []
    with pytest.raises(ValueError):
        detector.process([1, 2, 3], [0.0, 0.001])
