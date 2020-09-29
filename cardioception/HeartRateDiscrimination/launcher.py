# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from parameters import getParameters
from task import run
from psychopy import gui

# Create a GUI and ask for high-evel experiment parameters
g = gui.Dlg()
g.addField("participant", initial='Participant')
g.addField("session", initial='HRD')
g.addField("Serial Port:", initial=None)
g.addField("Setup:", initial='behavioral')
g.show()

# Set global task parameters here
parameters = getParameters(
    participant=g.data[0], session=g.data[1], serialPort=g.data[2],
    setup=g.data[3], nTrials=160, nTrialsUpDown=80,
    screenNb=0, psiCatchTrials=0.2)

# Run task
run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()
