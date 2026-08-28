# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Confidence scale definitions, independent of input device.

``Confidence`` used to hold three different scales in one column: 0-100 from
the mouse slider, 1-10 from the HRD keyboard and 1-7 from HBC, with nothing in
the output saying which. `HRD/parameters.py` wrote `[1, 7]` and then overwrote
it with `[1, 10]`, and for `device="mouse"` never set it at all.

A scale is now one object, used by both input devices and recorded on every
row, so a results file is interpretable without the parameters pickle.
"""

from dataclasses import dataclass
from typing import Sequence, Tuple


@dataclass(frozen=True)
class ConfidenceScale:
    """How confidence is collected and what its numbers mean.

    Parameters
    ----------
    kind :
        ``"vas"`` for a continuous visual analogue scale, ``"discrete"`` for a
        fixed number of steps.
    low, high :
        Ends of the scale, inclusive.
    granularity :
        Step size. ``1`` on a 0-100 VAS gives 101 positions; ``1`` on a 1-7
        discrete scale gives 7.
    labels :
        Text for the two ends.

    """

    kind: str = "vas"
    low: float = 0.0
    high: float = 100.0
    granularity: float = 1.0
    labels: Sequence[str] = ("Guess", "Certain")

    def __post_init__(self):
        if self.kind not in ("vas", "discrete"):
            raise ValueError(f"kind should be 'vas' or 'discrete', got {self.kind!r}")
        if self.high <= self.low:
            raise ValueError(f"high ({self.high}) must exceed low ({self.low})")
        if self.granularity <= 0:
            raise ValueError(f"granularity must be positive, got {self.granularity}")

    @property
    def n_levels(self) -> int:
        """Number of positions a participant can select."""
        return int(round((self.high - self.low) / self.granularity)) + 1

    @property
    def bounds(self) -> Tuple[float, float]:
        return (self.low, self.high)

    def clamp(self, value: float) -> float:
        """Snap a raw position onto the scale."""
        stepped = round((value - self.low) / self.granularity) * self.granularity
        return float(min(max(self.low + stepped, self.low), self.high))

    def to_unit(self, value: float) -> float:
        """Rescale to 0-1, which is what a bounded model wants as input."""
        return (float(value) - self.low) / (self.high - self.low)

    def from_unit(self, unit: float) -> float:
        """Inverse of :meth:`to_unit`, snapped to the scale."""
        return self.clamp(self.low + float(unit) * (self.high - self.low))

    def describe(self) -> dict:
        """Columns identifying this scale, written on every trial."""
        return {
            "ConfidenceScale": self.kind,
            "ConfidenceLow": self.low,
            "ConfidenceHigh": self.high,
            "ConfidenceGranularity": self.granularity,
            "ConfidenceLevels": self.n_levels,
        }


#: A continuous 0-100 slider. What the HRD mouse branch has always used.
VAS_0_100 = ConfidenceScale(kind="vas", low=0, high=100, granularity=1)

#: Seven discrete steps, the Heartbeat Counting default.
DISCRETE_1_7 = ConfidenceScale(kind="discrete", low=1, high=7, granularity=1)

#: Ten discrete steps, what the HRD keyboard branch actually used.
DISCRETE_1_10 = ConfidenceScale(kind="discrete", low=1, high=10, granularity=1)
