# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""What one trial produced, and how it becomes a row of the results file.

`trial()` returned an 18-element tuple, unpacked positionally at its one
non-tutorial call site. Adding a measurement meant editing the tuple, the
unpacking and the results dictionary together and in the same order; getting
that wrong swaps two columns silently, and the file still looks right.

The names are the file's column names, so :meth:`TrialOutcome.row` is the only
place that decides what a results row contains.
"""

from dataclasses import dataclass, fields
from typing import Any, Dict, Optional


@dataclass
class TrialOutcome:
    """One trial's measurements.

    Attributes are what the trial produced. Everything about *which* trial it
    was — the staircase, the modality, the trial number — belongs to the run
    and is added by :meth:`row`.
    """

    condition: Optional[str]
    listenBPM: float
    responseBPM: float
    decision: Optional[str]
    decisionRT: Optional[float]
    confidence: Optional[float]
    confidenceRT: Optional[float]
    alpha: float
    isCorrect: Optional[bool]
    respProvided: bool
    ratingProvided: bool

    #: Absolute times, seconds since the epoch, for aligning with the recording.
    startTrigger: Optional[float] = None
    soundTrigger: Optional[float] = None
    responseMadeTrigger: Optional[float] = None
    ratingStartTrigger: Optional[float] = None
    ratingEndTrigger: Optional[float] = None
    endTrigger: Optional[float] = None

    #: How the heart rate was obtained and how the presentation went. Kept as a
    #: mapping because it is quality control rather than measurement, and the
    #: two are worth telling apart.
    quality: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.quality is None:
            self.quality = {}

    def row(self, **context) -> Dict[str, list]:
        """This trial as one row, ready for ``pd.DataFrame``.

        ``context`` carries what the run knows and the trial does not:
        ``TrialType``, ``Modality``, ``StairCond``, ``nTrials`` and the
        staircase estimates. Column order is fixed here so the results file
        does not depend on the order arguments happened to be passed in.
        """
        row: Dict[str, Any] = {
            "TrialType": context.get("TrialType"),
            "Condition": self.condition,
            "Modality": context.get("Modality"),
            "StairCond": context.get("StairCond"),
            "Decision": self.decision,
            "DecisionRT": self.decisionRT,
            "Confidence": self.confidence,
            "ConfidenceRT": self.confidenceRT,
            "ConfidenceUnit": context.get("ConfidenceUnit"),
            "Device": context.get("Device"),
        }
        row.update(context.get("scale", {}))
        row.update(
            {
                "Alpha": self.alpha,
                "listenBPM": self.listenBPM,
                "responseBPM": self.responseBPM,
                "nRepresentations": context.get("nRepresentations"),
            }
        )
        row.update(self.quality)
        row.update(
            {
                "ResponseCorrect": self.isCorrect,
                "DecisionProvided": self.respProvided,
                "RatingProvided": self.ratingProvided,
                "nTrials": context.get("nTrials"),
                "EstimatedThreshold": context.get("EstimatedThreshold"),
                "EstimatedSlope": context.get("EstimatedSlope"),
                "StartListening": self.startTrigger,
                "StartDecision": self.soundTrigger,
                "ResponseMade": self.responseMadeTrigger,
                "RatingStart": self.ratingStartTrigger,
                "RatingEnds": self.ratingEndTrigger,
                "endTrigger": self.endTrigger,
            }
        )
        return {key: [value] for key, value in row.items()}

    def __iter__(self):
        """Unpack like the tuple this replaced, for the tutorial call sites."""
        return iter(getattr(self, f.name) for f in fields(self))
