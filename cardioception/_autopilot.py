# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""A synthetic participant, so a session can run without a human at the keyboard.

Supplies the input only: the same stimuli, staircase updates, triggers and files
as a real session. ``p_miss`` and ``p_hold`` reproduce missed trials and a held
mouse button, so tests can assert on those paths.
"""

from typing import List, Optional, Sequence, Tuple

import numpy as np


class AutoResponder:
    """Generate synthetic responses in place of a participant.

    Parameters
    ----------
    rng :
        The session generator, so a seeded run is reproducible.
    accuracy :
        Probability of answering in the direction the stimulus implies. ``0.5``
        is chance; the default is a plausible middling performer.
    p_miss :
        Probability that a trial gets no decision at all.
    rt_range :
        Bounds on the synthetic decision time, in seconds. Values are drawn
        uniformly and clipped to the task's own response deadline by the caller.
    confidence_range :
        Bounds on the synthetic confidence rating, as a fraction of the scale.
    p_hold :
        Probability of simulating a held button, which in the real task carries
        into the next trial. Off by default; set it in tests that assert the
        edge-triggering fix.

    """

    def __init__(
        self,
        rng: np.random.Generator,
        accuracy: float = 0.75,
        p_miss: float = 0.0,
        rt_range: Tuple[float, float] = (0.4, 2.5),
        confidence_range: Tuple[float, float] = (0.2, 0.9),
        p_hold: float = 0.0,
    ):
        self.rng = rng
        self.accuracy = accuracy
        self.p_miss = p_miss
        self.rt_range = rt_range
        self.confidence_range = confidence_range
        self.p_hold = p_hold
        # Everything it did, so a test can assert against intent rather than
        # having to reverse the behaviour out of the results file.
        self.log: List[dict] = []

    # -- helpers ---------------------------------------------------------

    def _rt(self, max_wait: Optional[float]) -> float:
        low, high = self.rt_range
        if max_wait is not None:
            high = min(high, max_wait)
            low = min(low, high)
        return float(self.rng.uniform(low, high))

    def _misses(self) -> bool:
        return bool(self.rng.random() < self.p_miss)

    # -- the three input points -----------------------------------------

    def advance(self) -> None:
        """Stand in for ``waitInput``. Returns at once."""
        self.log.append({"event": "advance"})

    def decide(
        self,
        condition: str,
        allowed: Sequence[str],
        max_wait: Optional[float] = None,
    ) -> Optional[Tuple[str, float]]:
        """Answer one decision.

        Returns ``(response, rt)``, or ``None`` for a missed trial. The response
        is one of ``allowed`` when the caller is the keyboard branch, or one of
        ``"More"``/``"Less"`` when it is the mouse branch, matching whatever the
        caller passed in ``allowed``.
        """
        if self._misses():
            self.log.append({"event": "decide", "response": None})
            return None
        correct = bool(self.rng.random() < self.accuracy)
        options = list(allowed)
        if condition in options:
            wrong = [o for o in options if o != condition]
            response = condition if correct else str(self.rng.choice(wrong))
        else:
            response = str(self.rng.choice(options))
        rt = 0.0 if self.rng.random() < self.p_hold else self._rt(max_wait)
        self.log.append({"event": "decide", "response": response, "rt": rt})
        return response, rt

    def rate(
        self,
        low: float,
        high: float,
        min_time: float = 0.0,
        max_wait: Optional[float] = None,
    ) -> Optional[Tuple[float, float]]:
        """Answer one confidence rating, or ``None`` if it times out."""
        if self._misses():
            self.log.append({"event": "rate", "confidence": None})
            return None
        lo, hi = self.confidence_range
        value = float(low + (high - low) * self.rng.uniform(lo, hi))
        rt = max(min_time + 0.001, self._rt(max_wait))
        self.log.append({"event": "rate", "confidence": value, "rt": rt})
        return value, rt
