# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Design values the task used to hardcode, gathered in one place.

The principle is that the trial- and run-level functions should not carry
design values of their own. Changing the response window, the tutorial length
or the plausible heart-rate range meant editing the middle of
``getParameters``, so people either forked the package or monkey-patched the
parameters dictionary afterwards, where the change was invisible to anyone
reading the results.

This is not a claim to cover every conceivable change — trial counts, block
length and which conditions run are arguments to ``getParameters``, and the
stimulus timings that define the protocol are deliberately not settable here.
It covers the values that were hardcoded where they should not have been.

Set them here instead. The whole configuration is written to ``manifest.json``
at session start, so a change is recorded with the data it produced::

    from cardioception.HRD import getParameters
    from cardioception.HRD.config import TaskConfig

    parameters = getParameters(
        participant="sub-01",
        config=TaskConfig(respMax=8, nFeedback=10, HRcutOff=(45, 130)),
    )

Where the line is drawn: these are values someone changing the design would
reasonably want to set. Session identifiers belong in the call, stimulus
timings that define the protocol are deliberately fixed, and the psi solver's
grid precision stays in the code — it is a memory/resolution tradeoff rather
than a design choice, and every knob here costs a reader something.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class TaskConfig:
    """Design factors an experimenter is likely to want to change.

    Every default is the value the task used before this class existed, so an
    unconfigured session behaves exactly as it did.
    """

    # --- responses -----------------------------------------------------------
    #: Seconds a participant has to make the faster/slower decision.
    respMax: float = 5.0
    #: Seconds before a confidence rating can be submitted, so the starting
    #: value cannot be confirmed reflexively.
    minRatingTime: float = 0.5
    #: Seconds before the rating scale gives up and records no rating.
    maxRatingTime: float = 5.0
    #: Key that advances instruction screens.
    startKey: str = "space"
    #: Which key means which judgement. The values are the keys pressed; the
    #: names are the strings written to the `Decision` column.
    response_keys: Mapping[str, str] = field(
        default_factory=lambda: {"More": "up", "Less": "down"}
    )

    # --- tutorial ------------------------------------------------------------
    #: Tutorial trials that show whether the answer was correct.
    nFeedback: int = 5
    #: Tutorial trials that ask for a confidence rating.
    nConfidence: int = 8

    # --- timing --------------------------------------------------------------
    #: Inter-stimulus interval, drawn uniformly between the two values. The
    #: default is a fixed 0.25 s.
    isi: Tuple[float, float] = (0.25, 0.25)
    #: Seconds of listening per trial. Matches the interoceptive recording
    #: window so both modalities give the same listening time; changing it
    #: changes the exteroceptive control as well as the recording.
    listeningDuration: float = 5.0

    # --- physiology ----------------------------------------------------------
    #: Heart rates outside this range are treated as artefact and the listening
    #: window is retaken. Biologically implausible values, not clinical limits.
    HRcutOff: Tuple[float, float] = (40.0, 120.0)
    #: How many times to retake a window before accepting whatever it holds and
    #: flagging the trial.
    maxHeartRateAttempts: int = 10
    #: Range the exteroceptive reference tone is drawn from, as
    #: (low, high, step) in BPM.
    exteroBPMRange: Tuple[float, float, float] = (40.0, 100.0, 0.5)

    # --- staircase -----------------------------------------------------------
    #: Bounds of the psi staircase, in delta-BPM. These set the range of
    #: stimuli a participant can be shown, so they are a design decision.
    intensRange: Tuple[float, float] = (-50.5, 50.5)
    alphaRange: Tuple[float, float] = (-50.5, 50.5)
    betaRange: Tuple[float, float] = (0.1, 25.0)
    #: Lapse rate, held fixed rather than estimated. A modelling choice, and
    #: one people reasonably disagree about, so it is settable.
    delta: float = 0.02

    # --- presentation --------------------------------------------------------
    #: Text height, in height units.
    textSize: float = 0.04

    @property
    def allowedKeys(self):
        """The keys the decision screen listens for."""
        return list(self.response_keys.values())

    def describe(self) -> Dict[str, Any]:
        """The whole configuration, for the manifest."""
        return asdict(self)

    def apply(self, parameters: Dict[str, Any]) -> None:
        """Write these factors into a parameters dictionary."""
        for name, value in asdict(self).items():
            parameters[name] = value
        parameters["allowedKeys"] = self.allowedKeys
