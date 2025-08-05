# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University


from psychopy import gui

from cardioception.HBC.parameters import getParameters
from cardioception.HBC.task import run

# Create a GUI and ask for high-evel experiment parameters
g = gui.Dlg()
g.addField("participant", initial="Participant")
g.addField("session", initial="HBC")
g.addField("Serial Port:", initial=None)
g.addField("Setup:", initial="behavioral")
g.show()

# Set global task parameters here
parameters = getParameters(
    participant=g.data[0],
    session=g.data[1],
    serialPort=g.data[2],
    setup=g.data[3],
    screenNb=0,
)

# Run task
run(parameters, runTutorial=True)

parameters["win"].close()
