# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Each constant still equals the literal it replaced.

Written from the pre-refactor source. Naming a value is only safe if the name
is pinned to the number, because a transcription error in a trigger code is
invisible in the results file and wrong in every physiological analysis made
from the recording afterwards.
"""

import unittest

from cardioception.HBC import _constants as hbc
from cardioception.HRD import _constants as hrd


class TestHRDConstants(unittest.TestCase):
    def test_trigger_codes(self):
        self.assertEqual(hrd.Trigger.TRIAL_START, 1)
        self.assertEqual(hrd.Trigger.LISTENING_START, 2)
        self.assertEqual(hrd.Trigger.DECISION_START, 3)
        self.assertEqual(hrd.Trigger.CONFIDENCE_START, 4)
        self.assertEqual(hrd.Trigger.TRIAL_STOP, 5)

    def test_the_codes_are_plain_integers_on_the_wire(self):
        """They are assigned into the recording's channel, which holds numbers."""
        self.assertIsInstance(hrd.Trigger.TRIAL_START, int)
        self.assertEqual(int(hrd.Trigger.DECISION_START), 3)

    def test_signal_constants(self):
        self.assertEqual(hrd.OXIMETER_SFREQ, 75)
        self.assertEqual(hrd.PPG_SFREQ, 1000)
        self.assertEqual(hrd.LISTENING_DURATION, 5.0)
        self.assertEqual(hrd.ANALYSIS_MARGIN, 1.0)

    def test_the_default_window_is_the_slice_it_replaced(self):
        """The window is now derived from `listeningDuration` rather than fixed.

        At the default the arithmetic has to come out where the hardcoded
        constants were: 6 s kept at 75 Hz, and 5 s of resampled signal
        searched for peaks.
        """
        duration = hrd.LISTENING_DURATION
        kept = int(hrd.OXIMETER_SFREQ * (duration + hrd.ANALYSIS_MARGIN))
        peak_window = int(duration * hrd.PPG_SFREQ)
        self.assertEqual(kept, 75 * 6)
        self.assertEqual(peak_window, 5000)

    def test_the_default_matches_the_configuration_default(self):
        """One source: the constant is only TaskConfig's default."""
        from cardioception.HRD.config import TaskConfig

        self.assertEqual(TaskConfig().listeningDuration, hrd.LISTENING_DURATION)

    def test_tone_range(self):
        self.assertEqual(hrd.TONE_BPM_MIN, 15.0)
        self.assertEqual(hrd.TONE_BPM_MAX, 199.0)


class TestHBCConstants(unittest.TestCase):
    def test_trigger_codes(self):
        self.assertEqual(hbc.Trigger.LISTENING_START, 1)
        self.assertEqual(hbc.Trigger.LISTENING_STOP, 2)

    def test_the_two_tasks_disagree_about_what_the_codes_mean(self):
        """Documented deliberately: the same channel, different vocabularies."""
        self.assertEqual(int(hbc.Trigger.LISTENING_START), 1)
        self.assertEqual(int(hrd.Trigger.TRIAL_START), 1)
        self.assertNotEqual(
            hbc.Trigger.LISTENING_START.name, hrd.Trigger.TRIAL_START.name
        )


if __name__ == "__main__":
    unittest.main()
