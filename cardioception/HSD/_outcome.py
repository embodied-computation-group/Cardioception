# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""What one HSD trial produced, and how it becomes a row of ``final.txt``.

The names of the columns, and their order, are decided in one place:
:meth:`HSDTrialOutcome.row`. Columns, in order::

    Trial, Axis, RequestedDelay, RealizedDelay, RealizedCorrected,
    nDelivered, nSkipped, Aborted, AbortReason, Explored,
    Decision, DecisionRT, Confidence, ConfidenceRT, ConfidenceUnit, Device,
    <scale columns: ConfidenceScale, ConfidenceLow, ConfidenceHigh,
     ConfidenceGranularity, ConfidenceLevels, ConfidenceSigned>,
    DecisionProvided, RatingProvided, nTrials,
    MuMean, MuMedian, MuCILow, MuCIHigh,
    SigmaMean, SigmaMedian, SigmaCILow, SigmaCIHigh,
    FloorMean, PeakMean, DetectionEvidence, DetectionBF, PeriodMean,
    <quality columns>,
    StartTrigger, TrainStart, TrainStop, DecisionStart, ResponseMade,
    RatingStart, RatingEnds, endTrigger

Units: ``RequestedDelay``, ``RealizedDelay`` and ``RealizedCorrected`` are in
engine units, ms on the absolute axis and fractions of the interbeat interval
on the phase axis, as are the ``Mu`` and ``Sigma`` summaries. Both realized
values are measured against the stamped R-wave. ``RealizedCorrected`` is the
value the engine was updated with.

On the absolute axis ``RealizedCorrected`` is ``RealizedDelay`` plus the
bridge lag. On the phase axis they are different quantities:

- ``RealizedDelay`` is the realized delay as a fraction of the *observed*
  interbeat interval, averaged over the tones whose next beat was seen during
  the train (usually not the last one). Empty if there were none.
- ``RealizedCorrected`` is the mean realized delay plus the bridge lag, as a
  fraction of the mean *anticipated* period: the same period the delay was
  scheduled with, so it is on the scale the engine chose from.

When the heart speeds up or slows down during a train, the two differ by more
than the lag. ``PeriodMean`` is seconds.
Triggers are clock seconds. The posterior summaries are taken after the
trial's update.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ._stimulus import TrainResult
from .psi import SynchronyPsi


@dataclass
class HSDTrialOutcome:
    """One trial's measurements, the train and the posterior after it."""

    trial: int
    axis: str
    #: The delay asked for, engine units.
    requestedDelay: float
    #: Mean realized delay against the stamped R-wave, engine units.
    realizedDelay: Optional[float]
    #: ``realizedDelay`` plus the bridge lag, engine units.
    realizedCorrected: Optional[float]
    nDelivered: int
    nSkipped: int
    aborted: bool
    explored: bool
    decision: Optional[str]
    decisionRT: Optional[float]
    confidence: Optional[float]
    confidenceRT: Optional[float]
    respProvided: bool
    ratingProvided: bool
    abortReason: Optional[str] = None

    # --- posterior after the update ------------------------------------------
    muMean: Optional[float] = None
    muMedian: Optional[float] = None
    muCILow: Optional[float] = None
    muCIHigh: Optional[float] = None
    sigmaMean: Optional[float] = None
    sigmaMedian: Optional[float] = None
    sigmaCILow: Optional[float] = None
    sigmaCIHigh: Optional[float] = None
    floorMean: Optional[float] = None
    peakMean: Optional[float] = None
    detectionEvidence: Optional[float] = None
    detectionBF: Optional[float] = None
    #: Mean anticipated interbeat interval of the delivered tones, seconds.
    periodMean: Optional[float] = None

    # --- clock times ---------------------------------------------------------
    startTrigger: Optional[float] = None
    trainStart: Optional[float] = None
    trainStop: Optional[float] = None
    decisionStart: Optional[float] = None
    responseMade: Optional[float] = None
    ratingStart: Optional[float] = None
    ratingEnd: Optional[float] = None
    endTrigger: Optional[float] = None

    #: Quality control rather than measurement, written as its own columns.
    quality: Dict[str, Any] = field(default_factory=dict)

    def row(self, **context) -> Dict[str, Any]:
        """This trial as one row, ready for ``pd.DataFrame``.

        ``context`` carries what the run knows and the trial does not:
        ``Device``, ``ConfidenceUnit``, ``scale`` (the columns of
        :meth:`cardioception.scales.ConfidenceScale.describe`) and ``nTrials``.
        """
        row: Dict[str, Any] = {
            "Trial": self.trial,
            "Axis": self.axis,
            "RequestedDelay": self.requestedDelay,
            "RealizedDelay": self.realizedDelay,
            "RealizedCorrected": self.realizedCorrected,
            "nDelivered": self.nDelivered,
            "nSkipped": self.nSkipped,
            "Aborted": self.aborted,
            "AbortReason": self.abortReason,
            "Explored": self.explored,
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
                "DecisionProvided": self.respProvided,
                "RatingProvided": self.ratingProvided,
                "nTrials": context.get("nTrials"),
                "MuMean": self.muMean,
                "MuMedian": self.muMedian,
                "MuCILow": self.muCILow,
                "MuCIHigh": self.muCIHigh,
                "SigmaMean": self.sigmaMean,
                "SigmaMedian": self.sigmaMedian,
                "SigmaCILow": self.sigmaCILow,
                "SigmaCIHigh": self.sigmaCIHigh,
                "FloorMean": self.floorMean,
                "PeakMean": self.peakMean,
                "DetectionEvidence": self.detectionEvidence,
                "DetectionBF": self.detectionBF,
                "PeriodMean": self.periodMean,
            }
        )
        row.update(self.quality)
        row.update(
            {
                "StartTrigger": self.startTrigger,
                "TrainStart": self.trainStart,
                "TrainStop": self.trainStop,
                "DecisionStart": self.decisionStart,
                "ResponseMade": self.responseMade,
                "RatingStart": self.ratingStart,
                "RatingEnds": self.ratingEnd,
                "endTrigger": self.endTrigger,
            }
        )
        return row


def train_fields(result: TrainResult) -> Dict[str, Any]:
    """The outcome fields a :class:`TrainResult` fills, in engine units.

    ``TrainResult.realized_mean`` is seconds on the absolute axis; here it is
    converted to ms so that every delay column of a row has the same unit.
    """
    realized = result.realized_mean
    if realized is not None and result.axis == "absolute":
        realized = realized * 1000.0
    periods = [t.period for t in result.delivered if t.period]
    return {
        "axis": result.axis,
        "requestedDelay": result.delay,
        "realizedDelay": realized,
        "realizedCorrected": result.realized_corrected,
        "nDelivered": result.n_delivered,
        "nSkipped": result.n_skipped,
        "aborted": result.aborted,
        "abortReason": result.abort_reason,
        "periodMean": sum(periods) / len(periods) if periods else None,
        "trainStart": result.started,
        "trainStop": result.ended,
    }


def posterior_fields(psi: SynchronyPsi) -> Dict[str, Any]:
    """The outcome fields summarizing the posterior of ``psi``."""
    mu, sigma = psi.estimate("mu"), psi.estimate("sigma")
    return {
        "muMean": mu["mean"],
        "muMedian": mu["median"],
        "muCILow": mu["ci_low"],
        "muCIHigh": mu["ci_high"],
        "sigmaMean": sigma["mean"],
        "sigmaMedian": sigma["median"],
        "sigmaCILow": sigma["ci_low"],
        "sigmaCIHigh": sigma["ci_high"],
        "floorMean": psi.estimate("floor")["mean"],
        "peakMean": psi.estimate("peak")["mean"],
        "detectionEvidence": psi.detection_evidence(),
        "detectionBF": psi.detection_bayes_factor(),
    }
