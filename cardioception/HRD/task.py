# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import pickle
import time
from collections import deque
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from systole.detection import ppg_peaks

from .._present import accept_press, hold  # noqa: F401
from .._resources import resource_filename
from .._triggers import fire

#: Rate ppg_peaks resamples the raw oximeter signal to, used to time the
#: samples written to the signal file.
PPG_SFREQ = 1000


def _save_session(parameters: dict, nTrial: int) -> None:
    """Write everything the session produced.

    Called from a finally clause so an abort or a crash still saves.
    """
    paths = parameters["paths"]

    print("Saving final results in .txt file...")
    parameters["results_df"].to_csv(paths.path("final"), index=False)

    print("Saving PPG signal data frame...")
    parameters["signal_df"].to_csv(paths.path("signal"), index=False)

    parameters["oxiTask"].save(paths.path(f"ppg-{nTrial}-end"))

    print("Saving posterior distributions...")
    for k in set(parameters["Modality"]):
        np.save(
            paths.path(f"posterior-{k}", ext="npy"),
            np.array(parameters["staircaisePosteriors"][k]),
        )

    print("Saving Parameters in pickle...")
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
    from psychopy import visual

    # Initialization of the Pulse Oximeter
    parameters["oxiTask"].setup().read(duration=1)

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
                messageStart = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["textTaskStart"],
                )
                press = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    pos=(0.0, -0.4),
                    text=parameters["texts"]["textNext"],
                )
                press.draw()
                messageStart.draw()  # Show instructions
                parameters["win"].flip()

                waitInput(parameters)

            # Next intensity value
            if trialType == "updown":
                print("... load UpDown staircase.")
                thisTrial = parameters["stairCase"][modality].next()
                stairCond = thisTrial[1]["label"]
                alpha = thisTrial[0]
            elif trialType == "psi":
                print("... load psi staircase.")
                alpha = parameters["stairCase"][modality].next()
                stairCond = "psi"
            elif trialType == "CatchTrial":
                print("... load catch trial.")
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
            parameters["oxiTask"].channels["Channel_0"][-1] = 1  # Trigger
            fire(parameters, "trialStart")

            # Start trial
            (
                condition,
                listenBPM,
                responseBPM,
                quality,
                decision,
                decisionRT,
                confidence,
                confidenceRT,
                alpha,
                isCorrect,
                respProvided,
                ratingProvided,
                startTrigger,
                soundTrigger,
                responseMadeTrigger,
                ratingStartTrigger,
                ratingEndTrigger,
                endTrigger,
            ) = trial(
                parameters,
                alpha,
                modality,
                confidenceRating=confidenceRating,
                nTrial=nTrial,
            )

            # A missed trial must not reach the staircase: decision is None,
            # which used to collapse to isMore = 0 and enter the posterior as
            # a "Less" the participant never gave.
            if not respProvided:
                canRepresent = (
                    onMissedTrial == "represent"
                    and thisItem["attempt"] + 1 < maxRepresentations
                )
                if canRepresent:
                    queue.append({**thisItem, "attempt": thisItem["attempt"] + 1})
                    print(
                        f"... no response, re-queued "
                        f"(attempt {thisItem['attempt'] + 2} of {maxRepresentations})."
                    )
                else:
                    print("... no response, trial not repeated.")

            if respProvided:
                # Check if response is 'More' or 'Less'
                isMore = 1 if decision == "More" else 0

                if trialType == "updown":
                    print("... update UpDown staircase.")
                    parameters["stairCase"][modality].addResponse(isMore)

                elif trialType == "psi":
                    print("... update psi staircase.")

                    # Update the Psi staircase with forced intensity value
                    # if impossible BPM was generated
                    if listenBPM + alpha < 15:
                        parameters["stairCase"][modality].addResponse(
                            isMore, intensity=15
                        )
                    elif listenBPM + alpha > 199:
                        parameters["stairCase"][modality].addResponse(
                            isMore, intensity=199
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

            print(
                f"... Initial BPM: {listenBPM} - Staircase value: {alpha} "
                f"- Response: {decision} ({isCorrect})"
            )

            # Confidence on 0-1 so sessions run on different scales stay
            # comparable, and the scale definition on every row so the file can
            # be read without the parameters pickle.
            scale = parameters["confidenceScale"]
            scaleColumns = scale.describe()
            confidenceUnit = None if confidence is None else scale.to_unit(confidence)

            # Store results
            parameters["results_df"] = pd.concat(
                [
                    parameters["results_df"],
                    pd.DataFrame(
                        {
                            "TrialType": [trialType],
                            "Condition": [condition],
                            "Modality": [modality],
                            "StairCond": [stairCond],
                            "Decision": [decision],
                            "DecisionRT": [decisionRT],
                            "Confidence": [confidence],
                            "ConfidenceRT": [confidenceRT],
                            "ConfidenceUnit": [confidenceUnit],
                            "Device": [parameters["device"]],
                            **{k: [v] for k, v in scaleColumns.items()},
                            "Alpha": [alpha],
                            "listenBPM": [listenBPM],
                            "responseBPM": [responseBPM],
                            "nRepresentations": [thisItem["attempt"]],
                            **{k: [v] for k, v in quality.items()},
                            "ResponseCorrect": [isCorrect],
                            "DecisionProvided": [respProvided],
                            "RatingProvided": [ratingProvided],
                            "nTrials": [nTrial],
                            "EstimatedThreshold": [estimatedThreshold],
                            "EstimatedSlope": [estimatedSlope],
                            "StartListening": [startTrigger],
                            "StartDecision": [soundTrigger],
                            "ResponseMade": [responseMadeTrigger],
                            "RatingStart": [ratingStartTrigger],
                            "RatingEnds": [ratingEndTrigger],
                            "endTrigger": [endTrigger],
                        }
                    ),
                ],
                ignore_index=True,
            )

            # Save the results at each iteration
            parameters["results_df"].to_csv(
                parameters["paths"].path("behaviour"), index=False
            )

            nTrial += 1

            # Breaks
            if parameters["nBreaking"] and nTrial % parameters["nBreaking"] == 0:
                message = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["textBreaks"],
                )
                percRemain = round(min(nTrial / nPlanned, 1.0) * 100, 2)
                remain = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    pos=(0.0, 0.2),
                    text=f" ---- {percRemain} % ---- ",
                )
                remain.draw()
                message.draw()
                parameters["win"].flip()
                parameters["oxiTask"].save(parameters["paths"].path(f"ppg-{nTrial}"))

                # Wait for participant input before continue
                waitInput(parameters)

                # Fixation cross
                fixation = visual.GratingStim(
                    win=parameters["win"], mask="cross", size=0.1, pos=[0, 0], sf=0
                )
                fixation.draw()
                parameters["win"].flip()

                # Reset recording when ready
                parameters["oxiTask"].setup()
                parameters["oxiTask"].read(duration=1)
    finally:
        _save_session(parameters, nTrial)

    # End of the task
    end = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text=parameters["texts"]["done"],
    )
    hold(parameters["win"], 3, end)


def trial(
    parameters: dict,
    alpha: float,
    modality: str,
    confidenceRating: bool = True,
    feedback: bool = False,
    nTrial: Optional[int] = None,
) -> Tuple[
    str,
    float,
    float,
    Optional[str],
    Optional[float],
    Optional[float],
    Optional[float],
    float,
    Optional[bool],
    bool,
    bool,
    float,
    float,
    float,
    Optional[float],
    Optional[float],
    float,
]:
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
    condition : str
        The trial condition, can be `'Higher'` or `'Lower'` depending on the
        alpha value.
    listenBPM : float
        The frequency of the tones (exteroceptive condition) or of the heart
        rate (interoceptive condition), expressed in BPM.
    responseBPM : float
        The frequency of thefeebdack tones, expressed in BPM.
    decision : str
        The participant decision. Can be `'up'` (the participant indicates
        the beats are faster than the recorded heart rate) or `'down'` (the
        participant indicates the beats are slower than recorded heart rate).
    decisionRT : float
        The response time from sound start to choice (seconds).
    confidence : int
        If confidenceRating is *True*, the confidence of the participant, on
        the scale given by `parameters['confidenceScale']`.
    confidenceRT : float
        The response time (RT) for the confidence rating scale.
    alpha : int
        The difference between the true heart rate and the delivered tone BPM.
        Alpha is defined by the stairCase.intensities values and is updated
        on each trial.
    isCorrect : int
        `0` for incorrect response, `1` for correct responses. Note that this
        value is not feeded to the staircase when using the (Yes/No) version
        of the task, but instead will check if the response is `'More'` or not.
    respProvided : bool
        Was the decision provided (`True`) or not (`False`).
    ratingProvided : bool
        Was the rating provided (`True`) or not (`False`). If no decision was
        provided, the ratig scale is not proposed and no ratings can be provided.
    startTrigger, soundTrigger, responseMadeTrigger, ratingStartTrigger,\
        ratingEndTrigger, endTrigger : float
        Time stamp of key timepoints inside the trial.
    """
    from psychopy import core, event, sound, visual

    # Print infos at each trial start
    print(f"Starting trial - Intensity: {alpha} - Modality: {modality}")

    parameters["win"].mouseVisible = False

    # Restart the trial until participant provide response on time
    confidence, confidenceRT, isCorrect, ratingProvided = None, None, None, False

    # Fixation cross
    fixation = visual.GratingStim(
        win=parameters["win"], mask="cross", size=0.1, pos=[0, 0], sf=0
    )
    hold(
        parameters["win"],
        parameters["rng"].uniform(parameters["isi"][0], parameters["isi"][1]),
        fixation,
    )

    keys = event.getKeys()
    if "escape" in keys:
        print("User abort")
        parameters["win"].close()
        core.quit()

    droppedAtStart = parameters["win"].nDroppedFrames
    heartRateAttempts, heartRateAccepted = None, None

    if modality == "Intero":
        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["textHeartListening"],
        )
        messageRecord.draw()

        # Start recording trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 2  # Trigger
        fire(parameters, "listeningStart")

        parameters["heartLogo"].draw()
        parameters["win"].flip()

        startTrigger = time.time()

        # Recording.
        #
        # Bounded and escapable. Unbounded before, with no escape poll inside
        # it, so one artefactual interval could hold a participant on this
        # screen indefinitely: np.any rejects the whole window on a single bad
        # value. On giving up it takes the window anyway and flags the trial,
        # which is recoverable, unlike a session that never advances.
        maxAttempts = parameters.get("maxHeartRateAttempts", 10)
        listenBPM = None
        attempt = 0
        for attempt in range(maxAttempts):
            if "escape" in event.getKeys(keyList=["escape"]):
                print("User abort")
                parameters["win"].close()
                core.quit()

            # Read the raw PPG signal from the pulse oximeter
            # You can adapt these line to work with a different setup provided that
            # it can measure and create the new variable `bpm` (the average beats per
            # minute over the 5 seconds of recording).
            signal = (
                parameters["oxiTask"].read(duration=5.0).recording[-75 * 6 :]  # noqa
            )
            signal, peaks = ppg_peaks(
                signal, sfreq=75, new_sfreq=PPG_SFREQ, clipping=True
            )

            recordedAt = time.time()

            # Get actual heart Rate
            # Only use the last 5 seconds of the recording
            ibi = np.diff(np.where(peaks[-5000:])[0])
            bpm = 60000 / ibi

            # # for Nonin3231USB
            # # Only use the last 5 seconds of the recording
            # bpm =  pd.Series(parameters["oxiTask"].read(duration=5.0).bpm)[-5:]
            # # use bpm as signal, Nonin3231USB gives no raw signal
            # signal = bpm

            print(f"... bpm: {[round(i) for i in bpm]}")

            # Prevent crash if NaN value
            if np.isnan(bpm).any() or (bpm is None) or (bpm.size == 0):
                message = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["checkOximeter"],
                    color="red",
                )
                hold(parameters["win"], 2, message)

            else:
                # Check for extreme heart rate values, if crosses theshold,
                # hold the task until resolved. Cutoff values determined in
                # parameters to correspond to biologically unlikely values.
                if not (
                    (np.any(bpm < parameters["HRcutOff"][0]))
                    or (np.any(bpm > parameters["HRcutOff"][1]))
                ):
                    # Rate over the window, not the average of the
                    # per-beat rates. Averaging 60000/IBI overestimates by
                    # Jensen's inequality, measured at +0.33 BPM on real PPG,
                    # so the tone was reliably faster than the heart it was
                    # meant to match. Round to the nearest .5 for the sound
                    # files.
                    listenBPM = round((60000 / ibi.mean()) * 2) / 2
                    listenBPM_arithmetic = round(bpm.mean() * 2) / 2
                    break
                else:
                    message = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        text=parameters["texts"]["stayStill"],
                        color="red",
                    )
                    hold(parameters["win"], 2, message)

        heartRateAttempts = attempt + 1
        heartRateAccepted = listenBPM is not None

        if listenBPM is None:
            # Out of attempts. Use the last window regardless and mark the
            # trial, rather than holding the session on this screen.
            print(f"... no acceptable heart rate after {maxAttempts} attempts.")
            usable = bpm.size and not np.isnan(bpm).all()
            listenBPM = (
                round((60000 / np.nanmean(ibi)) * 2) / 2
                if usable
                else float(np.mean(parameters["HRcutOff"]))
            )
            listenBPM_arithmetic = (
                round(float(np.nanmean(bpm)) * 2) / 2
                if usable
                else float(np.mean(parameters["HRcutOff"]))
            )

    elif modality == "Extero":
        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["textToneListening"],
        )
        messageRecord.draw()

        # Start recording trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 2  # Trigger
        fire(parameters, "listeningStart")

        parameters["listenLogo"].draw()
        parameters["win"].flip()

        startTrigger = time.time()

        # Random selection of HR frequency
        listenBPM = parameters["rng"].choice(np.arange(40, 100, 0.5))
        # No recording on this modality, so the two averages coincide.
        listenBPM_arithmetic = listenBPM

        # Play the corresponding beat file
        listenFile = resource_filename("cardioception.HRD", f"Sounds/{listenBPM}.wav")
        print(f"...loading file (Listen): {listenFile}")

        # 5 s matches the interoceptive recording window, so both
        # modalities give the same listening time. Do not derive it from
        # the rate. Parameterised only so tests can shorten it.
        listenSound = sound.Sound(listenFile)
        listenSound.play()
        hold(
            parameters["win"],
            parameters.get("listeningDuration", 5.0),
            messageRecord,
            parameters["listenLogo"],
        )
        listenSound.stop()

    else:
        raise ValueError("Invalid modality")

    # Fixation cross
    fixation = visual.GratingStim(
        win=parameters["win"], mask="cross", size=0.1, pos=[0, 0], sf=0
    )
    hold(parameters["win"], 0.5, fixation)

    #######
    # Sound
    #######

    # Generate actual stimulus frequency
    condition = "Less" if alpha < 0 else "More"

    # Check for extreme alpha values, e.g. if alpha changes massively from
    # trial to trial.
    if (listenBPM + alpha) < 15:
        responseBPM = 15.0
    elif (listenBPM + alpha) > 199:
        responseBPM = 199.0
    else:
        responseBPM = listenBPM + alpha
    responseFile = resource_filename("cardioception.HRD", f"Sounds/{responseBPM}.wav")
    print(f"...loading file (Response): {responseFile}")

    # Play selected BPM frequency
    responseSound = sound.Sound(responseFile)
    if modality == "Intero":
        parameters["heartLogo"].autoDraw = True
    elif modality == "Extero":
        parameters["listenLogo"].autoDraw = True
    else:
        raise ValueError("Invalid modality provided")
    # Record participant response (+/-)
    message = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0, 0.4),
        text=parameters["texts"]["Decision"][modality],
    )
    message.autoDraw = True

    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["responseText"],
        pos=(0.0, -0.4),
    )
    press.autoDraw = True

    # Sound trigger
    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = 3
    fire(parameters, "decisionStart")
    soundTrigger = time.time()
    parameters["win"].flip()

    #####################
    # Esimation Responses
    #####################
    (
        responseMadeTrigger,
        responseTrigger,
        respProvided,
        decision,
        decisionRT,
        isCorrect,
    ) = responseDecision(responseSound, parameters, feedback, condition)
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
        parameters["oxiTask"].channels["Channel_0"][-1] = 4  # Trigger
        fire(parameters, "confidenceStart")

        # Confidence rating scale
        ratingStartTrigger: Optional[float] = time.time()
        (
            confidence,
            confidenceRT,
            ratingProvided,
            ratingEndTrigger,
        ) = confidenceRatingTask(parameters)
    else:
        ratingStartTrigger, ratingEndTrigger = None, None

    # Confidence rating end trigger
    parameters["oxiTask"].readInWaiting()
    parameters["oxiTask"].channels["Channel_0"][-1] = 5
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

    return (
        condition,
        listenBPM,
        responseBPM,
        quality,
        decision,
        decisionRT,
        confidence,
        confidenceRT,
        alpha,
        isCorrect,
        respProvided,
        ratingProvided,
        startTrigger,
        soundTrigger,
        responseMadeTrigger,
        ratingStartTrigger,
        ratingEndTrigger,
        endTrigger,
    )


def waitInput(parameters: dict):
    """Wait for participant input before continue"""

    from psychopy import core, event

    # A synthetic participant advances at once. Whatever was drawn before this
    # call has already been drawn and flipped, so the screen is still exercised.
    if parameters.get("autopilot") is not None:
        parameters["autopilot"].advance()
        return

    if parameters["device"] == "keyboard":
        # Without this, a key pressed earlier is still buffered and dismisses
        # this screen before it is read.
        event.clearEvents(eventType="keyboard")
        while True:
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
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
            buttons, armed = accept_press(mouse.getPressed(), armed)
            if any(buttons):
                break
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()


def tutorial(parameters: dict):
    """Run tutorial before task run.

    Parameters
    ----------
    parameters : dict
        Task parameters.

    """

    from psychopy import event, visual

    # Introduction
    intro = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial1"],
    )
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, -0.4),
        text=parameters["texts"]["textNext"],
    )
    hold(parameters["win"], 1, intro, press)

    waitInput(parameters)

    # Pusle oximeter tutorial
    pulse1 = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["pulseTutorial1"],
    )
    press = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, -0.4),
        text=parameters["texts"]["textNext"],
    )
    hold(parameters["win"], 1, pulse1, parameters["pulseSchema"], press)

    waitInput(parameters)

    # Get finger number - Skip this part for the danish_children version (empty string)
    if parameters["texts"]["pulseTutorial2"]:
        pulse2 = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["texts"]["pulseTutorial2"],
        )
        pulse3 = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, -0.2),
            text=parameters["texts"]["pulseTutorial3"],
        )
        hold(parameters["win"], 1, pulse2, pulse3, press)

        waitInput(parameters)

    pulse4 = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["pulseTutorial4"],
    )
    hold(parameters["win"], 1, pulse4, parameters["handSchema"])

    # Record number
    nFinger = ""
    while True:
        # Record new key
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
            nFinger += [s for s in key[0] if s.isdigit()][0]

            # Save the finger number in the task parameters dictionary
            parameters["nFinger"] = nFinger

            hold(parameters["win"], 0.5, pulse4, parameters["handSchema"])
            break

    # Heartrate recording
    recording = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["Tutorial2"],
    )
    hold(parameters["win"], 1, recording, parameters["heartLogo"], press)

    waitInput(parameters)

    # Show reponse icon
    listenIcon = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["texts"]["Tutorial3_icon"],
    )
    hold(parameters["win"], 1, parameters["heartLogo"], listenIcon, press)

    waitInput(parameters)

    # Response instructions
    listenResponse = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text=parameters["texts"]["Tutorial3_responses"],
    )
    hold(parameters["win"], 1, listenResponse, press)

    waitInput(parameters)

    # Run training trials with feedback
    parameters["oxiTask"].setup().read(duration=2)
    for i in range(parameters["nFeedback"]):
        # Ramdom selection of condition
        condition = parameters["rng"].choice(["More", "Less"])
        alpha = -20.0 if condition == "Less" else 20.0

        _ = trial(
            parameters,
            alpha,
            "Intero",
            feedback=True,
            confidenceRating=False,
        )

    # If extero conditions required, show tutorial.
    if parameters["ExteroCondition"] is True:
        exteroText = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, -0.2),
            text=parameters["texts"]["Tutorial3bis"],
        )
        hold(parameters["win"], 1, exteroText, parameters["listenLogo"], press)

        waitInput(parameters)

        exteroResponse = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0.0, 0.0),
            text=parameters["texts"]["Tutorial3ter"],
        )
        hold(parameters["win"], 1, exteroResponse, press)

        waitInput(parameters)

        # Run 10 training trials with feedback
        parameters["oxiTask"].setup().read(duration=2)
        for i in range(parameters["nFeedback"]):
            # Ramdom selection of condition
            condition = parameters["rng"].choice(["More", "Less"])
            alpha = -20.0 if condition == "Less" else 20.0

            _ = trial(
                parameters,
                alpha,
                "Extero",
                feedback=True,
                confidenceRating=False,
            )

    ###################
    # Confidence rating
    ###################
    confidenceText = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial4"],
    )
    hold(parameters["win"], 1, confidenceText, press)

    waitInput(parameters)

    parameters["oxiTask"].setup().read(duration=2)

    # Run n training trials with confidence rating
    for i in range(parameters["nConfidence"]):
        modality = "Intero"
        condition = parameters["rng"].choice(["More", "Less"])
        stim_intense = parameters["rng"].choice(np.array([1, 10, 30]))
        alpha = -stim_intense if condition == "Less" else stim_intense
        _ = trial(parameters, alpha, modality, confidenceRating=True)

    # If extero conditions required, show tutorial.
    if parameters["ExteroCondition"] is True:
        # Run n training trials with confidence rating
        for i in range(parameters["nConfidence"]):
            modality = "Extero"
            condition = parameters["rng"].choice(["More", "Less"])
            stim_intense = parameters["rng"].choice(np.array([1, 10, 30]))
            alpha = -stim_intense if condition == "Less" else stim_intense
            _ = trial(
                parameters,
                alpha,
                modality,
                confidenceRating=True,
            )

    #################
    # End of tutorial
    #################
    taskPresentation = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial5"],
    )
    hold(parameters["win"], 1, taskPresentation, press)
    waitInput(parameters)

    # Task
    taskPresentation = visual.TextStim(
        parameters["win"],
        height=parameters["textSize"],
        text=parameters["texts"]["Tutorial6"],
    )
    hold(parameters["win"], 1, taskPresentation, press)
    waitInput(parameters)


def responseDecision(
    this_hr,
    parameters: dict,
    feedback: bool,
    condition: str,
) -> Tuple[
    float, Optional[float], bool, Optional[str], Optional[float], Optional[bool]
]:
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
    responseTrigger : float
        Time stamp of response start.
    respProvided : bool
        `True` if the response was provided, `False` otherwise.
    decision : str or None
        The decision made ('Higher', 'Lower' or None)
    decisionRT : float
        Decision response time (seconds).
    isCorrect : bool or None
        `True` if the response provided was correct, `False` otherwise.

    """

    from psychopy import core, event, visual

    print("...starting decision phase.")

    decision, decisionRT, isCorrect = None, None, None
    responseTrigger = time.time()

    if parameters["device"] == "keyboard":
        this_hr.play()
        clock = core.Clock()
        pilot = parameters.get("autopilot")
        if pilot is not None:
            # Same shape event.waitKeys returns: [[key, rt]] or None.
            answer = pilot.decide(
                condition,
                parameters["allowedKeys"],
                max_wait=parameters["respMax"],
            )
            responseKey = [list(answer)] if answer is not None else None
        else:
            responseKey = event.waitKeys(
                keyList=parameters["allowedKeys"],
                maxWait=parameters["respMax"],
                timeStamped=clock,
            )
        this_hr.stop()

        responseMadeTrigger = time.time()

        # Check for response provided by the participant
        if not responseKey:
            respProvided = False
            decision, decisionRT = None, None
            # Record participant response (+/-)
            message = visual.TextStim(
                parameters["win"],
                height=parameters["textSize"],
                text=parameters["texts"]["tooLate"],
            )
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

            # Read oximeter
            parameters["oxiTask"].readInWaiting()

            # Feedback
            if feedback is True:
                if isCorrect is False:
                    acc = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        color="red",
                        text="False",
                    )
                    hold(parameters["win"], 2, acc)
                elif isCorrect is True:
                    acc = visual.TextStim(
                        parameters["win"],
                        height=parameters["textSize"],
                        color="green",
                        text="Correct",
                    )
                    hold(parameters["win"], 2, acc)

    if parameters["device"] == "mouse":
        # Initialise response feedback
        slower = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            color="white",
            text=parameters["texts"]["slower"],
            pos=(-0.2, 0.2),
        )
        faster = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            color="white",
            text=parameters["texts"]["faster"],
            pos=(0.2, 0.2),
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
            message = visual.TextStim(
                parameters["win"],
                height=parameters["textSize"],
                text=parameters["texts"]["tooLate"],
                color="red",
                pos=(0.0, -0.2),
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
                acc = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    pos=(0.0, -0.2),
                    color=colorFeedback,
                    text=textFeedback,
                )
                hold(parameters["win"], 1, acc)

    return (
        responseMadeTrigger,
        responseTrigger,
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

    print("...starting confidence rating.")

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
        message = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0, 0.2),
            text=parameters["texts"]["Confidence"],
        )

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
            print(
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
        message = visual.TextStim(
            parameters["win"],
            height=parameters["textSize"],
            pos=(0, 0.2),
            text=parameters["texts"]["Confidence"],
        )
        slider = visual.Slider(
            win=parameters["win"],
            name="slider",
            pos=(0, -0.2),
            size=(0.7, 0.1),
            labels=parameters["confidenceScale"].labels,
            granularity=parameters["confidenceScale"].granularity,
            ticks=parameters["confidenceScale"].bounds,
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
                    print(
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
                message = visual.TextStim(
                    parameters["win"],
                    height=parameters["textSize"],
                    text=parameters["texts"]["tooLate"],
                    color="red",
                    pos=(0.0, -0.2),
                )
                hold(parameters["win"], 0.5, message)
                break
            slider.draw()
            message.draw()
            parameters["win"].flip()
    ratingEndTrigger = time.time()
    parameters["win"].flip()

    return confidence, confidenceRT, ratingProvided, ratingEndTrigger
