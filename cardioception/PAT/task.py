# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The PsychoPy side of the Phase Adjustment Task.

During a trial the participant sees a fixation cross inside a ring whose
pointer turns with the mouse wheel, from twelve o'clock at every trial start,
and flashes with each beep. The wheel moves the beeps relative to the
heartbeat through ``parameters["engine"]`` (see
:mod:`cardioception.PAT.engine`), which is polled on every frame and does all
the timing. Space ends the trial, then comes the
confidence rating. The experimenter gets one status line per second in the
console.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

#: Columns of final.txt, in order. Extra fields from the engine follow them.
FINAL_COLUMNS = [
    "Trial",
    "Block",
    "Mode",
    "Extero",
    "StartPhaseDeg",
    "ChosenPhaseDeg",
    "ChosenDelayMs",
    "AnticipatedPeriodMs",
    "ObservedPeriodMs",
    "LastRTime",
    "PressTime",
    "Confidence",
    "ConfidenceRT",
    "nTonesReal",
    "nTonesPredicted",
    "nTonesSkipped",
    "TrialDuration",
    "nDialMoves",
    "WallTime",
]

#: Columns of tones.txt, in order.
TONE_COLUMNS = [
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


class TaskAbort(Exception):
    """Raised when the experimenter presses Esc."""


def _clock() -> Callable[[], float]:
    """The LSL clock, which is also the PTB clock on Windows."""
    try:
        from pylsl import local_clock

        return local_clock
    except ImportError:  # pragma: no cover
        return time.perf_counter


def _idle(parameters: dict) -> None:
    """Keep the engine detecting beats between trials, without tones.

    Called on every frame of the screens between trials, so beats keep their
    true times and the anticipated period stays current.
    """
    idle_poll = getattr(parameters["engine"], "idle_poll", None)
    if idle_poll is not None:
        idle_poll()


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
        os.path.join(parameters["resultPath"], "parameters.txt"),
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
    """Write final.txt and tones.txt. Called after every trial.

    Nothing is written before the first trial is complete, so a run stopped
    during the instructions can be started again under the same session.
    """
    results = parameters["results_df"]
    if len(results) == 0:
        return
    extra = [c for c in results.columns if c not in FINAL_COLUMNS]
    _write(
        results.reindex(columns=FINAL_COLUMNS + extra),
        os.path.join(parameters["resultPath"], "final.txt"),
    )
    _write(toneTable(parameters), os.path.join(parameters["resultPath"], "tones.txt"))


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
    from psychopy import core

    parameters["aborted"] = False
    saveParameters(parameters)
    trialNumber = 0

    try:
        for page in parameters["texts"]["instructions"]:
            showText(parameters, page, footer=parameters["texts"]["textNext"])
            waitInput(parameters)

        if runTutorial is True:
            tutorial(parameters)

        if parameters["nPractice"] > 0:
            showText(parameters, parameters["texts"]["textPracticeStart"])
            waitInput(parameters)
            for i, startPhase in enumerate(parameters["startPhasePractice"]):
                if i > 0:
                    showText(parameters, parameters["texts"]["textNextTrial"])
                    waitInput(parameters)
                trialNumber += 1
                trial(
                    parameters,
                    trialNumber,
                    "practice",
                    startPhase,
                    confidenceRating=confidenceRating,
                )

        showText(parameters, parameters["texts"]["textTaskStart"])
        waitInput(parameters)
        for i, startPhase in enumerate(parameters["startPhaseMain"]):
            if i > 0:
                if i % parameters["nBreaking"] == 0:
                    remain = round(i / parameters["nTrials"] * 100)
                    showText(
                        parameters,
                        parameters["texts"]["textBreaks"],
                        header=f" ---- {remain} % ---- ",
                    )
                    print(f"... break after main trial {i} of {parameters['nTrials']}")
                else:
                    showText(parameters, parameters["texts"]["textNextTrial"])
                waitInput(parameters)
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
        print("... Esc pressed: the task stops here. Completed trials are saved.")

    finally:
        saveResults(parameters)
        print(
            f"... {len(parameters['results_df'])} trials saved in "
            f"{parameters['resultPath']}"
        )

    if not parameters["aborted"]:
        showText(parameters, parameters["texts"]["done"])
        core.wait(3)


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
    parameters["trialBlocks"][trialNumber] = block
    print(
        f"Starting {block} trial {trialNumber} - start phase {startPhase:g} deg "
        f"- mode {parameters['mode']}{' - extero' if parameters['extero'] else ''}"
    )

    press = dialLoop(parameters, trialNumber, block, startPhase)
    fields = engine.end_trial()

    confidence: Any = np.nan
    confidenceRT: Any = np.nan
    abort = False
    if confidenceRating is True:
        try:
            rating, ratingRT, provided = confidenceRatingTask(parameters)
        except TaskAbort:
            # The trial itself is complete: keep it, without a rating
            abort, provided = True, False
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
            "nDialMoves": press["n_dial_moves"],
            "WallTime": press["wall_time"],
        }
    )

    parameters["results_df"] = pd.concat(
        [parameters["results_df"], pd.DataFrame([row])], ignore_index=True
    )
    saveResults(parameters)
    if abort:
        raise TaskAbort()

    print(
        f"... trial {trialNumber} ({block}): phase {_fmt(row['ChosenPhaseDeg'])} deg, "
        f"delay {_fmt(row['ChosenDelayMs'])} ms, anticipated "
        f"{_fmt(row['AnticipatedPeriodMs'])} ms, observed "
        f"{_fmt(row['ObservedPeriodMs'])} ms, confidence {_fmt(confidence)}"
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
    """

    text: Optional[str] = None
    wheel: bool = True
    ready: Callable[[dict], bool] = field(default=lambda state: True)
    footer: Union[str, Callable[[dict], Optional[str]], None] = None


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
    nothing.

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
        `phase_deg` and `delay_ms` (the dial at the press), `press_time` (LSL
        seconds), `wall_time` (`time.time()`), `duration` (seconds from the
        start of the trial) and `n_dial_moves`.

    """
    from psychopy import event, visual

    engine = parameters["engine"]
    win = parameters["win"]
    mouse = parameters["myMouse"]
    now = _clock()
    dialKeys = list(parameters["dialKeys"])
    watched = [parameters["startKey"], "escape"] + dialKeys
    if stages is None:
        minTime = parameters["minTrialTime"]
        stages = [Stage(ready=lambda state: state["elapsed"] >= minTime)]

    dial = _Dial(parameters)
    textSize = parameters["textSize"]
    waiting = visual.TextStim(
        win,
        height=textSize,
        pos=(0, 0.3),
        text=parameters["texts"]["waitingFirstTone"],
    )
    stageTexts = []
    for s in stages:
        text = footer = None
        if s.text:
            text = visual.TextStim(
                win, height=textSize, pos=(0, 0.33), text=s.text, wrapWidth=1.2
            )
        if s.footer:
            footer = visual.TextStim(
                win,
                height=textSize,
                pos=(0, -0.35),
                text=s.footer if isinstance(s.footer, str) else "",
            )
        stageTexts.append((text, footer))
    win.mouseVisible = False

    # Forget the press that started the trial, and wheel turns made before it
    event.clearEvents()
    mouse.getWheelRel()
    wheel = 0.0
    nDialMoves = 0

    engine.start_trial(trialNumber, startPhase, block=block)
    tStart = now()
    status = _Status(parameters, trialNumber, block, tStart)

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
        wheel += parameters["wheelDirection"] * float(mouse.getWheelRel()[1])
        if abs(wheel) >= 1:
            notches = int(wheel)  # whole notches, the rest carries over
            wheel -= notches

        pressed = False
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
            if parameters["mode"] == "relative":
                turn = notches * parameters["dialGainDeg"]
            else:
                period = _periodS(engine, trialNumber)
                turn = notches * parameters["dialGainMs"] / (period * 1000) * 360
            engine.nudge(notches, parameters["dialGainDeg"], parameters["dialGainMs"])
            dial.turn(turn)
            state["notches"] += notches
            state["later" if notches > 0 else "earlier"] += abs(notches)
            nDialMoves += 1

        if pressed and stageIndex < len(stages) - 1:
            stageIndex += 1
            tStage = t
            state = _newState()
        elif pressed:
            pressTime, wallTime = now(), time.time()
            engine.stop_tones()
            press = {
                "phase_deg": engine.phase_deg,
                "delay_ms": engine.delay_ms,
                "press_time": pressTime,
                "wall_time": wallTime,
                "duration": pressTime - tStart,
                "n_dial_moves": nDialMoves,
            }
            dial.draw(dial=False)
            win.flip()
            return press

        status.update(t)
        if heard:
            text, footer = stageTexts[stageIndex]
            if text is not None:
                text.draw()
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
        print(line)


def showText(
    parameters: dict,
    text: str,
    footer: Optional[str] = None,
    header: Optional[str] = None,
) -> None:
    """Draw a text screen, with an optional footer and header line."""
    from psychopy import visual

    win = parameters["win"]
    visual.TextStim(win, height=parameters["textSize"], text=text, wrapWidth=1.2).draw()
    if footer is not None:
        visual.TextStim(
            win, height=parameters["textSize"], pos=(0.0, -0.4), text=footer
        ).draw()
    if header is not None:
        visual.TextStim(
            win, height=parameters["textSize"], pos=(0.0, 0.3), text=header
        ).draw()
    win.flip()


def waitInput(parameters: dict) -> None:
    """Wait for the start key. Esc stops the task; the wheel does nothing."""
    from psychopy import event

    event.clearEvents(eventType="keyboard")
    while True:
        _idle(parameters)
        keys = event.getKeys(keyList=[parameters["startKey"], "escape"])
        _checkEscape(keys)
        if parameters["startKey"] in keys:
            parameters["myMouse"].getWheelRel()  # drop turns made while waiting
            return
        time.sleep(0.005)


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

    showText(parameters, texts["tutorialIntro"], footer=texts["textNext"])
    waitInput(parameters)

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
        ),
        Stage(
            texts["tutorialEarlier"],
            ready=rolled("earlier"),
            footer=progress("earlier"),
        ),
        Stage(
            texts["tutorialFree"],
            ready=lambda state: state["elapsed"] >= min(minTime, timeout),
        ),
    ]
    startPhase = float(np.random.choice(parameters["startPhases"]))
    dialLoop(parameters, TUTORIAL_TRIAL, "tutorial", startPhase, stages=stages)
    parameters["engine"].end_trial()

    showText(parameters, texts["tutorialEnd"])
    waitInput(parameters)


class _EscapableText:
    """A text stimulus that raises TaskAbort on Esc when drawn.

    The shared keyboard rating draws its message on every frame, which makes
    this the place to watch for Esc without changing the rating itself.
    """

    def __init__(self, parameters: dict, text: str):
        from psychopy import visual

        self.parameters = parameters
        self.parts = [
            visual.TextStim(
                parameters["win"],
                height=parameters["textSize"],
                pos=(0, 0.2),
                text=text,
                wrapWidth=1.2,
            ),
            visual.TextStim(
                parameters["win"],
                height=parameters["textSize"] * 0.7,
                pos=(0, -0.4),
                text=parameters["texts"]["ratingHelp"],
            ),
        ]

    def draw(self) -> None:
        from psychopy import event

        _idle(self.parameters)  # the rating draws this on every frame
        _checkEscape(event.getKeys(keyList=["escape"]))
        for part in self.parts:
            part.draw()


def confidenceRatingTask(
    parameters: dict,
) -> Tuple[Optional[float], Optional[float], bool]:
    """Confidence rating, with the arrow keys or the mouse.

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
    from psychopy import core, event, visual

    from ._rating import wheel_rating

    low, high = parameters["confScale"]
    message = _EscapableText(parameters, parameters["texts"]["Confidence"])

    if parameters["device"] == "keyboard":
        confidence, confidenceRT, provided = wheel_rating(
            win=parameters["win"],
            message=message,
            low=low,
            high=high,
            labels=parameters["labelsRating"],
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            accept_keys=(parameters["startKey"],),
            label_height=parameters["textSize"] * 0.6,
            wheel=_wheelNotches(parameters),
        )
    else:
        # As the HRD mouse slider: the cursor is hidden, warped once to a random
        # start, and only brought back when it nears the screen edge (warping
        # on every frame freezes the mouse on macOS, issue #103).
        win, mouse = parameters["win"], parameters["myMouse"]
        win.mouseVisible = False
        mouse.setPos((np.random.uniform(-0.25, 0.25), 0.2))
        slider = visual.Slider(
            win=win,
            name="slider",
            pos=(0, -0.2),
            size=(0.7, 0.1),
            labels=parameters["labelsRating"],
            granularity=1,
            ticks=(low, high),
            style="rating",
            color="LightGray",
            flip=False,
            labelHeight=parameters["textSize"] * 0.6,
        )
        slider.marker.size = (0.03, 0.03)
        confidence, confidenceRT, provided = None, None, False
        clock = core.Clock()
        mouse.clickReset()
        event.clearEvents(eventType="keyboard")
        while True:
            elapsed = clock.getTime()
            buttons = mouse.getPressed()
            mouseX, mouseY = mouse.getPos()[:2]
            newX = min(max(float(mouseX), -0.35), 0.35)
            slider.markerPos = round(low + (newX + 0.35) / 0.7 * (high - low))
            if abs(mouseX) > 0.85 or abs(mouseY) > 0.45:
                mouse.setPos((newX, 0.2))
            if buttons[0] and elapsed > parameters["minRatingTime"]:
                confidence, confidenceRT, provided = slider.markerPos, elapsed, True
                slider.marker.color = "green"
                slider.draw()
                message.draw()
                win.flip()
                core.wait(0.2)
                break
            maxTime = parameters["maxRatingTime"]
            if maxTime is not None and elapsed > maxTime:
                break
            slider.draw()
            message.draw()
            win.flip()

    if provided:
        print(f"... confidence {confidence} after {confidenceRT:.2f} s")
    else:
        print("... no confidence rating")
        if parameters["maxRatingTime"] is not None:
            visual.TextStim(
                parameters["win"],
                height=parameters["textSize"],
                text=parameters["texts"]["tooLate"],
                color="red",
            ).draw()
            parameters["win"].flip()
            core.wait(0.5)
    parameters["win"].flip()
    return confidence, confidenceRT, provided
