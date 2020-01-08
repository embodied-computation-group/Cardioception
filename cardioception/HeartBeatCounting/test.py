# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartBeatCounting.task import sequence, tutorial, rest
from cardioception.HeartBeatCounting.parameters import getParameters
from psychopy import gui

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("Serial Port:")
g.show()

# Get parameters
parameters = getParameters('test', str(1), g.data[0], taskVersion='test')

# Run tutorial
tutorial(parameters)

parameters['restLength'] = 5
rest(parameters)

# Run the entire sequence
sequence(parameters)
