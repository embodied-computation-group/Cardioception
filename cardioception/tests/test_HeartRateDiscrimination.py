# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import unittest
import pytest
from unittest import TestCase
from cardioception.HeartRateDiscrimination import task
from cardioception.HeartRateDiscrimination.parameters import getParameters


class TestHeartRateDiscrimination(TestCase):

    def test_trial(self):
        """Test task functions"""

        # Set global task parameters here
        params = getParameters(setup='behavioral')

        # Limit the number of trials to run
        params['Conditions'] = params['Conditions'][:4]
        params['nFeedback'] = 1
        params['nConfidence'] = 1
        params['nBreaking'] = 2

        # Run task
        task.run(params, win=params['win'], confidenceRating=True,
                 runTutorial=True)

        # Save results
        params['win'].close()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
