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
# The recordings cannot see two delays: the transport before the ECG is
# stamped, and the speaker after the onset the audio driver reports. Together
# they are 30 to 70 ms (the PAT dry run), so every target is moved
# LATENCY_BIAS earlier, as the PAT task does, and the realized delay measured
# against the stamped R-wave is LATENCY_BIAS short of the physical one.
#
# A tone for a physical delay d after the true R-wave is therefore due at
# r_time + d - LATENCY_BIAS on the clock, and can be scheduled only if that is
# at least AUDIO_LEAD after the beat becomes known, 31 ms (p95) after r_time:
#
#     d >= 0.031 + AUDIO_LEAD + LATENCY_BIAS = 0.031 + 0.05 + 0.05 = 0.131 s
#
# MIN_DELAY_S is that floor, rounded. Shorter candidates stay in the grid;
# the per-trial bounds leave them out.

#: Seconds a tone must be scheduled ahead of its onset to land on time.
AUDIO_LEAD = 0.05

#: Seconds of physical delay the recordings do not show (transport plus
#: speaker), subtracted from every target and added to every realized delay.
LATENCY_BIAS = 0.05

#: Shortest physical R-to-tone delay the task will request, in seconds.
MIN_DELAY_S = 0.13

#: Longest delay, as a fraction of the interbeat interval. Beyond it the tone
#: falls close enough to the next R-wave to be heard as belonging to it.
MAX_PERIOD_FRACTION = 0.75
