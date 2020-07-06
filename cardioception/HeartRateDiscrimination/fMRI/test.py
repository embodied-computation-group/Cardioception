# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from psychopy import event
from cardioception.HeartRateDiscrimination.fMRI.parameters import getParameters
from cardioception.HeartRateDiscrimination.fMRI.task import run
from psychopy.event import Mouse
import numpy as np


def test_HRD():

    # Set global task parameters here
    parameters = getParameters('test', 1)
    parameters['win'].close()
    # Limit the number of trials to run
    parameters['Conditions'] = parameters['Conditions'][:4]
    parameters['nFeedback'] = 1
    parameters['nConfidence'] = 1
    parameters['nBreaking'] = 2

    # Wait for fMRI to start
    event.waitKeys(keyList='5')

    # Run task
    results_df = run(parameters, win=parameters['win'],
                     confidenceRating=True, runTutorial=True)

    # Save results
    results_df.to_csv(parameters['results'] + '/test.txt')

    # Save results
    parameters['win'].close()


if __name__ == "__main__":
    test_HRD()
