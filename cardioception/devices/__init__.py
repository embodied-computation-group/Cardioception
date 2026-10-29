# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Recording backends, passed to ``getParameters(recorder=...)``."""

from .lsl import LSLRecorder

__all__ = ["LSLRecorder"]
