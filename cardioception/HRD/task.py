# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University

import pickle
import time
from collections import deque
from typing import Optional, Tuple, cast

import numpy as np
import pandas as pd
from systole.detection import ppg_peaks

from .._log import get_logger
from .._present import accept_press, hold, on_every_frame  # noqa: F401
from .._resources import resource_filename
from .._screens import AskFingerNumber, Practice, Screen
from .._screens import fixation as fixation_cross
from .._screens import text
from .._triggers import fire
from ._constants import (
    ANALYSIS_MARGIN,
    OXIMETER_SFREQ,
    PPG_SFREQ,
    TONE_BPM_MAX,
    TONE_BPM_MIN,
    Trigger,
)
from ._outcome import HeartRateReading, TrialOutcome

logger = get_logger()


def _save_recording(parameters: dict) -> None:
    """Write the whole-session recording, if there is one.

    Rewritten at every break and again at the end, rather than once when the
    session finishes: the recording this feature exists to collect is an
    hour long, and a crash or an abort at minute fifty-nine would otherwise
    take all of it. Rewriting costs a few seconds a handful of times, which
    happens while the participant is resting.

    The per-block ``ppg-N`` files stay exactly as they were. This is a file
    alongside them, not a replacement, so nothing reading the old outputs
    changes.
    """
    if not parameters.get("continuousRecording"):
        return
    target = parameters["paths"].path("recording")
    logger.info(f"Saving the continuous recording ({target})...")
    parameters["oxiTask"].save(target)


def _save_session(parameters: dict, nTrial: int) -> None:
    """Write everything the session produced.

    Called from a finally clause so an abort or a crash still saves.
    """
    paths = parameters["paths"]

    logger.info("Saving final results in .txt file...")
    parameters["results_df"].to_csv(paths.path("final"), index=False)

    logger.info("Saving PPG signal data frame...")
    parameters["signal_df"].to_csv(paths.path("signal"), index=False)

    parameters["oxiTask"].save(paths.path(f"ppg-{nTrial}-end"))
    _save_recording(parameters)

    logger.info("Saving posterior distributions...")
    for k in set(parameters["Modality"]):
        np.save(
            paths.path(f"posterior-{k}", ext="npy"),
            np.array(parameters["staircaisePosteriors"][k]),
        )

    logger.info("Saving Parameters in pickle...")
    save_parameter = parameters.copy()
    # Unpicklable.
    for k in [
        "win",
        "heartLogo",
        "listenLogo",
        "stairCase",
        "oxiTask",
        "myMouse",
        "handSchema",
        "pulseSchema",
        "autopilot",
        "recorder",
        "triggers",
    ]:
        save_parameter.pop(k, None)
    # Already written to their own files above; keeping them here made the
    # pickle 30 MB of duplicates.
    for k in ["staircaisePosteriors", "signal_df", "results_df"]:
        save_parameter.pop(k, None)
    with open(paths.path("parameters", ext="pickle"), "wb") as handle:
        pickle.dump(save_parameter, handle, protocol=pickle.HIGHEST_PROTOCOL)


def run(
    parameters: dict,
    confidenceRating: bool = True,
    runTutorial: bool = False,
):
    """Run the Heart Rate Discrimination task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    confidenceRating : bool
        Whether the trial show include a confidence rating scale.
    runTutorial : bool
        If `True`, will present a tutorial with 10 training trial with feedback
        and 5 trials with confidence rating.
    """
    # Initialization of the Pulse Oximeter
    parameters["oxiTask"].setup().read(duration=1)

    # Continuous recording is one hook, because Phase 1 replaced every
    # core.wait with hold(): draining once per frame there covers the fixation
    # crosses, the feedback, the between-trial waits and the tutorial -- most
    # of a session's wall clock, and all of what used to fall outside the
    # saved signal. Installed before the tutorial so it is covered too.
    if parameters.get("continuousRecording"):
        on_every_frame(parameters["win"], parameters["oxiTask"].readInWaiting)
        logger.info("... continuous recording on: draining every frame.")

    # Show tutorial and training trials
    if runTutorial is True:
        tutorial(parameters)

    # A queue rather than a zip, so a missed trial can be re-presented.
    queue = deque(
        {"modality": m, "trialType": s, "attempt": 0, "alpha": None}
        for m, s in zip(parameters["Modality"], parameters["staircaseType"])
    )
    maxRepresentations = parameters.get("maxRepresentations", 3)
    onMissedTrial = parameters.get("onMissedTrial", "represent")
    # Counted as we go: slicing the design arrays breaks once a trial can
    # appear twice.
    catchSeen = {"Intero": 0, "Extero": 0}
    nTrial = 0
    nPlanned = parameters["nTrials"]

    try:
        while queue:
            thisItem = queue.popleft()
            modality, trialType = thisItem["modality"], thisItem["trialType"]

            # Initialize variable
            estimatedThreshold, estimatedSlope = None, None

            # Wait for key press if this is the first trial
            if nTrial == 0:
                # Ask the participant to press default button to start
                messageStart = text(parameters, parameters["texts"]["textTaskStart"])
                press = text(
                    parameters, parameters["texts"]["textNext"], pos=(0.0, -0.4)
                )
                press.draw()
                messageStart.draw()  # Show instructions
                parameters["win"].flip()

                waitInput(parameters)

            # Next intensity value
            if trialType == "psi":
                logger.info("... load psi staircase.")
                alpha = parameters["stairCase"][modality].next()
                stairCond = "psi"
            elif trialType == "CatchTrial":
                logger.info("... load catch trial.")
                # A re-presented catch trial keeps its first intensity.
                if thisItem["alpha"] is None:
                    catchIdx = catchSeen[modality]
                    catchSeen[modality] += 1
                    thisItem["alpha"] = float(
                        np.array([-30, 10, -20, 20, -10, 30])[catchIdx % 6]
                    )
                alpha = thisItem["alpha"]
                stairCond = "CatchTrial"

            # Before trial triggers
            parameters["oxiTask"].readInWaiting()
            parameters["oxiTask"].channels["Channel_0"][-1] = Trigger.TRIAL_START
            fire(parameters, "trialStart")

            # Start trial
            outcome = trial(
                parameters,
                alpha,
                modality,
                confidenceRating=confidenceRating,
                nTrial=nTrial,
            )

            # A missed trial must not reach the staircase: decision is None,
            # which used to collapse to isMore = 0 and enter the posterior as
            # a "Less" the participant never gave.
            if not outcome.respProvided:
                canRepresent = (
                    onMissedTrial == "represent"
                    and thisItem["attempt"] + 1 < maxRepresentations
                )
                if canRepresent:
                    queue.append({**thisItem, "attempt": thisItem["attempt"] + 1})
                    logger.info(
                        f"... no response, re-queued "
                        f"(attempt {thisItem['attempt'] + 2} of {maxRepresentations})."
                    )
                else:
                    logger.warning("... no response, trial not repeated.")

            if outcome.respProvided:
                # Check if response is 'More' or 'Less'
                isMore = 1 if outcome.decision == "More" else 0

                if trialType == "psi":
                    logger.info("... update psi staircase.")

                    # A tone outside TONE_BPM_MIN..MAX is clamped, so the
                    # delta actually heard is not the one psi asked for. The
                    # handler's `intensities` are deltas over intensRange, so
                    # the correction has to be a delta too: passing the
                    # clamped *absolute* BPM wrote 15.0 or 199.0 into a list
                    # scaled (-50.5, 50.5).
                    delivered = outcome.responseBPM - outcome.listenBPM
                    if delivered != outcome.alpha:
                        parameters["stairCase"][modality].addResponse(
                            isMore, intensity=delivered
                        )
                        # The posterior itself cannot be corrected here:
                        # PsiObject.update indexes the likelihood by
                        # nextIntensityIndex, the intensity psi chose, and
                        # ignores what addResponse was given. So this trial
                        # updates the posterior as though the requested delta
                        # had been delivered. Logged rather than hidden.
                        logger.warning(
                            f"... tone clamped: asked {outcome.alpha:+.1f} BPM, "
                            f"delivered {delivered:+.1f}. The recorded intensity "
                            f"is corrected; the psi posterior is not."
                        )
                    else:
                        parameters["stairCase"][modality].addResponse(isMore)

                    # copy() matters: [0, :, :, 0] is a view onto the 40 MB
                    # likelihood array for this trial, which would otherwise
                    # stay alive for the whole session.
                    parameters["staircaisePosteriors"][modality].append(
                        parameters["stairCase"][modality]
                        ._psi._probLambda[0, :, :, 0]
                        .copy()
                    )

                    # Save estimated threshold and slope for each trials
                    estimatedThreshold, estimatedSlope = parameters["stairCase"][
                        modality
                    ].estimateLambda()

            logger.info(
                f"... Initial BPM: {outcome.listenBPM} - Staircase value: "
                f"{outcome.alpha} - Response: {outcome.decision} "
                f"({outcome.isCorrect})"
            )

            # Confidence on 0-1 so sessions run on different scales stay
            # comparable, and the scale definition on every row so the file can
            # be read without the parameters pickle.
            scale = parameters["confidenceScale"]
            confidence = outcome.confidence

            parameters["results_rows"].append(
                outcome.row(
                    TrialType=trialType,
                    Modality=modality,
                    StairCond=stairCond,
                    Device=parameters["device"],
                    ConfidenceUnit=(
                        None if confidence is None else scale.to_unit(confidence)
                    ),
                    scale=scale.describe(),
                    nRepresentations=thisItem["attempt"],
                    nTrials=nTrial,
                    EstimatedThreshold=estimatedThreshold,
                    EstimatedSlope=estimatedSlope,
                )
            )
            parameters["results_df"] = pd.DataFrame(parameters["results_rows"])

            # Save the results at each iteration
            parameters["results_df"].to_csv(
                parameters["paths"].path("behaviour"), index=False
            )

            nTrial += 1

            # Breaks
            if parameters["nBreaking"] and nTrial % parameters["nBreaking"] == 0:
                message = text(parameters, parameters["texts"]["textBreaks"])
                percRemain = round(min(nTrial / nPlanned, 1.0) * 100, 2)
                remain = text(parameters, f" ---- {percRemain} % ---- ", pos=(0.0, 0.2))
                remain.draw()
                message.draw()
                parameters["win"].flip()
                parameters["oxiTask"].save(parameters["paths"].path(f"ppg-{nTrial}"))
                _save_recording(parameters)

                # Wait for participant input before continue
                waitInput(parameters)

                # Fixation cross
                fixation = fixation_cross(parameters)
                fixation.draw()
                parameters["win"].flip()

                if parameters.get("continuousRecording"):
                    # Do not reset. `setup()` clears the recording and the
                    # serial input buffer, and it runs at every break, so no
                    # saved file has ever spanned a whole session -- this is
                    # the hole continuous recording exists to close. Draining
                    # through the break, in `waitInput`, is what makes the
                    # reset unnecessary: there is no backlog to discard
                    # because nothing was left to accumulate.
                    parameters["oxiTask"].readInWaiting()
                else:
                    # Reset recording when ready
                    parameters["oxiTask"].setup()
                    parameters["oxiTask"].read(duration=1)
    finally:
        _save_session(parameters, nTrial)

    # End of the task
    end = text(parameters, parameters["texts"]["done"])
    hold(parameters["win"], 3, end)


def trial(
    parameters: dict,
    alpha: float,
    modality: str,
    confidenceRating: bool = True,
    feedback: bool = False,
    nTrial: Optional[int] = None,
) -> TrialOutcome:
    """Run one trial of the Heart Rate Discrimination task.

    Parameters
    ----------
    parameter : dict
        Task parameters.
    alpha : float
        The intensity of the stimulus, from the staircase procedure.
    modality : str
        The modality, can be `'Intero'` or `'Extro'` if an exteroceptive
        control condition has been added.
    confidenceRating : boolean
        If `False`, do not display confidence rating scale.
    feedback : boolean
        If `True`, will provide feedback.
    nTrial : int
        Trial number (optional).

    Returns
    -------
    outcome : TrialOutcome
        Everything the trial measured: the condition, the heard and delivered
        rates, the decision and whether it was correct, the confidence rating,
        and the six timestamps. The field names are the results file's column
        names -- see :class:`cardioception.HRD._outcome.TrialOutcome`, whose
        :meth:`~cardioception.HRD._outcome.TrialOutcome.row` is the only place
        that decides what a row contains.

    """
    from psychopy import core, event, sound

    # Print infos at each trial start
    logger.info(f"Starting trial - Intensity: {alpha} - Modality: {modality}")

    parameters["win"].mouseVisible = False

    # Restart the trial until participant provide response on time
    confidence, confidenceRT, isCorrect, ratingProvided = None, None, None, False

    # Fixation cross
    fixation = fixation_cross(parameters)
    hold(
        parameters["win"],
        parameters["rng"].uniform(parameters["isi"][0], parameters["isi"][1]),
        fixation,
    )

    keys = event.getKeys()
    if "escape" in keys:
        logger.warning("User abort")
        parameters["win"].close()
        core.quit()

    droppedAtStart = parameters["win"].nDroppedFrames
    heartRateAttempts, heartRateAccepted = None, None

    if modality == "Intero":
        reading = listen_to_heart(parameters)
    elif modality == "Extero":
        reading = listen_to_tone(parameters)
    else:
        raise ValueError(f"modality should be 'Intero' or 'Extero', got {modality!r}")

    listenBPM = reading.bpm
    listenBPM_arithmetic = reading.bpm_arithmetic
    startTrigger = reading.started
    signal, recordedAt = reading.signal, reading.recorded_at
    heartRateAttempts, heartRateAccepted = reading.attempts, reading.accepted
    # Fixation cross
    fixation = fixation_cross(parameters)
    hold(parameters["win"], 0.5, fixation)

    #######
    # Sound
    #######

    # Generate actual stimulus frequency
    condition = "Less" if alpha < 0 else "More"

    # Check for extreme alpha values, e.g. if alpha changes massively from
    # trial to trial.
    if (listenBPM + alpha) < TONE_BPM_MIN:
        responseBPM = TONE_BPM_MIN
    elif (listenBPM + alpha) > TONE_BPM_MAX:
        responseBPM = TONE_BPM_MAX
    else:
        responseBPM = listenBPM + alpha
    responseFile = resource_filename("cardioception.HRD", f"Sounds/{responseBPM}.wav")
    logger.info(f"...loading file (Response): {responseFile}")

    # Play selected BPM frequency
    responseSound = sound.Sound(responseFile)
    if modality == "Intero":
        parameters["heartLogo"].autoDraw = True
    elif modality == "Extero":
        parameters["listenLogo"].autoDraw = True
    else:
        raise ValueError("Invalid modality provided")
    # Record participant response (+/-)
    message = text(parameters, parameters["texts"]["Decision"][modality], pos=(0, 0.4))
    message.autoDraw = True

    press = text(parameters, parameters["texts"]["responseText"], pos=(0.0, -0.4))
    press.autoDraw = True

    # Sound trigger
    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = Trigger.DECISION_START
    fire(parameters, "decisionStart")
    soundTrigger = time.time()
    parameters["win"].flip()

    #####################
    # Esimation Responses
    #####################
    (
        responseMadeTrigger,
        respProvided,
        decision,
        decisionRT,
        isCorrect,
    ) = responseDecision(responseSound, parameters, feedback, condition)
    fire(parameters, "decisionStop")
    press.autoDraw = False
    message.autoDraw = False
    if modality == "Intero":
        parameters["heartLogo"].autoDraw = False
    elif modality == "Extero":
        parameters["listenLogo"].autoDraw = False
    else:
        raise ValueError("Invalid modality provided")
    ###################
    # Confidence Rating
    ###################

    # Record participant confidence
    if (confidenceRating is True) & (respProvided is True):
        # Confidence rating start trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = Trigger.CONFIDENCE_START
        fire(parameters, "confidenceStart")

        # Confidence rating scale
        ratingStartTrigger: Optional[float] = time.time()
        (
            confidence,
            confidenceRT,
            ratingProvided,
            ratingEndTrigger,
        ) = confidenceRatingTask(parameters)
        fire(parameters, "confidenceStop")
    else:
        ratingStartTrigger, ratingEndTrigger = None, None

    # Confidence rating end trigger
    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = Trigger.TRIAL_STOP
    fire(parameters, "trialStop")
    endTrigger = time.time()

    # Save PPG signal
    if nTrial is not None:  # Not during the tutorial
        if modality == "Intero":
            this_df = None
            # Save physio signal
            # Absolute time per sample, so the signal can be aligned
            # with the trial triggers and with anything recorded alongside
            # it. Counted back from the moment the accepted window was
            # read, at the rate ppg_peaks resampled to.
            nSamples = len(signal)
            # Only the interoceptive path records, so `recorded_at` is set
            # here by construction; it is None only for Extero, which cannot
            # reach this branch.
            recordedAt = cast(float, recordedAt)
            this_df = pd.DataFrame(
                {
                    "signal": signal,
                    "time": recordedAt
                    - (nSamples - 1 - np.arange(nSamples)) / PPG_SFREQ,
                    "nTrial": pd.Series([nTrial] * nSamples, dtype="category"),
                }
            )

            parameters["signal_df"] = pd.concat(
                [parameters["signal_df"], this_df], ignore_index=True
            )

    quality = {
        "listenBPM_arithmetic": listenBPM_arithmetic,
        "HeartRateAttempts": heartRateAttempts,
        "HeartRateAccepted": heartRateAccepted,
        "DroppedFrames": parameters["win"].nDroppedFrames - droppedAtStart,
    }

    return TrialOutcome(
        condition=condition,
        listenBPM=listenBPM,
        responseBPM=responseBPM,
        decision=decision,
        decisionRT=decisionRT,
        confidence=confidence,
        confidenceRT=confidenceRT,
        alpha=alpha,
        isCorrect=isCorrect,
        respProvided=respProvided,
        ratingProvided=ratingProvided,
        startTrigger=startTrigger,
        soundTrigger=soundTrigger,
        responseMadeTrigger=responseMadeTrigger,
        ratingStartTrigger=ratingStartTrigger,
        ratingEndTrigger=ratingEndTrigger,
        endTrigger=endTrigger,
        quality=quality,
    )


def _drain_for(parameters: dict, duration: float, *stims) -> None:
    """Record for ``duration`` seconds while the window keeps redrawing.

    What `Oximeter.read(duration=...)` does, without blocking: it busy-waits
    inside systole for the whole window, so the screen freezes, PsychoPy
    records no frame intervals, and a keypress cannot be seen until it ends.

    Escape is honoured here too. The listening window is the longest stretch
    of a trial in which the participant is asked to do nothing, so it is where
    an experimenter is most likely to want to stop.
    """
    from psychopy import core, event

    recorder = parameters["oxiTask"]
    clock = core.Clock()
    while clock.getTime() < duration:
        recorder.readInWaiting()
        for stim in stims:
            stim.draw()
        parameters["win"].flip()
        if "escape" in event.getKeys(keyList=["escape"]):
            logger.warning("User abort")
            parameters["win"].close()
            core.quit()


def listen_to_heart(parameters: dict) -> HeartRateReading:
    """Record the participant's pulse and derive the rate the tone will match.

    Bounded and escapable. This loop was unbounded and polled no keys, so a
    single artefactual interval could hold a participant on the listening
    screen indefinitely: np.any rejects the whole window on one bad value. On
    running out of attempts it takes the last window anyway and flags the
    trial, which is recoverable; a session that never advances is not.

    This is the only place the task touches physiology, which is what makes it
    the seam a different recording device would be fitted at.
    """
    from psychopy import core, event

    messageRecord = text(
        parameters, parameters["texts"]["textHeartListening"], pos=(0.0, 0.2)
    )
    messageRecord.draw()

    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = Trigger.LISTENING_START
    fire(parameters, "listeningStart")

    parameters["heartLogo"].draw()
    parameters["win"].flip()

    started = time.time()
    maxAttempts = parameters.get("maxHeartRateAttempts", 10)
    listenBPM = None
    listenBPM_arithmetic = None
    attempt = 0
    signal = None
    recordedAt = None

    for attempt in range(maxAttempts):
        if "escape" in event.getKeys(keyList=["escape"]):
            logger.warning("User abort")
            parameters["win"].close()
            core.quit()

        # The window is `listeningDuration`, not a constant: it is documented
        # as matching the exteroceptive tone so both modalities give the same
        # listening time, and it did not. Shortening it moved the tone only,
        # leaving the control condition quietly unmatched to the recording.
        duration = parameters["listeningDuration"]
        kept = int(OXIMETER_SFREQ * (duration + ANALYSIS_MARGIN))
        peak_window = int(duration * PPG_SFREQ)

        # Adapt these lines for a different setup, provided it can produce
        # `bpm`, the per-beat rates over the listening window.
        #
        # Drain per frame rather than block. `Oximeter.read` busy-waits for
        # the whole window inside systole: nothing is drawn, no frame
        # intervals are recorded, and escape cannot be seen until the window
        # is over. Draining while flipping records the same samples and keeps
        # the screen alive. It also yields a cleaner slice -- a buffer emptied
        # continuously holds the listening window, where a buffer read once at
        # the end holds the window plus whatever backlog preceded it.
        _drain_for(parameters, duration, messageRecord, parameters["heartLogo"])

        # Stamped where the recording stops, not after the analysis. This sat
        # below ppg_peaks, which resamples the window to 1000 Hz and detects
        # peaks first, so every sample time written to the signal file was late
        # by however long that took -- a variable offset in the one column
        # whose purpose is aligning the pulse to the triggers.
        recordedAt = time.time()
        signal = parameters["oxiTask"].recording[-kept:]
        signal, peaks = ppg_peaks(
            signal, sfreq=OXIMETER_SFREQ, new_sfreq=PPG_SFREQ, clipping=True
        )

        ibi = np.diff(np.where(peaks[-peak_window:])[0])
        bpm = 60000 / ibi
        logger.info(f"... bpm: {[round(i) for i in bpm]}")

        if np.isnan(bpm).any() or (bpm is None) or (bpm.size == 0):
            message = text(
                parameters, parameters["texts"]["checkOximeter"], color="red"
            )
            hold(parameters["win"], 2, message)
            continue

        # Cutoffs correspond to biologically unlikely values.
        outside = (np.any(bpm < parameters["HRcutOff"][0])) or (
            np.any(bpm > parameters["HRcutOff"][1])
        )
        if outside:
            message = text(parameters, parameters["texts"]["stayStill"], color="red")
            hold(parameters["win"], 2, message)
            continue

        # Rate over the window, not the average of the per-beat rates.
        # Averaging 60000/IBI overestimates by Jensen's inequality, measured at
        # +0.33 BPM on real PPG, so the tone was reliably faster than the heart
        # it was meant to match. Rounded to the nearest .5 for the sound files.
        listenBPM = round((60000 / ibi.mean()) * 2) / 2
        listenBPM_arithmetic = round(bpm.mean() * 2) / 2
        break

    accepted = listenBPM is not None
    if listenBPM is None or listenBPM_arithmetic is None:
        logger.warning(f"... no acceptable heart rate after {maxAttempts} attempts.")
        usable = bpm.size and not np.isnan(bpm).all()
        fallback = float(np.mean(parameters["HRcutOff"]))
        listenBPM = round((60000 / np.nanmean(ibi)) * 2) / 2 if usable else fallback
        listenBPM_arithmetic = (
            round(float(np.nanmean(bpm)) * 2) / 2 if usable else fallback
        )

    fire(parameters, "listeningStop")
    return HeartRateReading(
        bpm=listenBPM,
        bpm_arithmetic=listenBPM_arithmetic,
        signal=signal,
        recorded_at=recordedAt,
        attempts=attempt + 1,
        accepted=accepted,
        started=started,
    )


def listen_to_tone(parameters: dict) -> HeartRateReading:
    """Play a reference tone at a random rate: the exteroceptive control.

    Nothing is recorded, so the two averages coincide and there is no heart
    rate to accept or reject.
    """
    from psychopy import sound

    messageRecord = text(
        parameters, parameters["texts"]["textToneListening"], pos=(0.0, 0.2)
    )
    messageRecord.draw()

    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = Trigger.LISTENING_START
    fire(parameters, "listeningStart")

    parameters["listenLogo"].draw()
    parameters["win"].flip()

    started = time.time()
    listenBPM = parameters["rng"].choice(np.arange(*parameters["exteroBPMRange"]))

    listenFile = resource_filename("cardioception.HRD", f"Sounds/{listenBPM}.wav")
    logger.info(f"...loading file (Listen): {listenFile}")

    # 5 s matches the interoceptive recording window, so both modalities give
    # the same listening time. Do not derive it from the rate. Parameterised
    # only so tests can shorten it.
    listenSound = sound.Sound(listenFile)
    listenSound.play()
    hold(
        parameters["win"],
        parameters["listeningDuration"],
        messageRecord,
        parameters["listenLogo"],
    )
    listenSound.stop()

    fire(parameters, "listeningStop")
    return HeartRateReading(bpm=listenBPM, bpm_arithmetic=listenBPM, started=started)


def waitInput(parameters: dict):
    """Wait for participant input before continue"""

    from psychopy import core, event

    # A synthetic participant advances at once. Whatever was drawn before this
    # call has already been drawn and flipped, so the screen is still exercised.
    if parameters.get("autopilot") is not None:
        parameters["autopilot"].advance()
        return

    # A break is the longest the task ever waits, and it does not flip, so the
    # per-frame hook does not reach here. Undrained, the driver buffer holds
    # about 10.9 seconds -- 4096 bytes at 5 bytes a packet and 75 Hz -- and a
    # participant resting for longer loses whatever overflows.
    drain = (
        parameters["oxiTask"].readInWaiting
        if parameters.get("continuousRecording")
        else None
    )

    if parameters["device"] == "keyboard":
        # Without this, a key pressed earlier is still buffered and dismisses
        # this screen before it is read.
        event.clearEvents(eventType="keyboard")
        while True:
            if drain is not None:
                drain()
            keys = event.getKeys()
            if "escape" in keys:
                logger.warning("User abort")
                parameters["win"].close()
                core.quit()
            elif parameters["startKey"] in keys:
                break
    elif parameters["device"] == "mouse":
        mouse = parameters["myMouse"]
        mouse.clickReset()
        # clickReset resets click times, not button state, so a button still
        # held from the previous screen reads as a fresh press. Wait for a
        # release, then for a press.
        armed = not any(mouse.getPressed())
        while True:
            if drain is not None:
                drain()
            buttons, armed = accept_press(mouse.getPressed(), armed)
            if any(buttons):
                break
            keys = event.getKeys()
            if "escape" in keys:
                logger.warning("User abort")
                parameters["win"].close()
                core.quit()


#: The tutorial, phase by phase, in the order participants meet them.
#:
#: A tutorial is the experiment in miniature: instruction screens interleaved
#: with short practice blocks that differ in what the participant is asked to
#: do. Written out this way the sequence is visible and editable — which
#: screens, in what order, how long each practice block runs and at what
#: difficulty — without touching the code that presents it.
TUTORIAL = (
    Screen([("Tutorial1", (0.0, 0.0))]),
    Screen([("pulseTutorial1", (0.0, 0.3))], image="pulseSchema"),
    # The Danish children's version leaves pulseTutorial2 empty to skip this.
    Screen(
        [("pulseTutorial2", (0.0, 0.2)), ("pulseTutorial3", (0.0, -0.2))],
        requires="pulseTutorial2",
    ),
    AskFingerNumber(
        screen=Screen(
            [("pulseTutorial4", (0.0, 0.3))],
            image="handSchema",
            prompt=False,
            wait=False,
        ),
    ),
    Screen([("Tutorial2", (0.0, 0.3))], image="heartLogo"),
    # The icon is drawn before the text here. Preserved from the original.
    Screen([("Tutorial3_icon", (0.0, 0.3))], image="heartLogo", image_first=True),
    Screen([("Tutorial3_responses", (0.0, 0.0))]),
    # First practice: judge, with feedback, at an easy fixed difference.
    Practice("Intero", count="nFeedback", feedback=True, intensities=(20.0,)),
    Screen([("Tutorial3bis", (0.0, -0.2))], image="listenLogo", extero_only=True),
    Screen([("Tutorial3ter", (0.0, 0.0))], extero_only=True),
    Practice(
        "Extero",
        count="nFeedback",
        feedback=True,
        intensities=(20.0,),
        extero_only=True,
    ),
    Screen([("Tutorial4", (0.0, 0.0))]),
    # Second practice: judge and rate confidence, no feedback, mixed difficulty.
    Practice("Intero", count="nConfidence", rating=True, intensities=(1, 10, 30)),
    Practice(
        "Extero",
        count="nConfidence",
        rating=True,
        intensities=(1, 10, 30),
        # The original does not reset the recording before this block. Extero
        # records nothing, so it makes no difference, but it is preserved
        # rather than quietly regularised.
        setup_recording=False,
        extero_only=True,
    ),
    Screen([("Tutorial5", (0.0, 0.0))]),
    Screen([("Tutorial6", (0.0, 0.0))]),
)


def show_screen(parameters: dict, screen, prompt=None) -> list:
    """Draw one instruction screen and, unless told otherwise, wait.

    Returns the stimuli it built, so a caller that keeps the screen up can
    redraw the same objects rather than constructing them again.
    """
    stims = [
        text(parameters, parameters["texts"][key], pos=pos) for key, pos in screen.texts
    ]
    if screen.image:
        image = parameters[screen.image]
        stims = [image] + stims if screen.image_first else stims + [image]
    if screen.prompt and prompt is not None:
        stims.append(prompt)

    hold(parameters["win"], screen.seconds, *stims)
    if screen.wait:
        waitInput(parameters)
    return stims


def ask_finger_number(parameters: dict, step) -> None:
    """Record which finger the oximeter is on.

    Kept apart from the screen table because it is the one place the tutorial
    reads something other than "continue" from the participant.
    """
    from psychopy import event

    stims = show_screen(parameters, step.screen)

    while True:
        key = event.waitKeys(
            keyList=[
                "1",
                "2",
                "3",
                "4",
                "5",
                "num_1",
                "num_2",
                "num_3",
                "num_4",
                "num_5",
            ]
        )
        if key:
            parameters["nFinger"] = [s for s in key[0] if s.isdigit()][0]
            hold(parameters["win"], 0.5, *stims)
            break


def run_practice(parameters: dict, block) -> None:
    """A short run of the real task, at fixed difficulty."""
    if block.setup_recording:
        parameters["oxiTask"].setup().read(duration=2)

    for _ in range(parameters[block.count]):
        condition = parameters["rng"].choice(["More", "Less"])
        magnitude = parameters["rng"].choice(np.array(block.intensities))
        alpha = -magnitude if condition == "Less" else magnitude
        _ = trial(
            parameters,
            alpha,
            block.modality,
            feedback=block.feedback,
            confidenceRating=block.rating,
        )


def tutorial(parameters: dict):
    """Walk the participant through the task before it starts.

    The sequence lives in :data:`TUTORIAL`; this only presents it.
    """
    prompt = text(parameters, parameters["texts"]["textNext"], pos=(0.0, -0.4))

    for step in TUTORIAL:
        if step.skipped(parameters):
            continue
        if isinstance(step, Practice):
            run_practice(parameters, step)
        elif isinstance(step, AskFingerNumber):
            ask_finger_number(parameters, step)
        else:
            show_screen(parameters, step, prompt)


def responseDecision(
    this_hr,
    parameters: dict,
    feedback: bool,
    condition: str,
) -> Tuple[float, bool, Optional[str], Optional[float], Optional[bool]]:
    """Recording response during the decision phase.

    Parameters
    ----------
    this_hr : psychopy sound instance
        The sound .wav file to play.
    parameters : dict
        Parameters dictionary.
    feedback : bool
        If `True`, provide feedback after decision.
    condition : str
        The trial condition [`'More'` or `'Less'`] used to check is response is
        correct or not.

    Returns
    -------
    responseMadeTrigger : float
        Time stamp of response provided.
    respProvided : bool
        `True` if the response was provided, `False` otherwise.
    decision : str or None
        `'More'`, `'Less'`, or `None` if no response was given in time.
    decisionRT : float
        Decision response time (seconds).
    isCorrect : bool or None
        `True` if the response provided was correct, `False` otherwise.

    """

    from psychopy import core, event

    logger.info("...starting decision phase.")

    decision, decisionRT, isCorrect = None, None, None

    if parameters["device"] == "keyboard":
        this_hr.play()
        clock = core.Clock()
        pilot = parameters.get("autopilot")
        if pilot is not None:
            # Answer in the condition's own terms, then map back to the key.
            # Passing allowedKeys ("up"/"down") meant `condition in options`
            # was never true, so the autopilot fell through to a uniform draw
            # and every keyboard session ran at chance whatever `accuracy`
            # said. The mouse branch passes ["Less", "More"] and was correct.
            response_keys = parameters["response_keys"]
            answer = pilot.decide(
                condition,
                list(response_keys),
                max_wait=parameters["respMax"],
            )
            # Same shape event.waitKeys returns: [[key, rt]] or None.
            responseKey = (
                [[response_keys[answer[0]], answer[1]]] if answer is not None else None
            )
        else:
            # `escape` has to be in keyList or waitKeys discards it, and the
            # abort is then lost rather than merely deferred.
            responseKey = event.waitKeys(
                keyList=list(parameters["allowedKeys"]) + ["escape"],
                maxWait=parameters["respMax"],
                timeStamped=clock,
            )
            if responseKey and responseKey[0][0] == "escape":
                this_hr.stop()
                logger.warning("User abort")
                parameters["win"].close()
                core.quit()
        this_hr.stop()

        responseMadeTrigger = time.time()

        # Drain before branching. This sat inside the response-provided branch,
        # so a missed trial -- the longest wait in the task, a full respMax --
        # left the serial buffer alone until the next trial's trigger, which is
        # where a gap is most likely rather than least.
        parameters["oxiTask"].readInWaiting()

        # Check for response provided by the participant
        if not responseKey:
            respProvided = False
            decision, decisionRT = None, None
            # Record participant response (+/-)
            message = text(parameters, parameters["texts"]["tooLate"])
            hold(parameters["win"], 1, message)
        else:
            respProvided = True
            decision = responseKey[0][0]
            decisionRT = responseKey[0][1]

            # Translate keyboard response to decision labels if mapping provided
            response_keys = parameters.get("response_keys")
            if response_keys:
                key_to_condition = {key: cond for cond, key in response_keys.items()}
                decision_label = key_to_condition.get(decision, decision)
                isCorrect = decision_label == condition
                decision = decision_label
            else:
                isCorrect = True if (decision == condition) else False

            # Feedback
            if feedback is True:
                if isCorrect is False:
                    acc = text(parameters, "False", color="red")
                    hold(parameters["win"], 2, acc)
                elif isCorrect is True:
                    acc = text(parameters, "Correct", color="green")
                    hold(parameters["win"], 2, acc)

    if parameters["device"] == "mouse":
        # Initialise response feedback
        slower = text(
            parameters, parameters["texts"]["slower"], pos=(-0.2, 0.2), color="white"
        )
        faster = text(
            parameters, parameters["texts"]["faster"], pos=(0.2, 0.2), color="white"
        )
        slower.draw()
        faster.draw()
        parameters["win"].flip()

        this_hr.play()
        clock = core.Clock()
        clock.reset()
        parameters["myMouse"].clickReset()
        buttons, decisionRT = parameters["myMouse"].getPressed(getTime=True)
        pilot = parameters.get("autopilot")
        # A button still held from the previous trial must not count as an
        # answer here. Only a release-then-press is accepted.
        armed = not any(parameters["myMouse"].getPressed())
        while True:
            if pilot is not None:
                answer = pilot.decide(
                    condition, ["Less", "More"], max_wait=parameters["respMax"]
                )
                if answer is None:
                    # Drive the existing timeout branch rather than duplicating it.
                    buttons, decisionRT = [0, 0, 0], [0.0, 0.0, 0.0]
                    trialdur = parameters["respMax"] + 1.0
                else:
                    _decision, _rt = answer
                    buttons = [1, 0, 0] if _decision == "Less" else [0, 0, 1]
                    decisionRT, trialdur = [_rt, 0.0, _rt], _rt
            else:
                if "escape" in event.getKeys(keyList=["escape"]):
                    this_hr.stop()
                    logger.warning("User abort")
                    parameters["win"].close()
                    core.quit()
                buttons, decisionRT = parameters["myMouse"].getPressed(getTime=True)
                trialdur = clock.getTime()
                buttons, armed = accept_press(buttons, armed)
            parameters["oxiTask"].readInWaiting()
            if buttons == [1, 0, 0]:
                decisionRT = decisionRT[0]
                decision, respProvided = "Less", True
                slower.color = "blue"

                # Show feedback for .5 seconds if enough time
                remain = parameters["respMax"] - trialdur
                pauseFeedback = 0.5 if (remain > 0.5) else remain
                hold(parameters["win"], pauseFeedback, slower, faster)
                break
            elif buttons == [0, 0, 1]:
                decisionRT = decisionRT[-1]
                decision, respProvided = "More", True
                faster.color = "blue"

                # Show feedback for .5 seconds if enough time
                remain = parameters["respMax"] - trialdur
                pauseFeedback = 0.5 if (remain > 0.5) else remain
                hold(parameters["win"], pauseFeedback, slower, faster)
                break
            elif trialdur > parameters["respMax"]:  # if too long
                respProvided = False
                decisionRT = None
                break
            else:
                slower.draw()
                faster.draw()
                parameters["win"].flip()
        responseMadeTrigger = time.time()
        this_hr.stop()

        # Check for response provided by the participant
        if respProvided is False:
            # Record participant response (+/-)
            message = text(
                parameters, parameters["texts"]["tooLate"], pos=(0.0, -0.2), color="red"
            )
            hold(parameters["win"], 0.5, message)
        else:
            # Is the answer Correct?
            isCorrect = True if (decision == condition) else False
            # Feedback
            if feedback is True:
                if isCorrect == 0:
                    textFeedback = parameters["texts"]["incorrectResponse"]
                else:
                    textFeedback = parameters["texts"]["correctResponse"]
                colorFeedback = "red" if isCorrect == 0 else "green"
                acc = text(
                    parameters, textFeedback, pos=(0.0, -0.2), color=colorFeedback
                )
                hold(parameters["win"], 1, acc)

    return (
        responseMadeTrigger,
        respProvided,
        decision,
        decisionRT,
        isCorrect,
    )


def confidenceRatingTask(
    parameters: dict,
) -> Tuple[Optional[float], Optional[float], bool, Optional[float]]:
    """Confidence rating scale, using keyboard or mouse inputs.

    Parameters
    ----------
    parameters : dict
        Parameters dictionary.

    """

    from psychopy import core, visual

    from .._rating import keyboard_rating

    logger.info("...starting confidence rating.")

    # Initialise default values
    confidence, confidenceRT = None, None

    pilot = parameters.get("autopilot")
    if pilot is not None:
        # The rating widget itself is covered by its own tests; here we only
        # need a value of the right shape so the session can run unattended.
        answer = pilot.rate(
            *parameters["confidenceScale"].bounds,
            min_time=parameters["minRatingTime"],
            max_wait=parameters["maxRatingTime"],
        )
        if answer is None:
            return None, None, False, time.time()
        confidence, confidenceRT = answer
        return confidence, confidenceRT, True, time.time()

    if parameters["device"] == "keyboard":
        message = text(parameters, parameters["texts"]["Confidence"], pos=(0, 0.2))

        # Arrow keys move the marker, the down key confirms. This was a
        # visual.RatingScale until PsychoPy 2026 moved that class into the
        # psychopy-legacy plugin, where constructing one raises
        # PluginRequiredError. Slider is the supported replacement and is what
        # the mouse branch below already used, so both devices now show the
        # same widget.
        scale = parameters["confidenceScale"]
        confidence, confidenceRT, ratingProvided = keyboard_rating(
            win=parameters["win"],
            message=message,
            low=scale.low,
            high=scale.high,
            labels=scale.labels,
            granularity=scale.granularity,
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            label_height=parameters["textSize"] * 0.6,
            rng=parameters["rng"],
        )
        if ratingProvided and confidenceRT is not None:
            logger.info(
                f"... Confidence level: {confidence}"
                + f" with response time {round(confidenceRT, 2)} seconds"
            )

    elif parameters["device"] == "mouse":
        # Use the mouse position to update the slider position
        # The mouse movement is limited to a rectangle above the Slider
        # To avoid being dragged out of the screen (in case of multi screens)
        # and to avoid interferences with the Slider when clicking.
        parameters["win"].mouseVisible = False
        parameters["myMouse"].setPos((parameters["rng"].uniform(-0.25, 0.25), 0.2))
        parameters["myMouse"].clickReset()
        message = text(parameters, parameters["texts"]["Confidence"], pos=(0, 0.2))
        slider = visual.Slider(
            win=parameters["win"],
            name="slider",
            pos=(0, -0.2),
            size=(0.7, 0.1),
            labels=parameters["confidenceScale"].labels,
            granularity=parameters["confidenceScale"].granularity,
            ticks=parameters["confidenceScale"].ticks,
            style=("rating"),
            color="LightGray",
            flip=False,
            labelHeight=0.1 * 0.6,
        )
        slider.marker.size = (0.03, 0.03)
        clock = core.Clock()
        parameters["myMouse"].clickReset()
        buttons, confidenceRT = parameters["myMouse"].getPressed(getTime=True)
        # The button used to answer the decision is often still down here, and
        # would submit the rating on the first frame past minRatingTime with
        # whatever value the marker happened to hold.
        armed = not any(buttons)

        while True:
            parameters["win"].mouseVisible = False
            trialdur = clock.getTime()
            buttons, confidenceRT = parameters["myMouse"].getPressed(getTime=True)
            buttons, armed = accept_press(buttons, armed)

            # Mouse position (keep in in the rectangle)
            newPos = parameters["myMouse"].getPos()
            if newPos[0] < -0.5:
                newX = -0.5
            elif newPos[0] > 0.5:
                newX = 0.5
            else:
                newX = newPos[0]
            if newPos[1] < 0.1:
                newY = 0.1
            elif newPos[1] > 0.3:
                newY = 0.3
            else:
                newY = newPos[1]
            parameters["myMouse"].setPos((newX, newY))

            # Marker position from the mouse, expressed on whichever scale
            # the session is using rather than assuming 0-100.
            p = newX / 0.5
            slider.markerPos = parameters["confidenceScale"].from_unit((p + 1) / 2)

            # Check if response provided
            if (buttons == [1, 0, 0]) & (trialdur > parameters["minRatingTime"]):
                confidence, confidenceRT, ratingProvided = (
                    slider.markerPos,
                    clock.getTime(),
                    True,
                )
                if confidenceRT is not None:
                    logger.info(
                        f"... Confidence level: {confidence}"
                        + f" with response time {round(confidenceRT, 2)} seconds"
                    )
                # Change marker color after response provided
                slider.marker.color = "green"
                hold(parameters["win"], 0.2, slider, message)
                break
            elif trialdur > parameters["maxRatingTime"]:  # if too long
                ratingProvided = False
                confidenceRT = parameters["myMouse"].clickReset()

                # Text feedback if no rating provided
                message = text(
                    parameters,
                    parameters["texts"]["tooLate"],
                    pos=(0.0, -0.2),
                    color="red",
                )
                hold(parameters["win"], 0.5, message)
                break
            slider.draw()
            message.draw()
            parameters["win"].flip()
    ratingEndTrigger = time.time()
    parameters["win"].flip()

    return confidence, confidenceRT, ratingProvided, ratingEndTrigger
