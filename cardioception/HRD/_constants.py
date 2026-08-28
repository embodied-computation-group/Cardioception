# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Fixed values of the Heart Rate Discrimination task.

These were literals scattered through task.py. The trigger codes are the ones
that matter: they are written into the PPG recording's marker channel, nothing
validates them, and a transcription error would be invisible in the results
file and wrong in every physiological analysis afterwards.
"""

from enum import IntEnum


class Trigger(IntEnum):
    """Marker values written to ``Channel_0`` of the oximeter recording.

    The Heartbeat Counting task writes different meanings to the same channel,
    so a recording cannot be interpreted without knowing which task made it.
    See :class:`cardioception.HBC._constants.Trigger`.
    """

    TRIAL_START = 1
    LISTENING_START = 2
    DECISION_START = 3
    CONFIDENCE_START = 4
    TRIAL_STOP = 5


#: Sampling rate of the Nonin oximeter, in Hz.
OXIMETER_SFREQ = 75

#: Rate ``ppg_peaks`` resamples to before peak detection, in Hz. The sample
#: times written to the signal file are spaced at this rate.
PPG_SFREQ = 1000

#: Seconds of pulse recorded per listening window.
LISTENING_DURATION = 5.0

#: Seconds of that recording kept for peak detection. Longer than the window so
#: a beat straddling the boundary is not lost.
ANALYSIS_WINDOW = 6

#: Samples of the resampled signal used to measure the heart rate, at
#: ``PPG_SFREQ``. Five seconds.
PEAK_WINDOW_SAMPLES = 5000

#: Range the pre-generated tone files cover, in BPM. A staircase value that
#: would take the tone outside this has no sound file, so it is clamped and the
#: staircase is told the clamped value rather than the one it asked for.
TONE_BPM_MIN = 15.0
TONE_BPM_MAX = 199.0
