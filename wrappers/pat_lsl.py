# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Phase Adjustment Task, with ECG read from an LSL stream.

Start the device's streaming program first. Needs `pip install cardioception-toolbox[lsl]`.

The exteroceptive task (a vibration on the hand instead of the heartbeat) needs
no ECG, so the stream and channel are ignored when it is ticked. It is saved
under the session name with `Extero` appended, so both runs of one session
keep their own files.
"""

import sys

from psychopy import gui

from cardioception.PAT.parameters import getParameters
from cardioception.PAT.task import run

g = gui.Dlg(title="Phase Adjustment Task")
g.addField("participant", initial="Participant")
g.addField("session", initial="PAT")
g.addField("LSL stream:", initial="PLUX")
g.addField("Channel:", initial="ECG2")
g.addField("Mode:", initial="relative", choices=["relative", "absolute"])
g.addField("Extero (vibration):", initial=False)
g.addField("Language:", initial="english", choices=["english", "danish"])
g.show()
if not g.OK:
    sys.exit("Cancelled.")

participant, session, stream, channel, mode, language = (
    g.data[i] for i in (0, 1, 2, 3, 4, 6)
)
extero = bool(g.data[5])
if extero:
    session += "Extero"

recorder = None
if not extero:
    from cardioception.devices import LSLRecorder

    try:
        # The task opens its own "PAT" marker stream, so none here
        recorder = LSLRecorder(name=stream, channel=channel, marker_stream=None)
    except Exception as error:
        gui.criticalDlg("No ECG", f"Could not open the LSL stream:\n\n{error}")
        raise

try:
    parameters = getParameters(
        participant=participant,
        session=session,
        recorder=recorder,
        mode=mode,
        extero=extero,
        language=language,
        nTrials=28,
        nPractice=8,
    )
except Exception as error:
    gui.criticalDlg("Cannot start", str(error))
    if recorder is not None:
        recorder.close()
    raise

try:
    run(parameters, runTutorial=True, confidenceRating=True)
finally:
    parameters["win"].close()
    parameters["engine"].close()
    if recorder is not None:
        recorder.close()
