# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Parameters of the Phase Adjustment Task (PAT).

The task follows the ECG version of Hodgetts et al. (2026), Psychophysiology
63:e70415: one tone per heartbeat, at a delay after the R-wave that the
participant moves with the mouse wheel until tones and heartbeats feel
simultaneous. The exteroceptive control task replaces the heartbeat with a
vibration on the hand.

As for the other tasks, one random generator, built from ``seed`` by
:func:`cardioception._rng.make_rng`, draws everything random in a session:
the start phases, the simulated heart of the exteroceptive task, the tutorial
start phase and the starting position of every confidence marker. The seed is
recorded in ``manifest.json``, so a session can be drawn again.
"""

import datetime
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from .._log import get_logger, start_session_log
from .._rng import make_rng
from ..output import SessionPaths
from ..scales import DISCRETE_1_10, ConfidenceScale
from .languages import available as available_languages
from .languages import get_texts

logger = get_logger()

MODES = ("relative", "absolute")
DEVICES = ("keyboard", "mouse")


def startPhaseSequence(
    n: int,
    phases: Sequence[float] = (0, 90, 180, 270),
    rng: Optional[np.random.Generator] = None,
) -> List[float]:
    """Draw the start phase of each trial, as the PAT-ECG firmware does.

    The sequence is made of blocks, each a random permutation of `phases`. A
    block is drawn again when its first value equals the last value of the
    block before, so no start phase follows itself across a block boundary
    (or within a block, since a permutation holds each value once).

    Parameters
    ----------
    n : int
        Length of the sequence.
    phases : sequence of float
        The start phases, in degrees.
    rng : numpy.random.Generator | None
        Random generator, for reproducible sequences.

    Returns
    -------
    sequence : list of float
        `n` start phases, in degrees.

    """
    if n < 0:
        raise ValueError(f"n should be 0 or more, got {n}.")
    phases = list(phases)
    if len(phases) == 0:
        raise ValueError("Give at least one start phase.")
    rng = np.random.default_rng() if rng is None else rng
    distinct = len(set(phases)) > 1

    sequence: List[float] = []
    while len(sequence) < n:
        block = [phases[i] for i in rng.permutation(len(phases))]
        while distinct and sequence and block[0] == sequence[-1]:
            block = [phases[i] for i in rng.permutation(len(phases))]
        sequence.extend(block)
    return sequence[:n]


def _validate(
    mode: str,
    nTrials: int,
    nPractice: int,
    startPhases: Sequence[float],
    device: str,
    language: str,
    extero: bool,
    exteroPeriod: Union[str, float, Sequence[float]],
    audioLead: float,
    toneFreq: float,
    toneDuration: float,
    toneVolume: float,
    vibrationVolume: float,
    dialGainDeg: float,
    dialGainMs: float,
    minToneGap: float,
    confidenceScale: Optional[ConfidenceScale],
    wheelDirection: int = 1,
) -> None:
    """Raise a ValueError naming the first invalid setting."""
    if mode not in MODES:
        raise ValueError(f"mode should be one of {MODES}, got {mode!r}.")
    if language not in available_languages():
        raise ValueError(
            f"Invalid language: {language!r}. Can be one of "
            f"{', '.join(available_languages())}."
        )
    if device not in DEVICES:
        raise ValueError(f"device should be one of {DEVICES}, got {device!r}.")
    if not isinstance(extero, bool):
        raise ValueError(f"extero should be True or False, got {extero!r}.")
    if int(nTrials) != nTrials or nTrials < 1:
        raise ValueError(
            f"nTrials should be a whole number of 1 or more, got {nTrials}."
        )
    if int(nPractice) != nPractice or nPractice < 0:
        raise ValueError(
            f"nPractice should be a whole number of 0 or more, got {nPractice}."
        )
    if len(startPhases) == 0:
        raise ValueError("startPhases should hold at least one phase.")
    for phase in startPhases:
        if not 0 <= phase < 360:
            raise ValueError(
                f"Start phases are degrees in [0, 360), got {phase} in {startPhases}."
            )
    if isinstance(exteroPeriod, str):
        if exteroPeriod != "simulated":
            raise ValueError(
                "exteroPeriod should be 'simulated', a period in seconds or a "
                f"sequence of periods in seconds, got {exteroPeriod!r}."
            )
    else:
        periods = np.atleast_1d(np.asarray(exteroPeriod, dtype=float))
        if periods.size == 0 or np.any(~np.isfinite(periods)) or np.any(periods <= 0):
            raise ValueError(
                f"exteroPeriod should hold positive seconds, got {exteroPeriod!r}."
            )
        if np.any(periods < 0.25) or np.any(periods > 3.0):
            raise ValueError(
                "exteroPeriod should be seconds between 0.25 and 3, got "
                f"{exteroPeriod!r}."
            )
    for name, value in (
        ("audioLead", audioLead),
        ("toneFreq", toneFreq),
        ("toneDuration", toneDuration),
        ("dialGainDeg", dialGainDeg),
        ("dialGainMs", dialGainMs),
    ):
        if not value > 0:
            raise ValueError(f"{name} should be above 0, got {value}.")
    if not 0 < toneVolume <= 1:
        raise ValueError(f"toneVolume should be in (0, 1], got {toneVolume}.")
    if not 0 <= vibrationVolume <= 1:
        raise ValueError(f"vibrationVolume should be in [0, 1], got {vibrationVolume}.")
    if wheelDirection not in (1, -1):
        raise ValueError(f"wheelDirection should be 1 or -1, got {wheelDirection!r}.")
    if not minToneGap >= 0:
        raise ValueError(f"minToneGap should be 0 or more, got {minToneGap}.")
    if confidenceScale is not None and not isinstance(confidenceScale, ConfidenceScale):
        raise ValueError(
            "confidenceScale should be a cardioception.scales.ConfidenceScale "
            f"or None, got {confidenceScale!r}."
        )


def _markerOutlet(name: str):
    """Open an LSL string outlet for the task's JSON markers."""
    import pylsl

    info = pylsl.StreamInfo(
        name,
        "Markers",
        1,
        pylsl.IRREGULAR_RATE,
        pylsl.cf_string,
        f"cardioception-{name}",
    )
    return pylsl.StreamOutlet(info)


def getParameters(
    participant: str = "SubjectTest",
    session: str = "001",
    recorder=None,
    mode: str = "relative",
    nTrials: int = 28,
    nPractice: int = 8,
    startPhases: Sequence[float] = (0, 90, 180, 270),
    device: str = "keyboard",
    screenNb: int = 0,
    fullscr: bool = True,
    resultPath: Optional[str] = None,
    overwrite: bool = False,
    seed: Optional[int] = None,
    language: str = "english",
    extero: bool = False,
    exteroPeriod: Union[str, float, Sequence[float]] = "simulated",
    latencyBias: float = 0.05,
    audioLead: float = 0.05,
    toneFreq: float = 1000.0,
    toneDuration: float = 0.03,
    toneVolume: float = 0.5,
    vibrationVolume: float = 0.0,
    dialGainDeg: float = 10.0,
    dialGainMs: float = 25.0,
    wheelDirection: int = 1,
    showDial: bool = True,
    minToneGap: float = 0.3,
    confidenceScale: Optional[ConfidenceScale] = None,
    markerStream: Optional[str] = "PAT",
    engine=None,
) -> Dict[str, Any]:
    """Create Phase Adjustment Task parameters.

    Parameters
    ----------
    participant : str
        Participant ID.
    session : str
        Session label.
    recorder : :class:`cardioception.devices.LSLRecorder` | None
        The ECG stream. Required unless `extero=True`. The task reads its inlet
        through the beat detector, so do not read from it yourself.
    mode : str
        `"relative"`: the dial is a phase of the anticipated heart period, in
        degrees, and wraps at 360. `"absolute"`: the dial is a delay in ms after
        the R-wave, and wraps at the anticipated period.
    nTrials : int
        Number of main trials. The paper used 28.
    nPractice : int
        Number of practice trials before the main trials. The paper used 8.
    startPhases : sequence of float
        Start phases of the dial, in degrees. Each trial starts at one of them,
        in blocks of a random permutation (see :func:`startPhaseSequence`).
    device : str
        Confidence rating with the arrow keys (`"keyboard"`) or the mouse
        (`"mouse"`). The dial is the mouse wheel either way.
    screenNb : int
        Screen number, passed to :py:class:`psychopy.visual.Window`.
    fullscr : bool
        If `True`, the window is full screen.
    resultPath : str | None
        Root directory holding every participant; results go to
        `<resultPath>/sub-<participant>/ses-<session>/run-<timestamp>/`.
        Defaults to `<cwd>/data`.
    overwrite : bool
        Allow writing into a run directory that already holds results.
    seed : int | None
        Seeds the session generator, which draws the start phases, the
        simulated heart of the exteroceptive task, the tutorial start phase
        and the starting position of the confidence marker. Drawn from
        entropy when `None`, and recorded either way.
    language : str
        A language in `cardioception/PAT/texts`, `"english"` or `"danish"` so
        far (:func:`cardioception.PAT.languages.available` lists them).
    extero : bool
        If `True`, run the exteroceptive control task: a vibration on the hand
        takes the place of the heartbeat, and no ECG is needed.
    exteroPeriod : str | float | sequence of float
        Period of the vibration in the extero task: `"simulated"` (a heart
        period series with realistic variability, as in the PAT-ECG firmware),
        a fixed period in seconds, or a sequence of periods in seconds to replay.
    latencyBias : float
        Seconds subtracted from every tone target, for the delay between the
        R-wave and its LSL timestamp plus the speaker's delay after the
        reported onset. Neither shows in the recording.
    audioLead : float
        Minimum time between scheduling a tone and its target, in seconds. A
        tone that cannot be scheduled that far ahead is anchored on the
        predicted next R-wave instead.
    toneFreq, toneDuration, toneVolume : float
        The tone: frequency (Hz), duration (s) and volume (0 to 1).
    vibrationVolume : float
        Volume (0 to 1) of the 50 Hz burst on the right audio channel that marks
        each beat of the exteroceptive task, for an amplifier and tactor on that
        channel. Default is `0`, silent, so headphones or speakers never carry
        it by accident.
    dialGainDeg : float
        Degrees per wheel notch in relative mode.
    dialGainMs : float
        Milliseconds per wheel notch in absolute mode.
    wheelDirection : int
        `1` or `-1`. With `1`, rolling the wheel away from you (a positive
        wheel step in PsychoPy, which is Windows' forward rotation) moves the
        beeps later. Use `-1` for a mouse or driver that reverses the wheel.
    showDial : bool
        If `True`, a ring with a pointer around the fixation cross shows how
        far the wheel has turned since the trial began (never the phase
        itself), and the pointer flashes with each beep.
    minToneGap : float
        A tone is skipped when its target is less than this many seconds after
        the previous target, so the participant never hears two tones in quick
        succession while turning the dial.
    confidenceScale : ConfidenceScale | None
        How confidence is collected. `None` takes
        :data:`cardioception.scales.DISCRETE_1_10`, the 1 to 10 of the paper,
        with the end labels of the language. A scale passed in keeps its own
        labels. Its ends are the numbers the instructions name.
    markerStream : str | None
        Name of the LSL marker stream the task opens. Every beat, tone, dial
        move, press and rating is pushed to it as one JSON string, so a
        LabRecorder file holds the ECG and the task together. `None` falls back
        on the recorder's own marker outlet, if it has one.

    Returns
    -------
    parameters : dict
        The settings above, plus:

        * `win`: the PsychoPy window.
        * `texts`: the instructions, from :mod:`cardioception.PAT.languages`.
        * `engine`: the :class:`cardioception.PAT.engine.PhaseEngine` that turns
          beats and dial moves into tones.
        * `outlet`: the LSL marker outlet, or `None`.
        * `startPhasePractice`, `startPhaseMain`: the start phase of each trial.
        * `results_df`: the trial results, filled during the task.
        * `tones`: the tone rows, filled during the task.
        * `rng`, `seed`: the session generator and its seed.
        * `paths`: the :class:`cardioception.output.SessionPaths` of the run.
        * `path`, `resultPath`: working and run directories.

    Notes
    -----
    `manifest.json` (the session's settings) and `session.log` are written to
    the run directory at once. Three tab-separated files follow, each named
    `sub-<participant>_ses-<session>_run-<timestamp>_<kind>.txt`: `final`
    (one row per trial) and `tones` (one row per tone), rewritten after every
    trial, and `parameters` (the settings), written when the task starts. All
    times are LSL seconds (`pylsl.local_clock`), except `WallTime` in
    `final`, which is `time.time()` at the press.

    """
    _validate(
        mode=mode,
        nTrials=nTrials,
        nPractice=nPractice,
        startPhases=startPhases,
        device=device,
        language=language,
        extero=extero,
        exteroPeriod=exteroPeriod,
        audioLead=audioLead,
        toneFreq=toneFreq,
        toneDuration=toneDuration,
        toneVolume=toneVolume,
        vibrationVolume=vibrationVolume,
        dialGainDeg=dialGainDeg,
        dialGainMs=dialGainMs,
        minToneGap=minToneGap,
        confidenceScale=confidenceScale,
        wheelDirection=wheelDirection,
    )
    if recorder is None and not extero and engine is None:
        raise ValueError(
            "The PAT needs an ECG recorder, e.g. "
            "recorder=LSLRecorder(name='PLUX', channel='ECG2'), unless extero=True."
        )

    from .. import __version__

    parameters: Dict[str, Any] = {}
    parameters["rng"], parameters["seed"] = make_rng(seed)
    parameters["participant"] = participant
    parameters["session"] = session
    parameters["mode"] = mode
    parameters["extero"] = extero
    parameters["exteroPeriod"] = (
        exteroPeriod
        if isinstance(exteroPeriod, str)
        else np.atleast_1d(np.asarray(exteroPeriod, dtype=float)).tolist()
    )
    parameters["nTrials"] = int(nTrials)
    parameters["nPractice"] = int(nPractice)
    parameters["nBreaking"] = 10
    parameters["startPhases"] = [float(p) for p in startPhases]
    parameters["device"] = device
    parameters["screenNb"] = screenNb
    parameters["monitor"] = "testMonitor"
    parameters["language"] = language
    parameters["latencyBias"] = float(latencyBias)
    parameters["audioLead"] = float(audioLead)
    parameters["toneFreq"] = float(toneFreq)
    parameters["toneDuration"] = float(toneDuration)
    parameters["toneVolume"] = float(toneVolume)
    parameters["vibrationVolume"] = float(vibrationVolume)
    parameters["dialGainDeg"] = float(dialGainDeg)
    parameters["dialGainMs"] = float(dialGainMs)
    parameters["minToneGap"] = float(minToneGap)
    parameters["markerStream"] = markerStream

    # Task flow
    parameters["startKey"] = "space"  # starts a trial, and ends it
    parameters["dialKeys"] = ["left", "right"]  # a second dial; [] to disable
    parameters["minTrialTime"] = 3.0  # space is ignored this long into a trial
    parameters["minRatingTime"] = 0.5
    parameters["maxRatingTime"] = None  # wait for the rating, as the paper did
    parameters["statusEvery"] = 1.0  # seconds between experimenter status lines
    parameters["noBeatWarning"] = 3.0  # warn the experimenter after this silence
    parameters["textSize"] = 0.04

    # The dial on screen, and the guided tutorial
    parameters["wheelDirection"] = int(wheelDirection)
    parameters["showDial"] = bool(showDial)
    parameters["dialRadius"] = 0.15  # height units, around the fixation cross
    parameters["flashDuration"] = 0.1  # seconds the pointer brightens per beep
    parameters["tutorialListenTones"] = 4  # beeps heard before going on
    parameters["tutorialNotches"] = 3  # notches each way before going on
    parameters["tutorialStageTimeout"] = 20.0  # space works after this anyway

    # Start phases: one sequence for practice, one for the main trials
    parameters["startPhasePractice"] = startPhaseSequence(
        parameters["nPractice"], parameters["startPhases"], rng=parameters["rng"]
    )
    parameters["startPhaseMain"] = startPhaseSequence(
        parameters["nTrials"], parameters["startPhases"], rng=parameters["rng"]
    )

    parameters["results_df"] = pd.DataFrame([])
    parameters["tones"] = []
    parameters["trialBlocks"] = {}  # trial number -> block, for tones.txt

    # Run directory: <resultPath>/sub-<participant>/ses-<session>/run-<time>/
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
    parameters["resultPath"] = parameters["paths"].directory
    parameters["logFile"] = start_session_log(parameters["paths"].directory)

    ##############
    # Load texts #
    ##############
    # The ends of the scale are known before its labels, which come from the
    # texts, so the instructions can name them.
    ends = confidenceScale if confidenceScale is not None else DISCRETE_1_10
    parameters["texts"] = get_texts(
        language,
        device=device,
        extero=extero,
        low=ends.low,
        high=ends.high,
        showDial=showDial,
    )
    if confidenceScale is None:
        confidenceScale = DISCRETE_1_10.with_labels(parameters["texts"]["VASlabels"])
    parameters["confidenceScale"] = confidenceScale
    parameters["labelsRating"] = list(confidenceScale.labels)

    ###########################
    # Marker outlet and engine #
    ###########################
    # Built before the window, so a missing sound card or stream fails with
    # its own message rather than behind a full screen window.
    # An injected engine brings its own markers, so no stream is opened for it.
    parameters["outlet"] = None
    if engine is None and markerStream is not None:
        parameters["outlet"] = _markerOutlet(markerStream)
    elif recorder is not None:
        parameters["outlet"] = getattr(recorder, "outlet", None)
    parameters["recorder"] = recorder

    if engine is None:
        from .engine import LSLBeatSource, PhaseEngine, TonePlayer, VirtualBeatSource

        source: Any
        if extero:
            # The simulated heart draws its own series from a seed, taken from
            # the session generator so the seed in the manifest decides it.
            source = VirtualBeatSource(
                exteroPeriod, seed=int(parameters["rng"].integers(2**32))
            )
        else:
            source = LSLBeatSource(recorder)
        player = TonePlayer(
            freq=parameters["toneFreq"],
            duration=parameters["toneDuration"],
            volume=parameters["toneVolume"],
            vib_volume=parameters["vibrationVolume"],
        )
        engine = PhaseEngine(
            source,
            player,
            mode,
            latency_bias=parameters["latencyBias"],
            audio_lead=parameters["audioLead"],
            min_tone_gap=parameters["minToneGap"],
            outlet=parameters["outlet"],
        )
    parameters["engine"] = engine

    ###############
    # Open window #
    ###############
    from psychopy import event, visual

    parameters["win"] = visual.Window(
        monitor=parameters["monitor"],
        screen=parameters["screenNb"],
        fullscr=fullscr,
        units="height",
    )
    parameters["win"].mouseVisible = False
    # The wheel is the dial, so the mouse is needed whatever the rating device
    parameters["myMouse"] = event.Mouse(win=parameters["win"])

    parameters["startTime"] = time.time()
    parameters["paths"].write_manifest(
        task="PAT",
        version=__version__,
        start_epoch=parameters["startTime"],
        start_local=datetime.datetime.now().isoformat(timespec="seconds"),
        seed=parameters["seed"],
        device=device,
        language=language,
        mode=mode,
        extero=extero,
        exteroPeriod=parameters["exteroPeriod"],
        nTrials=parameters["nTrials"],
        nPractice=parameters["nPractice"],
        startPhases=parameters["startPhases"],
        confidence=confidenceScale.describe(),
        recording=(
            recorder.describe()
            if recorder is not None and hasattr(recorder, "describe")
            else None
        ),
    )
    logger.info(
        f"PAT session {participant}/{session}: {mode} mode"
        f"{', exteroceptive' if extero else ''}, seed {parameters['seed']}, "
        f"results in {parameters['resultPath']}"
    )

    return parameters
