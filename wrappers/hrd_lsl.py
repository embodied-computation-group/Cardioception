# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University
"""Heart Rate Discrimination task, with ECG read from an LSL stream.

Start the device's streaming program first. Needs `pip install cardioception-toolbox[lsl]`.
"""

from psychopy import gui

from cardioception.devices import LSLRecorder
from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run

g = gui.Dlg()
g.addField("participant", initial="Participant")
g.addField("session", initial="HRD")
g.addField("LSL stream:", initial="PLUX")
g.addField("Channel:", initial="ECG2")
g.addField("Signal:", initial="ecg", choices=["ecg", "ppg"])
g.addField("Device:", initial="mouse", choices=["mouse", "keyboard"])
g.addField(
    "Language:", initial="english", choices=["english", "danish", "french", "german"]
)
g.show()

recorder = LSLRecorder(name=g.data[2], channel=g.data[3], signal_type=g.data[4])

parameters = getParameters(
    participant=g.data[0],
    session=g.data[1],
    recorder=recorder,
    device=g.data[5],
    language=g.data[6],
    stairType="psi",
    catchTrials=0.0,
    nTrials=120,
    exteroception=True,
)

run(parameters, confidenceRating=True, runTutorial=True)

parameters["win"].close()
recorder.close()
