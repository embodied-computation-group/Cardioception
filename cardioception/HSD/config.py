# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Design values of the Heartbeat Synchrony Discrimination task.

As for the HRD (:mod:`cardioception.HRD.config`), the trial and run functions
carry no design values of their own: they read them from a frozen
:class:`TaskConfig`, which is applied into the parameters dictionary and
written whole to ``manifest.json``, so a change is recorded with the data it
produced::

    from cardioception.HSD.config import TaskConfig

    config = TaskConfig(axis="phase", maxTrials=80)

The stimulus axis decides the units of everything the engine sees. On the
``"absolute"`` axis a delay is milliseconds after the R-wave; on the
``"phase"`` axis it is a fraction of the anticipated interbeat interval.
:meth:`TaskConfig.candidates`, :meth:`TaskConfig.grids` and
:meth:`TaskConfig.ci_width` return the values for the chosen axis.

The stopping rule (``minTrials``, ``maxTrials``, ``ciWidth``) is provisional:
it follows the simulations in :mod:`cardioception.HSD.simulate` and should be
revisited once real sessions exist.
"""

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np

from ._constants import (
    AUDIO_LEAD,
    AXES,
    LATENCY_BIAS,
    MAX_PERIOD_FRACTION,
    MIN_DELAY_S,
    N_TONES,
    TONE_FREQ,
    TONE_RAMP,
    TONE_SECS,
)
from .psi import PARAMETERS, SynchronyPsi, default_grids


def _json_ready(value: Any) -> Any:
    """Tuples as lists, recursively, so the result survives ``json.dumps``."""
    if isinstance(value, Mapping):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def _steps(low: float, high: float, step: float) -> np.ndarray:
    """``low`` to ``high`` inclusive in steps of ``step``, without float drift."""
    n = int(round((high - low) / step)) + 1
    return np.round(low + step * np.arange(n), 6)


def _round_up(value: float) -> float:
    """``value`` rounded up at six decimals, forgiving float error below that."""
    return math.ceil(value * 1e6 - 1e-6) / 1e6


def _round_down(value: float) -> float:
    """``value`` rounded down at six decimals, forgiving float error below that."""
    return math.floor(value * 1e6 + 1e-6) / 1e6


@dataclass(frozen=True)
class TaskConfig:
    """Design factors of an HSD session."""

    # --- stimulus ------------------------------------------------------------
    #: ``"absolute"`` (delay in ms after the R-wave) or ``"phase"`` (delay as a
    #: fraction of the anticipated interbeat interval).
    axis: str = "absolute"
    #: Tones per trial.
    nTones: int = N_TONES
    #: Candidate delays on the absolute axis, as (low, high, step) in ms.
    absoluteDelays: Tuple[float, float, float] = (80.0, 600.0, 20.0)
    #: Candidate delays on the phase axis, as (low, high, step) in fractions
    #: of the interbeat interval. They end at ``maxPeriodFraction``, since a
    #: longer one could never be drawn.
    phaseDelays: Tuple[float, float, float] = (0.10, MAX_PERIOD_FRACTION, 0.025)

    # --- engine --------------------------------------------------------------
    #: Probability that a trial draws its delay uniformly instead of by
    #: expected information gain.
    explore: float = 0.1
    #: Parameters whose posterior entropy the delay placement minimizes.
    targets: Tuple[str, ...] = ("mu",)
    #: The session stops once the credible interval of ``mu`` is no wider
    #: than :meth:`ci_width`, but not before ``minTrials`` and never after
    #: ``maxTrials``.
    minTrials: int = 15
    maxTrials: int = 60
    #: Width of the 95% credible interval of ``mu`` at which to stop, in ms
    #: (absolute axis) and in fractions of the period (phase axis).
    ciWidth: float = 100.0
    ciWidthPhase: float = 0.17

    # --- timing --------------------------------------------------------------
    #: Shortest physical R-to-tone delay requested, in seconds, on both axes:
    #: the 31 ms (p95, bench) it takes to know of a beat, plus ``audioLead``,
    #: plus ``latencyBias`` (see :mod:`cardioception.HSD._constants`). On the
    #: hardware dry run the beats of a train were polled up to 48 ms (p95) and
    #: 63 ms (p99) after their stamped R-wave, so set it from the lag a
    #: session actually shows. Candidates below it stay in the grid and are
    #: left out by :meth:`bounds`.
    minDelay: float = MIN_DELAY_S
    #: Longest delay, as a fraction of the current interbeat interval.
    maxPeriodFraction: float = MAX_PERIOD_FRACTION
    #: Fraction by which the absolute-axis ceiling drawn at the start of a
    #: trial is lowered below ``maxPeriodFraction`` of the period. The
    #: scheduler checks every beat against its own period without the margin,
    #: so without it the top candidate would abort whenever the next beat came
    #: slightly early.
    ceilingMargin: float = 0.05
    #: Seconds a tone is scheduled ahead of its onset.
    audioLead: float = AUDIO_LEAD
    #: Seconds of physical delay the recordings cannot see: the transport
    #: before the ECG is stamped plus the speaker after the onset the audio
    #: driver reports, 30 to 70 ms on the PAT dry run. Subtracted from every
    #: tone target and added to every realized delay before it reaches the
    #: engine, as the PAT task does.
    latencyBias: float = LATENCY_BIAS
    #: Inter-stimulus interval, drawn uniformly between the two values.
    isi: Tuple[float, float] = (0.25, 0.25)

    # --- responses -----------------------------------------------------------
    #: Seconds a participant has to make the decision.
    respMax: float = 5.0
    #: Seconds before a confidence rating can be submitted.
    minRatingTime: float = 0.5
    #: Seconds before the rating scale gives up and records no rating.
    maxRatingTime: float = 5.0
    #: Key that advances instruction screens.
    startKey: str = "space"
    #: Which key means which judgement. The names are written to the
    #: ``Decision`` column.
    response_keys: Mapping[str, str] = field(
        default_factory=lambda: {"Synchronous": "up", "NotSynchronous": "down"}
    )

    # --- presentation --------------------------------------------------------
    #: Text height, in height units.
    textSize: float = 0.04
    #: Fixation cross, in height units.
    fixationSize: float = 0.04
    #: The tone: frequency in Hz, duration and ramps in seconds, volume 0 to 1.
    toneFreq: float = TONE_FREQ
    toneSecs: float = TONE_SECS
    toneRamp: float = TONE_RAMP
    toneVolume: float = 0.5

    def __post_init__(self):
        if self.axis not in AXES:
            raise ValueError(f"axis should be one of {AXES}, got {self.axis!r}")
        if self.nTones < 1:
            raise ValueError("nTones should be at least 1")
        if not 1 <= self.minTrials <= self.maxTrials:
            raise ValueError("need 1 <= minTrials <= maxTrials")
        if not 0.0 < self.maxPeriodFraction < 1.0:
            raise ValueError("maxPeriodFraction should lie strictly between 0 and 1")
        if not 0.0 <= self.ceilingMargin < 1.0:
            raise ValueError("ceilingMargin should lie in [0, 1)")
        if not 0.0 <= self.explore <= 1.0:
            raise ValueError("explore should be a probability")
        if not self.targets or any(t not in PARAMETERS for t in self.targets):
            raise ValueError(f"targets should be a non-empty subset of {PARAMETERS}")
        for name in ("absoluteDelays", "phaseDelays"):
            low, high, step = getattr(self, name)
            if not (step > 0 and high >= low):
                raise ValueError(f"{name} should be (low, high, step) with step > 0")

    @property
    def allowedKeys(self):
        """The keys the decision screen listens for."""
        return list(self.response_keys.values())

    # --- the engine, for the chosen axis -------------------------------------

    def candidates(self) -> np.ndarray:
        """Candidate delays in engine units: ms (absolute) or fractions (phase).

        Phase candidates above ``maxPeriodFraction`` are dropped: the ceiling
        would refuse them on every trial.
        """
        if self.axis == "absolute":
            return _steps(*self.absoluteDelays)
        delays = _steps(*self.phaseDelays)
        return delays[delays <= self.maxPeriodFraction + 1e-9]

    def grids(self) -> Dict[str, np.ndarray]:
        """Parameter grids for :class:`~cardioception.HSD.psi.SynchronyPsi`.

        The absolute axis takes :func:`~cardioception.HSD.psi.default_grids`
        up to the longest candidate. The phase axis has ``mu`` from 0 to 1 in
        steps of 0.02 and ``sigma`` log-spaced from 0.03 to 0.5, with the same
        floor and peak grids.
        """
        if self.axis == "absolute":
            return default_grids(max_delay=float(self.absoluteDelays[1]))
        defaults = default_grids()
        return {
            "mu": _steps(0.0, 1.0, 0.02),
            "sigma": np.geomspace(0.03, 0.5, 20),
            "floor": defaults["floor"],
            "peak": defaults["peak"],
        }

    def ci_width(self) -> float:
        """Stopping width of the ``mu`` credible interval, in engine units."""
        return self.ciWidth if self.axis == "absolute" else self.ciWidthPhase

    def engine(self, rng: Optional[np.random.Generator] = None) -> SynchronyPsi:
        """A fresh posterior over the envelope for this configuration."""
        grids = self.grids()
        return SynchronyPsi(
            self.candidates(),
            mu=grids["mu"],
            sigma=grids["sigma"],
            floor=grids["floor"],
            peak=grids["peak"],
            targets=self.targets,
            explore=self.explore,
            rng=rng,
        )

    def bounds(self, period: float) -> Tuple[float, float]:
        """``(min_delay, max_delay)`` for ``next_delay``, given the period in s.

        In engine units: ms on the absolute axis, fractions of the period on
        the phase axis. The floor is ``minDelay``. On the absolute axis the
        ceiling is ``maxPeriodFraction * (1 - ceilingMargin)`` of the current
        period, leaving room for the next beats to come a little early. On the
        phase axis it is ``maxPeriodFraction`` itself: the delay scales with
        each beat's period, so the check cannot be tripped by variability.

        The floor is rounded up and the ceiling down, at six decimals, so a
        candidate inside the bounds is never refused by the scheduler.
        """
        if not period > 0:
            raise ValueError("period should be positive seconds")
        if self.axis == "absolute":
            low = self.minDelay * 1000.0
            high = self.maxPeriodFraction * (1.0 - self.ceilingMargin) * period * 1000.0
        else:
            low, high = self.minDelay / period, self.maxPeriodFraction
        return _round_up(low), _round_down(high)

    # --- records -------------------------------------------------------------

    def describe(self) -> Dict[str, Any]:
        """The whole configuration, for the manifest, ready for ``json.dumps``."""
        return _json_ready(asdict(self))

    def apply(self, parameters: Dict[str, Any]) -> None:
        """Write these factors into a parameters dictionary."""
        for name, value in asdict(self).items():
            parameters[name] = value
        parameters["allowedKeys"] = self.allowedKeys
