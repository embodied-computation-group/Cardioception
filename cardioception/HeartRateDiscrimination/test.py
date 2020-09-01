# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

from parameters import getParameters
from task import run
from psychopy import gui

# Create a GUI and ask for high-evel experiment parameters
g = gui.Dlg()
g.addField("participant", initial='test')
g.addField("session", initial='001')
g.addField("Serial Port:", initial='COM3')
g.addField("Setup:", initial='test')
g.show()

# Set global task parameters here
parameters = getParameters(
    participant=g.data[0], session=g.data[1], serialPort=g.data[2],
    setup=g.data[3], nTrials=4, nTrialsUpDown=2,
    screenNb=0)
parameters['nBreaking'] = 2
parameters['nFeedback'] = 1
parameters['nConfidence'] = 1

# Run task
run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()
