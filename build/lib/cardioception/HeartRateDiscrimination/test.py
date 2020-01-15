# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartRateDiscrimination.parameters import getParameters
from cardioception.HeartRateDiscrimination.task import run
from psychopy import gui


def test_HRD():
    # Create a GUI and store subject ID
    g = gui.Dlg()
    g.addField("Serial Port:")
    g.show()

    # Set global task parameters here
    parameters = getParameters('test', 1, g.data[0])

    # Limit the number of trials to run
    parameters['Conditions'] = parameters['Conditions'][:4]
    parameters['nFeedback'] = 1
    parameters['nConfidence'] = 1

    # Run task
    results_df = run(parameters, win=parameters['win'],
                     confidenceRating=True, runTutorial=True)

    # Save results
    results_df.to_csv(parameters['results'] + '/test.txt')

    # Save results
    parameters['win'].close()


if __name__ == "__main__":
    test_HRD()
