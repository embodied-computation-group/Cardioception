# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
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
grid precision is not a knob of its own — it is a memory/resolution tradeoff
rather than a design choice, and every knob here costs a reader something. It
moves only as part of a named psi preset.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from ._constants import LISTENING_DURATION

_LEGACY_PSI: Dict[str, Any] = {
    "intensRange": (-50.5, 50.5),
    "alphaRange": (-50.5, 50.5),
    "betaRange": (0.1, 25.0),
    "betaPrecision": 0.1,
    "delta": 0.02,
}

#: Psi staircase settings, per modality, selected by ``TaskConfig.psiPreset``.
#:
#: ``"legacy"`` is the setting of the original HRD paper (Legrand et al.,
#: 2022) and of every release before 1.0: uniform over the full stimulus range
#: in both conditions. ``"courtin"`` narrows the threshold and slope ranges to
#: what the hierarchical refit of the Visceral Mind Project data found
#: plausible, separately for each condition, and halves the lapse rate
#: (Courtin et al., 2026). PsychoPy's psi method only takes a uniform prior, so
#: a narrower range is the way to concentrate it. The ranges are hard bounds: a
#: participant whose threshold lies outside them is estimated at the edge.
PSI_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "legacy": {"Intero": dict(_LEGACY_PSI), "Extero": dict(_LEGACY_PSI)},
    "courtin": {
        "Intero": {
            "intensRange": (-50.5, 50.5),
            "alphaRange": (-42.0, 26.0),
            "betaRange": (3.2, 29.0),
            "betaPrecision": 0.2,
            "delta": 0.01,
        },
        "Extero": {
            "intensRange": (-50.5, 50.5),
            "alphaRange": (-9.0, 9.0),
            "betaRange": (2.5, 15.2),
            "betaPrecision": 0.2,
            "delta": 0.01,
        },
    },
}


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
    #: Seconds of listening per trial, in both modalities: the exteroceptive
    #: tone plays for this long and the interoceptive pulse is recorded for
    #: it. The peak-detection window follows from it, so shortening it below
    #: about two seconds leaves too few beats to measure a rate.
    listeningDuration: float = LISTENING_DURATION

    # --- physiology ----------------------------------------------------------
    #: Heart rates outside this range are treated as artefact and the listening
    #: window is retaken. Biologically implausible values, not clinical limits.
    HRcutOff: Tuple[float, float] = (40.0, 120.0)
    #: Keep the pulse recorded for the whole session, not only inside the
    #: listening windows. Off by default: it costs per-frame work, and every
    #: existing study is calibrated against the trial-window behaviour. When
    #: on, the recorder is a `ContinuousOximeter` and the serial buffer is
    #: drained on every frame the task holds a screen for.
    continuousRecording: bool = False
    #: How many times to retake a window before accepting whatever it holds and
    #: flagging the trial.
    maxHeartRateAttempts: int = 10
    #: Range the exteroceptive reference tone is drawn from, as
    #: (low, high, step) in BPM.
    exteroBPMRange: Tuple[float, float, float] = (40.0, 100.0, 0.5)

    # --- staircase -----------------------------------------------------------
    #: Named psi settings for both staircases, from :data:`PSI_PRESETS`:
    #: ``"legacy"`` (the default, as in the original paper) or ``"courtin"``.
    psiPreset: str = "legacy"
    #: Bounds of the psi staircase, in delta-BPM. These set the range of
    #: stimuli a participant can be shown, so they are a design decision.
    #: ``None`` takes the preset's value; a value overrides it in both
    #: conditions.
    intensRange: Optional[Tuple[float, float]] = None
    alphaRange: Optional[Tuple[float, float]] = None
    betaRange: Optional[Tuple[float, float]] = None
    #: Lapse rate, held fixed rather than estimated. A modelling choice, and
    #: one people reasonably disagree about, so it is settable. ``None`` takes
    #: the preset's value.
    delta: Optional[float] = None

    # --- presentation --------------------------------------------------------
    #: Text height, in height units.
    textSize: float = 0.04
    #: Fixation cross, in height units. Was 0.1 — a tenth of the screen height,
    #: around 144 px on a 1440-pixel display, which is several times the usual
    #: half to one degree.
    fixationSize: float = 0.04

    def __post_init__(self) -> None:
        if self.psiPreset not in PSI_PRESETS:
            raise ValueError(
                f"psiPreset should be one of {sorted(PSI_PRESETS)}, "
                f"got {self.psiPreset!r}"
            )

    @property
    def allowedKeys(self):
        """The keys the decision screen listens for."""
        return list(self.response_keys.values())

    def psi(self, modality: str) -> Dict[str, Any]:
        """The psi settings one staircase runs with: the preset, then overrides."""
        settings = dict(PSI_PRESETS[self.psiPreset][modality])
        for name in ("intensRange", "alphaRange", "betaRange", "delta"):
            value = getattr(self, name)
            if value is not None:
                settings[name] = value
        return settings

    def describe(self) -> Dict[str, Any]:
        """The whole configuration, for the manifest, with the psi settings
        each staircase actually used."""
        described = asdict(self)
        described["psi"] = {m: self.psi(m) for m in ("Intero", "Extero")}
        return described

    def apply(self, parameters: Dict[str, Any]) -> None:
        """Write these factors into a parameters dictionary."""
        for name, value in asdict(self).items():
            parameters[name] = value
        parameters["psi"] = {m: self.psi(m) for m in ("Intero", "Extero")}
        parameters["allowedKeys"] = self.allowedKeys
