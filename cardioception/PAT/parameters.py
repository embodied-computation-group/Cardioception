# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Parameters of the Phase Adjustment Task (PAT).

The task follows the ECG version of Hodgetts et al. (2026), Psychophysiology
63:e70415: one tone per heartbeat, at a delay after the R-wave that the
participant moves with the mouse wheel until tones and heartbeats feel
simultaneous. The exteroceptive control task replaces the heartbeat with a
vibration on the hand.
"""

import os
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from .languages import danish, english

LANGUAGES = ("english", "danish")
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
    confScale: Sequence[int],
    wheelDirection: int = 1,
) -> None:
    """Raise a ValueError naming the first invalid setting."""
    if mode not in MODES:
        raise ValueError(f"mode should be one of {MODES}, got {mode!r}.")
    if language not in LANGUAGES:
        raise ValueError(
            f"Invalid language: {language!r}. Can be one of {', '.join(LANGUAGES)}."
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
    if len(confScale) != 2 or not confScale[0] < confScale[1]:
        raise ValueError(f"confScale should be (low, high), got {confScale!r}.")


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
    confScale: Sequence[int] = (1, 10),
    markerStream: Optional[str] = "PAT",
    engine=None,
) -> Dict[str, Any]:
    """Create Phase Adjustment Task parameters.

    Parameters
    ----------
    participant : str
        Participant ID.
    session : str
        Session label. Results go to `data/<participant><session>/` unless
        `resultPath` is given.
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
        Where to save the results. Default is `<cwd>/data/<participant><session>/`.
    language : str
        `"english"` or `"danish"`.
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
    confScale : tuple of int
        Ends of the confidence scale. The paper used 1 to 10.
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
        * `path`, `resultPath`: working and result directories.

    Notes
    -----
    Three files are written to `resultPath`, after every trial: `final.txt`
    (one row per trial), `tones.txt` (one row per tone) and `parameters.txt`
    (the settings). All times are LSL seconds (`pylsl.local_clock`), except
    `WallTime` in `final.txt`, which is `time.time()` at the press.

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
        confScale=confScale,
        wheelDirection=wheelDirection,
    )
    if recorder is None and not extero and engine is None:
        raise ValueError(
            "The PAT needs an ECG recorder, e.g. "
            "recorder=LSLRecorder(name='PLUX', channel='ECG2'), unless extero=True."
        )

    parameters: Dict[str, Any] = {}
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
    parameters["confScale"] = [int(confScale[0]), int(confScale[1])]
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

    # Start phases: one sequence for practice, one for the main trials
    parameters["startPhasePractice"] = startPhaseSequence(
        parameters["nPractice"], parameters["startPhases"]
    )
    parameters["startPhaseMain"] = startPhaseSequence(
        parameters["nTrials"], parameters["startPhases"]
    )

    parameters["results_df"] = pd.DataFrame([])
    parameters["tones"] = []
    parameters["trialBlocks"] = {}  # trial number -> block, for tones.txt

    # Result directory, default /data/<participant><session>/
    parameters["path"] = os.getcwd()
    if resultPath is None:
        parameters["resultPath"] = os.path.join(
            parameters["path"], "data", participant + session
        )
    else:
        parameters["resultPath"] = resultPath
    if os.path.exists(os.path.join(parameters["resultPath"], "final.txt")):
        raise ValueError(
            f"{parameters['resultPath']} already holds a PAT run (final.txt). "
            "Use another session name, or move the old files away first."
        )
    os.makedirs(parameters["resultPath"], exist_ok=True)

    ##############
    # Load texts #
    ##############
    texts_fn = english if language == "english" else danish
    parameters["texts"] = texts_fn(
        device=device, extero=extero, confScale=confScale, showDial=showDial
    )
    parameters["labelsRating"] = parameters["texts"]["VASlabels"]

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
            source = VirtualBeatSource(exteroPeriod)
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

    return parameters
