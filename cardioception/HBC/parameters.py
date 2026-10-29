# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import serial
from systole import serialSim
from systole.recording import Oximeter

from .._resources import resource_filename
from .languages import english, german


def getParameters(
    participant: str = "Participant",
    session: str = "001",
    serialPort: str = "COM3",
    taskVersion: str = "Garfinkel",
    setup: str = "behavioral",
    screenNb: int = 0,
    fullscr: bool = True,
    resultPath: Optional[str] = None,
    systole_kw: dict = {},
    language: str = "english",
    recorder=None,
) -> Dict:
    """Create Heartbeat Counting task parameters.

    Parameters
    ----------
    language : str
        The language used for the instructions. Can be `"english"` (default) or
        `"german"`.
    participant : str
        Subject ID. Default is 'exteroStairCase'.
    recorder : object | None
        A recording device to use instead of the pulse oximeter `setup` would
        open, e.g. :class:`cardioception.devices.LSLRecorder` to read ECG from an
        LSL stream. `setup` still decides the window. Default is `None`, which
        leaves the task exactly as it was.
    resultPath : str or None
        Where to save the results.
    screenNb : int
        Screen number. Used to parametrize py:func:`psychopy.visual.Window`.
        Default is set to 0.
    serialPort: str
        The USB port where the pulse oximeter is plugged. Should be written as a string
        e.g. `"COM3"` for USB ports on Windows.
    session : int
        Session number. Default to '001'.
    setup : str
        Context of oximeter recording. `"behavioral"` will record through a Nonin
        pulse oximeter, `"test"` will use pre-recorded pulse time series (for testing
        only).
    systole_kw : dict
        Additional keyword arguments for :py:class:`systole.recorder.Oxmeter`.
    taskVersion : str or None
        Task version to run. Can be 'Garfinkel', 'Shandry', 'test' or None.

    Attributes
    ----------
    conditions : 1d array-like of str
        The conditions. Can be 'Rest', 'Training' or 'Count'.
    confScale : list
        The range of the confidence rating scale.
    heartLogo : `psychopy.visual.ImageStim`
        Image presented during resting conditions.
    labelsRating : list
        The labels of the confidence rating scale.
    noteStart : psychopy.sound.Sound instance
        The sound that will be played when trial starts.
    noteStop : psychopy.sound.Sound instance
        The sound that will be played when trial ends.
    path : str
        The task working directory.
    randomize : bool
        If `True` (default), will randomize the order of the conditions. If
        taskVersion is not None, will use the default task parameter instead.
    rating : bool
        If `True` (default), will add a rating scale after the evaluation.
    restLength : int
        The length of the resting period (seconds). Default is 300 seconds.
    restLogo : `psychopy.visual.ImageStim`
        Image presented during resting conditions.
    restPeriod : bool
        If `True`, a resting period will be proposed before the task.
    resultPath : str
        The subject result directory.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    serial : `serial.Serial`
        The serial port used to record the PPG activity.
    startKey : str
        The key to press to start the task and go to next steps.
    taskVersion : str or None
        Task version to run. Can be 'Garfinkel', 'Shandry', 'test' or None.
    texts : dict
        Dictionary containing the texts to be presented.
    textSize : float
        Text size.
    triggers : dict
        Dictionary {str, callable or None}. The function will be executed
        before the corresponding trial sequence. The default values are
        `None` (no trigger sent).
        * `"trialStart"`
        * `"trialStop"`
        * `"listeningStart"`
        * `"listeningStop"`
        * `"decisionStart"`
        * `"decisionStop"`
        * `"confidenceStart"`
        * `"confidenceStop"`
    times : 1d array-like of int
        Length of trials, in seconds.
    win : `psychopy.visual.window`
        The window in which to draw objects.

    """
    if language not in ("english", "german"):
        raise ValueError(
            f"Invalid language: {language!r}. Can be 'english' or 'german'."
        )

    from psychopy import sound, visual

    parameters: Dict[str, Any] = {}
    parameters["restPeriod"] = True
    parameters["restLength"] = 30
    parameters["randomize"] = True
    parameters["startKey"] = "space"
    parameters["rating"] = True
    parameters["confScale"] = [1, 7]
    parameters["taskVersion"] = taskVersion
    parameters["results_df"] = pd.DataFrame({})
    parameters["setup"] = setup

    # Initialize triggers dictionary with None
    # Some or all can later be overwrited with callable
    # sending the information needed.
    parameters["triggers"] = {
        "trialStart": None,
        "trialStop": None,
        "listeningStart": None,
        "listeningStop": None,
        "decisionStart": None,
        "decisionStop": None,
        "confidenceStart": None,
        "confidenceStop": None,
    }

    # Experimental design - can choose between a version based on recent
    # papers from Sarah Garfinkel's group, or the classic Schandry approach.
    # The primary difference ebtween the two is the order of trials and the
    # use of resting periods between trials.
    if parameters["taskVersion"] == "Garfinkel":
        parameters["times"] = np.array([25, 30, 35, 40, 45, 50])
        np.random.shuffle(parameters["times"])
        parameters["conditions"] = [
            "Count",
            "Count",
            "Count",
            "Count",
            "Count",
            "Count",
        ]

    elif parameters["taskVersion"] == "Schandry":
        parameters["times"] = np.array([60, 25, 30, 35, 30, 45])
        parameters["conditions"] = ["Rest", "Count", "Rest", "Count", "Rest", "Count"]

    elif parameters["taskVersion"] == "test":
        parameters["times"] = np.array([5, 5])
        parameters["conditions"] = ["Rest", "Count"]
    else:
        raise ValueError("Invalid task condition")

    # Set default path /Results/ 'Subject ID' /
    parameters["participant"] = participant
    parameters["session"] = session
    parameters["path"] = os.getcwd()
    if resultPath is None:
        parameters["resultPath"] = parameters["path"] + "/data/" + participant + session
    else:
        parameters["resultPath"] = resultPath
    # Create Results directory of not already exists
    if not os.path.exists(parameters["resultPath"]):
        os.makedirs(parameters["resultPath"])

    # Set note played at trial start
    parameters["noteStart"] = sound.Sound(
        resource_filename("cardioception.HBC", "Sounds/start.wav")
    )

    parameters["noteStop"] = sound.Sound(
        resource_filename("cardioception.HBC", "Sounds/stop.wav")
    )

    # Open window
    if parameters["setup"] == "test":
        fullscr = False
    parameters["win"] = visual.Window(screen=screenNb, fullscr=fullscr, units="height")
    parameters["win"].mouseVisible = False

    parameters["restLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=resource_filename("cardioception.HBC", "Images/rest.png"),
        pos=(0.0, -0.2),
    )
    parameters["restLogo"].size *= 0.15
    parameters["heartLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=resource_filename("cardioception.HBC", "Images/heartbeat.png"),
        pos=(0.0, -0.2),
    )
    parameters["heartLogo"].size *= 0.05

    if recorder is not None:
        # Wins over `setup`, and touches no serial port.
        parameters["oxiTask"] = recorder
        parameters["oxiTask"].setup().read(duration=1)
    elif setup == "behavioral":
        # PPG recording
        port = serial.Serial(serialPort)
        parameters["oxiTask"] = Oximeter(
            serial=port, sfreq=75, add_channels=1, **systole_kw
        )
        parameters["oxiTask"].setup().read(duration=1)
    elif setup == "test":
        # Use pre-recorded pulse time series for testing
        port = serialSim()
        parameters["oxiTask"] = Oximeter(
            serial=port, sfreq=75, add_channels=1, **systole_kw
        )
        parameters["oxiTask"].setup().read(duration=1)

    #######
    # Texts
    #######
    if language == "english":
        texts = english()
    elif language == "german":
        texts = german()
    parameters["labelsRating"] = texts.pop("labelsRating")
    parameters["texts"] = texts
    parameters["textSize"] = 0.04

    return parameters
