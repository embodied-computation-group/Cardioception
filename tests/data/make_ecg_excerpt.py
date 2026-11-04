# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""How ``ecg_excerpt.npz`` was made, from the recording it was cut from.

Usage, from the repository root, with pyxdf and systole installed::

    python tests/data/make_ecg_excerpt.py <recording.xdf> 340

The recording (an HSD hardware dry run, 2026-11-03) is not in the
repository. The excerpt is 60 s of channel ECG1 of its ``PLUX`` stream from
``start`` seconds after the stream's first sample, chosen as the 60 s window
with the most regular RR intervals and no beat the offline detector placed
implausibly (one extra beat at 160 s rules out the windows that hold it).

Stored, and nothing else (no markers, no other channel, no identifier):

``ecg``
    The ADC counts as int16, minus ``ecg_offset`` and divided by
    ``ecg_scale``. The PLUX counts are 16-bit unsigned and this stretch spans
    15,000 to 65,000 of them, so the scale is 1 and the int16 is lossless.
``sfreq``
    The nominal sample rate, Hz.
``stamps``
    The LSL timestamps as recorded, without pyxdf's dejitter, in seconds
    from the first sample: the times the samples reached the PC, with the
    Bluetooth arrival jitter in them. Rounded to multiples of 2**-20 s
    (under half a microsecond), which leaves the low bits of each float64
    zero and so halves the compressed file.
``r_peaks``
    The reference R peaks, seconds from the first sample (sample index over
    ``sfreq``), found by :func:`cardioception.devices._beats.detect_beats`
    on the excerpt alone. ``reference`` says how.
``meta``
    What the recording is.
"""

import sys

import numpy as np
import pyxdf

from cardioception.devices._beats import detect_beats

SECONDS = 60
OFFSET = 32768
#: Steps per second the timestamps are rounded to.
STAMP_QUANTUM = 2**20
META = (
    "60 s excerpt of a resting ECG, PLUX biosignalsplux over LSL, ECG1, "
    "2026-11-03, recorded for the Cardioception test suite"
)
REFERENCE = (
    "R peaks of the excerpt alone, from "
    "cardioception.devices._beats.detect_beats(ecg, 1000, 'ecg', 1000): "
    "systole's sleepecg detector, each detection then moved to the largest "
    "deflection within 100 ms before to 150 ms after it (snap_to_qrs). "
    "Seconds from the first sample, as sample index / sfreq."
)


def main(path: str, start: float, out: str = "tests/data/ecg_excerpt.npz") -> None:
    streams, _ = pyxdf.load_xdf(path, dejitter_timestamps=False)
    plux = next(s for s in streams if s["info"]["name"][0] == "PLUX")
    channels = plux["info"]["desc"][0]["channels"][0]["channel"]
    labels = [c["label"][0] for c in channels]
    sfreq = float(plux["info"]["nominal_srate"][0])
    lo = int(round(start * sfreq))
    hi = lo + int(SECONDS * sfreq)
    counts = np.asarray(plux["time_series"][lo:hi, labels.index("ECG1")])
    stamps = np.asarray(plux["time_stamps"][lo:hi], dtype=np.float64)
    assert counts.size == hi - lo
    ecg = counts - OFFSET
    assert ecg.min() >= np.iinfo(np.int16).min and ecg.max() <= np.iinfo(np.int16).max
    _, peaks = detect_beats(counts.astype(float), sfreq, "ecg", int(sfreq))
    r_peaks = np.flatnonzero(peaks) / sfreq
    np.savez_compressed(
        out,
        ecg=ecg.astype(np.int16),
        ecg_scale=np.float64(1.0),
        ecg_offset=np.float64(OFFSET),
        sfreq=np.float64(sfreq),
        stamps=np.round((stamps - stamps[0]) * STAMP_QUANTUM) / STAMP_QUANTUM,
        r_peaks=r_peaks.astype(np.float64),
        reference=np.array(REFERENCE),
        meta=np.array(META),
    )
    rr = np.diff(r_peaks)
    print(
        f"{out}: {r_peaks.size} beats, RR {rr.mean() * 1000:.1f} ms "
        f"(SD {rr.std(ddof=1) * 1000:.1f}), {60 / rr.mean():.1f} bpm"
    )


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
