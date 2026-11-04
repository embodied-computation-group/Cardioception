# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Heartbeat Synchrony Discrimination task (HSD): adaptive estimation of the heartbeat sensation envelope."""

from .parameters import getParameters
from .psi import PARAMETERS, RATES, SynchronyPsi, default_grids, gaussian_envelope
from .task import run, trial, tutorial

__all__ = [
    "PARAMETERS",
    "RATES",
    "SynchronyPsi",
    "default_grids",
    "gaussian_envelope",
    "getParameters",
    "run",
    "trial",
    "tutorial",
]
