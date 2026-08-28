# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Confidence scale definitions."""

import unittest

from cardioception.scales import DISCRETE_1_7, DISCRETE_1_10, VAS_0_100, ConfidenceScale


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

    def test_invalid_definitions_are_rejected(self):
        with self.assertRaises(ValueError):
            ConfidenceScale(kind="likert")
        with self.assertRaises(ValueError):
            ConfidenceScale(low=10, high=1)
        with self.assertRaises(ValueError):
            ConfidenceScale(granularity=0)


if __name__ == "__main__":
    unittest.main()
