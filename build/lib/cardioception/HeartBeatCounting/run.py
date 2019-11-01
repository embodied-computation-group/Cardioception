# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartBeatCounting.task import sequence
from cardioception.HeartBeatCounting.parameters import getParameters
from psychopy import gui

path = 'C:/Users/au646069/Google Drive/ECG_root/Code/PythonToolboxes/cardioception/cardioception/HeartBeatCounting'

# Wrapper function
##################

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("Subject Number:")
g.addField("Subject ID:")
g.show()

# Get parameters
parameters = getParameters()

parameters['nSub'] = g.data[0]
parameters['sub'] = g.data[1]

# Run the entire sequence
sequence(parameters)
