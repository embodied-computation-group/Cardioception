# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import shutil
import tempfile
import unittest
from unittest import TestCase

import numpy as np
import pytest

from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run


class TestHRD(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_parameters(self):
        """Test parameters function"""

        parameters = getParameters(
            setup="test",
            nTrials=80,
            exteroception=True,
            stairType="psi",
            resultPath=self.tmp,
        )
        parameters["win"].close()

        assert len(parameters["Modality"]) == 80
        assert sum(parameters["Modality"] == "Extero") == 40
        assert len(parameters["staircaseType"]) == 80
        assert np.all(parameters["staircaseType"] == "psi")

        parameters = getParameters(
            setup="test",
            nTrials=4,
            exteroception=True,
            catchTrials=0.2,
            resultPath=self.tmp,
        )
        parameters["win"].close()

        assert sum(parameters["Modality"] == "Intero") == 2
        assert len(parameters["Modality"]) == 4
        assert len(parameters["staircaseType"]) == 4
        assert sum(parameters["staircaseType"] == "psi") == 4

    def test_the_updown_staircase_is_gone(self):
        """Removed in 0.8.0. The error has to say so, not just reject."""
        with pytest.raises(ValueError, match="removed in 0.8.0"):
            getParameters(setup="test", nTrials=4, stairType="updown")

    @pytest.mark.blocking
    def test_run(self):
        """A whole session driven by hand.

        test_headless.py covers the same ground with the autopilot and the
        replay recorder, so this is kept only as a manual smoke test.
        """

        # VErsion 1
        parameters = getParameters(
            setup="test",
            nTrials=4,
            exteroception=True,
            stairType="psi",
            catchTrials=0.5,
            resultPath=self.tmp,
        )
        parameters["nConfidence"] = 1
        parameters["nFeedback"] = 1

        run(parameters, confidenceRating=True, runTutorial=True)
        parameters["win"].close()

        # Version 2
        parameters = getParameters(
            setup="test",
            nTrials=4,
            exteroception=False,
            device="keyboard",
            catchTrials=0.0,
            resultPath=self.tmp,
        )

        run(parameters, confidenceRating=True, runTutorial=False)
        parameters["win"].close()


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
