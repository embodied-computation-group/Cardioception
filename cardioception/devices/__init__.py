# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Recording backends, passed to ``getParameters(recorder=...)``."""

from .continuous import ContinuousOximeter
from .replay import ReplayRecorder

__all__ = ["ContinuousOximeter", "ReplayRecorder"]
