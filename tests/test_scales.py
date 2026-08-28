# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Confidence scale definitions."""

import unittest

from cardioception.scales import (
    DISCRETE_1_7,
    DISCRETE_1_10,
    VAS_0_100,
    VAS_SIGNED_100,
    ConfidenceScale,
)


class TestConfidenceScale(unittest.TestCase):
    def test_level_counts(self):
        self.assertEqual(VAS_0_100.n_levels, 101)
        self.assertEqual(DISCRETE_1_7.n_levels, 7)
        self.assertEqual(DISCRETE_1_10.n_levels, 10)

    def test_granularity_changes_the_level_count(self):
        coarse = ConfidenceScale(kind="vas", low=0, high=100, granularity=5)
        self.assertEqual(coarse.n_levels, 21)

    def test_clamp_snaps_to_the_grid_and_the_bounds(self):
        coarse = ConfidenceScale(kind="vas", low=0, high=100, granularity=5)
        self.assertEqual(coarse.clamp(12), 10)
        self.assertEqual(coarse.clamp(13), 15)
        self.assertEqual(coarse.clamp(-40), 0)
        self.assertEqual(coarse.clamp(140), 100)

    def test_unit_conversion_round_trips(self):
        for scale in (VAS_0_100, DISCRETE_1_7, DISCRETE_1_10):
            for value in (scale.low, scale.high):
                self.assertEqual(scale.from_unit(scale.to_unit(value)), value)

    def test_unit_conversion_makes_scales_comparable(self):
        """The point of recording the scale: 1-7 and 0-100 become one measure."""
        self.assertAlmostEqual(DISCRETE_1_7.to_unit(7), VAS_0_100.to_unit(100))
        self.assertAlmostEqual(DISCRETE_1_7.to_unit(1), VAS_0_100.to_unit(0))
        self.assertAlmostEqual(DISCRETE_1_7.to_unit(4), 0.5)

    def test_describe_identifies_the_scale_without_the_pickle(self):
        described = DISCRETE_1_10.describe()
        self.assertEqual(described["ConfidenceScale"], "discrete")
        self.assertEqual(described["ConfidenceLow"], 1)
        self.assertEqual(described["ConfidenceHigh"], 10)
        self.assertEqual(described["ConfidenceLevels"], 10)

    def test_a_signed_scale_is_recognised_as_signed(self):
        self.assertTrue(VAS_SIGNED_100.signed)
        self.assertEqual(VAS_SIGNED_100.midpoint, 0)
        for scale in (VAS_0_100, DISCRETE_1_7, DISCRETE_1_10):
            self.assertFalse(scale.signed)

    def test_a_signed_rating_separates_into_confidence_and_belief(self):
        """The sign is the believed outcome; the magnitude is the confidence."""
        s = VAS_SIGNED_100
        self.assertEqual(s.magnitude(100), 1.0)
        self.assertEqual(s.magnitude(-100), 1.0)
        self.assertEqual(s.magnitude(0), 0.0)
        self.assertEqual(s.magnitude(-50), 0.5)

        self.assertIs(s.believes_correct(80), True)
        self.assertIs(s.believes_correct(-80), False)
        self.assertIsNone(s.believes_correct(0), "the midpoint asserts nothing")

    def test_an_unsigned_scale_carries_no_belief(self):
        self.assertIsNone(VAS_0_100.believes_correct(90))
        self.assertEqual(VAS_0_100.magnitude(50), 0.5)

    def test_signed_scales_still_round_trip_through_unit(self):
        for value in (-100, -37, 0, 51, 100):
            self.assertEqual(
                VAS_SIGNED_100.from_unit(VAS_SIGNED_100.to_unit(value)), value
            )

    def test_the_scale_records_that_it_is_signed(self):
        self.assertTrue(VAS_SIGNED_100.describe()["ConfidenceSigned"])
        self.assertFalse(VAS_0_100.describe()["ConfidenceSigned"])

    def test_a_midpoint_label_is_allowed(self):
        self.assertEqual(len(VAS_SIGNED_100.labels), 3)
        with self.assertRaises(ValueError):
            ConfidenceScale(labels=("a", "b", "c", "d"))

    def test_invalid_definitions_are_rejected(self):
        with self.assertRaises(ValueError):
            ConfidenceScale(kind="likert")
        with self.assertRaises(ValueError):
            ConfidenceScale(low=10, high=1)
        with self.assertRaises(ValueError):
            ConfidenceScale(granularity=0)


if __name__ == "__main__":
    unittest.main()


class TestTicksMatchLabels(unittest.TestCase):
    """PsychoPy snaps each label to a tick, so the counts have to agree.

    `Slider._getLabelParams` spreads labels with `linspace(left, right,
    num=len(labels))` and then snaps each to the nearest tick position. Three
    labels against two ticks put the midpoint label on top of an end label,
    which is what a signed scale with a "No idea" midpoint always did.
    """

    def test_a_two_label_scale_has_two_ticks(self):
        self.assertEqual(len(VAS_0_100.ticks), len(VAS_0_100.labels))
        self.assertEqual(VAS_0_100.ticks, VAS_0_100.bounds)

    def test_a_three_label_scale_gets_a_midpoint_tick(self):
        self.assertEqual(len(VAS_SIGNED_100.ticks), len(VAS_SIGNED_100.labels))
        self.assertEqual(VAS_SIGNED_100.ticks, (-100, 0.0, 100))

    def test_every_shipped_scale_agrees(self):
        for scale in (DISCRETE_1_10, VAS_0_100, VAS_SIGNED_100):
            with self.subTest(scale=scale.labels):
                self.assertEqual(len(scale.ticks), len(scale.labels))
