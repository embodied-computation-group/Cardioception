# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Run the Heartbeat Synchrony Discrimination task.

A trial: a fixation cross; a delay chosen by the engine; a train of tones,
each that delay after its own R-wave; a "synchronous" or "not synchronous"
judgement on the keyboard; a confidence rating; and an update of the
posterior with the delay actually realized. The session stops once the
credible interval of ``mu`` is narrow enough, after ``minTrials`` trials that
reached the posterior, or after ``maxTrials`` trials in all.

Every clock time written by this module is on the session clock,
``parameters["clock"]``, which the beat source and the tone player share.
"""

import json
import math
import pickle
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .._log import get_logger
from .._present import hold, on_every_frame
from .._screens import Screen
from .._screens import fixation as fixation_cross
from .._screens import text
from .._session import confidence_rating
from .._session import show_screen as _show_screen
from .._session import waitInput
from .._triggers import fire
from ._constants import Trigger
from ._outcome import HSDTrialOutcome, posterior_fields, train_fields
from ._stimulus import TrainResult, TrainScheduler

logger = get_logger()

#: Seconds to wait for the beat source to report an interbeat interval before
#: a phase-axis trial is skipped.
PERIOD_WAIT = 5.0

#: Trials in a row that deliver no tone before the session gives up. A train
#: that cannot be delivered means the beat source has lost the heart, and
#: carrying on would only fill the results with empty rows.
MAX_EMPTY_TRIALS = 3

#: Keys of ``parameters`` that cannot be pickled, or are written to their own
#: files, and are left out of the parameters pickle.
_NOT_PICKLED = (
    "win",
    "engine",
    "beatSource",
    "tonePlayer",
    "scheduler",
    "autopilot",
    "recorder",
    "triggers",
    "clock",
    "results_rows",
    "results_df",
    "tone_rows",
    "beat_rows",
    "posteriors",
)


@dataclass(frozen=True)
class PracticeBlock:
    """Practice trials: the real trial, without updating the engine.

    There is no feedback, because a synchrony judgement has no correct answer.
    """

    count: int = 3
    rating: bool = True


#: The tutorial: what the task is, how to answer, the confidence rating, and
#: three practice trials.
TUTORIAL = (
    Screen([("Tutorial1", (0.0, 0.0))]),
    Screen([("Tutorial2", (0.0, 0.0))]),
    Screen([("Tutorial3", (0.0, 0.0))]),
    PracticeBlock(count=3, rating=True),
)

#: Shown once, before the first trial.
START_SCREEN = Screen([("textTaskStart", (0.0, 0.0))])


# -- markers -------------------------------------------------------------------


def _json_safe(value: Any) -> Any:
    """NaN and infinities as ``null``, numpy scalars as Python ones."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _marker(parameters: dict, nTrial: int, practice: bool = False) -> Callable:
    """``marker(kind, stamp, **fields)`` for one trial.

    Pushes ``{"kind": kind, "trial": nTrial, ...}`` as JSON to the recorder's
    marker outlet, stamped ``stamp`` (0 for now). Without an outlet the marker
    is logged at debug level instead.
    """
    outlet = getattr(parameters.get("recorder"), "outlet", None)

    def mark(kind: str, stamp: float = 0.0, **fields: Any) -> None:
        payload: Dict[str, Any] = {"kind": kind, "trial": nTrial}
        if practice:
            payload["practice"] = True
        payload = _json_safe({**payload, **fields})
        message = json.dumps(payload)
        if outlet is not None:
            outlet.push_sample([message], float(stamp))
        else:
            logger.debug(f"marker {message}")

    return mark


def _trigger(parameters: dict, code: Trigger, event: str, mark: Callable) -> float:
    """Mark ``code``, run the callback for ``event``, and return the time."""
    stamp = parameters["clock"]()
    mark("trigger", 0.0, name=code.name, code=int(code))
    fire(parameters, event)
    return stamp


# -- small pieces ----------------------------------------------------------------


def _check_escape(parameters: dict) -> None:
    from psychopy import core, event

    if "escape" in event.getKeys(keyList=["escape"]):
        logger.warning("User abort")
        parameters["win"].close()
        core.quit()


def show_screen(parameters: dict, screen, prompt=None) -> list:
    """Draw one instruction screen and, unless told otherwise, wait.

    :func:`cardioception._session.show_screen`, with ``text``, ``hold`` and
    ``waitInput`` looked up in this module when it is called, so that a test
    can stub them here.
    """
    return _show_screen(
        parameters,
        screen,
        prompt,
        text_fn=text,
        hold_fn=hold,
        wait_fn=waitInput,
    )


def _poll_source(parameters: dict) -> None:
    """Keep the beat source current between trains, without losing beats.

    What is polled goes to the scheduler, which keeps it for the record and
    for the RR interval of the next beat.
    """
    _scheduler(parameters).observe(parameters["beatSource"].poll())


def _wait_for_period(parameters: dict, *stims) -> Optional[float]:
    """Hold ``stims`` until the beat source knows the period, or give up."""
    from psychopy import core

    source = parameters["beatSource"]
    clock = core.Clock()
    while source.period is None and clock.getTime() < PERIOD_WAIT:
        _poll_source(parameters)
        hold(parameters["win"], 0.05, *stims)
    return source.period


def _redraw_period(result: TrainResult, source) -> Optional[float]:
    """The interbeat interval to draw a new delay for, after a refusal.

    The last anticipated period the train saw, else the source's, else the
    last RR interval between beats the train saw. A floor refusal is checked
    against the source's period at the start of the train, so that comes
    first there.
    """
    if result.abort_reason == "floor" and source.period:
        return float(source.period)
    for beat in reversed(result.beats_seen):
        if beat.get("period"):
            return float(beat["period"])
    if source.period:
        return float(source.period)
    r_times = sorted(b["r_time"] for b in result.beats_seen)
    if len(r_times) >= 2:
        return float(r_times[-1] - r_times[-2])
    return None


def _scheduler(parameters: dict) -> TrainScheduler:
    """The session's scheduler, made on first use.

    One for the whole session, so the first beat of a train still has the RR
    interval from the beat before it.
    """
    if parameters.get("scheduler") is None:
        config = parameters["config"]
        parameters["scheduler"] = TrainScheduler(
            parameters["beatSource"],
            parameters["tonePlayer"],
            parameters["clock"],
            n_tones=config.nTones,
            audio_lead=config.audioLead,
            bridge_lag=config.bridgeLag,
        )
    return parameters["scheduler"]


def responseDecision(
    parameters: dict, realized: float
) -> Tuple[float, bool, Optional[str], Optional[float]]:
    """Collect the synchrony judgement from the keyboard.

    The keyboard branch of the HRD's ``responseDecision``, without the sound.
    ``realized`` is the delay heard, in engine units, which only the autopilot
    reads.

    Returns
    -------
    responseMade, respProvided, decision, decisionRT
        ``decision`` is ``"Synchronous"``, ``"NotSynchronous"`` or ``None``.
    """
    from psychopy import core, event

    logger.info("...starting decision phase.")
    response_keys = parameters["response_keys"]
    pilot = parameters.get("autopilot")
    clock = core.Clock()

    if pilot is not None:
        answer = pilot.decide(realized, max_wait=parameters["respMax"])
        responseKey = (
            [[response_keys[answer[0]], answer[1]]] if answer is not None else None
        )
    else:
        # Keys pressed while the tones played are not an answer to a question
        # that had not been asked yet. Escape is looked for first, so it is
        # not cleared away with them.
        _check_escape(parameters)
        event.clearEvents(eventType="keyboard")
        watched = list(parameters["allowedKeys"]) + ["escape"]
        responseKey = None
        while clock.getTime() < parameters["respMax"]:
            # Keep the beat source current, so the next train does not start
            # on a backlog.
            _poll_source(parameters)
            pressed = event.getKeys(keyList=watched, timeStamped=clock)
            if pressed:
                responseKey = pressed
                break
        if responseKey and responseKey[0][0] == "escape":
            logger.warning("User abort")
            parameters["win"].close()
            core.quit()

    responseMade = parameters["clock"]()

    if not responseKey:
        message = text(parameters, parameters["texts"]["tooLate"])
        hold(parameters["win"], 1, message)
        return responseMade, False, None, None

    key_to_label = {key: label for label, key in response_keys.items()}
    decision = key_to_label.get(responseKey[0][0], responseKey[0][0])
    decisionRT = float(responseKey[0][1])
    logger.info(f"... decision: {decision} ({decisionRT:.2f} s)")
    return responseMade, True, decision, decisionRT


# -- one trial -------------------------------------------------------------------


def trial(
    parameters: dict,
    nTrial: int,
    confidenceRating: bool = True,
    practice: bool = False,
) -> HSDTrialOutcome:
    """Run one trial of the Heartbeat Synchrony Discrimination task.

    Parameters
    ----------
    parameters : dict
        Task parameters, from :func:`cardioception.HSD.parameters.getParameters`.
    nTrial : int
        Trial number, written to the results and to every marker.
    confidenceRating : bool
        Ask for a confidence rating after the decision.
    practice : bool
        A tutorial trial: the engine is not updated and nothing is kept for
        the output files.

    Returns
    -------
    outcome : HSDTrialOutcome
        The train, the judgement and the posterior after the update. A trial
        whose train delivered no tone has ``nDelivered == 0``, no decision,
        and did not touch the posterior.
    """
    config = parameters["config"]
    engine = parameters["engine"]
    source = parameters["beatSource"]
    win = parameters["win"]
    texts = parameters["texts"]
    mark = _marker(parameters, nTrial, practice)
    scheduler = _scheduler(parameters)
    # Set now, so the beats observed before the train are marked with it.
    scheduler.marker = mark

    logger.info(f"Starting trial {nTrial}{' (practice)' if practice else ''}")
    win.mouseVisible = False
    droppedAtStart = win.nDroppedFrames

    startTrigger = _trigger(parameters, Trigger.TRIAL_START, "trialStart", mark)

    fixation = fixation_cross(parameters)
    hold(win, parameters["rng"].uniform(*parameters["isi"]), fixation)
    _check_escape(parameters)

    prompt = text(parameters, texts["trainPrompt"])
    if source.period is None and config.axis == "phase":
        _wait_for_period(parameters, fixation)
    hold(win, 0, prompt)
    # Read after the last hold, so the delay is drawn for the current period.
    period = source.period

    results: List[TrainResult] = []
    explored = False
    if period is None and config.axis == "phase":
        logger.warning(
            f"... the beat source reported no interbeat interval within "
            f"{PERIOD_WAIT:g} s; a phase-axis delay cannot be set, so the "
            "trial is skipped."
        )
        now = parameters["clock"]()
        result = TrainResult(
            delay=math.nan,
            axis=config.axis,
            aborted=True,
            abort_reason="no_period",
            end_reason="no_period",
            started=now,
            ended=now,
        )
    else:
        # On the absolute axis the period only sets the ceiling, and a 1 s
        # period allows every default candidate.
        delay, explored = engine.next_delay(
            *config.bounds(period if period is not None else 1.0)
        )

        def on_frame() -> None:
            prompt.draw()
            win.flip()
            _check_escape(parameters)

        scheduler.on_frame = on_frame
        # The window flips once per tone at most during the train, by design,
        # so those intervals are not dropped frames.
        win.recordFrameIntervals = False
        _trigger(parameters, Trigger.TRAIN_START, "trainStart", mark)
        logger.info(f"... train at {delay:g} ({config.axis}).")
        result = scheduler.run(
            delay, config.axis, config.minDelay, config.maxPeriodFraction
        )
        results.append(result)

        redraw = result.aborted and result.abort_reason in ("ceiling", "floor")
        if redraw and result.n_delivered > 0:
            # The participant heard these tones: they are the stimulus.
            logger.warning(
                f"... train stopped at the {result.abort_reason} after "
                f"{result.n_delivered} tone(s); kept as the stimulus."
            )
        elif redraw:
            # Nothing was heard. The period changed between the draw and the
            # train, so draw again for the period the train saw.
            redraw_period = _redraw_period(result, source)
            logger.warning(
                f"... {delay:g} refused at the {result.abort_reason} "
                f"(interbeat interval {redraw_period}); drawing again."
            )
            try:
                delay, explored = engine.next_delay(
                    *config.bounds(redraw_period if redraw_period else 1.0)
                )
            except ValueError as error:
                logger.warning(f"... no candidate for this period: {error}")
            else:
                result = scheduler.run(
                    delay, config.axis, config.minDelay, config.maxPeriodFraction
                )
                results.append(result)
        # No trigger code of its own: the tone_onset markers carry the train.
        mark("train_stop", 0.0, reason=result.end_reason)
        fire(parameters, "trainStop")
        win.recordFrameIntervals = True

    # A train that ended short ("max_beats") still counts if one tone played.
    realized = result.realized_corrected if result.n_delivered > 0 else None
    decision, decisionRT, respProvided = None, None, False
    confidence, confidenceRT, ratingProvided = None, None, False
    decisionStart = responseMade = ratingStart = ratingEnd = None

    if realized is None:
        logger.warning(
            f"... no tone delivered ({result.end_reason}); the trial is "
            "recorded as not presented."
        )
    else:
        question = text(parameters, texts["Decision"]["question"], pos=(0.0, 0.3))
        upper = text(parameters, texts["Decision"]["Synchronous"], pos=(0.0, 0.1))
        lower = text(parameters, texts["Decision"]["NotSynchronous"], pos=(0.0, -0.1))
        press = text(parameters, texts["responseText"], pos=(0.0, -0.4))
        stims = (question, upper, lower, press)
        for stim in stims:
            stim.autoDraw = True
        decisionStart = _trigger(
            parameters, Trigger.DECISION_START, "decisionStart", mark
        )
        win.flip()
        # Waiting for a key does not flip either.
        win.recordFrameIntervals = False
        responseMade, respProvided, decision, decisionRT = responseDecision(
            parameters, realized
        )
        win.recordFrameIntervals = True
        fire(parameters, "decisionStop")
        for stim in stims:
            stim.autoDraw = False
        mark("decision", 0.0, decision=decision, rt=decisionRT)

        if confidenceRating and respProvided:
            ratingStart = _trigger(
                parameters, Trigger.CONFIDENCE_START, "confidenceStart", mark
            )
            confidence, confidenceRT, ratingProvided, _ = confidence_rating(parameters)
            ratingEnd = parameters["clock"]()
            fire(parameters, "confidenceStop")
            mark("confidence", 0.0, confidence=confidence, rt=confidenceRT)

    if not practice and realized is not None and respProvided:
        engine.update(realized, decision == "Synchronous", explored)

    endTrigger = _trigger(parameters, Trigger.TRIAL_STOP, "trialStop", mark)

    if not practice:
        for attempt, train in enumerate(results):
            for tone in train.tones:
                parameters["tone_rows"].append(
                    {"Trial": nTrial, "Attempt": attempt, **asdict(tone)}
                )
            for beat in train.beats_seen:
                parameters["beat_rows"].append(
                    {"Trial": nTrial, "Attempt": attempt, **beat}
                )
        parameters["posteriors"].append(
            np.asarray(engine.posterior).reshape(engine.shape).copy()
        )

    return HSDTrialOutcome(
        trial=nTrial,
        explored=explored,
        decision=decision,
        decisionRT=decisionRT,
        confidence=confidence,
        confidenceRT=confidenceRT,
        respProvided=respProvided,
        ratingProvided=ratingProvided,
        startTrigger=startTrigger,
        decisionStart=decisionStart,
        responseMade=responseMade,
        ratingStart=ratingStart,
        ratingEnd=ratingEnd,
        endTrigger=endTrigger,
        quality={
            "nTrains": len(results),
            "EndReason": result.end_reason,
            "nBeatsSeen": sum(len(t.beats_seen) for t in results),
            "DroppedFrames": win.nDroppedFrames - droppedAtStart,
        },
        **train_fields(result),
        **posterior_fields(engine),
    )


# -- the session -------------------------------------------------------------------


def _save_session(parameters: dict) -> None:
    """Write everything the session produced.

    Called from a finally clause, so an abort or a crash still saves.
    """
    paths = parameters["paths"]
    engine = parameters["engine"]

    logger.info("Saving final results in .txt file...")
    pd.DataFrame(parameters["results_rows"]).to_csv(paths.path("final"), index=False)
    pd.DataFrame(parameters["tone_rows"]).to_csv(paths.path("tones"), index=False)
    pd.DataFrame(parameters["beat_rows"]).to_csv(paths.path("beats"), index=False)

    logger.info("Saving the posterior and the engine...")
    posteriors = parameters["posteriors"]
    np.save(
        paths.path("posterior", ext="npy"),
        np.array(posteriors) if posteriors else np.empty((0, *engine.shape)),
    )
    with open(paths.path("engine", ext="json"), "w") as handle:
        json.dump(engine.state(), handle)

    # No recording file: the beat source is the only reader of the LSL
    # inlet, so the recorder holds no signal. The ECG and the markers are in
    # the LabRecorder XDF.

    logger.info("Saving Parameters in pickle...")
    save_parameter = {k: v for k, v in parameters.items() if k not in _NOT_PICKLED}
    with open(paths.path("parameters", ext="pickle"), "wb") as handle:
        pickle.dump(save_parameter, handle, protocol=pickle.HIGHEST_PROTOCOL)


def _break(parameters: dict, nTrial: int) -> None:
    message = text(parameters, parameters["texts"]["textBreaks"])
    percent = round(min(nTrial / parameters["maxTrials"], 1.0) * 100, 2)
    remain = text(parameters, f" ---- {percent} % ---- ", pos=(0.0, 0.2))
    remain.draw()
    message.draw()
    parameters["win"].flip()
    waitInput(parameters)
    fixation = fixation_cross(parameters)
    fixation.draw()
    parameters["win"].flip()


def run(
    parameters: dict,
    confidenceRating: bool = True,
    runTutorial: bool = True,
):
    """Run the Heartbeat Synchrony Discrimination task.

    Parameters
    ----------
    parameters : dict
        Task parameters, from :func:`cardioception.HSD.parameters.getParameters`.
    confidenceRating : bool
        Ask for a confidence rating after each decision.
    runTutorial : bool
        Show the instructions and three practice trials first.

    Notes
    -----
    Writes ``final`` (one row per trial, see
    :class:`cardioception.HSD._outcome.HSDTrialOutcome`), ``tones`` (one row
    per beat a tone was tried on), ``beats`` (every beat polled),
    ``posterior`` (``.npy``, one posterior per trial), ``engine`` (JSON, the
    engine's state) and the parameters pickle. The ``nTrials`` column counts
    the trials that had reached the posterior when the row was written.

    ``beats`` holds every beat polled during the session. Those polled
    between trains have status ``"between"`` and are filed with the trial
    whose train followed them; those after the last train have no trial.

    Raises
    ------
    RuntimeError
        After :data:`MAX_EMPTY_TRIALS` trials in a row that delivered no tone.
        The files are saved first.
    """
    config = parameters["config"]
    engine = parameters["engine"]
    source = parameters["beatSource"]
    win = parameters["win"]
    scale = parameters["confidenceScale"]

    # The detector needs a few seconds of signal and three beats before it
    # knows the period, so the source runs for the whole session; draining it
    # on every held frame keeps it current between trains.
    source.start()
    _scheduler(parameters)
    on_every_frame(win, lambda: _poll_source(parameters))

    nTrial = 0
    try:
        if runTutorial is True:
            tutorial(parameters)

        prompt = text(parameters, parameters["texts"]["textNext"], pos=(0.0, -0.4))
        show_screen(parameters, START_SCREEN, prompt)

        empty = 0
        while nTrial < config.maxTrials:
            outcome = trial(parameters, nTrial, confidenceRating=confidenceRating)
            confidence = outcome.confidence
            parameters["results_rows"].append(
                outcome.row(
                    Device=parameters["device"],
                    ConfidenceUnit=(
                        None if confidence is None else scale.to_unit(confidence)
                    ),
                    scale=scale.describe(),
                    nTrials=len(engine.history),
                )
            )
            parameters["results_df"] = pd.DataFrame(parameters["results_rows"])
            parameters["results_df"].to_csv(
                parameters["paths"].path("behaviour"), index=False
            )
            nTrial += 1

            empty = 0 if outcome.nDelivered else empty + 1
            if empty >= MAX_EMPTY_TRIALS:
                message = (
                    f"{empty} trials in a row delivered no tone, so the beat "
                    "source has lost the heart. Check the ECG signal and the "
                    "beat source. The trials so far are saved."
                )
                logger.error(message)
                raise RuntimeError(message)
            if len(engine.history) >= config.minTrials and engine.converged(
                config.ci_width()
            ):
                logger.info(
                    f"... converged after {len(engine.history)} trials "
                    f"(mu interval {engine.ci_width():.3g})."
                )
                break

            if (
                parameters["nBreaking"]
                and nTrial % parameters["nBreaking"] == 0
                and nTrial < config.maxTrials
            ):
                _break(parameters, nTrial)
    finally:
        on_every_frame(win, None)
        player = parameters["tonePlayer"]
        if hasattr(player, "stop_all"):
            player.stop_all()
        source.stop()
        for beat in _scheduler(parameters).take_between():
            parameters["beat_rows"].append({"Trial": None, "Attempt": None, **beat})
        _save_session(parameters)

    end = text(parameters, parameters["texts"]["done"])
    hold(win, 3, end)


def tutorial(parameters: dict) -> None:
    """Walk the participant through the task before it starts.

    The sequence lives in :data:`TUTORIAL`; this only presents it. Practice
    trials go through :func:`trial` with ``practice=True``.
    """
    prompt = text(parameters, parameters["texts"]["textNext"], pos=(0.0, -0.4))
    for step in TUTORIAL:
        if isinstance(step, PracticeBlock):
            for i in range(step.count):
                trial(parameters, i, confidenceRating=step.rating, practice=True)
        else:
            show_screen(parameters, step, prompt)
