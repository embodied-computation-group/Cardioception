# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import datetime
import os
import time
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import serial
from systole import serialSim
from systole.recording import Oximeter

from cardioception.HRD.languages import get_texts

from .._log import get_logger, start_session_log
from .._resources import resource_filename
from .._rng import make_rng
from .._triggers import validate as validate_triggers
from ..output import SessionPaths
from ..scales import DISCRETE_1_10, VAS_0_100, ConfidenceScale
from .config import TaskConfig

logger = get_logger()


def _build_design(
    parameters: Dict[str, Any],
    exteroception: bool,
    catchTrials: float,
    stairType: str,
) -> None:
    """Decide which trial is which, and in what order.

    Writes ``Modality``, ``staircaseType`` and the posterior store. Everything
    random here comes from ``parameters["rng"]``, so the design is reproducible
    from the recorded seed alone.
    """
    # Store posterior in a dictionary
    parameters["staircaisePosteriors"] = {}
    parameters["staircaisePosteriors"]["Intero"] = []
    if exteroception is True:
        parameters["staircaisePosteriors"]["Extero"] = []

    nCatch = int(parameters["nTrials"] * catchTrials)
    nStaircase = parameters["nTrials"] - nCatch

    if stairType != "psi":
        raise ValueError(
            f"stairType={stairType!r}. The nUp/nDown staircase was removed in "
            "0.8.0: it was a 1-up/1-down rule, which converges on 50% correct, "
            "not the 71% the documentation claimed, and it was never used for "
            "published data. 'psi' is the only staircase."
        )
    sc = np.array(["psi"] * nStaircase)

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
            logger.warning(
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


def _build_staircases(
    parameters: Dict[str, Any], exteroception: bool, nTrials: int
) -> None:
    """One psi staircase per modality."""
    from psychopy import data

    # Default parameters for the basic staircase are set here. Please see
    # PsychoPy Staircase Handler Documentation for full options. By default,
    # the task implements a staircase using Psi method.
    # If UpDown is selected, 1 or 2 interleaved staircases are used (see
    # options in parameters dictionary), one is initalized 'high' and the other
    # 'low'.
    def psiHandler():
        """One psi staircase over the full stimulus range."""
        return data.PsiHandler(
            nTrials=nTrials,
            intensRange=list(parameters["intensRange"]),
            alphaRange=list(parameters["alphaRange"]),
            betaRange=list(parameters["betaRange"]),
            # Grid resolution of the psi posterior. Not configurable: this is
            # a memory/resolution tradeoff, and the array it sizes is the one
            # that used to leak 2.6 GB over a session.
            intensPrecision=1,
            alphaPrecision=1,
            betaPrecision=0.1,
            delta=parameters["delta"],
            stepType="lin",
            expectedMin=0,
        )

    parameters["stairCase"] = {"Intero": psiHandler()}
    if exteroception is True:
        parameters["stairCase"]["Extero"] = psiHandler()


def _open_recording(
    parameters: Dict[str, Any],
    setup: str,
    serialPort: str,
    systole_kw: dict,
    recorder,
) -> None:
    """Attach the device the pulse will be read from.

    An explicit ``recorder`` wins over ``setup`` and touches no serial port,
    which is what lets a session run with no hardware attached.
    """
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

        # parameters['oxiTask'] = Nonin3231USB(serial=port, add_channels=1).setup().read(1)

    elif setup == "test":
        # Use pre-recorded pulse time series for testing
        port = serialSim()
        parameters["oxiTask"] = Oximeter(
            serial=port, sfreq=75, add_channels=1, **systole_kw
        )
        parameters["oxiTask"].setup().read(duration=1)

    else:
        # Unguarded before, so an unknown value returned a dict with no
        # "oxiTask" and died inside run() after the window had opened.
        raise ValueError(
            f"setup should be 'behavioral' or 'test', got {setup!r}. "
            "Pass recorder= to use a device other than the Nonin oximeter."
        )


def _build_stimuli(parameters: Dict[str, Any], fullscr: bool) -> None:
    """Open the window and load every image the task will draw."""
    from psychopy import event, visual

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
    # Needed for nDroppedFrames to count anything, which is what the per-trial
    # DroppedFrames column reports.
    parameters["win"].recordFrameIntervals = True

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
    if parameters["device"] == "mouse":
        parameters["myMouse"] = event.Mouse()


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
    overwrite: bool = False,
    confidenceScale: Optional[ConfidenceScale] = None,
    language: str = "english",
    systole_kw: dict = {},
    seed: Optional[int] = None,
    autopilot=None,
    recorder=None,
    onMissedTrial: str = "represent",
    maxRepresentations: int = 3,
    maxHeartRateAttempts: Optional[int] = None,
    triggers: Optional[Dict[str, Any]] = None,
    config: Optional[TaskConfig] = None,
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
        The number of trials to run.

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
        Root directory holding every participant. Results go to
        `<resultPath>/sub-<participant>/ses-<session>/run-<timestamp>/`. Defaults
        to `<cwd>/data`.
    overwrite : bool
        Allow writing into a run directory that already holds results. Off by
        default, so a repeated run cannot silently replace an earlier one.
    confidenceScale : ConfidenceScale | None
        How confidence is collected and what its numbers mean. Defaults to a
        0-100 visual analogue scale for the mouse and ten discrete steps for the
        keyboard. See :mod:`cardioception.scales`.
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
        Staircase type. `"psi"` is the only value; `"updown"` was removed in
        0.8.0 and now raises. Kept as an argument so scripts passing it fail
        with an explanation rather than a TypeError.
    systole_kw : dict
        Additional keyword arguments for :py:class:`systole.recorder.Oxmeter`.

    Attributes
    ----------
    allowedKeys : list of str
        The possible response keys.
    confidenceScale : :py:class:`cardioception.scales.ConfidenceScale`
        The confidence scale in use, and the meaning of its numbers.
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
        Number of tutorial trials that ask for a confidence rating.
    nFeedback : int
        Number of tutorial trials that show whether the answer was correct.
    nFinger : str or None
        The finger number ("1", "2", "3", "4" or "5") where the participant
        decided to place the pulse oximeter (if relevant).
    nTrials : int
        The number of trials to run. See the parameter of the same name.
    participant : str
        Subject ID. Default is 'Participant'.
    path : str
        The task working directory.
    resultPath : str | None
        Where to save the results.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    signal_df : pandas.DataFrame instance
        Dataframe where the pulse signal recorded during the interoception
        condition will be stored.
    stairCase : dict
        One `psychopy.data.PsiHandler` per modality, keyed `'Intero'` and,
        when the exteroceptive condition is included, `'Extero'`.
    staircaseType : 1d array-like
        Which staircase drives each trial: `'psi'` or `'CatchTrial'`.
    startKey : str
        The key to press to start the task and go to next steps.
    response_keys : dict
        Mapping from trial conditions to keyboard response keys.
    respMax : float
        The maximum time for decision (in seconds).
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

    - 1: trial start
    - 2: listening window opens
    - 3: tone starts, decision begins
    - 4: confidence rating begins
    - 5: trial end

    See :class:`cardioception.HRD._constants.Trigger`. The Heartbeat Counting
    task writes different meanings to the same channel, so a recording has to be
    read knowing which task produced it.

    Every one of these except the trial start also has a timestamp in the
    behavioural results.

    """
    from .. import __version__

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

    # Callables run at each trial event. Documented for years but never
    # created here, so following the docs raised KeyError.
    parameters["triggers"] = validate_triggers(triggers)
    parameters["ExteroCondition"] = exteroception
    parameters["device"] = device
    parameters["screenNb"] = screenNb
    parameters["monitor"] = "testMonitor"

    # The design values that used to be literals in this function, in one
    # object, recorded in the manifest below.
    config = TaskConfig() if config is None else config
    config.apply(parameters)
    if maxHeartRateAttempts is not None:
        # Kept working, though config is where it belongs now.
        parameters["maxHeartRateAttempts"] = maxHeartRateAttempts
    parameters["nTrials"] = nTrials
    parameters["nBreaking"] = nBreaking
    parameters["nFinger"] = None
    parameters["signal_df"] = pd.DataFrame([])  # Physiological recording
    # Rows accumulate in a list and the frame is rebuilt from it. Repeated
    # pd.concat warned on the all-NA row a missed trial produces, and was
    # quadratic in the number of trials.
    parameters["results_rows"] = []
    parameters["results_df"] = pd.DataFrame([])  # Behavioral results

    # Set default path /Results/ 'Subject ID' /
    parameters["participant"] = participant
    parameters["session"] = session
    parameters["path"] = os.getcwd()
    parameters["paths"] = SessionPaths(
        root=(
            resultPath
            if resultPath is not None
            else os.path.join(parameters["path"], "data")
        ),
        participant=participant,
        session=session,
        overwrite=overwrite,
    )
    # Kept for scripts that read it. It is now the run directory, not
    # data/<participant><session>, which two different sessions could share.
    parameters["resultPath"] = parameters["paths"].directory
    parameters["logFile"] = start_session_log(parameters["paths"].directory)

    _build_design(parameters, exteroception, catchTrials, stairType)

    _build_staircases(parameters, exteroception, nTrials)

    parameters["setup"] = setup
    _open_recording(parameters, setup, serialPort, systole_kw, recorder)

    ##############
    # Load texts #
    ##############
    # An unknown language used to leave parameters["texts"] unset, which
    # surfaced as a KeyError at whatever screen first needed a string.
    parameters["texts"] = get_texts(language, device, exteroception)

    _build_stimuli(parameters, fullscr)

    # Resolved here rather than above because the default takes its end labels
    # from the chosen language.
    if confidenceScale is None:
        confidenceScale = DISCRETE_1_10 if device == "keyboard" else VAS_0_100
        confidenceScale = confidenceScale.with_labels(parameters["texts"]["VASlabels"])
    parameters["confidenceScale"] = confidenceScale
    parameters["labelsRating"] = list(confidenceScale.labels)

    # Written now, not at the end: an aborted session used to leave no record of
    # what it had been asked to do.
    parameters["startTime"] = time.time()
    parameters["paths"].write_manifest(
        task="HRD",
        version=__version__,
        start_epoch=parameters["startTime"],
        start_local=datetime.datetime.now().isoformat(timespec="seconds"),
        seed=parameters["seed"],
        device=device,
        language=language,
        setup=setup,
        stairType=stairType,
        exteroception=exteroception,
        nTrials=nTrials,
        catchTrials=catchTrials,
        onMissedTrial=onMissedTrial,
        maxRepresentations=maxRepresentations,
        confidence=confidenceScale.describe(),
        config=config.describe(),
    )

    return parameters
