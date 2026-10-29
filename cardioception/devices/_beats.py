# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Beat detection for whichever signal the recorder provides."""


def detect_beats(signal, sfreq: float, signal_type: str, new_sfreq: int = 1000):
    """Resample to ``new_sfreq`` and find the beats.

    Returns ``(resampled_signal, peaks)``, ``peaks`` being a boolean mask at
    ``new_sfreq``, which is what both systole detectors return.
    """
    from systole.detection import ecg_peaks, ppg_peaks

    if signal_type == "ecg":
        return ecg_peaks(signal, sfreq=sfreq, new_sfreq=new_sfreq, method="sleepecg")
    return ppg_peaks(signal, sfreq=sfreq, new_sfreq=new_sfreq, clipping=True)
