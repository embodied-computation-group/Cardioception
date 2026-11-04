# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The PsychoPy side of the Phase Adjustment Task.

During a trial the participant sees a fixation cross inside a ring whose
pointer turns with the mouse wheel, from twelve o'clock at every trial start,
and flashes with each beep. The wheel moves the beeps relative to the
heartbeat through ``parameters["engine"]`` (see
:mod:`cardioception.PAT.engine`), which is polled on every frame and does all
the timing. Space ends the trial, then comes the
confidence rating. The experimenter gets one status line per second in the
console.

Between trials the engine keeps detecting beats, without tones: :func:`run`
installs ``engine.idle_poll`` as the window's per-frame hook
(:func:`cardioception._present.on_every_frame`), so every frame held through
:func:`cardioception._present.hold` polls it, and the rating polls it on
every frame of its own loop.

With ``parameters["autopilot"]`` set (see
:class:`cardioception.PAT._autopilot.PATAutopilot`) a simulated participant
turns the dial, presses and rates, so a whole session runs without anyone at
the keyboard.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .._log import get_logger
from .._present import hold, on_every_frame
from .._screens import Screen, text
from .._session import show_screen as _show_screen
from .._triggers import fire

logger = get_logger()

#: Columns of final.txt, in order. Extra fields from the engine follow them.
FINAL_COLUMNS = [
    "Trial",
    "Block",
    "TrialStatus",
    "Mode",
    "Extero",
    "StartPhaseDeg",
    "ChosenPhaseDeg",
    "ChosenDelayMs",
    "AnticipatedPeriodMs",
    "ObservedPeriodMs",
    "LastRTime",
    "PressTime",
    "LastToneIndex",
    "LastToneAnchor",
    "LastToneRTime",
    "LastToneDelayMs",
    "Confidence",
    "ConfidenceRT",
    "ConfidenceUnit",
    "Device",
    "ConfidenceScale",
    "ConfidenceLow",
    "ConfidenceHigh",
    "ConfidenceGranularity",
    "ConfidenceLevels",
    "ConfidenceSigned",
    "nTonesReal",
    "nTonesPredicted",
    "nTonesSkipped",
    "TrialDuration",
    "nDialMoves",
    "WallTime",
]

#: Columns of tones.txt, in order.
TONE_COLUMNS = [
    "ToneIndex",
    "Trial",
    "Block",
    "RTime",
    "PeriodS",
    "PhaseDeg",
    "DelayMs",
    "Target",
    "Anchor",
    "Onset",
    "Kind",
]

#: Trial number given to the engine during the tutorial. Its tones are not saved.
TUTORIAL_TRIAL = 0

#: Before the practice trials.
PRACTICE_SCREEN = Screen([("textPracticeStart", (0.0, 0.0))], seconds=0.0)

#: Before the main trials.
TASK_SCREEN = Screen([("textTaskStart", (0.0, 0.0))], seconds=0.0)

#: Between two trials.
NEXT_TRIAL_SCREEN = Screen([("textNextTrial", (0.0, 0.0))], seconds=0.0)

#: Before the dial tutorial, with the "press space" line.
TUTORIAL_INTRO = Screen([("tutorialIntro", (0.0, 0.0))], seconds=0.0)

#: After the dial tutorial.
TUTORIAL_END = Screen([("tutorialEnd", (0.0, 0.0))], seconds=0.0)


class TaskAbort(Exception):
    """Raised when the experimenter presses Esc."""


def _clock() -> Callable[[], float]:
    """The LSL clock, which is also the PTB clock on Windows."""
    try:
        from pylsl import local_clock

        return local_clock
    except ImportError:  # pragma: no cover
        return time.perf_counter


def _checkEscape(keys: List[str]) -> None:
    if "escape" in keys:
        raise TaskAbort()


def _pushMarker(parameters: dict, kind: str, **fields: Any) -> None:
    """Push a JSON marker through the engine's outlet, or the task's own."""
    mark = getattr(parameters["engine"], "mark", None)
    if mark is not None:
        mark(kind, **fields)
        return
    outlet = parameters.get("outlet")
    if outlet is not None:
        outlet.push_sample([json.dumps({"kind": kind, **fields})])


def _plain(value: Any) -> bool:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return True
    if isinstance(value, (list, tuple)):
        return all(_plain(v) for v in value)
    return False


def _write(df: pd.DataFrame, path: str) -> None:
    """Write a table atomically, so a crash never leaves half a file."""
    tmp = path + ".tmp"
    df.to_csv(tmp, sep="\t", index=False)
    os.replace(tmp, path)


def saveParameters(parameters: dict) -> None:
    """Write the plain settings to parameters.txt, one per line."""
    rows = [
        {"Parameter": k, "Value": json.dumps(v, ensure_ascii=False)}
        for k, v in parameters.items()
        if _plain(v) and k not in ("texts", "tones", "labelsRating")
    ]
    _write(
        pd.DataFrame(rows, columns=["Parameter", "Value"]),
        parameters["paths"].path("parameters"),
    )


def toneTable(parameters: dict) -> pd.DataFrame:
    """The engine's tone rows for logged trials, with their block."""
    blocks: Dict[int, str] = parameters["trialBlocks"]
    rows = []
    for tone in parameters["engine"].tones:
        trial = tone.get("Trial")
        if trial in blocks:
            row = dict(tone)
            row["Block"] = blocks[trial]
            rows.append(row)
    parameters["tones"] = rows
    df = pd.DataFrame(rows)
    extra = [c for c in df.columns if c not in TONE_COLUMNS]
    return df.reindex(columns=TONE_COLUMNS + extra)


def saveResults(parameters: dict) -> None:
    """Write the final and tones files. Called after every trial.

    Nothing is written before the first trial is complete, so a run stopped
    during the instructions leaves no empty results behind.
    """
    results = parameters["results_df"]
    if len(results) == 0:
        return
    extra = [c for c in results.columns if c not in FINAL_COLUMNS]
    _write(
        results.reindex(columns=FINAL_COLUMNS + extra),
        parameters["paths"].path("final"),
    )
    _write(toneTable(parameters), parameters["paths"].path("tones"))


def run(
    parameters: dict,
    runTutorial: bool = True,
    confidenceRating: bool = True,
) -> None:
    """Run the Phase Adjustment Task.

    Instructions, the dial tutorial, `nPractice` practice trials, then
    `nTrials` main trials with a break every `nBreaking`. Results are saved
    after every trial. Esc at any point stops the task and keeps what was
    saved; the window and the engine stay open for the caller to close.

    The engine's ``idle_poll`` is the window's per-frame hook for the length
    of the session, so beats are detected on every screen between trials.

    Parameters
    ----------
    parameters : dict
        Task parameters, from :func:`cardioception.PAT.parameters.getParameters`.
    runTutorial : bool
        If `True`, let the participant try the dial on a few free beats before
        the practice trials.
    confidenceRating : bool
        If `True`, ask for a confidence rating after each trial.

    """
    win = parameters["win"]
    parameters["aborted"] = False
    saveParameters(parameters)
    trialNumber = 0
    on_every_frame(win, parameters["engine"].idle_poll)

    try:
        for page in parameters["texts"]["instructions"]:
            showText(parameters, page, footer=parameters["texts"]["textNext"])

        if runTutorial is True:
            tutorial(parameters)

        if parameters["nPractice"] > 0:
            show_screen(parameters, PRACTICE_SCREEN)
            for i, startPhase in enumerate(parameters["startPhasePractice"]):
                if i > 0:
                    show_screen(parameters, NEXT_TRIAL_SCREEN)
                trialNumber += 1
                trial(
                    parameters,
                    trialNumber,
                    "practice",
                    startPhase,
                    confidenceRating=confidenceRating,
                )

        show_screen(parameters, TASK_SCREEN)
        for i, startPhase in enumerate(parameters["startPhaseMain"]):
            if i > 0:
                if i % parameters["nBreaking"] == 0:
                    remain = round(i / parameters["nTrials"] * 100)
                    logger.info(
                        f"... break after main trial {i} of {parameters['nTrials']}"
                    )
                    showText(
                        parameters,
                        parameters["texts"]["textBreaks"],
                        header=f" ---- {remain} % ---- ",
                    )
                else:
                    show_screen(parameters, NEXT_TRIAL_SCREEN)
            trialNumber += 1
            trial(
                parameters,
                trialNumber,
                "main",
                startPhase,
                confidenceRating=confidenceRating,
            )

    except TaskAbort:
        parameters["aborted"] = True
        logger.warning(
            "... Esc pressed: the task stops here. Completed trials are saved."
        )

    finally:
        on_every_frame(win, None)
        saveResults(parameters)
        logger.info(
            f"... {len(parameters['results_df'])} trials saved in "
            f"{parameters['resultPath']}"
        )

    if not parameters["aborted"]:
        hold(win, 3, text(parameters, parameters["texts"]["done"], wrapWidth=1.2))


def trial(
    parameters: dict,
    trialNumber: int,
    block: str,
    startPhase: float,
    confidenceRating: bool = True,
) -> Dict[str, Any]:
    """Run one trial of the Phase Adjustment Task.

    The engine starts tones at `startPhase`; the mouse wheel (and the left and
    right keys) moves them until the participant presses space. The engine
    then waits for the next R-wave, for the observed period, and the
    participant rates their confidence. The row is appended to
    `parameters["results_df"]` and the files are saved.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    trialNumber : int
        Trial number, counted across practice and main trials so that it is
        unique in the marker stream and in tones.txt.
    block : str
        `"practice"` or `"main"`.
    startPhase : float
        Start phase of the dial, in degrees.
    confidenceRating : bool
        If `False`, no confidence rating is asked.

    Returns
    -------
    row : dict
        The row added to final.txt.

    """
    engine = parameters["engine"]
    scale = parameters["confidenceScale"]
    parameters["trialBlocks"][trialNumber] = block
    logger.info(
        f"Starting {block} trial {trialNumber} - start phase {startPhase:g} deg "
        f"- mode {parameters['mode']}{' - extero' if parameters['extero'] else ''}"
    )

    fire(parameters, "trialStart")
    press = dialLoop(parameters, trialNumber, block, startPhase)
    fields = engine.end_trial()
    timedOut = press["status"] == "timeout"

    confidence: Any = np.nan
    confidenceRT: Any = np.nan
    abort = False
    # A trial that timed out has no choice, so nothing to be confident about
    if confidenceRating is True and not timedOut:
        fire(parameters, "confidenceStart")
        try:
            rating, ratingRT, provided = confidenceRatingTask(parameters)
        except TaskAbort:
            # The trial itself is complete: keep it, without a rating
            abort, provided = True, False
        fire(parameters, "confidenceStop")
        if provided:
            confidence, confidenceRT = rating, ratingRT
        _pushMarker(
            parameters,
            "confidence",
            trial=trialNumber,
            value=confidence if provided else None,
            rt=confidenceRT if provided else None,
        )

    # Engine fields first, the task's own on top for what only the task knows,
    # and the task's measurements as fallback for what the engine left out.
    row: Dict[str, Any] = {c: np.nan for c in FINAL_COLUMNS}
    row.update(
        {
            "TrialStatus": press["status"],
            "ChosenPhaseDeg": press["phase_deg"],
            "ChosenDelayMs": press["delay_ms"],
            "PressTime": press["press_time"],
            "TrialDuration": press["duration"],
        }
    )
    row.update({k: v for k, v in dict(fields).items() if v is not None})
    row.update(
        {
            "Trial": trialNumber,
            "Block": block,
            "Mode": parameters["mode"],
            "Extero": parameters["extero"],
            "StartPhaseDeg": startPhase,
            "Confidence": confidence,
            "ConfidenceRT": confidenceRT,
            "ConfidenceUnit": (
                scale.to_unit(confidence) if np.isfinite(confidence) else np.nan
            ),
            "Device": parameters["device"],
            **scale.describe(),
            "nDialMoves": press["n_dial_moves"],
            "WallTime": press["wall_time"],
        }
    )
    if timedOut:
        # Whatever the engine made of the dial, nobody chose it
        row.update(TrialStatus="timeout", ChosenPhaseDeg=np.nan, ChosenDelayMs=np.nan)

    fire(parameters, "trialStop")
    parameters["results_df"] = pd.concat(
        [parameters["results_df"], pd.DataFrame([row])], ignore_index=True
    )
    saveResults(parameters)
    if abort:
        raise TaskAbort()

    logger.info(
        f"... trial {trialNumber} ({block}): phase {_fmt(row['ChosenPhaseDeg'])} deg, "
        f"delay {_fmt(row['ChosenDelayMs'])} ms, anticipated "
        f"{_fmt(row['AnticipatedPeriodMs'])} ms, observed "
        f"{_fmt(row['ObservedPeriodMs'])} ms, confidence {_fmt(confidence)}"
    )
    if row["TrialStatus"] != "ok":
        logger.warning(
            f"... trial {trialNumber} is {row['TrialStatus']}: the scores will "
            "leave it out (check the ECG)"
        )
    return row


def _fmt(value: Any) -> str:
    try:
        return "--" if value is None or np.isnan(value) else f"{value:.0f}"
    except TypeError:
        return str(value)


@dataclass
class Stage:
    """One screen of the dial loop.

    Parameters
    ----------
    text : str | None
        Shown above the dial. `None` in real trials, which show only the dial.
    wheel : bool
        Whether the wheel moves the beeps in this stage.
    ready : callable
        Takes the loop state and says whether space may end the stage. The
        state holds `elapsed` (seconds in this stage), `tones` (beeps played in
        this stage), `notches` (net notches in this stage, positive later), and
        `later` and `earlier` (notches rolled each way in this stage, both
        counted up, so rolling back does not undo them).
    footer : str | callable | None
        A text, shown below the dial once the stage is ready, or a function of
        the loop state that returns the text to show on each frame (or None).
    roll : int
        The way the stage asks for the wheel to be rolled: `1` away (later),
        `-1` towards (earlier), `0` to find the heartbeat. Only the autopilot
        reads it.
    """

    text: Optional[str] = None
    wheel: bool = True
    ready: Callable[[dict], bool] = field(default=lambda state: True)
    footer: Union[str, Callable[[dict], Optional[str]], None] = None
    roll: int = 0


def _newState() -> Dict[str, float]:
    return {"elapsed": 0.0, "tones": 0, "notches": 0, "later": 0, "earlier": 0}


class _Dial:
    """A ring with a pointer around the fixation cross.

    The pointer starts at twelve o'clock and turns by the same angle as the
    phase, so it shows the change since the trial began and nothing about the
    phase itself. It brightens for `flashDuration` after each beep.
    """

    RING = "#a8a8a8"
    POINTER = "#303030"
    FLASH = "white"

    def __init__(self, parameters: dict):
        from psychopy import visual

        win = parameters["win"]
        self.show = parameters["showDial"]
        self.radius = parameters["dialRadius"]
        self.angle = 0.0
        self.fixation = visual.GratingStim(
            win=win, mask="cross", size=0.1, pos=[0, 0], sf=0
        )
        self.ring = visual.Circle(
            win,
            radius=self.radius,
            edges=128,
            lineColor=self.RING,
            fillColor=None,
            lineWidth=3,
        )
        self.pointer = visual.Rect(
            win, width=0.012, height=0.07, fillColor=self.POINTER, lineColor=None
        )
        self.dot = visual.Circle(
            win, radius=0.016, edges=32, fillColor=self.FLASH, lineColor=None
        )

    def turn(self, degrees: float) -> None:
        self.angle = (self.angle + degrees) % 360.0

    def _at(self, r: float) -> Tuple[float, float]:
        theta = np.radians(self.angle)  # clockwise from twelve o'clock
        return float(r * np.sin(theta)), float(r * np.cos(theta))

    def draw(self, dial: bool = True, flash: bool = False) -> None:
        if self.show and dial:
            self.ring.draw()
            self.pointer.pos = self._at(self.radius - 0.035)
            self.pointer.ori = self.angle
            self.pointer.fillColor = self.FLASH if flash else self.POINTER
            self.pointer.draw()
            if flash:
                self.dot.pos = self._at(self.radius)
                self.dot.draw()
        self.fixation.draw()


def _degreesPerNotch(parameters: dict, engine: Any, trialNumber: int) -> float:
    """How far one notch turns the pointer, in degrees of the period."""
    if parameters["mode"] == "relative":
        return parameters["dialGainDeg"]
    period = _periodS(engine, trialNumber)
    return parameters["dialGainMs"] / (period * 1000) * 360


def _periodS(engine: Any, trialNumber: int) -> float:
    """The latest period the engine used in this trial, 1 s before any."""
    for tone in reversed(engine.tones):
        if tone.get("Trial") != trialNumber:
            break
        if tone.get("PeriodS"):
            return float(tone["PeriodS"])
    return 1.0


def dialLoop(
    parameters: dict,
    trialNumber: int,
    block: str,
    startPhase: float,
    stages: Optional[List[Stage]] = None,
) -> Dict[str, Any]:
    """Run the engine and the dial until space ends the last stage.

    A trial is one stage: the dial and the fixation cross, and space ends it
    after `minTrialTime`. The tutorial is several stages on the same beeps.
    Until the first beep has played, the screen says that the task is
    listening for the heartbeat, the dial is hidden and the wheel does
    nothing. A stage still running after `maxTrialTime` seconds (a lost ECG,
    say, when space would never work) ends the loop with no choice, status
    `timeout`.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    trialNumber : int
        Trial number given to the engine.
    block : str
        Shown in the experimenter status line.
    startPhase : float
        Start phase of the beeps, in degrees.
    stages : list of Stage | None
        The screens to go through. Default is one trial screen.

    Returns
    -------
    press : dict
        `phase_deg` and `delay_ms` (the dial at the press, NaN after a
        timeout), `press_time` (LSL seconds), `wall_time` (`time.time()`),
        `duration` (seconds from the start of the trial), `n_dial_moves` and
        `status` (`ok`, or `timeout` when `maxTrialTime` ran out).

    """
    from psychopy import event

    engine = parameters["engine"]
    win = parameters["win"]
    mouse = parameters["myMouse"]
    pilot = parameters.get("autopilot")
    now = _clock()
    dialKeys = list(parameters["dialKeys"])
    watched = [parameters["startKey"], "escape"] + dialKeys
    maxTime = parameters.get("maxTrialTime")
    if stages is None:
        minTime = parameters["minTrialTime"]
        stages = [Stage(ready=lambda state: state["elapsed"] >= minTime)]

    dial = _Dial(parameters)
    waiting = text(parameters, parameters["texts"]["waitingFirstTone"], pos=(0, 0.3))
    stageTexts = []
    for s in stages:
        above = below = None
        if s.text:
            above = text(parameters, s.text, pos=(0, 0.33), wrapWidth=1.2)
        if s.footer:
            below = text(
                parameters,
                s.footer if isinstance(s.footer, str) else "",
                pos=(0, -0.35),
            )
        stageTexts.append((above, below))
    win.mouseVisible = False

    # Forget the press that started the trial, and wheel turns made before it
    event.clearEvents()
    mouse.getWheelRel()
    wheel = 0.0
    nDialMoves = 0

    engine.start_trial(trialNumber, startPhase, block=block)
    tStart = now()
    status = _Status(parameters, trialNumber, block, tStart)
    if pilot is not None:
        pilot.start_trial(trialNumber)

    # Target times of this trial's beeps, to know when one has played
    seen = len(engine.tones)
    pending: List[float] = []
    nPlayed, lastPlayed = 0, -np.inf

    stageIndex = 0
    state = _newState()
    tStage = tStart

    while True:
        engine.poll()
        t = now()

        tones = engine.tones
        for tone in tones[seen:]:
            if tone.get("Trial") == trialNumber and tone.get("Kind", "tone") == "tone":
                pending.append(float(tone["Target"]))
        seen = len(tones)
        for target in [p for p in pending if p <= t]:
            pending.remove(target)
            nPlayed += 1
            state["tones"] += 1
            lastPlayed = max(lastPlayed, target)
        heard = nPlayed > 0
        stage = stages[stageIndex]
        state["elapsed"] = t - tStage

        notches = 0
        pressed = False
        if pilot is not None:
            # The simulated participant rolls and presses in place of the
            # wheel and the keyboard, and only once the first beep is heard.
            if heard:
                notches, done = pilot.frame(
                    t,
                    engine.phase_deg,
                    _degreesPerNotch(parameters, engine, trialNumber),
                    wheel=stage.wheel,
                    roll=stage.roll,
                )
                pressed = done and stage.ready(state)
        else:
            wheel += parameters["wheelDirection"] * float(mouse.getWheelRel()[1])
            if abs(wheel) >= 1:
                notches = int(wheel)  # whole notches, the rest carries over
                wheel -= notches

            for key in event.getKeys(keyList=watched):
                if key == "escape":
                    engine.stop_tones()
                    raise TaskAbort()
                elif len(dialKeys) == 2 and key == dialKeys[0]:
                    notches -= 1
                elif len(dialKeys) == 2 and key == dialKeys[1]:
                    notches += 1
                elif key == parameters["startKey"]:
                    pressed = heard and stage.ready(state)

        if not (heard and stage.wheel):
            notches, wheel = 0, 0.0
        if notches != 0:
            turn = notches * _degreesPerNotch(parameters, engine, trialNumber)
            engine.nudge(notches, parameters["dialGainDeg"], parameters["dialGainMs"])
            dial.turn(turn)
            state["notches"] += notches
            state["later" if notches > 0 else "earlier"] += abs(notches)
            nDialMoves += 1

        timedOut = maxTime is not None and state["elapsed"] >= maxTime
        if pressed and stageIndex < len(stages) - 1:
            stageIndex += 1
            tStage = t
            state = _newState()
        elif pressed or timedOut:
            pressTime, wallTime = now(), time.time()
            outcome = "ok"
            if timedOut and not pressed:
                outcome = "timeout"
                logger.warning(
                    f"... {block} trial {trialNumber}: no press after {maxTime:g} s, "
                    f"{nPlayed} beeps heard. The trial ends without a choice."
                )
            engine.stop_tones(reason="press" if outcome == "ok" else "timeout")
            press = {
                "phase_deg": engine.phase_deg if outcome == "ok" else np.nan,
                "delay_ms": engine.delay_ms if outcome == "ok" else np.nan,
                "press_time": pressTime,
                "wall_time": wallTime,
                "duration": pressTime - tStart,
                "n_dial_moves": nDialMoves,
                "status": outcome,
            }
            dial.draw(dial=False)
            win.flip()
            return press

        status.update(t)
        if heard:
            above, footer = stageTexts[stageIndex]
            if above is not None:
                above.draw()
            stageFooter = stages[stageIndex].footer
            if footer is not None and callable(stageFooter):
                line = stageFooter(state)
                if line:
                    if footer.text != line:
                        footer.text = line
                    footer.draw()
            elif footer is not None and stages[stageIndex].ready(state):
                footer.draw()
            dial.draw(flash=t - lastPlayed < parameters["flashDuration"])
        else:
            waiting.draw()
            dial.draw(dial=False)
        win.flip()


class _Status:
    """One console line per second for the experimenter."""

    def __init__(self, parameters: dict, trialNumber: int, block: str, tStart: float):
        self.parameters = parameters
        self.trial = trialNumber
        self.block = block
        self.tStart = tStart
        self.next = tStart + parameters["statusEvery"]
        self.nTones = 0
        self.lastNew = tStart

    def _tones(self) -> List[dict]:
        return [
            t for t in self.parameters["engine"].tones if t.get("Trial") == self.trial
        ]

    def update(self, t: float) -> None:
        if t < self.next:
            return
        self.next = t + self.parameters["statusEvery"]
        engine = self.parameters["engine"]
        tones = self._tones()
        # Skipped tones are beats too, so they count as signs of life
        activity = len(tones) + getattr(engine, "counts", {}).get("skipped", 0)
        if activity != self.nTones:
            self.nTones, self.lastNew = activity, t
        tones = [tone for tone in tones if tone.get("Kind", "tone") == "tone"]

        hr = "--"
        if tones and tones[-1].get("PeriodS"):
            hr = f"{60 / tones[-1]['PeriodS']:.0f}"
        nReal = sum(tone.get("Anchor") == "real" for tone in tones)
        nPred = sum(tone.get("Anchor") == "predicted" for tone in tones)
        line = (
            f"  [{self.block} {self.trial}] {t - self.tStart:5.1f} s | HR {hr} bpm"
            f" | phase {engine.phase_deg:5.1f} deg | delay {engine.delay_ms:6.1f} ms"
            f" | tones real {nReal} / predicted {nPred}"
        )
        silent = t - self.lastNew
        if silent >= self.parameters["noBeatWarning"]:
            what = (
                "vibrations" if self.parameters["extero"] else "beats (check the ECG)"
            )
            line += f" | NO {what.upper()} FOR {silent:.0f} s"
        logger.info(line)


def _text(parameters: dict, message: str, pos=(0.0, 0.0)):
    """A text of an instruction screen, wrapped as the PAT's always were."""
    return text(parameters, message, pos=pos, wrapWidth=1.2)


def _no_wait(parameters: dict) -> None:
    """Stand-in for the shared wait, which would not redraw the screen."""


def show_screen(parameters: dict, screen: Screen, prompt=None) -> list:
    """Show one instruction screen until the start key.

    :func:`cardioception._session.show_screen` builds and holds it; the wait
    is :func:`waitInput`, which redraws it on every frame so the per-frame
    hook keeps polling the engine.
    """
    stims = _show_screen(
        parameters, screen, prompt, text_fn=_text, hold_fn=hold, wait_fn=_no_wait
    )
    if screen.wait:
        waitInput(parameters, *stims)
    return stims


def showText(
    parameters: dict,
    message: str,
    footer: Optional[str] = None,
    header: Optional[str] = None,
) -> None:
    """Show a text, with an optional footer and header line, until the start key."""
    stims = [_text(parameters, message)]
    if footer is not None:
        stims.append(text(parameters, footer, pos=(0.0, -0.4)))
    if header is not None:
        stims.append(text(parameters, header, pos=(0.0, 0.3)))
    waitInput(parameters, *stims)


def waitInput(parameters: dict, *stims) -> None:
    """Hold `stims` on screen until the start key. Esc stops the task.

    Every frame goes through :func:`cardioception._present.hold`, so the
    window's per-frame hook (the engine's idle poll, during :func:`run`) keeps
    detecting beats while the participant reads. The wheel does nothing here.
    With an autopilot the screen is drawn once and passed at once.
    """
    from psychopy import event

    win = parameters["win"]
    pilot = parameters.get("autopilot")
    if pilot is not None:
        hold(win, 0, *stims)
        pilot.advance()
        parameters["myMouse"].getWheelRel()
        return

    event.clearEvents(eventType="keyboard")
    while True:
        hold(win, 0, *stims)
        keys = event.getKeys(keyList=[parameters["startKey"], "escape"])
        _checkEscape(keys)
        if parameters["startKey"] in keys:
            parameters["myMouse"].getWheelRel()  # drop turns made while waiting
            return


def _wheelNotches(parameters: dict) -> Callable[[], float]:
    """Wheel travel since the last call, away from the participant positive.

    Turns made before the call (e.g. while the trial ended) are dropped.
    """
    mouse = parameters["myMouse"]
    mouse.getWheelRel()
    return lambda: parameters["wheelDirection"] * float(mouse.getWheelRel()[1])


def tutorial(parameters: dict) -> None:
    """Guide the participant through the wheel on free beats. Nothing is saved.

    Four screens on the same beeps: listen to one beep per heartbeat; roll the
    wheel away (beeps later); roll it towards you (beeps earlier); then find
    the position that matches the heartbeat and press space.

    Parameters
    ----------
    parameters : dict
        Task parameters.

    """
    texts = parameters["texts"]
    nTones = parameters["tutorialListenTones"]
    nNotches = parameters["tutorialNotches"]
    minTime = parameters["minTrialTime"]
    timeout = parameters["tutorialStageTimeout"]

    def rolled(direction: str) -> Callable[[dict], bool]:
        # Notches rolled that way count, whatever was rolled back afterwards;
        # after `timeout` space works anyway, so nobody can be stuck here.
        return lambda state: (
            state[direction] >= nNotches or state["elapsed"] >= timeout
        )

    def progress(direction: str) -> Callable[[dict], str]:
        ready = rolled(direction)

        def footer(state: dict) -> str:
            if ready(state):
                return texts["tutorialReady"]
            done = int(min(state[direction], nNotches))
            return texts["tutorialProgress"].format(done=done, total=nNotches)

        return footer

    show_screen(
        parameters,
        TUTORIAL_INTRO,
        prompt=text(parameters, texts["textNext"], pos=(0.0, -0.4)),
    )

    stages = [
        Stage(
            texts["tutorialListen"],
            wheel=False,
            ready=lambda state: (
                state["tones"] >= nTones or state["elapsed"] >= timeout
            ),
            footer=texts["textNext"],
        ),
        Stage(
            texts["tutorialLater"],
            ready=rolled("later"),
            footer=progress("later"),
            roll=1,
        ),
        Stage(
            texts["tutorialEarlier"],
            ready=rolled("earlier"),
            footer=progress("earlier"),
            roll=-1,
        ),
        Stage(
            texts["tutorialFree"],
            ready=lambda state: state["elapsed"] >= min(minTime, timeout),
        ),
    ]
    startPhase = float(parameters["rng"].choice(parameters["startPhases"]))
    dialLoop(parameters, TUTORIAL_TRIAL, "tutorial", startPhase, stages=stages)
    parameters["engine"].end_trial()

    show_screen(parameters, TUTORIAL_END)


class _Prompt:
    """The rating question and the line saying how to answer, drawn as one."""

    def __init__(self, parameters: dict):
        self.parts = [
            text(
                parameters,
                parameters["texts"]["Confidence"],
                pos=(0, 0.2),
                wrapWidth=1.2,
            ),
            text(
                parameters,
                parameters["texts"]["ratingHelp"],
                pos=(0, -0.4),
                height=parameters["textSize"] * 0.7,
            ),
        ]

    def draw(self) -> None:
        for part in self.parts:
            part.draw()


def _abort() -> None:
    raise TaskAbort()


def confidenceRatingTask(
    parameters: dict,
) -> Tuple[Optional[float], Optional[float], bool]:
    """Confidence rating, with the wheel and arrow keys or with the mouse.

    The shared rating widgets of :mod:`cardioception._rating`, on
    ``parameters["confidenceScale"]``. With ``device="keyboard"`` the mouse
    wheel and the arrow keys move the marker and space confirms; with
    ``device="mouse"`` the cursor moves it and a click confirms, once the
    button that may still be down from the trial has been released. The
    engine is polled on every frame, so beats keep being detected, and Esc
    raises :class:`TaskAbort`, so the trial being rated is kept.

    Parameters
    ----------
    parameters : dict
        Task parameters.

    Returns
    -------
    confidence, confidenceRT : float | None
        The rating and its response time in seconds, `None` if not given.
    ratingProvided : bool
        Whether a rating was given before `maxRatingTime`.

    """
    from psychopy import event

    from .._rating import keyboard_rating, mouse_rating

    scale = parameters["confidenceScale"]
    engine = parameters["engine"]
    message = _Prompt(parameters)
    pilot = parameters.get("autopilot")

    if pilot is not None:
        # The scale is drawn once; the simulated participant answers on it.
        hold(parameters["win"], 0, message)
        answer = pilot.rate(
            *scale.bounds,
            min_time=parameters["minRatingTime"],
            max_wait=parameters["maxRatingTime"],
        )
        confidence, confidenceRT, provided = None, None, False
        if answer is not None:
            # The widget can only stop on a step of the scale.
            confidence, confidenceRT, provided = scale.clamp(answer[0]), answer[1], True
    elif parameters["device"] == "keyboard":
        confidence, confidenceRT, provided = keyboard_rating(
            win=parameters["win"],
            message=message,
            low=scale.low,
            high=scale.high,
            labels=scale.labels,
            granularity=scale.granularity,
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            accept_keys=(parameters["startKey"],),
            label_height=parameters["textSize"] * 0.6,
            rng=parameters["rng"],
            on_frame=engine.idle_poll,
            wheel=_wheelNotches(parameters),
            on_escape=_abort,
        )
    else:

        def on_frame() -> None:
            engine.idle_poll()
            # The mouse rating reads no keys, so Esc is looked for here.
            _checkEscape(event.getKeys(keyList=["escape"]))

        confidence, confidenceRT, provided = mouse_rating(
            win=parameters["win"],
            mouse=parameters["myMouse"],
            message=message,
            scale=scale,
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            label_height=parameters["textSize"] * 0.6,
            rng=parameters["rng"],
            on_frame=on_frame,
        )

    if provided:
        logger.info(f"... confidence {confidence} after {confidenceRT:.2f} s")
    else:
        logger.info("... no confidence rating")
        if parameters["maxRatingTime"] is not None:
            late = text(parameters, parameters["texts"]["tooLate"], color="red")
            hold(parameters["win"], 0.5, late)
    parameters["win"].flip()
    return confidence, confidenceRT, provided
