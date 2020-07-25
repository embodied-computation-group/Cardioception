# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from task import run
from parameters import getParameters
from psychopy import gui

# Create a GUI and ask for high-evel experiment parameters
g = gui.Dlg()
g.addField("participant", initial='Participant')
g.addField("session", initial='001')
g.addField("Serial Port:", initial=None)
g.addField("Setup:", initial='behavioral')
g.show()

# Get parameters
# Set global task parameters here
parameters = getParameters(
    participant=g.data[0], session=g.data[1], serialPort=g.data[2],
    setup=g.data[3], screenNb=0)

# Run task
run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()
