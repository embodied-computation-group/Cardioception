# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""TrialOutcome owns the results row, so its column order is the file's."""

import unittest

from cardioception.HRD._outcome import TrialOutcome

MEASUREMENTS = dict(
    condition="More",
    listenBPM=60.0,
    responseBPM=65.0,
    decision="More",
    decisionRT=1.2,
    confidence=80,
    confidenceRT=0.9,
    alpha=5.0,
    isCorrect=True,
    respProvided=True,
    ratingProvided=True,
)

CONTEXT = dict(
    TrialType="psi",
    Modality="Intero",
    StairCond="psi",
    Device="mouse",
    ConfidenceUnit=0.8,
    scale={"ConfidenceScale": "vas", "ConfidenceLevels": 101},
    nRepresentations=0,
    nTrials=3,
    EstimatedThreshold=1.5,
    EstimatedSlope=2.5,
)


class TestTrialOutcome(unittest.TestCase):
    def test_the_row_is_one_scalar_per_column(self):
        """Scalars, so rows can be collected in a list and framed at the end."""
        row = TrialOutcome(**MEASUREMENTS).row(**CONTEXT)
        for column, value in row.items():
            self.assertNotIsInstance(value, list, column)
        self.assertEqual(row["Decision"], "More")
        self.assertEqual(row["listenBPM"], 60.0)

    def test_column_order_is_fixed_here_not_by_call_order(self):
        """Reordering the keyword arguments must not reorder the file."""
        outcome = TrialOutcome(**MEASUREMENTS)
        forward = list(outcome.row(**CONTEXT))
        backward = list(outcome.row(**dict(reversed(list(CONTEXT.items())))))
        self.assertEqual(forward, backward)

    def test_the_scale_and_quality_columns_land_where_they_used_to(self):
        outcome = TrialOutcome(**MEASUREMENTS, quality={"HeartRateAttempts": 1})
        columns = list(outcome.row(**CONTEXT))
        self.assertEqual(columns[columns.index("Device") + 1], "ConfidenceScale")
        self.assertEqual(
            columns[columns.index("nRepresentations") + 1], "HeartRateAttempts"
        )
        self.assertEqual(columns[0], "TrialType")
        self.assertEqual(columns[-1], "endTrigger")

    def test_quality_defaults_to_empty_rather_than_shared(self):
        """A mutable default would be shared by every trial in the session."""
        first, second = TrialOutcome(**MEASUREMENTS), TrialOutcome(**MEASUREMENTS)
        first.quality["x"] = 1
        self.assertEqual(second.quality, {})

    def test_it_still_unpacks_like_the_tuple_it_replaced(self):
        condition, listenBPM = list(TrialOutcome(**MEASUREMENTS))[:2]
        self.assertEqual(condition, "More")
        self.assertEqual(listenBPM, 60.0)


if __name__ == "__main__":
    unittest.main()
