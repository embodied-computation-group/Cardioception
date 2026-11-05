# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Parameters of a Heartbeat Synchrony Discrimination session.

:func:`getParameters` builds the dictionary :func:`cardioception.HSD.task.run`
reads, in the order the HRD's does: the random generator, the autopilot, the
triggers, the design values, the output directory and log, the texts, the
engine, the devices, the window, the confidence scale and the manifest.

Two devices drive a session: a beat source, which reports R-waves as they are
detected, and a tone player, which plays a tone at a given clock time (see
:mod:`cardioception.HSD._stimulus` for the protocols they satisfy). Both, and
the scheduler between them, must read the same clock, which is kept in
``parameters["clock"]``: :func:`cardioception.devices.beat_source.default_clock`
(``pylsl.local_clock``, or PsychToolbox's ``GetSecs`` without pylsl) unless
``clock=`` says otherwise.

With ``setup="behavioral"`` the devices are the shared ones:
:class:`cardioception.devices.beat_source.LSLBeatSource` over the recorder's
stream and :class:`cardioception.devices.tone_player.TonePlayer`.
"""

import datetime
import os
import time
from dataclasses import replace
from typing import Any, Callable, Dict, Optional, Tuple

from .._log import get_logger, start_session_log
from .._rng import make_rng
from .._triggers import validate as validate_triggers
from ..devices import beat_source as _beat_source
from ..devices import tone_player as _tone_player
from ..output import SessionPaths
from ..scales import DISCRETE_1_10, ConfidenceScale
from ._constants import EVENTS
from ._stimulus import BeatSource, TonePlayer
from .config import TaskConfig
from .languages import get_texts

logger = get_logger()


def _clock_name(clock: Callable[[], float]) -> str:
    module = getattr(clock, "__module__", None) or type(clock).__module__
    name = getattr(clock, "__qualname__", None) or type(clock).__qualname__
    if module.startswith("pylsl") and name == "local_clock":
        return "pylsl.local_clock"
    return f"{module}.{name}"


def default_clock() -> Tuple[Callable[[], float], str]:
    """The session clock and its name.

    :func:`cardioception.devices.beat_source.default_clock`, the clock the
    shared beat sources and tone player use by default: ``pylsl.local_clock``,
    so that beat times, tone onsets and the LSL marker stream share one
    clock, or PsychToolbox's ``GetSecs`` without pylsl. On Windows both read
    QueryPerformanceCounter.
    """
    clock = _beat_source.default_clock()
    return clock, _clock_name(clock)


def _check_devices(setup: str, recorder, beat_source, tone_player) -> None:
    """Refuse a session whose devices cannot be built.

    Checked before anything is written, so a launch that cannot run leaves no
    run directory and no open log behind.
    """
    if beat_source is not None and tone_player is not None:
        return
    if setup == "test":
        raise ValueError(
            "setup='test' has no beat source or tone player of its own. "
            "Pass beat_source= and tone_player=, both reading the "
            "session clock (cardioception.HSD.parameters.default_clock, "
            "or the clock= you pass)."
        )
    if beat_source is None and recorder is None:
        raise ValueError(
            "setup='behavioral' reads the beats from an LSL stream: "
            "pass recorder=LSLRecorder(...)."
        )


def _describe_player(player) -> Dict[str, Any]:
    """The tone player's own description, or what can be read off it.

    The shared PsychPortAudio player has no ``describe``.
    """
    if hasattr(player, "describe"):
        return player.describe()
    return {
        "class": type(player).__name__,
        "fs": getattr(player, "fs", None),
        "device": getattr(player, "device", None),
        "latency_class": getattr(player, "latency_class", None),
    }


def _lsl_beat_source(recorder) -> BeatSource:
    """The shared LSL beat source, typed as HSD's protocol so mypy checks it."""
    source: BeatSource = _beat_source.LSLBeatSource(recorder)
    return source


def _ptb_tone_player(config: TaskConfig, clock: Callable[[], float]) -> TonePlayer:
    """The shared PsychPortAudio tone player, typed as HSD's protocol.

    Its vibration channel is silent: the HSD plays tones only.
    """
    player: TonePlayer = _tone_player.TonePlayer(
        freq=config.toneFreq,
        duration=config.toneSecs,
        ramp=config.toneRamp,
        volume=config.toneVolume,
        vib_volume=0.0,
        clock=clock,
    )
    return player


def _open_devices(
    parameters: Dict[str, Any],
    recorder,
    beat_source,
    tone_player,
    config: TaskConfig,
) -> None:
    """Attach the beat source and the tone player.

    Explicit objects win over ``setup``. Otherwise ``"behavioral"`` builds
    the shared LSL beat source over ``recorder`` and the PsychPortAudio tone
    player on the session clock.
    """
    if beat_source is None:
        beat_source = _lsl_beat_source(recorder)
    if tone_player is None:
        tone_player = _ptb_tone_player(config, parameters["clock"])
    parameters["beatSource"] = beat_source
    parameters["tonePlayer"] = tone_player
    parameters["recorder"] = recorder


def _build_window(parameters: Dict[str, Any], fullscr: bool) -> None:
    """Open the window, as the HRD does."""
    from psychopy import visual

    if parameters["setup"] == "test":
        fullscr = False
    parameters["win"] = visual.Window(
        monitor=parameters["monitor"],
        screen=parameters["screenNb"],
        fullscr=fullscr,
        units="height",
    )
    parameters["win"].mouseVisible = False
    # Needed for nDroppedFrames, which the DroppedFrames column reports.
    parameters["win"].recordFrameIntervals = True


def getParameters(
    participant: str = "SubjectTest",
    session: str = "001",
    setup: str = "behavioral",
    axis: Optional[str] = None,
    nTrials: Optional[int] = None,
    device: str = "keyboard",
    screenNb: int = 0,
    fullscr: bool = True,
    nBreaking: int = 20,
    resultPath: Optional[str] = None,
    overwrite: bool = False,
    confidenceScale: Optional[ConfidenceScale] = None,
    language: str = "english",
    seed: Optional[int] = None,
    autopilot=None,
    recorder=None,
    beat_source=None,
    tone_player=None,
    triggers: Optional[Dict[str, Any]] = None,
    config: Optional[TaskConfig] = None,
    clock: Optional[Callable[[], float]] = None,
) -> Dict[str, Any]:
    """Create Heartbeat Synchrony Discrimination task parameters.

    Beta. The design is documented in ``docs/source/tasks/hsd/design.md``.

    Parameters
    ----------
    participant, session : str
        Identifiers, as for the HRD.
    setup : str
        ``"behavioral"`` builds
        :class:`~cardioception.devices.beat_source.LSLBeatSource` over
        ``recorder`` and :class:`~cardioception.devices.tone_player.TonePlayer`
        (PsychPortAudio, the tone from ``config``), both on the session clock.
        ``"test"`` opens a small window and needs ``beat_source`` and
        ``tone_player`` passed in.
    axis : str | None
        ``"absolute"``: delays in ms after the R-wave. ``"phase"``: delays as
        a fraction of the anticipated interbeat interval. ``None`` keeps the
        axis of ``config`` (``"absolute"`` by default).
    nTrials : int | None
        The most trials to run, written into ``config`` as ``maxTrials``.
        ``None`` keeps ``config.maxTrials`` (60 by default). The session
        stops earlier once the ``mu`` credible interval is narrow enough,
        after ``config.minTrials``, which ``nTrials`` may not be below.
    device : str
        ``"keyboard"``, the only device so far.
    screenNb : int
        Screen number, for :class:`psychopy.visual.Window`.
    fullscr : bool
        Full screen. Always off with ``setup="test"``.
    nBreaking : int
        Trials between breaks. ``0`` for none.
    resultPath : str | None
        Root directory holding every participant; results go to
        ``<resultPath>/sub-<participant>/ses-<session>/run-<timestamp>/``.
        Defaults to ``<cwd>/data``.
    overwrite : bool
        Allow writing into a run directory that already holds results.
    confidenceScale : ConfidenceScale | None
        How confidence is collected. ``None`` takes ten discrete steps, as the
        HRD keyboard does, with the language's end labels.
    language : str
        A language in ``cardioception/HSD/texts``; ``"english"`` so far.
    seed : int | None
        Seeds the session generator. Recorded either way.
    autopilot : HSDAutopilot | None
        A simulated participant, for headless runs.
    recorder : LSLRecorder | None
        The LSL recorder whose stream the beat source reads, and whose marker
        outlet receives the task's JSON markers. Its own ``read`` and
        ``readInWaiting`` are not used: the beat source is the sole reader of
        the inlet, so the recorder holds no signal and the task saves no
        recording file of its own. Record the ECG stream and the marker
        stream with LabRecorder: the XDF is the session's recording.
    beat_source, tone_player :
        Objects satisfying :class:`~cardioception.HSD._stimulus.BeatSource`
        and :class:`~cardioception.HSD._stimulus.TonePlayer`. They win over
        ``setup``. Both must report times on the session clock.
    triggers : dict | None
        ``{event: callable}`` for the events in
        :data:`cardioception.HSD._constants.EVENTS`.
    config : TaskConfig | None
        Every design value. ``axis`` and ``nTrials``, when given, replace its
        ``axis`` and ``maxTrials``.
    clock : callable | None
        The session clock. ``None`` takes :func:`default_clock`.

    Notes
    -----
    The HSD writes nothing to ``Channel_0``. Its trigger codes
    (:class:`cardioception.HSD._constants.Trigger`) go to the recorder's
    marker stream as JSON instead, ``{"kind": "trigger", "name", "code",
    "trial"}``, together with the scheduler's ``beat``, ``tone_scheduled``,
    ``tone_onset`` and ``tone_skipped`` markers and the ``decision`` and
    ``confidence`` markers, one string per marker. The HRD writes different
    meanings to the same trigger codes.
    """
    from .. import __version__

    parameters: Dict[str, Any] = {}
    parameters["rng"], parameters["seed"] = make_rng(seed)
    parameters["autopilot"] = autopilot
    parameters["triggers"] = validate_triggers(triggers, events=EVENTS)

    if setup not in ("behavioral", "test"):
        raise ValueError(f"setup should be 'behavioral' or 'test', got {setup!r}")
    if device != "keyboard":
        raise ValueError(
            f"device={device!r}: the HSD task takes keyboard responses only."
        )
    parameters["setup"] = setup
    parameters["device"] = device
    parameters["screenNb"] = screenNb
    parameters["monitor"] = "testMonitor"

    config = TaskConfig() if config is None else config
    if nTrials is not None and nTrials < config.minTrials:
        raise ValueError(
            f"nTrials={nTrials} is below the {config.minTrials} trials the "
            "stopping rule requires (config.minTrials). Raise nTrials, or pass "
            "a config with a lower minTrials."
        )
    changes: Dict[str, Any] = {}
    if axis is not None:
        changes["axis"] = axis
    if nTrials is not None:
        changes["maxTrials"] = nTrials
    config = replace(config, **changes)
    config.apply(parameters)
    parameters["config"] = config
    parameters["nTrials"] = config.maxTrials
    parameters["nBreaking"] = nBreaking

    if clock is None:
        clock, clock_name = default_clock()
    else:
        clock_name = _clock_name(clock)
    parameters["clock"] = clock
    parameters["clockName"] = clock_name

    # Before the run directory and the log exist, so a launch that cannot
    # find its devices leaves nothing behind.
    _check_devices(setup, recorder, beat_source, tone_player)

    # Rows, tones, beats and posterior snapshots accumulate here and are
    # written by the task.
    parameters["results_rows"] = []
    parameters["tone_rows"] = []
    parameters["beat_rows"] = []
    parameters["posteriors"] = []

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
    parameters["resultPath"] = parameters["paths"].directory
    parameters["logFile"] = start_session_log(parameters["paths"].directory)

    parameters["texts"] = get_texts(language, device)

    parameters["engine"] = config.engine(parameters["rng"])

    _open_devices(parameters, recorder, beat_source, tone_player, config)

    _build_window(parameters, fullscr)

    if confidenceScale is None:
        confidenceScale = DISCRETE_1_10.with_labels(parameters["texts"]["VASlabels"])
    parameters["confidenceScale"] = confidenceScale
    parameters["labelsRating"] = list(confidenceScale.labels)

    player = parameters["tonePlayer"]
    parameters["startTime"] = time.time()
    parameters["paths"].write_manifest(
        task="HSD",
        axis=config.axis,
        version=__version__,
        start_epoch=parameters["startTime"],
        start_local=datetime.datetime.now().isoformat(timespec="seconds"),
        seed=parameters["seed"],
        device=device,
        language=language,
        setup=setup,
        nTrials=config.maxTrials,
        clock=clock_name,
        confidence=confidenceScale.describe(),
        config=config.describe(),
        recording=(
            recorder.describe()
            if recorder is not None and hasattr(recorder, "describe")
            else None
        ),
        beat_source=type(parameters["beatSource"]).__name__,
        tone_player=_describe_player(player),
    )

    return parameters
