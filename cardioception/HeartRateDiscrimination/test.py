# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartRateDiscrimination.parameters import getParameters
from cardioception.HeartRateDiscrimination.task import run
from psychopy import gui


def test_hrd():

    # Create a GUI and store subject ID
    g = gui.Dlg()
    g.addField("Serial Port:")
    g.show()

    # Set global task parameters here
    parameters = getParameters('test', 1, g.data[0])
    parameters['nTrials'] = 1

    # Run task
    run(parameters, win=parameters['win'],
        confidenceRating=True, runTutorial=True)

    # Save results
    parameters['win'].close()
