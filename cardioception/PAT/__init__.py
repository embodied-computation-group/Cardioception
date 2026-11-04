# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Phase adjustment task (PAT), after the PAT-ECG of Hodgetts et al. (2026).

The participant hears one tone per heartbeat, at a delay after the R-wave they
set with a dial, and turns the dial until tones and heartbeats feel
simultaneous. Interoceptive accuracy is the consistency of the chosen delays,
expressed as phase angles, across trials.

``engine`` holds the real-time part (beats in, tones out) and imports no
PsychoPy; ``task`` is the PsychoPy side.
"""
