# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import pkg_resources
import serial
from psychopy import core, data, event, visual
from systole import serialSim
from systole.recording import Oximeter, findOximeter


def getParameters(
    participant: str = "SubjectTest",
    session: str = "001",
    serialPort: Optional[str] = None,
    setup: str = "behavioral",
    stairType: str = "psi",
    exteroception: bool = True,
    catchTrials: float = 0.0,
    nTrials: int = 160,
    BrainVisionIP: Optional[str] = None,
    device: str = "mouse",
    screenNb: int = 0,
    fullscr: bool = True,
    nBreaking: int = 20,
    resultPath: Optional[str] = None,
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
    BrainVisionIP : str
        The IP address of the recording computer (fMRI version only).
    device : str
        Select how the participant provide responses. Can be 'mouse' or
        'keyboard'.
    exteroception : bool
        If *True*, an exteroceptive condition with be interleaved with the
        interoceptive condition (either block or randomized design).
    fullscr : bool
        If *True*, activate full screen mode.
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
        Select screen number.
    serialPort: str
        The USB port where the pulse oximeter is plugged. Should be written as
        a string e.g., `'COM3'`, `'COM4'`. If set to *None*, the pulse oximeter
        will be automatically detected. using the
        :py:func:`systole.recording.findOximeter()` function.
    session : int
        Session number. Default to '001'.
    setup : str
        Context of oximeter recording. Behavioral will record through a Nonin
        pulse oximeter, `'fMRI'` will record through BrainVision amplifier
        through TCP/IP conneciton. *test* will use pre-recorded pulse time
        series (for testing only).
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
        The device used for response and rating scale. Can be 'keyboard' or
        'mouse'.
    HRcutOff : list
        Cut off for extreme heart rate values during recording.
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
    nTrials : int
        The number of trial to run in each condition, interoception and
        exteroception (if selected).
    participant : str
        Subject ID. Default is 'Participant'.
    path : str
        The task working directory.
    referenceTone : callable
        Function selecting the reference tones for the exteroceptive condition.
        The output should be a single float matching the name of the `.wav` files
        (ending with `.0` or `.5`). Default is uniform between 40.0 and 100.0 BPM
        (`np.random.choice(np.arange(40, 100, 0.5))`).
    serial : PySerial instance
        The serial port used to record the PPG activity.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    signal_df : pandas.DataFrame instance
        Dataframe where the pulse signal recorded during the interoception
        condition will be stored.
    stairCase : dict
        The staircase instances for 'psi' and 'UpDown'. Each entry contain
        dictionnary for 'Intero' and 'Extero conditions' (if relevant).
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
        The context of recording. Can be 'behavioral', 'fMRI' or 'test'.
    texts : dict
        Long text elements.
    textSize : float
        Scalling parameter for text size.
    win : Psychopy window instance
        The window where to run the task.
    """
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
    parameters["startKey"] = "space"
    parameters["allowedKeys"] = ["up", "down"]
    parameters["nTrials"] = nTrials
    parameters["nBreaking"] = nBreaking
    parameters["lambdaIntero"] = []  # Save the history of lambda values
    parameters["lambdaExtero"] = []  # Save the history of lambda values
    parameters["referenceTone"] = np.random.choice(np.arange(40, 100, 0.5))

    parameters["signal_df"] = pd.DataFrame([])  # Physiological recording
    parameters["results_df"] = pd.DataFrame([])  # Behavioral results

    # Set default path /Results/ 'Subject ID' /
    parameters["participant"] = participant
    parameters["session"] = session
    parameters["path"] = os.getcwd()
    if resultPath is None:
        parameters["results"] = parameters["path"] + "/data/" + participant + session
    else:
        parameters["results"] = None
    # Create Results directory if not already exists
    if not os.path.exists(parameters["results"]):
        os.makedirs(parameters["results"])

    # Store posterior in a dictionnary
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
        if serialPort is None:
            serialPort = findOximeter()
            if serialPort is None:
                print(
                    "Cannot find the Pulse Oximeter automatically, please",
                    " enter port reference in the GUI",
                )
                core.quit()

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
    elif setup == "fMRI":
        parameters["fMRItrigger"] = ["5"]  # Keys to listen for fMRI trigger

    #######
    # Texts
    #######
    btnext = "press SPACE" if parameters["device"] == "keyboard" else "click the mouse"
    parameters["texts"] = {
        "textTaskStart": "The task is now going to start, get ready.",
        "textBreaks": f"Break. You can rest as long as you want. Just {btnext} when you want to resume the task.",
        "textNext": f"Please {btnext} to continue",
        "textWaitTrigger": "Waiting for fMRI trigger...",
        "Decision": {
            "Intero": """Are these beeps faster or slower than your heart?""",
            "Extero": """Are these beeps faster or slower than the previous?""",
        },
        "Confidence": """How confident are you in your choice?""",
    }

    parameters[
        "Tutorial1"
    ] = """During this experiment, we will record your pulse and play beeps based on your heart rate.

You will only be allowed to focus on the internal sensations of your heartbeats, but not to measure your heart rate by any other means (e.g. checking pulse at your wrist or your neck).
        """
    if parameters["setup"] != "fmri":

        parameters[
            "pulseTutorial1"
        ] = "Please place the pulse oximeter on your forefinger. Use your non-dominant hand as depicted in this schema."

        parameters[
            "pulseTutorial2"
        ] = "If you can feel your heartbeats when you have the pulse oximeter in your forefinger, try to place it on another finger."

        parameters[
            "pulseTutorial3"
        ] = "You can test different configurations until you find the finger which provides you with the less sensory input about your heart rate."

        parameters[
            "pulseTutorial4"
        ] = "Please enter the number of the finger corresponding to the finger where you decided to place the pulse oximeter."

    parameters[
        "Tutorial2"
    ] = "When you see this icon, try to focus on your heartbeat for 5 seconds. Try not to move, as we are recording your pulse in this period"

    moreResp = "UP key" if parameters["device"] == "keyboard" else "RIGHT mouse button"
    lessResp = "DOWN key" if parameters["device"] == "keyboard" else "LEFT mouse button"
    parameters[
        "Tutorial3_icon"
    ] = """After this 'heart listening' period, you will see the same icon and hear a series of beeps."""
    parameters[
        "Tutorial3_responses"
    ] = f"""As quickly and accurately as possible, you will listen to these beeps and decide if they are faster ({moreResp}) or slower ({lessResp}) than your own heart rate.

The beeps will ALWAYS be slower or faster than your heart. Please guess, even if you are unsure."""

    if parameters["ExteroCondition"] is True:
        parameters[
            "Tutorial3bis"
        ] = """For some trials, instead of seeing the heart icon, you will see a listening icon. You will then have to listen to a first set of beeps, instead of your heart."""

        parameters[
            "Tutorial3ter"
        ] = f"""After these first beeps, you will see the response icons appear, and a second set of beeps will play.

As quickly and accurately as possible, you will listen to these beeps and decide if they are faster ({moreResp}) or slower ({lessResp}) than the first set of beeps.

The second series of beeps will ALWAYS be slower or faster than the first series. Please guess, even if you are unsure."""

    parameters[
        "Tutorial4"
    ] = """Once you have provided your decision, you will also be asked to rate how confident you feel in your decision.

Here, the maximum rating (100) means that you are totally certain in your choice, and the smallest rating (0) means that you felt that you were guessing.

You should use mouse to select your rating"""

    parameters[
        "Tutorial5"
    ] = """This sequence will be repeated during the task.

At times the task may be very difficult; the difference between your true heart rate and the presented beeps may be very small.

This means that you should try to use the entire length of the confidence scale to reflect your subjective uncertainty on each trial.

As the task difficulty will change over time, it is rare that you will be totally confident or totally uncertain."""

    parameters[
        "Tutorial6"
    ] = """This concludes the tutorial. If you have any questions, please ask the experimenter now.
Otherwise, you can continue to the main task."""
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
    parameters["BrainVisionIP"] = BrainVisionIP
    if parameters["device"] == "keyboard":
        parameters["confScale"] = [1, 10]
    elif parameters["device"] == "mouse":
        parameters["myMouse"] = event.Mouse()

    return parameters
