# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import pkg_resources  # type: ignore
import serial
from systole import serialSim
from systole.recording import Oximeter


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
) -> Dict:
    """Create Heartbeat Counting task parameters.

    Parameters
    ----------
    participant : str
        Subject ID. Default is 'exteroStairCase'.
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
    from psychopy import sound, visual

    parameters: Dict[str, Any] = {}
    parameters["restPeriod"] = True
    parameters["restLength"] = 30
    parameters["randomize"] = True
    parameters["startKey"] = "space"
    parameters["rating"] = True
    parameters["confScale"] = [1, 7]
    parameters["labelsRating"] = ["Guess", "Certain"]
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
        pkg_resources.resource_filename("cardioception.HBC", "Sounds/start.wav")
    )

    parameters["noteStop"] = sound.Sound(
        pkg_resources.resource_filename("cardioception.HBC", "Sounds/stop.wav")
    )

    # Open window
    if parameters["setup"] == "test":
        fullscr = False
    parameters["win"] = visual.Window(screen=screenNb, fullscr=fullscr, units="height")
    parameters["win"].mouseVisible = False

    parameters["restLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=pkg_resources.resource_filename(__name__, "Images/rest.png"),
        pos=(0.0, -0.2),
    )
    parameters["restLogo"].size *= 0.15
    parameters["heartLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=pkg_resources.resource_filename(__name__, "Images/heartbeat.png"),
        pos=(0.0, -0.2),
    )
    parameters["heartLogo"].size *= 0.05

    if setup == "behavioral":
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

    # Task instructions
    parameters["texts"] = dict()
    parameters["texts"]["Rest"] = "Please sit quietly until the next session"
    parameters["texts"]["Count"] = (
        "After you hear START, try to count your heartbeats"
        " by concentrating on your body feelings."
        " Stop counting when you hear STOP"
    )
    parameters["texts"]["Training"] = (
        "After you hear START, try to count your heartbeats"
        " by concentrating on your body feelings"
        " Stop counting when you hear STOP"
    )
    parameters["texts"]["nCount"] = (
        "How many heartbeats did you count?"
        " Write a number and press ENTER to validate."
    )
    parameters["texts"]["confidence"] = (
        "How confident are you about your count?"
        "Use the RIGHT/LEFT keys to select and the DOWN key to confirm"
    )

    # Tutorial instructions
    parameters["texts"]["Tutorial1"] = (
        "During this experiment, we will ask you to silently"
        " count your heartbeats for different intervals of time."
    )
    parameters["texts"]["Tutorial2"] = (
        'When you see this "heart" icon, you will silently count your'
        " heartbeats by focusing on your body sensations."
    )
    parameters["texts"]["Tutorial3"] = (
        'Sometime, you will also encounter this "rest" icon.'
        " In this case your task will just be to sit quietly until the next"
        " session."
    )
    parameters["texts"]["Tutorial4"] = (
        "The beginning and the end of the task will be signalled when you hear"
        " the words 'START'' and 'STOP'. While counting your heartbeats, you"
        " may close your eyes if you find that helpful. Please keep your hand"
        " still during the counting period, to avoid interfering with"
        " the heartbeat recording."
    )
    parameters["texts"]["Tutorial5"] = (
        "After the counting part of the task, you will be asked to report the"
        " exact number of heartbeats you felt during the interval between"
        " 'START' and 'STOP'. Please do not try to estimate the number of"
        " heartbeats, but instead only report the heartbeats you actually felt"
        " during the interval. You will input your response using the number"
        " pad and press return when done. You can also correct your response"
        " using backspace."
    )
    parameters["texts"]["Tutorial6"] = (
        "Once you have made your response, you will estimate your subjective"
        " feeling of confidence in how accurate your count was"
        " for that interval. A large number here means that you are totally"
        " certain you counted the exact number of heartbeats that occured,"
        " and a small number means that you are totally uncertain or felt that"
        " you were guessing about the"
        " number of heartbeats. You should use the RIGHT and LEFT"
        " key to select your response and the DOWN key to confirm."
    )
    parameters["texts"]["Tutorial7"] = (
        "Before the main task begins there is a short resting period of"
        " several minutes, during which we will calibrate the heartbeat"
        " recording. During this period, please sit quietly with your"
        " hands still to avoid interfering with the calibration."
        " Afterwards, the counting task will begin, and will take about"
        " 6 minutes in total."
    )
    parameters["texts"]["Tutorial8"] = (
        "You will now complete a short practice task."
        " Please ask the experimenter if you have any questions before"
        " continuing to the main experiment."
    )
    parameters["texts"]["Tutorial9"] = (
        "Good job! If you have any question, ask the experimenter now,"
        " otherwise press SPACE to continue to the experiment."
    )
    parameters["textSize"] = 0.04

    return parameters
