# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Heartbeat Synchrony Discrimination task, with ECG read from an LSL stream.

Experimental. Start the device's streaming program first. Needs
`pip install cardioception-toolbox[lsl]`.

Beats are found online by `cardioception.devices.beat_source.LSLBeatSource`
and tones played by `cardioception.devices.tone_player.TonePlayer`
(PsychPortAudio). Record the ECG stream and the "HSD" marker stream with
LabRecorder: the XDF is the session's recording.
"""

from psychopy import gui

from cardioception.devices import LSLRecorder
from cardioception.HSD.parameters import getParameters
from cardioception.HSD.task import run

g = gui.Dlg()
g.addField("participant", initial="Participant")
g.addField("session", initial="HSD")
g.addField("LSL stream:", initial="PLUX")
g.addField("Channel:", initial="ECG2")
g.addField("Axis:", initial="absolute", choices=["absolute", "phase"])
g.addField("Device:", initial="keyboard", choices=["keyboard"])
g.addField("Language:", initial="english", choices=["english"])
g.show()

recorder = LSLRecorder(
    name=g.data[2], channel=g.data[3], signal_type="ecg", marker_stream="HSD"
)

parameters = getParameters(
    participant=g.data[0],
    session=g.data[1],
    setup="behavioral",
    axis=g.data[4],
    nTrials=60,
    device=g.data[5],
    language=g.data[6],
    recorder=recorder,
)

try:
    run(parameters, confidenceRating=True, runTutorial=True)
finally:
    # Escape and crashes too: the audio device and the LSL inlet are released,
    # and the session's files have already been written by run().
    if not getattr(parameters["win"], "_closed", False):  # escape closes it
        parameters["win"].close()
    parameters["tonePlayer"].close()
    recorder.close()
