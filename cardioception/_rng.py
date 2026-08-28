# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""One random number generator per session, and a seed that is always recorded.

Before this, every random draw in the package went through the global numpy RNG
and nothing recorded a seed, so a session could not be reproduced, trial order
could not be fixed or counterbalanced across participants, and a run could not
be replayed to debug it.

The generator is created once in ``getParameters`` and carried in the task
parameters. Passing ``seed=None`` still gives a different session every time,
but the seed that was actually used is drawn explicitly and stored, so a session
is reproducible after the fact even when nobody chose a seed in advance.
"""

from typing import Optional, Tuple

import numpy as np


def make_rng(seed: Optional[int] = None) -> Tuple[np.random.Generator, int]:
    """Build the session generator and return it with the seed it came from.

    Parameters
    ----------
    seed :
        The seed to use. When ``None``, one is drawn from system entropy and
        returned, rather than left implicit inside the generator where it could
        not be recovered.

    Returns
    -------
    rng :
        The generator every random draw in the session should go through.
    seed :
        The seed it was built from. Store this in the results.

    """
    if seed is None:
        # Truncated to 32 bits deliberately. The full entropy is a 128 bit
        # integer, which JSON readers outside Python (JavaScript, some R
        # parsers) silently round, and a seed that cannot survive a round trip
        # through the results file is not a seed anyone can replay from.
        seed = int(np.random.SeedSequence().entropy) % (2**32)  # type: ignore[arg-type]
    return np.random.default_rng(seed), int(seed)
