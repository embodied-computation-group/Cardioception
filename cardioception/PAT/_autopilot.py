# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""A simulated PAT participant, who turns the dial towards a phase and presses.

The HRD autopilot answers a question; the PAT asks for an adjustment. This
one is given the phase at which it "feels" the heartbeat, aims each trial at
that phase plus Gaussian noise, rolls the wheel one notch at a time towards
the aim, and presses once the dial has stayed within half a notch of it for a
moment. It rates its confidence through
:meth:`cardioception._autopilot.AutoResponder.rate`, so a whole session runs
headless against :class:`cardioception.devices.beat_source.VirtualBeatSource`.

Set it as ``parameters["autopilot"]``, built on the session generator so a
seeded run is reproducible::

    parameters = getParameters(..., seed=1)
    parameters["autopilot"] = PATAutopilot(parameters["rng"], target=120.0)
"""

import math
from typing import List, Optional, Tuple

import numpy as np

from cardioception._autopilot import AutoResponder


class PATAutopilot:
    """Generate synthetic PAT responses in place of a participant.

    Parameters
    ----------
    rng :
        The session generator, so a seeded run is reproducible.
    target :
        The phase, in degrees after the R-wave, at which the simulated
        participant feels the heartbeat.
    spread :
        Standard deviation, in degrees, of each trial's aim around `target`.
        Small values make a consistent, "interoceptive" participant; large
        ones a guesser.
    notch_interval :
        Seconds between two notches of the wheel.
    settle :
        Seconds the dial has to stay at the aim before the press.
    p_miss :
        Probability that a confidence rating is not given.
    rt_range :
        Bounds on the synthetic rating times, seconds.
    confidence_range :
        Bounds on the synthetic confidence rating, as a fraction of the scale.
    """

    def __init__(
        self,
        rng: np.random.Generator,
        target: float = 120.0,
        spread: float = 10.0,
        notch_interval: float = 0.03,
        settle: float = 0.2,
        p_miss: float = 0.0,
        rt_range: Tuple[float, float] = (0.4, 2.5),
        confidence_range: Tuple[float, float] = (0.2, 0.9),
    ):
        self.rng = rng
        self.target = float(target)
        self.spread = float(spread)
        self.notch_interval = float(notch_interval)
        self.settle = float(settle)
        self._responder = AutoResponder(
            rng,
            p_miss=p_miss,
            rt_range=rt_range,
            confidence_range=confidence_range,
        )
        # One log for everything, the wrapped responder's entries included.
        self.log: List[dict] = self._responder.log
        self.aim = self.target
        self._last_notch = -math.inf
        self._settled: Optional[float] = None

    def start_trial(self, trial: int) -> None:
        """Draw this trial's aim. Called when the dial starts turning."""
        self.aim = float((self.target + self.rng.normal(0.0, self.spread)) % 360.0)
        self._last_notch = -math.inf
        self._settled = None
        self.log.append({"event": "trial", "trial": trial, "aim": self.aim})

    def frame(
        self,
        t: float,
        phase_deg: float,
        step_deg: float,
        wheel: bool = True,
        roll: int = 0,
    ) -> Tuple[int, bool]:
        """One frame of the dial: notches to roll now, and whether to press.

        Parameters
        ----------
        t :
            The time now, seconds.
        phase_deg :
            Where the dial is, in degrees.
        step_deg :
            How far one notch turns it, in degrees.
        wheel :
            Whether the screen takes the wheel at all. When it does not, the
            participant only presses, which the task accepts once the screen
            is ready.
        roll :
            A tutorial screen asking for the wheel to be rolled one way: `1`
            later, `-1` earlier. The participant rolls that way and presses,
            which the task accepts once enough notches are in.

        Returns
        -------
        notches, press :
            Positive notches move the beeps later.
        """
        due = t - self._last_notch >= self.notch_interval
        if not wheel:
            return 0, True
        if roll:
            if due:
                self._last_notch = t
                return int(np.sign(roll)), True
            return 0, True
        # Signed distance from the dial to the aim, the short way round
        diff = (self.aim - phase_deg + 180.0) % 360.0 - 180.0
        if not math.isfinite(diff):  # no period known yet, so no phase
            return 0, False
        if abs(diff) <= step_deg / 2:
            if self._settled is None:
                self._settled = t
            return 0, t - self._settled >= self.settle
        self._settled = None
        if not due:
            return 0, False
        self._last_notch = t
        return (1 if diff > 0 else -1), False

    def advance(self) -> None:
        """Stand in for ``waitInput``. Returns at once."""
        self._responder.advance()

    def rate(
        self,
        low: float,
        high: float,
        min_time: float = 0.0,
        max_wait: Optional[float] = None,
    ) -> Optional[Tuple[float, float]]:
        """Answer one confidence rating, or ``None`` if it is not given."""
        return self._responder.rate(low, high, min_time=min_time, max_wait=max_wait)
