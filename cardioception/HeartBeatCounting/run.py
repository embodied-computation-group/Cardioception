# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from Tasks.HeartBeatCounting.task import HeartBeatCounting
from Tasks.HeartBeatCounting.parameters import getParameters
from cardioception.recording import Oximeter
from psychopy import visual, gui

path = 'C:/Users/au646069/Google Drive/ECG_root/Code/PythonToolboxes/cardioception/cardioception/HeartBeatCounting'

# Wrapper function
##################

# Get parameters
parameters = getParameters()

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("Subject Number:")
g.addField("Subject ID:")
g.show()
nSub = g.data[0]
subID = g.data[1]

oximeter = Oximeter(serial=ser, sample=75)
oximeter.setup()
oximeter.read(nSeconds=1)

# Run the entire sequence
hbcTask = HeartBeatCounting()
