# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Every tone the task can ask for must exist on disk.

The filename is built from a float, so an uncovered rate or an unexpected repr
is a crash mid-session. Walks the reachable space rather than sampling it.
"""

import os
import unittest

import numpy as np

from cardioception._resources import resource_filename

BPM_FLOOR, BPM_CEIL = 15.0, 199.0

# Interoceptive listening rates are whatever the heart produced, rounded to the
# nearest half beat and accepted only inside HRcutOff. Exteroceptive rates are
# drawn from a fixed grid in the task. Alphas come off the psi grid, which spans
# intensRange at intensPrecision=1, plus the fixed catch-trial and tutorial
# intensities.
INTERO_BPM = np.arange(40.0, 120.5, 0.5)
EXTERO_BPM = np.arange(40.0, 100.0, 0.5)
PSI_ALPHA = np.arange(-50.5, 51.5, 1.0)
CATCH_ALPHA = np.array([-30.0, 10.0, -20.0, 20.0, -10.0, 30.0])
TUTORIAL_ALPHA = np.array([-30.0, -20.0, -10.0, -1.0, 1.0, 10.0, 20.0, 30.0])


def _sound_path(response_bpm):
    return resource_filename("cardioception.HRD", f"Sounds/{response_bpm}.wav")


class TestSoundInventory(unittest.TestCase):
    def test_every_reachable_tone_exists(self):
        alphas = np.concatenate([PSI_ALPHA, CATCH_ALPHA, TUTORIAL_ALPHA])
        missing, checked = set(), 0
        for listen in np.concatenate([INTERO_BPM, EXTERO_BPM]):
            for alpha in alphas:
                response = float(np.clip(listen + alpha, BPM_FLOOR, BPM_CEIL))
                checked += 1
                if not os.path.exists(_sound_path(response)):
                    missing.add(response)
        self.assertEqual(missing, set(), f"missing tones after {checked} combinations")
        # Breadth guard, not an exact count: if someone narrows the reachable
        # ranges above, this test would still pass while checking almost
        # nothing. 32,596 is the current sweep.
        self.assertGreater(checked, 30000)

    def test_the_listening_tones_themselves_exist(self):
        for listen in np.concatenate([INTERO_BPM, EXTERO_BPM]):
            self.assertTrue(
                os.path.exists(_sound_path(float(listen))), f"missing {listen}"
            )

    def test_the_clipping_bounds_exist(self):
        for bound in (BPM_FLOOR, BPM_CEIL):
            self.assertTrue(os.path.exists(_sound_path(bound)))

    def test_floats_format_to_the_names_on_disk(self):
        """numpy float64 and python float must both render as e.g. '40.0'."""
        for value in (40.0, np.float64(40.0), 15.0, 199.0, 100.5):
            self.assertTrue(os.path.exists(_sound_path(value)), f"{value!r}")

    def test_every_rate_lands_on_the_half_beat_grid(self):
        """The inventory is a 0.5 grid, so any reachable rate must be on it."""
        for listen in (40.0, 72.5, 119.5):
            for alpha in np.concatenate([PSI_ALPHA, CATCH_ALPHA]):
                response = float(np.clip(listen + alpha, BPM_FLOOR, BPM_CEIL))
                self.assertAlmostEqual((response * 2) % 1, 0.0, places=9)


if __name__ == "__main__":
    unittest.main()
