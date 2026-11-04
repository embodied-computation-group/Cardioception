# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""A simulated HSD participant whose answers depend on the delay heard.

The HRD autopilot answers correctly with a fixed probability, which suits a
task with a right answer. HSD has none: the probability of "synchronous"
depends on the realized delay through the participant's envelope. This one
answers from a :class:`cardioception.HSD.simulate.Observer`, so a headless
session can check that the engine recovers the envelope it was given.
"""

from typing import List, Optional, Tuple

import numpy as np

from cardioception._autopilot import AutoResponder

from .simulate import Observer


class HSDAutopilot:
    """Generate synthetic HSD responses in place of a participant.

    Parameters
    ----------
    rng :
        The session generator, so a seeded run is reproducible.
    observer :
        The simulated envelope. Its delays are in engine units: ms on the
        absolute axis, fractions of the interbeat interval on the phase axis
        (construct it with ``mu`` and ``sigma`` in fractions there).
    p_miss :
        Probability that a decision, or a rating, is not given.
    rt_range :
        Bounds on the synthetic response times, seconds.
    confidence_range :
        Bounds on the synthetic confidence rating, as a fraction of the scale.
    """

    def __init__(
        self,
        rng: np.random.Generator,
        observer: Observer,
        p_miss: float = 0.0,
        rt_range: Tuple[float, float] = (0.4, 2.5),
        confidence_range: Tuple[float, float] = (0.2, 0.9),
    ):
        self.rng = rng
        self.observer = observer
        self.p_miss = p_miss
        self._responder = AutoResponder(
            rng,
            p_miss=p_miss,
            rt_range=rt_range,
            confidence_range=confidence_range,
        )
        # One log for everything, the wrapped responder's entries included.
        self.log: List[dict] = self._responder.log

    def advance(self) -> None:
        """Stand in for ``waitInput``. Returns at once."""
        self._responder.advance()

    def decide(
        self, realized: float, max_wait: Optional[float] = None
    ) -> Optional[Tuple[str, float]]:
        """Answer one decision about a train heard at ``realized`` delay.

        Returns ``("Synchronous" | "NotSynchronous", rt)``, or ``None`` for a
        missed trial.
        """
        if self.rng.random() < self.p_miss:
            self.log.append({"event": "decide", "delay": realized, "response": None})
            return None
        label = (
            "Synchronous"
            if self.observer.respond(realized, self.rng)
            else "NotSynchronous"
        )
        rt = self._responder._rt(max_wait)
        self.log.append(
            {"event": "decide", "delay": realized, "response": label, "rt": rt}
        )
        return label, rt

    def rate(
        self,
        low: float,
        high: float,
        min_time: float = 0.0,
        max_wait: Optional[float] = None,
    ) -> Optional[Tuple[float, float]]:
        """Answer one confidence rating, or ``None`` if it times out."""
        return self._responder.rate(low, high, min_time=min_time, max_wait=max_wait)
