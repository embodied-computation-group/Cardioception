# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import shutil
import unittest
from unittest import TestCase

import numpy as np
from psychopy import prefs

prefs.hardware["audioLib"] = ["pygame"]

from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run


class TestHRD(TestCase):
    def test_parameters(self):
        """Test parameters function"""

        parameters = getParameters(
            setup="test", nTrials=80, exteroception=True, stairType="psi"
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
            stairType="updown",
            catchTrials=0.2,
        )
        parameters["win"].close()
        shutil.rmtree(parameters["resultPath"])

        assert sum(parameters["Modality"] == "Intero") == 2
        assert len(parameters["Modality"]) == 4
        assert len(parameters["staircaseType"]) == 4
        assert sum(parameters["staircaseType"] == "updown") == 4

    def test_run(self):
        """Test run function"""

        # VErsion 1
        parameters = getParameters(
            setup="test",
            nTrials=4,
            exteroception=True,
            stairType="psi",
            catchTrials=0.5,
        )
        parameters["nConfidence"] = 1
        parameters["nFeedback"] = 1

        run(parameters, confidenceRating=True, runTutorial=True)
        parameters["win"].close()
        shutil.rmtree(parameters["resultPath"])

        # Version 2
        parameters = getParameters(
            setup="test",
            nTrials=4,
            exteroception=False,
            stairType="updown",
            device="keyboard",
            catchTrials=0.0,
        )

        run(parameters, confidenceRating=True, runTutorial=False)
        parameters["win"].close()
        shutil.rmtree(parameters["resultPath"])


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
