# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartBeatCounting.task import sequence, tutorial
from cardioception.HeartBeatCounting.parameters import getParameters
from psychopy import gui

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("Subject ID:")
g.addField("Subject Number:")
g.show()

# Get parameters
parameters = getParameters(g.data[0], g.data[1])

# Run tutorial
tutorial(parameters)

# Run the entire sequence
sequence(parameters)
