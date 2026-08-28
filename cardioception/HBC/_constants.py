# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Fixed values of the Heartbeat Counting task."""

from enum import IntEnum


class Trigger(IntEnum):
    """Marker values written to ``Channel_0`` of the oximeter recording.

    These are **not** the Heart Rate Discrimination codes. Both tasks write to
    the same channel, and there 1 means the trial started and 2 means the
    listening window opened. A recording has to be read knowing which task
    produced it.
    """

    LISTENING_START = 1
    LISTENING_STOP = 2
