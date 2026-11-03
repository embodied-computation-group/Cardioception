# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The PsychoPy side of the Phase Adjustment Task.

During a trial the participant sees a fixation cross and nothing else. The
mouse wheel moves the tones relative to the heartbeat through
``parameters["engine"]`` (see :mod:`cardioception.PAT.engine`), which is polled
on every frame and does all the timing. Space ends the trial, then comes the
confidence rating. The experimenter gets one status line per second in the
console.
"""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

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


def dialLoop(
    parameters: dict,
    trialNumber: int,
    block: str,
    startPhase: float,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the engine and the dial until the participant presses space.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    trialNumber : int
        Trial number given to the engine.
    block : str
        Shown in the experimenter status line.
    startPhase : float
        Start phase of the dial, in degrees.
    message : str | None
        Text shown instead of the fixation cross (for the tutorial).

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

    if message is None:
        stim = visual.GratingStim(win=win, mask="cross", size=0.1, pos=[0, 0], sf=0)
    else:
        stim = visual.TextStim(win, height=parameters["textSize"], text=message)
    win.mouseVisible = False

    # Forget the press that started the trial, and wheel turns made before it
    event.clearEvents()
    mouse.getWheelRel()
    wheel = 0.0
    nDialMoves = 0

    engine.start_trial(trialNumber, startPhase, block=block)
    tStart = now()
    status = _Status(parameters, trialNumber, block, tStart)

    while True:
        engine.poll()

        notches = 0
        wheel += float(mouse.getWheelRel()[1])
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
                # Ignored early in the trial, so a double press does not end it
                if now() - tStart >= parameters["minTrialTime"]:
                    pressed = True

        if notches != 0:
            engine.nudge(notches, parameters["dialGainDeg"], parameters["dialGainMs"])
            nDialMoves += 1

        if pressed:
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
            stim.draw()
            win.flip()
            return press

        status.update(now())
        stim.draw()
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
    """Wait for the start key. Esc stops the task."""
    from psychopy import event

    event.clearEvents(eventType="keyboard")
    while True:
        keys = event.getKeys(keyList=[parameters["startKey"], "escape"])
        _checkEscape(keys)
        if parameters["startKey"] in keys:
            return
        time.sleep(0.005)


def tutorial(parameters: dict) -> None:
    """Let the participant try the dial on free beats. Nothing is saved.

    Parameters
    ----------
    parameters : dict
        Task parameters.

    """
    texts = parameters["texts"]
    showText(parameters, texts["tutorialDial"], footer=texts["textNext"])
    waitInput(parameters)

    startPhase = float(np.random.choice(parameters["startPhases"]))
    dialLoop(
        parameters,
        TUTORIAL_TRIAL,
        "tutorial",
        startPhase,
        message=texts["tutorialRunning"],
    )
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

    from .._rating import keyboard_rating

    low, high = parameters["confScale"]
    message = _EscapableText(parameters, parameters["texts"]["Confidence"])

    if parameters["device"] == "keyboard":
        confidence, confidenceRT, provided = keyboard_rating(
            win=parameters["win"],
            message=message,
            low=low,
            high=high,
            labels=parameters["labelsRating"],
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            accept_keys=(parameters["startKey"],),
            label_height=parameters["textSize"] * 0.6,
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
