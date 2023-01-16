# Author: Nicolas Legrand <nicolas.legrand@cas.au.dk>


from psychopy import gui

from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run

################################
# Heart rate Discrimination task
################################

# Create a GUI and ask for high-evel experiment parameters
g = gui.Dlg()
g.addField("participant", initial="Participant")
g.addField("session", initial="HRD")
g.addField("Serial Port:", initial="COM5")
g.addField("Setup:", initial="behavioral", choices=["behavioral", "test", "fMRI"])
g.addField("Device:", initial="mouse", choices=["mouse", "keyboard"])
g.addField("Language:", initial="english", choices=["english", "danish", "french"])
g.show()

# Set global task parameters herecd
parameters = getParameters(
    participant=g.data[0],
    session=g.data[1],
    serialPort=g.data[2],
    setup=g.data[3],
    device=g.data[4],
    language=g.data[5],
    stairType="psi",
    catchTrials=0.0,
    nTrials=120,
    exteroception=True,
)

# Run task
run(parameters, confidenceRating=True, runTutorial=True)

parameters["win"].close()
