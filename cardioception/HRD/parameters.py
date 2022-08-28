# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import pkg_resources  # type: ignore
import serial
from systole import serialSim
from systole.recording import Oximeter

from cardioception.HRD.languages import danish, danish_children, english, french


def getParameters(
    participant: str = "SubjectTest",
    session: str = "001",
    serialPort: str = "COM3",
    setup: str = "behavioral",
    stairType: str = "psi",
    exteroception: bool = True,
    catchTrials: float = 0.0,
    nTrials: int = 120,
    device: str = "mouse",
    screenNb: int = 0,
    fullscr: bool = True,
    nBreaking: int = 20,
    resultPath: Optional[str] = None,
    language: str = "english",
    systole_kw: dict = {},
):
    """Create Heart Rate Discrimination task parameters.

    Many task parameters, aesthetics, and options are controlled by the
    parameters dictonary defined herein. These are intended to provide
    flexibility and modularity to task. In many cases, unique versions of the
    task (e.g., with or without confidence ratings or choice feedback) can be
    created simply by changing these parameters, with no further interaction
    with the underlying task code.

    Parameters
    ----------
    device : str
        Select how the participant provide responses. Can be 'mouse' or
        'keyboard'.
    exteroception : bool
        If *True*, an exteroceptive condition with be interleaved with the
        interoceptive condition (either block or randomized design).
    fullscr : bool
        If *True*, activate full screen mode.
    language : str
        The language used for the instruction. Can be `"english"`, `"danish"` or
        `"danish_children"` (a slightly simplified danish version), or `"french"`.
    nBreaking : int
        Number of trials to run before the break.
    nStaircase : int
        Number of staircase to use per condition (exteroceptive and
        interoceptive).
    nTrials : int
        Number of trials to run (UpDown + psi staircase).
    participant : str
        Subject ID. Default is 'Participant'.
    catchTrials : float
        Ratio of Psi trials allocated to extreme values (+20 or -20 bpm with
        some jitter) to control for range of stimuli presented. The default is
        `0.0` (no catch trials). If not `0.0`, recomended value is `0.2`.
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
        Context of oximeter recording. `"ehavioral"` will record through a Nonin
        pulse oximeter and `"test"` will use pre-recorded pulse time series (for
        testing only).
    stairType : str
        Staircase type. Can be "psi" or "updown". Default set to "psi".
    systole_kw : dict
        Additional keyword arguments for :py:class:`systole.recorder.Oxmeter`.

    Attributes
    ----------
    allowedKeys : list of str
        The possible response keys.
    confScale : list
        The range of the confidence rating scale.
    device : str
        The device used for response and rating scale. Can be `"keyboard"` or
        `"mouse"`.
    HRcutOff : list
        Cut off for extreme heart rate values during recording.
    isi : tuple
        Range of the inter-stimulus interval (seconds). Should be in the form of (low,
        high). At each trial the value is generated using a uniform distribution
        between these two values. Default is set to `(0.25, 0.25)` so the value is
        fixed at `0.25`.
    labelsRating : list
        The labels of the confidence rating scale.
    lambdaExtero : 3d numpy array
        Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the exteroceptive condition.
    lambdaIntero : 3d numpy array
        Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the interoceptive condition.
    listenLogo, heartLogo : Psychopy visual instance
        Image used for the inference and recording phases, respectively.
    maxRatingTime : float
        The maximum time for a confidence rating (in seconds).
    minRatingTime : float
        The minimum time before a rating can be provided during the confidence
        rating (in seconds).
    monitor : str
        The monitor used to present the task (Psychopy parameter).
    nBreaking : int
        Number of trials to run before the break.
    nConfidence : int
        The number of trial with feedback during the tutorial phase (no
        feedback).
    nFeedback : int
        The number of trial with feedback during the tutorial phase (no
        confidence rating).
    nFinger : str or None
        The finger number ("1", "2", "3", "4" or "5") where the participant
        decided to place the pulse oximeter (if relevant).
    nTrials : int
        The number of trial to run in each condition, interoception and
        exteroception (if selected).
    participant : str
        Subject ID. Default is 'Participant'.
    path : str
        The task working directory.
    resultPath : str or None
        Where to save the results.
    serial : PySerial instance
        The serial port used to record the PPG activity.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    signal_df : pandas.DataFrame instance
        Dataframe where the pulse signal recorded during the interoception
        condition will be stored.
    stairCase : dict
        The staircase instances for 'psi' and 'UpDown'. Each entry contain
        dictionary for 'Intero' and 'Extero conditions' (if relevant).
    staircaseType : 1d array-like
        Vector indexing stairce type (`'UpDown'`, `'psi'`, `'psiCatchTrial'`).
    startKey : str
        The key to press to start the task and go to next steps.
    respMax : float
        The maximum time for decision (in seconds).
    results : str
        The result directory.
    session : int
        Session number. Default to '001'.
    setup : str
        The context of recording. Can be `'behavioral'` or `'test'`.
    texts : dict
        Long text elements.
    textSize : float
        Scalling parameter for text size.
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
    win : `psychopy.visual.window`
        The window in which to draw objects.

    Notes
    -----
    When using the `behavioral` setup, triggers will be sent to the PPG
    recording. The trigger channel is coding for different events during
    the task as follows:
        * Trial start: 1
        * recording trigger: 2
        * sound trigger : 3
        * rating trigger: 4
        * end trigger: 5
    All these events, except trial start, have also their time stamps
    encoded in the behavioral results data frame.

    """
    from psychopy import data, event, visual

    parameters: Dict[str, Any] = {}
    parameters["ExteroCondition"] = exteroception
    parameters["device"] = device
    if parameters["device"] == "keyboard":
        parameters["confScale"] = [1, 7]
    parameters["labelsRating"] = ["Guess", "Certain"]
    parameters["screenNb"] = screenNb
    parameters["monitor"] = "testMonitor"
    parameters["nFeedback"] = 5
    parameters["nConfidence"] = 8
    parameters["respMax"] = 5
    parameters["minRatingTime"] = 0.5
    parameters["maxRatingTime"] = 5
    parameters["isi"] = (0.25, 0.25)
    parameters["startKey"] = "space"
    parameters["allowedKeys"] = ["up", "down"]
    parameters["nTrials"] = nTrials
    parameters["nBreaking"] = nBreaking
    parameters["lambdaIntero"] = []  # Save the history of lambda values
    parameters["lambdaExtero"] = []  # Save the history of lambda values
    parameters["nFinger"] = None
    parameters["signal_df"] = pd.DataFrame([])  # Physiological recording
    parameters["results_df"] = pd.DataFrame([])  # Behavioral results

    # Set default path /Results/ 'Subject ID' /
    parameters["participant"] = participant
    parameters["session"] = session
    parameters["path"] = os.getcwd()
    if resultPath is None:
        parameters["resultPath"] = parameters["path"] + "/data/" + participant + session
    else:
        parameters["resultPath"] = None
    # Create Results directory if not already exists
    if not os.path.exists(parameters["resultPath"]):
        os.makedirs(parameters["resultPath"])

    # Store posterior in a dictionary
    parameters["staircaisePosteriors"] = {}
    parameters["staircaisePosteriors"]["Intero"] = []
    if exteroception is True:
        parameters["staircaisePosteriors"]["Extero"] = []

    nCatch = int(parameters["nTrials"] * catchTrials)
    nStaircase = parameters["nTrials"] - nCatch

    # Vector encoding the staircase type
    if stairType == "psi":
        sc = np.array(["psi"] * nStaircase)
    elif stairType == "updown":
        sc = np.array(["updown"] * nStaircase)
    else:
        raise ValueError("stairType should be 'psi' or 'updown'")

    # Create and randomize condition vectors separately for each staircase
    if exteroception is True:
        # Create a modality vector containing nTrials/2 Intero and Extero conditions
        parameters["Modality"] = np.hstack(
            [np.array(["Extero", "Intero"] * int(parameters["nTrials"] / 2))]
        )
    elif exteroception is False:
        # Create a modality vector containing nTrials/2 Intero and Extero conditions
        parameters["Modality"] = np.array(["Intero"] * int(parameters["nTrials"]))
    else:
        raise ValueError("exteroception should be a boolean")

    # Vector encoding the type of trial (psi, up/down or catch)
    parameters["staircaseType"] = np.hstack(
        [
            sc,
            np.array(["CatchTrial"] * int((parameters["nTrials"] * catchTrials))),
        ]
    )

    # Shuffle all trials
    shuffler = np.random.permutation(parameters["nTrials"])
    parameters["Modality"] = parameters["Modality"][shuffler]
    parameters["staircaseType"] = parameters["staircaseType"][shuffler]

    # Default parameters for the basic staircase are set here. Please see
    # PsychoPy Staircase Handler Documentation for full options. By default,
    # the task implements a staircase using Psi method.
    # If UpDown is selected, 1 or 2 interleaved staircases are used (see
    # options in parameters dictionary), one is initalized 'high' and the other
    # 'low'.
    parameters["stairCase"] = {}

    if stairType == "updown":

        conditions = [
            {
                "label": "low",
                "startVal": -40.5,
                "nUp": 1,
                "nDown": 1,
                "stepSizes": [20, 12, 12, 7, 4, 3, 2, 1],
                "stepType": "lin",
                "minVal": -40.5,
                "maxVal": 40.5,
            },
            {
                "label": "high",
                "startVal": 40.5,
                "nUp": 1,
                "nDown": 1,
                "stepSizes": [20, 12, 12, 7, 4, 3, 2, 1],
                "stepType": "lin",
                "minVal": -40.5,
                "maxVal": 40.5,
            },
        ]
        parameters["stairCase"]["Intero"] = data.MultiStairHandler(
            conditions=conditions, nTrials=parameters["nTrials"]
        )

    elif stairType == "psi":

        parameters["stairCase"]["Intero"] = data.PsiHandler(
            nTrials=nTrials,
            intensRange=[-50.5, 50.5],
            alphaRange=[-50.5, 50.5],
            betaRange=[0.1, 25],
            intensPrecision=1,
            alphaPrecision=1,
            betaPrecision=0.1,
            delta=0.02,
            stepType="lin",
            expectedMin=0,
        )

    if exteroception is True:
        if stairType == "updown":

            conditions = [
                {
                    "label": "low",
                    "startVal": -40.5,
                    "nUp": 1,
                    "nDown": 1,
                    "stepSizes": [20, 12, 12, 7, 4, 3, 2, 1],
                    "stepType": "lin",
                    "minVal": -40.5,
                    "maxVal": 40.5,
                },
                {
                    "label": "high",
                    "startVal": 40.5,
                    "nUp": 1,
                    "nDown": 1,
                    "stepSizes": [20, 12, 12, 7, 4, 3, 2, 1],
                    "stepType": "lin",
                    "minVal": -40.5,
                    "maxVal": 40.5,
                },
            ]
            parameters["stairCase"]["Extero"] = data.MultiStairHandler(
                conditions=conditions, nTrials=parameters["nTrials"]
            )

        elif stairType == "psi":

            parameters["stairCase"]["Extero"] = data.PsiHandler(
                nTrials=nTrials,
                intensRange=[-50.5, 50.5],
                alphaRange=[-50.5, 50.5],
                betaRange=[0.1, 25],
                intensPrecision=1,
                alphaPrecision=1,
                betaPrecision=0.1,
                delta=0.02,
                stepType="lin",
                expectedMin=0,
            )

    parameters["setup"] = setup
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

    ##############
    # Load texts #
    ##############
    if language == "english":
        parameters["texts"] = english(
            device=device, setup=setup, exteroception=exteroception
        )
    elif language == "danish":
        parameters["texts"] = danish(
            device=device, setup=setup, exteroception=exteroception
        )
    elif language == "danish_children":
        parameters["texts"] = danish_children(
            device=device, setup=setup, exteroception=exteroception
        )
    elif language == "french":
        parameters["texts"] = french(
            device=device, setup=setup, exteroception=exteroception
        )

    # Open window
    if parameters["setup"] == "test":
        fullscr = False
    parameters["win"] = visual.Window(
        monitor=parameters["monitor"],
        screen=parameters["screenNb"],
        fullscr=fullscr,
        units="height",
    )
    parameters["win"].mouseVisible = False

    ###############
    # Image loading
    ###############
    if parameters["setup"] in ["test", "behavioral"]:
        parameters["pulseSchema"] = visual.ImageStim(
            win=parameters["win"],
            units="height",
            image=pkg_resources.resource_filename(__name__, "Images/pulseOximeter.png"),
            pos=(0.0, 0.0),
        )
        parameters["pulseSchema"].size *= 0.2
        parameters["handSchema"] = visual.ImageStim(
            win=parameters["win"],
            units="height",
            image=pkg_resources.resource_filename(__name__, "Images/hand.png"),
            pos=(0.0, -0.08),
        )
        parameters["handSchema"].size *= 0.15

    parameters["listenLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=pkg_resources.resource_filename(__name__, "Images/listen.png"),
        pos=(0.0, 0.0),
    )
    parameters["listenLogo"].size *= 0.08

    parameters["heartLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=pkg_resources.resource_filename(__name__, "Images/heartbeat.png"),
        pos=(0.0, 0.0),
    )
    parameters["heartLogo"].size *= 0.04
    parameters["textSize"] = 0.04
    parameters["HRcutOff"] = [40, 120]
    if parameters["device"] == "keyboard":
        parameters["confScale"] = [1, 10]
    elif parameters["device"] == "mouse":
        parameters["myMouse"] = event.Mouse()

    return parameters
