# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import serial
from systole import serialSim
from systole.recording import Oximeter

from cardioception.HRD.languages import danish, danish_children, english, french

from .._resources import resource_filename
from .._rng import make_rng
from .._triggers import validate as validate_triggers


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
    seed: Optional[int] = None,
    autopilot=None,
    recorder=None,
    onMissedTrial: str = "represent",
    maxRepresentations: int = 3,
    triggers: Optional[Dict[str, Any]] = None,
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
        Select how the participant provide responses. Can be `'mouse'` or `'keyboard'`.
    exteroception : bool
        If `True`, the task will include an exteroceptive (half of the trials).
    fullscr : bool
        If `True`, activate full screen mode.
    language : str
        The language used for the instruction. Can be `"english"`, `"danish"` or
        `"danish_children"` (a slightly simplified danish version), or `"french"`.
    nBreaking : int
        Number of trials to run before the break.
    nStaircase : int
        Number of staircase to use per condition (exteroceptive and
        interoceptive).
    nTrials : int
        The number of trials to run (UpDown and psi staircase).

        .. note::
           This number indicates the total number of trials that will be presented
           during the experiment. If `nTrials=50` and `exteroception=False`, the task
           contains 50 interoceptive trials. If `nTrials=50` and `exteroception=True`,
           the task contains 25 interoceptive trials and 25 exteroceptive trials.

    onMissedTrial : str
        What to do when the participant does not respond in time. `"represent"`
        (the default) returns the trial to the end of the queue so the intended
        number of usable trials is collected, at the cost of a session whose
        length varies. `"skip"` moves on, giving a fixed number of presentations
        and a variable number of usable trials.

        .. note::
           Under either setting the missed trial is written to the results with
           `DecisionProvided=False` and is **not** used to update the staircase.
           Before this was fixed, a missed trial entered the staircase as a
           fabricated `"Less"` response.

    maxRepresentations : int
        How many times in total a trial may be presented before it is abandoned,
        when `onMissedTrial="represent"`. Defaults to `3`. Without a cap, a
        participant who stops responding would never reach the end.
    participant : str
        Subject ID. Default is 'Participant'.
    catchTrials : float
        Ratio of Psi trials allocated to extreme values (+20 or -20 bpm with some
        jitter) to control for range of stimuli presented. Default to `0.0` (no catch
        trials). If not `0.0`, recomended value is `0.2`.
    resultPath : str | None
        Where to save the results.
    screenNb : int
        Screen number. Used to parametrize py:func:`psychopy.visual.Window`. Defaults
        to `0`.
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
    ExteroCondition : bool
        If `True`, the task includes an exteroceptive (half of the trials).
    isi : tuple
        Range of the inter-stimulus interval (seconds). Should be in the form of (low,
        high). At each trial the value is generated using a uniform distribution
        between these two values. Default is set to `(0.25, 0.25)` so the value is
        fixed at `0.25`.
    labelsRating : list
        The labels of the confidence rating scale.
    lambdaExtero : np.ndarray
        (3d) Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the exteroceptive condition.
    lambdaIntero : np.ndarray
        (3d) Posterior estimate of the psychophysics function parameters (slope and
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
        The number of trials to run (UpDown and psi staircase).

        .. note::
           This number indicates the total number of trials that will be presented
           during the experiment. If `nTrials=50` and `exteroception=False`, the task
           contains 50 interoceptive trials. If `nTrials=50` and `exteroception=True`,
           the task contains 25 interoceptive trials and 25 exteroceptive trials.
    participant : str
        Subject ID. Default is 'Participant'.
    path : str
        The task working directory.
    resultPath : str | None
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
    response_keys : dict
        Mapping from trial conditions to keyboard response keys.
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
    When using the `behavioral` setup, triggers will be sent to the PPG  recording. The
    trigger channel is coding for different events during the task as follows:

    - Trial start: 1
    - recording trigger: 2
    - sound trigger : 3
    - rating trigger: 4
    - end trigger: 5

    All these events, except trial start, have also their time stamps encoded in the
    behavioral results data frame.

    """
    from psychopy import data, event, visual

    parameters: Dict[str, Any] = {}
    # One generator for the whole session. The seed is always recorded, so a
    # session can be replayed even when the caller did not choose one.
    parameters["rng"], parameters["seed"] = make_rng(seed)
    # A synthetic participant, for headless runs and tests. None means a human.
    parameters["autopilot"] = autopilot

    if onMissedTrial not in ("represent", "skip"):
        raise ValueError(
            f"onMissedTrial should be 'represent' or 'skip', got {onMissedTrial!r}"
        )
    parameters["onMissedTrial"] = onMissedTrial
    parameters["maxRepresentations"] = maxRepresentations

    # Callables run at each trial event, for a parallel port, an LSL marker
    # stream or an amplifier. This docstring documented the key for years while
    # the function never created it, so anyone following the documentation got a
    # KeyError. Validated here so a typo fails at launch, not at trial eighty.
    parameters["triggers"] = validate_triggers(triggers)
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
    parameters["response_keys"] = {"More": "up", "Less": "down"}
    parameters["allowedKeys"] = list(parameters["response_keys"].values())
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
        parameters["resultPath"] = resultPath
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
        # Alternate the two modalities, then trim to exactly nTrials.
        #
        # This used to build `["Extero", "Intero"] * int(nTrials / 2)`, which is
        # one entry short whenever nTrials is odd. The shuffle below then indexed
        # past the end of it, so every odd nTrials failed at parameter setup with
        # `IndexError: index 0 is out of bounds for axis 0 with size 0`, naming
        # neither nTrials nor exteroception.
        pairs = -(-parameters["nTrials"] // 2)  # ceiling division
        parameters["Modality"] = np.array(["Extero", "Intero"] * pairs)[
            : parameters["nTrials"]
        ]
        if parameters["nTrials"] % 2:
            print(
                f"... nTrials={parameters['nTrials']} is odd, so the two modalities"
                " cannot be balanced: there will be one more Extero trial than"
                " Intero. Use an even number if you want them balanced."
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
    shuffler = parameters["rng"].permutation(parameters["nTrials"])
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
    if recorder is not None:
        # An explicitly supplied backend wins over `setup`, which conflates
        # "which device" with "is this a test". Nothing here touches a serial
        # port, so this is also the only path that works without hardware.
        parameters["oxiTask"] = recorder
        parameters["oxiTask"].setup().read(duration=1)
    elif setup == "behavioral":
        # PPG recording
        port = serial.Serial(serialPort)
        parameters["oxiTask"] = Oximeter(
            serial=port, sfreq=75, add_channels=1, **systole_kw
        )
        parameters["oxiTask"].setup().read(duration=1)

        # # for Nonin 3231 USB
        # parameters['oxiTask'] = Nonin3231USB(serial=port, add_channels=1).setup().read(1)

    elif setup == "test":
        # Use pre-recorded pulse time series for testing
        port = serialSim()
        parameters["oxiTask"] = Oximeter(
            serial=port, sfreq=75, add_channels=1, **systole_kw
        )
        parameters["oxiTask"].setup().read(duration=1)

    else:
        # setup decides whether a recorder exists at all, and was the only
        # string parameter with no guard. An unrecognised value returned a
        # parameters dict with no "oxiTask" key, and the task then died on the
        # first line of run() with KeyError, after the window had opened in
        # front of a participant. wrappers/hrd.py offered "fMRI" in its dropdown
        # for years after that mode was removed, so this was reachable by
        # clicking a menu entry the project shipped.
        raise ValueError(
            f"setup should be 'behavioral' or 'test', got {setup!r}. "
            "Pass recorder= to use a device other than the Nonin oximeter."
        )

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
            image=resource_filename("cardioception.HRD", "Images/pulseOximeter.png"),
            pos=(0.0, 0.0),
        )
        parameters["pulseSchema"].size *= 0.2
        parameters["handSchema"] = visual.ImageStim(
            win=parameters["win"],
            units="height",
            image=resource_filename("cardioception.HRD", "Images/hand.png"),
            pos=(0.0, -0.08),
        )
        parameters["handSchema"].size *= 0.15

    parameters["listenLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=resource_filename("cardioception.HRD", "Images/listen.png"),
        pos=(0.0, 0.0),
    )
    parameters["listenLogo"].size *= 0.08

    parameters["heartLogo"] = visual.ImageStim(
        win=parameters["win"],
        units="height",
        image=resource_filename("cardioception.HRD", "Images/heartbeat.png"),
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
