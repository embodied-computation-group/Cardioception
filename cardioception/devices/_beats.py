# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Beat detection for whichever signal the recorder provides."""

import numpy as np

#: Seconds either side of a detection searched for the R peak. sleepecg marks
#: a point near the QRS rather than its peak: on a biosignalsplux chest ECG
#: the mark fell anywhere from 26 ms before to 87 ms after the largest
#: deflection. The T wave starts well after the far edge, the P wave well
#: before the near one.
QRS_SEARCH = (0.1, 0.15)


def detect_beats(signal, sfreq: float, signal_type: str, new_sfreq: int = 1000):
    """Resample to ``new_sfreq`` and find the beats.

    Returns ``(resampled_signal, peaks)``, ``peaks`` being a boolean mask at
    ``new_sfreq``, which is what both systole detectors return.
    """
    from systole.detection import ecg_peaks, ppg_peaks

    if signal_type == "ecg":
        resampled, peaks = ecg_peaks(
            signal, sfreq=sfreq, new_sfreq=new_sfreq, method="sleepecg"
        )
        return resampled, snap_to_qrs(resampled, peaks, new_sfreq)
    return ppg_peaks(signal, sfreq=sfreq, new_sfreq=new_sfreq, clipping=True)


def snap_to_qrs(signal, peaks, sfreq: float) -> np.ndarray:
    """Move each detection to the largest deflection of its QRS complex.

    Where the detector marks a beat varies by tens of milliseconds from one
    beat to the next, and that jitter goes straight into the intervals the
    heart rate is computed from: on a 30 s bench recording it took the RMSSD
    from 20 ms to 55. The largest deflection is taken in either direction,
    so electrode polarity does not matter.
    """
    signal = np.asarray(signal, dtype=float)
    before, after = (int(s * sfreq) for s in QRS_SEARCH)
    snapped = np.zeros(len(signal), dtype=bool)
    for i in np.flatnonzero(peaks):
        lo, hi = max(i - before, 0), min(i + after, len(signal))
        window = signal[lo:hi]
        snapped[lo + int(np.argmax(np.abs(window - np.median(window))))] = True
    return snapped
