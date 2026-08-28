# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""One random number generator per session, and a seed that is always recorded."""

from typing import Optional, Tuple

import numpy as np


def make_rng(seed: Optional[int] = None) -> Tuple[np.random.Generator, int]:
    """Build the session generator and return it with the seed it came from.

    A seed of None is drawn from entropy and returned, so an unseeded session
    is still reproducible after the fact. Truncated to 32 bits because JSON
    readers outside Python round the full 128-bit value.
    """
    if seed is None:
        seed = int(np.random.SeedSequence().entropy) % (2**32)  # type: ignore[arg-type]
    return np.random.default_rng(seed), int(seed)
