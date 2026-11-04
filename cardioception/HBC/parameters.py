# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University

import datetime
import os
import time
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import serial
from systole import serialSim
from systole.recording import Oximeter

from .._log import start_session_log
from .._resources import resource_filename
from .._rng import make_rng
from .._triggers import validate as validate_triggers
from ..output import SessionPaths
from ..scales import DISCRETE_1_7, ConfidenceScale
from .languages import get_texts


def getParameters(
    participant: str = "Participant",
    session: str = "001",
    serialPort: str = "COM3",
    taskVersion: str = "Garfinkel",
    setup: str = "behavioral",
    screenNb: int = 0,
    fullscr: bool = True,
    resultPath: Optional[str] = None,
    overwrite: bool = False,
    confidenceScale: Optional[ConfidenceScale] = None,
    systole_kw: dict = {},
    seed: Optional[int] = None,
    triggers: Optional[Dict[str, Any]] = None,
    language: str = "english",
    recorder=None,
) -> Dict:
    """Create Heartbeat Counting task parameters.

    Parameters
    ----------
    language : str
        The language of the instructions, a file in ``HBC/texts/``. Can be
        `"english"` (default) or `"german"`;
        :func:`cardioception.HBC.languages.available` lists them. An unknown
        language raises ``ValueError`` before anything is created.
    participant : str
        Subject ID. Default is 'exteroStairCase'.
    recorder : object | None
        A recording device to use instead of the one `setup` would open, e.g.
        :class:`cardioception.devices.LSLRecorder` to read ECG from an LSL
        stream. Overrides `setup`'s choice of device but not its window.
    resultPath : str or None
        Root directory holding every participant. Results go to
        `<resultPath>/sub-<participant>/ses-<session>/run-<timestamp>/`. Defaults
        to `<cwd>/data`.
    overwrite : bool
        Allow writing into a run directory that already holds results. Off by
        default, so a repeated run cannot silently replace an earlier one.
    confidenceScale : ConfidenceScale | None
        How confidence is collected and what its numbers mean. Defaults to seven
        discrete steps, labelled in the chosen language. A scale passed here
        keeps its own labels. See :mod:`cardioception.scales`.
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
        Task version to run. Can be 'Garfinkel', 'Schandry', 'test' or None.

    Attributes
    ----------
    conditions : 1d array-like of str
        The conditions. Can be 'Rest', 'Training' or 'Count'.
    confidenceScale : :py:class:`cardioception.scales.ConfidenceScale`
        The confidence scale in use, and the meaning of its numbers.
    heartLogo : `psychopy.visual.ImageStim`
        Image presented during resting conditions.
    labelsRating : list
        The labels of the confidence rating scale.
    language : str
        The language of the instructions.
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
        Task version to run. Can be 'Garfinkel', 'Schandry', 'test' or None.
    texts : dict
        The texts to be presented, from ``HBC/texts/<language>.yaml``.
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
    # Loaded first, so an unknown language or an incomplete file fails before
    # the session directory exists or a window opens.
    texts = get_texts(language)

    from psychopy import sound, visual

    from .. import __version__

    parameters: Dict[str, Any] = {}
    # One generator for the whole session. The seed is always recorded, so a
    # session can be replayed even when the caller did not choose one.
    parameters["rng"], parameters["seed"] = make_rng(seed)
    parameters["restPeriod"] = True
    parameters["restLength"] = 30
    parameters["randomize"] = True
    parameters["startKey"] = "space"
    parameters["rating"] = True
    # The default scale takes its end labels from the chosen language, as the
    # HRD's does. A scale the caller passes keeps the labels it was given.
    if confidenceScale is None:
        confidenceScale = DISCRETE_1_7.with_labels(texts["labelsRating"])
    parameters["confidenceScale"] = confidenceScale
    parameters["labelsRating"] = list(confidenceScale.labels)
    parameters["language"] = language
    parameters["texts"] = texts
    parameters["taskVersion"] = taskVersion
    parameters["results_df"] = pd.DataFrame({})
    parameters["setup"] = setup

    # Callables run at each trial event. Validated so a typo fails at launch.
    parameters["triggers"] = validate_triggers(triggers)

    # Experimental design - can choose between a version based on recent
    # papers from Sarah Garfinkel's group, or the classic Schandry approach.
    # The primary difference ebtween the two is the order of trials and the
    # use of resting periods between trials.
    if parameters["taskVersion"] == "Garfinkel":
        parameters["times"] = np.array([25, 30, 35, 40, 45, 50])
        parameters["rng"].shuffle(parameters["times"])
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
    # Validated here, before anything is created. Raising in the recorder
    # block below is too late: by then the session directory exists, the log
    # file is open and the window is on screen, so a typo leaves an empty run
    # directory behind and flashes a window at the participant.
    if setup not in ("behavioral", "test"):
        raise ValueError(f"setup should be 'behavioral' or 'test', got {setup!r}.")

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

    parameters["startTime"] = time.time()
    parameters["paths"].write_manifest(
        task="HBC",
        version=__version__,
        start_epoch=parameters["startTime"],
        start_local=datetime.datetime.now().isoformat(timespec="seconds"),
        seed=parameters["seed"],
        setup=setup,
        language=language,
        recording=recorder.describe() if hasattr(recorder, "describe") else None,
        taskVersion=taskVersion,
        conditions=parameters["conditions"],
        times=[int(t) for t in parameters["times"]],
        confidence=parameters["confidenceScale"].describe(),
    )

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
        # A read that finds no data returns after a second rather than blocking
        # forever, so an unplugged or stalled oximeter fails visibly.
        port = serial.Serial(serialPort, timeout=1)
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
    else:
        # Any other value used to fall through and return a dictionary with no
        # `oxiTask` in it, so the session died inside `trial()` -- after the
        # window had opened, in front of the participant, on a KeyError rather
        # than on the typo that caused it. HRD raises here; so does this now.
        raise ValueError(f"setup should be 'behavioral' or 'test', got {setup!r}.")

    parameters["textSize"] = 0.04

    return parameters
