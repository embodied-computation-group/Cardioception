# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Fixed values of the Heartbeat Synchrony Discrimination task.

The trigger codes are written into the recording's marker channel and nothing
validates them afterwards, so they are named here once. The HRD task writes
different meanings to the same codes: see
:class:`cardioception.HRD._constants.Trigger`.
"""

from enum import IntEnum
from typing import Tuple


class Trigger(IntEnum):
    """Marker values sent at the task's event boundaries."""

    TRIAL_START = 1
    TRAIN_START = 2
    TONE = 3
    DECISION_START = 4
    CONFIDENCE_START = 5
    TRIAL_STOP = 6


#: Event names the task fires callbacks for, in the order they occur in a
#: trial. HSD has its own set: the HRD events (``listeningStart`` and so on)
#: do not exist here.
EVENTS: Tuple[str, ...] = (
    "trialStart",
    "trialStop",
    "trainStart",
    "trainStop",
    "decisionStart",
    "decisionStop",
    "confidenceStart",
    "confidenceStop",
)

#: The two stimulus axes: delay in ms after the R-wave, or delay as a fraction
#: of the anticipated interbeat interval.
AXES: Tuple[str, ...] = ("absolute", "phase")

#: Tones per trial, each locked to its own R-wave.
N_TONES = 5

#: The tone: a 1000 Hz burst of 30 ms with 5 ms raised-cosine ramps, as the
#: PAT tone player makes it.
TONE_FREQ = 1000.0
TONE_SECS = 0.03
TONE_RAMP = 0.005

# Timing limits, measured on the PLUX ECG over LSL on the stim PC:
#
# - a beat is known 20 ms (median) and 31 ms (p95) after its stamped R peak;
# - a tone scheduled 50 ms ahead lands within 1 ms of its target (20 ms ahead
#   is still fine, 10 ms ahead is late);
# - the stamped R peak itself trails the true R peak by the Bluetooth
#   transport, 20 to 40 ms, which no scheduling can recover.
#
# So the shortest delay that can be met on every beat is about 31 + 50 ms
# after the stamped R, and realized delays measured against stamped R times
# understate the true R-to-tone interval by the transport lag.

#: Seconds a tone must be scheduled ahead of its onset to land on time.
AUDIO_LEAD = 0.05

#: Shortest R-to-tone delay the task will request, in seconds.
MIN_DELAY_S = 0.08

#: Longest delay, as a fraction of the interbeat interval. Beyond it the tone
#: falls close enough to the next R-wave to be heard as belonging to it.
MAX_PERIOD_FRACTION = 0.75
