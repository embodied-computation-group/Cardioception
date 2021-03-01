# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import unittest
from unittest import TestCase

import numpy as np
import pkg_resources
from psychopy import sound

from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import confidenceRatingTask, responseDecision, trial


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

        assert sum(parameters["Modality"] == "Intero") == 2
        assert len(parameters["Modality"]) == 4
        assert len(parameters["staircaseType"]) == 4
        assert sum(parameters["staircaseType"] == "updown") == 4

    def test_confidenceRatingTask(self):
        """Test confidence rating trial"""

        parameters = getParameters(
            setup="test",
            nTrials=200,
            exteroception=False,
            stairType="updown",
            catchTrials=0.5,
        )

        parameters["minRatingTime"] = 0.0
        parameters["maxRatingTime"] = 0.1

        parameters["device"] = "keyboard"
        parameters["confScale"] = [1, 7]
        (
            confidence,
            confidenceRT,
            ratingProvided,
            ratingEndTrigger,
        ) = confidenceRatingTask(parameters)

        parameters["device"] = "mouse"
        (
            confidence,
            confidenceRT,
            ratingProvided,
            ratingEndTrigger,
        ) = confidenceRatingTask(parameters)

        parameters["win"].close()

        assert confidence is None
        assert confidenceRT is None
        assert ratingProvided is False
        assert isinstance(ratingEndTrigger, float)

    def test_trial(self):
        """Test confidence rating trial"""

        parameters = getParameters(
            setup="test",
            nTrials=200,
            exteroception=False,
            stairType="updown",
            catchTrials=0.5,
        )
        (
            condition,
            listenBPM,
            responseBPM,
            decision,
            decisionRT,
            confidence,
            confidenceRT,
            alpha,
            isCorrect,
            respProvided,
            ratingProvided,
            startTrigger,
            soundTrigger,
            responseMadeTrigger,
            ratingStartTrigger,
            ratingEndTrigger,
            endTrigger,
        ) = trial(parameters, alpha=10, modality="Intero", feedback=True)
        parameters["win"].close()

        assert condition == "More"
        assert listenBPM == 60.0
        assert responseBPM == 70.0
        assert decision is None
        assert decisionRT is None
        assert confidence is None
        assert confidenceRT is None
        assert alpha == 10
        assert isCorrect is None
        assert respProvided is False
        assert ratingProvided is False
        assert isinstance(soundTrigger, float)
        assert isinstance(startTrigger, float)
        assert isinstance(responseMadeTrigger, float)
        assert ratingStartTrigger is None
        assert ratingEndTrigger is None
        assert isinstance(endTrigger, float)

    def test_responseDecision(self):
        """Test decision trial"""

        parameters = getParameters(
            setup="test",
            nTrials=200,
            exteroception=False,
            stairType="updown",
            catchTrials=0.5,
        )
        this_hr = sound.Sound(
            pkg_resources.resource_filename("cardioception.HRD", "Sounds/60.0.wav")
        )

        (
            responseMadeTrigger,
            responseTrigger,
            respProvided,
            decision,
            decisionRT,
            isCorrect,
        ) = responseDecision(
            this_hr=this_hr, parameters=parameters, feedback=False, condition="Less"
        )
        parameters["win"].close()

        assert isinstance(responseMadeTrigger, float)
        assert isinstance(responseTrigger, float)
        assert respProvided is False
        assert decision is None
        assert decisionRT is None
        assert isCorrect is None


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
