# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Recorded ECG for the beat detection tests: a committed excerpt, and the lab files.

``excerpt`` is ``tests/data/ecg_excerpt.npz``: 60 s of a resting chest ECG
from a biosignalsplux streamed over LSL, with the R peaks the offline
detector found in it (``tests/data/make_ecg_excerpt.py`` made it). It needs
nothing beyond numpy, so the tests that use it run everywhere.

``hrd20`` and ``lsl07`` are two full lab recordings (XDF, channel ECG2). They
are not in the repository. Point :data:`ENV` at the directory that holds
``sub-test/ses-hrd20/...`` and ``sub-test/ses-lsl07/...`` to run on them too;
without it those cases skip. They need pyxdf, and systole for the reference.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest

SFREQ = 1000
EXCERPT = Path(__file__).parent / "data" / "ecg_excerpt.npz"
ENV = "CARDIOCEPTION_RECORDINGS"
LAB = {
    "hrd20": Path("sub-test", "ses-hrd20", "sub-test_ses-hrd20_task-hrd_physio.xdf"),
    "lsl07": Path("sub-test", "ses-lsl07", "sub-test_ses-lsl07_task-hrd_physio.xdf"),
}
#: Where the excerpt's timestamps start, as an LSL clock would be well past 0.
T0 = 1000.0


class Recording(NamedTuple):
    name: str
    #: The ECG in ADC counts.
    ecg: np.ndarray
    #: Each sample's timestamp as the inlet hands it to the detector, s.
    stamps: np.ndarray
    #: Sample indices of the offline detector's R peaks, the reference.
    reference: np.ndarray


def lsl_dejitter(stamps, sfreq=SFREQ, halftime=90.0):
    """The timestamps an inlet opened with ``proc_dejitter`` returns.

    The recorder's inlet is (``cardioception.devices.lsl``), and the
    detector depends on it: the raw stamps of the PLUX bridge come in bursts,
    with steps of up to 60 ms, which the detector would read as gaps in the
    signal. liblsl fits ``t = w0 + w1 * n`` to the sample index ``n`` by
    recursive least squares, forgetting with a half-life of ``halftime``
    seconds. This is the same recursion: on the excerpt it gives liblsl
    1.18's output to within 1e-12 s (checked by pushing the raw stamps
    through a pylsl outlet and inlet).
    """
    lam = 2.0 ** (-1.0 / (sfreq * halftime))
    t0 = float(stamps[0])
    w0, w1 = 0.0, 1.0 / sfreq
    p00, p01, p11 = 1e10, 0.0, 1e10
    out = np.empty(len(stamps))
    for n, t in enumerate(np.asarray(stamps, dtype=float) - t0):
        pi0 = p00 + n * p01
        pi1 = p01 + n * p11
        denominator = lam + pi0 + n * pi1
        g0, g1 = pi0 / denominator, pi1 / denominator
        error = t - (w0 + w1 * n)
        w0 += g0 * error
        w1 += g1 * error
        p00 = (p00 - g0 * pi0) / lam
        p01 = (p01 - g0 * pi1) / lam
        p11 = (p11 - g1 * pi1) / lam
        out[n] = w0 + w1 * n
    return out + t0


@lru_cache(maxsize=None)
def _load_excerpt() -> Recording:
    with np.load(EXCERPT) as npz:
        assert float(npz["sfreq"]) == SFREQ
        ecg = npz["ecg"] * float(npz["ecg_scale"]) + float(npz["ecg_offset"])
        stamps = lsl_dejitter(T0 + npz["stamps"])
        reference = np.round(npz["r_peaks"] * SFREQ).astype(int)
    return Recording("excerpt", ecg, stamps, reference)


@lru_cache(maxsize=None)
def _load_lab(name: str) -> Recording:
    import pyxdf

    from cardioception.devices._beats import detect_beats

    streams, _ = pyxdf.load_xdf(str(Path(os.environ[ENV]) / LAB[name]))
    plux = next(s for s in streams if s["info"]["name"][0] == "PLUX")
    channels = plux["info"]["desc"][0]["channels"][0]["channel"]
    labels = [c["label"][0] for c in channels]
    ecg = np.asarray(plux["time_series"][:, labels.index("ECG2")], dtype=float)
    stamps = np.asarray(plux["time_stamps"], dtype=float)
    _, peaks = detect_beats(ecg, SFREQ, "ecg", SFREQ)
    assert peaks.size == ecg.size
    return Recording(name, ecg, stamps, np.flatnonzero(peaks))


def load(name: str) -> Recording:
    """The excerpt, or a lab recording if :data:`ENV` points at it (else skip)."""
    if name == "excerpt":
        return _load_excerpt()
    if not os.environ.get(ENV):
        pytest.skip(
            f"lab recording {name}: set {ENV} to the directory holding "
            f"sub-test/ses-hrd20 and sub-test/ses-lsl07"
        )
    path = Path(os.environ[ENV]) / LAB[name]
    if not path.exists():
        pytest.skip(f"lab recording {name}: {path} not found")
    pytest.importorskip("pyxdf")
    pytest.importorskip("systole")
    return _load_lab(name)
