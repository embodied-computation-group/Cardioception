# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import pickle
import time
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pkg_resources
from psychopy import core, event, sound, visual
from systole.detection import oxi_peaks
from systole.recording import BrainVisionExG


def run(
    parameters: dict,
    win: Optional[visual.Window] = None,
    confidenceRating: bool = True,
    runTutorial: bool = False,
):
    """Run the Heart Rate Discrimination task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : `psychopy.visual.window`
        Instance of Psychopy window.
    confidenceRating : bool
        Whether the trial show include a confidence rating scale.
    runTutorial : bool
        If `True`, will present a tutorial with 10 training trial with feedback
        and 5 trials with confidence rating.
    """
    if win is None:
        win = parameters["win"]

    if parameters["setup"] in ["behavioral", "test"]:
        parameters["oxiTask"].setup().read(duration=1)
    elif parameters["setup"] == "fMRI":
        messageWaitTrigger = visual.TextStim(
            win,
            height=parameters["textSize"],
            text=parameters["texts"]["textWaitTrigger"],
        )
        messageWaitTrigger.draw()  # Show instructions
        win.flip()
        event.waitKeys(keyList=parameters["fMRItrigger"])
        fMRIStart = time.time()
        parameters["results_df"] = pd.DataFrame({"fMRITrigger": [fMRIStart]})

    # Show tutorial and training trials
    if runTutorial is True:
        tutorial(parameters)

    for nTrial, modality, trialType in zip(
        range(parameters["nTrials"]),
        parameters["Modality"],
        parameters["staircaseType"],
    ):

        # Initialize variable
        estimatedThreshold, estimatedSlope = None, None

        # Wait for key press if this is the first trial
        if nTrial == 0:

            # Ask the participant to press default button to start
            messageStart = visual.TextStim(
                win,
                height=parameters["textSize"],
                text=parameters["texts"]["textTaskStart"],
            )
            press = visual.TextStim(
                win,
                height=parameters["textSize"],
                pos=(0.0, -0.4),
                text=parameters["texts"]["textNext"],
            )
            press.draw()
            messageStart.draw()  # Show instructions
            win.flip()

            waitInput(parameters)

        # Next intensity value
        if trialType == "UpDown":
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
            # Select pseudo-random extrem value based on number
            # of previous catch trial.
            catchIdx = sum(
                parameters["staircaseType"][:nTrial][
                    parameters["Modality"][:nTrial] == modality
                ]
                == "CatchTrial"
            )
            alpha = np.array([-30, 10, -20, 20, -10, 30])[catchIdx % 6]
            stairCond = "CatchTrial"

        # Start trial
        (
            condition,
            listenBPM,
            responseBPM,
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
            win=win,
            confidenceRating=confidenceRating,
            nTrial=nTrial,
        )

        # Check if response is 'More' or 'Less'
        isMore = 1 if decision == "More" else 0
        # Update the UpDown staircase if initialization trial
        if trialType == "UpDown":
            print("... update UpDown staircase.")
            # Update the UpDown staircase
            parameters["stairCase"][modality].addResponse(isMore)
        elif trialType == "psi":
            print("... update psi staircase.")

            # Update the Psi staircase with forced intensity value
            # if impossible BPM was generated
            if listenBPM + alpha < 15:
                parameters["stairCase"][modality].addResponse(isMore, intensity=15)
            elif listenBPM + alpha > 199:
                parameters["stairCase"][modality].addResponse(isMore, intensity=199)
            else:
                parameters["stairCase"][modality].addResponse(isMore)

            # Store posteriors in list for each trials
            parameters["staircaisePosteriors"][modality].append(
                parameters["stairCase"][modality]._psi._probLambda[0, :, :, 0]
            )

            # Save estimated threshold and slope for each trials
            estimatedThreshold, estimatedSlope = parameters["stairCase"][
                modality
            ].estimateLambda()

        print(
            f"...Initial BPM: {listenBPM} - Staircase value: {alpha} "
            f"- Response: {decision} ({isCorrect})"
        )

        # Store results
        parameters["results_df"] = parameters["results_df"].append(
            [
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
                        "Alpha": [alpha],
                        "listenBPM": [listenBPM],
                        "responseBPM": [responseBPM],
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
                )
            ],
            ignore_index=True,
        )

        # Save the results at each iteration
        parameters["results_df"].to_csv(
            parameters["results"]
            + "/"
            + parameters["participant"]
            + parameters["session"]
            + ".txt",
            index=False,
        )

        # Breaks
        if (nTrial % parameters["nBreaking"] == 0) & (nTrial != 0):
            message = visual.TextStim(
                win,
                height=parameters["textSize"],
                text=parameters["texts"]["textBreaks"],
            )
            percRemain = round((nTrial / parameters["nTrials"]) * 100, 2)
            remain = visual.TextStim(
                win,
                height=parameters["textSize"],
                pos=(0.0, 0.2),
                text=f"You completed {percRemain} % of the task.",
            )
            remain.draw()
            message.draw()
            win.flip()
            if parameters["setup"] in ["behavioral", "test"]:
                parameters["oxiTask"].save(
                    parameters["results"]
                    + "/"
                    + parameters["participant"]
                    + str(nTrial)
                )

            # Wait for participant input before continue
            waitInput(parameters)

            # Fixation cross
            fixation = visual.GratingStim(
                win=win, mask="cross", size=0.1, pos=[0, 0], sf=0
            )
            fixation.draw()
            win.flip()

            # Reset recording when ready
            if parameters["setup"] in ["behavioral", "test"]:
                parameters["oxiTask"].setup()
                parameters["oxiTask"].read(duration=1)

    # save data as multiple formats
    try:
        parameters["stairCase"]["Intero"].saveAsPickle(
            parameters["results"] + "/" + parameters["participant"] + "_Intero"
        )
        parameters["stairCase"]["Extero"].saveAsPickle(
            parameters["results"] + "/" + parameters["participant"] + "_Extero"
        )
    except:
        print("Error when saving as Pickle")

    # Save the final results
    print("Saving final results in .txt file...")
    parameters["results_df"].to_csv(
        parameters["results"]
        + "/"
        + parameters["participant"]
        + parameters["session"]
        + "_final.txt",
        index=False,
    )

    # Save the final signals file
    print("Saving PPG signal data frame...")
    parameters["signal_df"].to_csv(
        parameters["results"] + "/" + parameters["participant"] + "_signal.txt",
        index=False,
    )

    # Save posterios (if relevant)
    print("Saving posterior distributions...")
    for k in set(parameters["Modality"]):
        np.save(
            parameters["results"]
            + "/"
            + parameters["participant"]
            + k
            + "_posterior.npy",
            np.array(parameters["staircaisePosteriors"][k]),
        )

    # Save parameters
    print("Saving Parameters in pickle...")
    save_parameter = parameters.copy()
    for k in ["win", "heartLogo", "listenLogo", "stairCase", "oxiTask"]:
        del save_parameter[k]
    if parameters["device"] == "mouse":
        del save_parameter["myMouse"]
    if parameters["setup"] in ["test", "behavioral"]:
        del save_parameter["handSchema"]
        del save_parameter["pulseSchema"]
    with open(
        save_parameter["results"]
        + "/"
        + save_parameter["participant"]
        + "_parameters.pickle",
        "wb",
    ) as handle:
        pickle.dump(save_parameter, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # End of the task
    end = visual.TextStim(
        win,
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text="You have completed the task. Thank you for your participation.",
    )
    end.draw()
    win.flip()
    core.wait(3)


def trial(
    parameters: dict,
    alpha: float,
    modality: str,
    win: Optional[visual.Window] = None,
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
    win :`psychopy.visual.window` or `None`
        Where to draw the task.
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
        The frequency of the tones (exteroceptive condition) or of the heart rate
        (interoceptive condition), expressed in BPM.
    responseBPM : float
        The frequency of thefeebdack tones, expressed in BPM.
    decision : str
        The participant decision. Can be `'up'` (the participant indicates
        the beats are faster than the recorded heart rate) or `'down'` (the
        participant indicates the beats are slower than recorded heart rate).
    decisionRT : float
        The response time from sound start to choice (seconds).
    confidence : int
        If confidenceRating is *True*, the confidence of the participant. The
        range of the scale is defined in `parameters['confScale']`. Default is
        `[1, 7]`.
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
        Was the rating provided (`True`) or not (`False`). If no decision was provided,
        the ratig scale is not proposed and no ratings can be provided.
    startTrigger, soundTrigger, responseMadeTrigger, ratingStartTrigger,\
        ratingEndTrigger, endTrigger : float
        Time stamp of key timepoints inside the trial.
    """
    if win is None:
        win = parameters["win"]

    # Print infos at each trial start
    print(f"Starting trial - Intensity: {alpha} - Modality: {modality}")

    win.mouseVisible = False

    # Restart the trial until participant provide response on time
    confidence, confidenceRT, isCorrect, ratingProvided = None, None, None, False

    # Fixation cross
    fixation = visual.GratingStim(win=win, mask="cross", size=0.1, pos=[0, 0], sf=0)
    fixation.draw()
    win.flip()
    core.wait(0.25)

    keys = event.getKeys()
    if "escape" in keys:
        print("User abort")
        win.close()
        core.quit()

    if modality == "Intero":

        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text="Listen to your Heart",
        )
        messageRecord.draw()

        parameters["heartLogo"].draw()
        win.flip()

        if parameters["setup"] in ["behavioral", "test"]:
            parameters["oxiTask"].channels["Channel_0"][-1] = 3
        startTrigger = time.time()

        # Recording
        while True:
            if parameters["setup"] == "fMRI":
                # Read ExG
                signal = BrainVisionExG(
                    ip=parameters["BrainVisionIP"], sfreq=1000
                ).read(5)["PLETH"]
                signal, peaks = oxi_peaks(signal, sfreq=1000, clipping=False)
            elif parameters["setup"] in ["behavioral", "test"]:
                # Read PPG
                signal = parameters["oxiTask"].read(duration=5.0).recording[-75 * 6 :]
                signal, peaks = oxi_peaks(signal, sfreq=75)

            # Get actual heart Rate
            # Only use the last 5 seconds of the recording
            bpm = 60000 / np.diff(np.where(peaks[-5000:])[0])

            print(f"...bpm: {[round(i) for i in bpm]}")

            # Prevent crash if NaN value
            if np.isnan(bpm).any() or (bpm is None) or (bpm.size == 0):
                message = visual.TextStim(
                    win,
                    height=parameters["textSize"],
                    text=(
                        "Please make sure the oximeter",
                        "is correctly clipped to your finger.",
                    ),
                    color="red",
                )
                message.draw()
                win.flip()
                core.wait(2)

            else:
                # Check for extreme heart rate values, if crosses theshold,
                # hold the task until resolved. Cutoff values determined in
                # parameters to correspond to biologically unlikely values.
                if not (
                    (np.any(bpm < parameters["HRcutOff"][0]))
                    or (np.any(bpm > parameters["HRcutOff"][1]))
                ):
                    listenBPM = round(bpm.mean() * 2) / 2  # Round nearest .5
                    break
                else:
                    message = visual.TextStim(
                        win,
                        height=parameters["textSize"],
                        text=("Please stay still during the recording"),
                        color="red",
                    )
                    message.draw()
                    win.flip()
                    core.wait(2)

    elif modality == "Extero":

        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text="Listen to the beeps",
        )
        messageRecord.draw()

        parameters["listenLogo"].draw()
        win.flip()

        if parameters["setup"] in ["behavioral", "test"]:
            parameters["oxiTask"].channels["Channel_0"][-1] = 3  # Trigger
        startTrigger = time.time()

        # Random selection of HR frequency
        listenBPM = parameters["referenceTone"]

        # Play the corresponding beat file
        listenFile = pkg_resources.resource_filename(
            "cardioception.HRD", f"Sounds/{listenBPM}.wav"
        )
        print(f"...loading file (Listen): {listenFile}")

        # Play selected BPM frequency
        listenSound = sound.Sound(listenFile)
        listenSound.play()
        core.wait(5)
        listenSound.stop()

    else:
        raise ValueError("Invalid modality")

    # Fixation cross
    fixation = visual.GratingStim(win=win, mask="cross", size=0.1, pos=[0, 0], sf=0)
    fixation.draw()
    win.flip()
    core.wait(0.5)

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
    responseFile = pkg_resources.resource_filename(
        "cardioception.HRD", f"Sounds/{responseBPM}.wav"
    )
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
        win,
        height=parameters["textSize"],
        pos=(0, 0.4),
        text=parameters["texts"]["Decision"][modality],
    )
    message.autoDraw = True

    if parameters["device"] == "keyboard":
        responseText = "Use DOWN key for slower - UP key for faster."
    elif parameters["device"] == "mouse":
        responseText = "Use LEFT button for slower - RIGHT button for faster."

    press = visual.TextStim(
        win, height=parameters["textSize"], text=responseText, pos=(0.0, -0.4)
    )
    press.autoDraw = True

    if parameters["setup"] in ["behavioral", "test"]:
        # Sound trigger
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 2
    soundTrigger = time.time()
    win.flip()

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

        if parameters["setup"] in ["behavioral", "test"]:
            # Start trigger
            parameters["oxiTask"].readInWaiting()
            parameters["oxiTask"].channels["Channel_0"][-1] = 4  # Trigger

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

    # End trigger
    if parameters["setup"] in ["behavioral", "test"]:
        parameters["oxiTask"].readInWaiting()
        parameters["oxiTask"].channels["Channel_0"][-1] = 5  # Start trigger
    endTrigger = time.time()

    # Save PPG signal
    if nTrial is not None:  # Not during the tutorial
        if modality == "Intero":
            this_df = None
            # Save physio signal
            this_df = pd.DataFrame(
                {
                    "signal": signal,
                    "nTrial": pd.Series([nTrial] * len(signal), dtype="category"),
                }
            )

            parameters["signal_df"] = parameters["signal_df"].append(
                this_df, ignore_index=True
            )

    return (
        condition,
        listenBPM,
        responseBPM,
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
    if parameters["device"] == "keyboard":
        while True:
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()
            elif parameters["startKey"] in keys:
                break
    elif parameters["device"] == "mouse":
        parameters["myMouse"].clickReset()
        while True:
            buttons = parameters["myMouse"].getPressed()
            if buttons != [0, 0, 0]:
                break
            keys = event.getKeys()
            if "escape" in keys:
                print("User abort")
                parameters["win"].close()
                core.quit()


def tutorial(parameters: dict, win: Optional[visual.Window] = None):
    """Run tutorial before task run.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : instance of `psychopy.visual.Window`
        Where to draw the task.
    """
    if win is None:
        win = parameters["win"]

    # Introduction
    intro = visual.TextStim(
        win, height=parameters["textSize"], text=parameters["Tutorial1"]
    )
    press = visual.TextStim(
        win,
        height=parameters["textSize"],
        pos=(0.0, -0.4),
        text=parameters["texts"]["textNext"],
    )
    intro.draw()
    press.draw()
    win.flip()
    core.wait(1)

    waitInput(parameters)

    # Pusle oximeter tutorial
    if parameters["setup"] in ["test", "behavioral"]:
        pulse1 = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, 0.3),
            text=parameters["pulseTutorial1"],
        )
        press = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, -0.4),
            text=parameters["texts"]["textNext"],
        )
        pulse1.draw()
        parameters["pulseSchema"].draw()
        press.draw()
        win.flip()
        core.wait(1)

        waitInput(parameters)

        # Get finger number
        pulse2 = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, 0.2),
            text=parameters["pulseTutorial2"],
        )
        pulse3 = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, -0.2),
            text=parameters["pulseTutorial3"],
        )
        pulse2.draw()
        pulse3.draw()
        press.draw()
        win.flip()
        core.wait(1)

        waitInput(parameters)

        pulse4 = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, 0.3),
            text=parameters["pulseTutorial4"],
        )
        pulse4.draw()
        parameters["handSchema"].draw()
        win.flip()
        core.wait(1)

        # Record number and save in a .txt file
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
                    "6",
                    "7",
                    "8",
                    "9",
                    "0",
                    "num_1",
                    "num_2",
                    "num_3",
                    "num_4",
                    "num_5",
                    "num_6",
                    "num_7",
                    "num_8",
                    "num_9",
                    "num_0",
                ]
            )
            if key:
                nFinger += [s for s in key[0] if s.isdigit()][0]
                log_df = pd.DataFrame(
                    {
                        "Subject": [parameters["participant"]],
                        "Session": [parameters["session"]],
                        "Finger": [nFinger],
                    }
                )
                log_df.to_csv(
                    parameters["results"]
                    + "/"
                    + parameters["participant"]
                    + parameters["session"]
                    + "_log.txt",
                    index=False,
                )
                core.wait(0.5)
                break

    # Heartrate recording
    recording = visual.TextStim(
        win, height=parameters["textSize"], pos=(0.0, 0.3), text=parameters["Tutorial2"]
    )
    recording.draw()
    parameters["heartLogo"].draw()
    press.draw()
    win.flip()
    core.wait(1)

    waitInput(parameters)

    # Show reponse icon
    listenIcon = visual.TextStim(
        win,
        height=parameters["textSize"],
        pos=(0.0, 0.3),
        text=parameters["Tutorial3_icon"],
    )
    parameters["heartLogo"].draw()
    listenIcon.draw()
    press.draw()
    win.flip()
    core.wait(1)

    waitInput(parameters)

    # Response instructions
    listenResponse = visual.TextStim(
        win,
        height=parameters["textSize"],
        pos=(0.0, 0.0),
        text=parameters["Tutorial3_responses"],
    )
    listenResponse.draw()
    press.draw()
    win.flip()
    core.wait(1)

    waitInput(parameters)

    # Run 10 training trials with feedback
    if parameters["setup"] in ["test", "behavioral"]:
        parameters["oxiTask"].setup().read(duration=2)
    for i in range(parameters["nFeedback"]):

        # Ramdom selection of condition
        condition = np.random.choice(["More", "Less"])
        alpha = -20.0 if condition == "Less" else 20.0

        (
            condition,
            listenBPM,
            responseBPM,
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
            parameters, alpha, "Intero", win=win, feedback=True, confidenceRating=False
        )

    # If extero conditions required, show tutorial.
    if parameters["ExteroCondition"] is True:
        exteroText = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, -0.2),
            text=parameters["Tutorial3bis"],
        )
        exteroText.draw()
        parameters["listenLogo"].draw()
        press.draw()
        win.flip()
        core.wait(1)

        waitInput(parameters)

        exteroResponse = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0.0, 0.0),
            text=parameters["Tutorial3ter"],
        )
        exteroResponse.draw()
        press.draw()
        win.flip()
        core.wait(1)

        waitInput(parameters)

        # Run 10 training trials with feedback
        if parameters["setup"] in ["test", "behavioral"]:
            parameters["oxiTask"].setup().read(duration=2)
        for i in range(parameters["nFeedback"]):

            # Ramdom selection of condition
            condition = np.random.choice(["More", "Less"])
            alpha = -20.0 if condition == "Less" else 20.0

            (
                condition,
                listenBPM,
                responseBPM,
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
                "Extero",
                win=win,
                feedback=True,
                confidenceRating=False,
            )

    # Confidence rating
    confidenceText = visual.TextStim(
        win, height=parameters["textSize"], text=parameters["Tutorial4"]
    )
    confidenceText.draw()
    press.draw()
    win.flip()
    core.wait(1)

    waitInput(parameters)

    if parameters["setup"] in ["test", "behavioral"]:
        parameters["oxiTask"].setup().read(duration=2)

    # Run 5 training trials with confidence rating
    for i in range(parameters["nConfidence"]):

        # Ramdom selection of condition
        modality = np.random.choice(["Intero", "Extero"])
        condition = np.random.choice(["More", "Less"])
        stim_intense = np.random.choice(np.array([1, 10, 30]))
        alpha = -stim_intense if condition == "Less" else stim_intense
        (
            condition,
            listenBPM,
            responseBPM,
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
        ) = trial(parameters, alpha, modality, win=win, confidenceRating=True)

    # End of tutorial
    taskPresentation = visual.TextStim(
        win, height=parameters["textSize"], text=parameters["Tutorial5"]
    )
    taskPresentation.draw()
    press.draw()
    win.flip()
    core.wait(1)
    waitInput(parameters)

    # Task
    taskPresentation = visual.TextStim(
        win, height=parameters["textSize"], text=parameters["Tutorial6"]
    )
    taskPresentation.draw()
    press.draw()
    win.flip()
    core.wait(1)
    waitInput(parameters)


def responseDecision(
    this_hr: sound.Sound,
    parameters: dict,
    feedback: bool,
    condition: str,
    win: Optional[visual.Window] = None,
) -> Tuple[
    float, Optional[float], bool, Optional[str], Optional[float], Optional[bool]
]:
    """Recording response during the decision phase.

    Parameters
    ----------
    this_hr : psychopy sound instance
        The sound .wav file to play.
    parameters : dict
        Parameters dictionnary.
    feedback : bool
        If `True`, provide feedback after decision.
    condition : str
        The trial condition [`'More'` or `'Less'`] used to check is response is
        correct or not.
    win : psychopy window instance.
        The window where to show the task.

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
    print("...starting decision phase.")

    if win is None:
        win = parameters["win"]

    decision, decisionRT, isCorrect = None, None, None
    responseTrigger = time.time()

    if parameters["device"] == "keyboard":
        this_hr.play()
        clock = core.Clock()
        responseKey = event.waitKeys(
            keyList=parameters["allowedKeys"],
            maxWait=parameters["respMax"],
            timeStamped=clock,
        )
        this_hr.stop()

        # End trigger
        if parameters["setup"] in ["behavioral", "test"]:
            parameters["oxiTask"].readInWaiting()
            parameters["oxiTask"].channels["Channel_0"][-1] = 2  # Trigger
        responseMadeTrigger = time.time()

        # Check for response provided by the participant
        if not responseKey:
            respProvided = False
            decision, decisionRT = None, None
            # Record participant response (+/-)
            message = visual.TextStim(
                win, height=parameters["textSize"], text="Too late"
            )
            message.draw()
            win.flip()
            core.wait(1)
        else:
            respProvided = True
            decision = responseKey[0][0]
            decisionRT = responseKey[0][1]

            # Read oximeter
            if parameters["setup"] in ["behavioral", "test"]:
                parameters["oxiTask"].readInWaiting()

            # Feedback
            if feedback is True:
                # Is the answer Correct?
                isCorrect = True if (decision == condition) else False
                if isCorrect is False:
                    acc = visual.TextStim(
                        win, height=parameters["textSize"], color="red", text="False"
                    )
                    acc.draw()
                    win.flip()
                    core.wait(2)
                elif isCorrect is True:
                    acc = visual.TextStim(
                        win,
                        height=parameters["textSize"],
                        color="green",
                        text="Correct",
                    )
                    acc.draw()
                    win.flip()
                    core.wait(2)

    if parameters["device"] == "mouse":

        # Initialise response feedback
        slower = visual.TextStim(
            win,
            height=parameters["textSize"],
            color="white",
            text="Slower",
            pos=(-0.2, 0.2),
        )
        faster = visual.TextStim(
            win,
            height=parameters["textSize"],
            color="white",
            text="Faster",
            pos=(0.2, 0.2),
        )
        slower.draw()
        faster.draw()
        win.flip()
        # Stat trigger
        if parameters["setup"] in ["behavioral", "test"]:
            parameters["oxiTask"].readInWaiting()
            parameters["oxiTask"].channels["Channel_0"][-1] = 3  # Trigger
        this_hr.play()
        clock = core.Clock()
        clock.reset()
        parameters["myMouse"].clickReset()
        buttons, decisionRT = parameters["myMouse"].getPressed(getTime=True)
        while True:
            buttons, decisionRT = parameters["myMouse"].getPressed(getTime=True)
            trialdur = clock.getTime()
            if parameters["setup"] in ["behavioral", "test"]:
                parameters["oxiTask"].readInWaiting()
            if buttons == [1, 0, 0]:
                decisionRT = decisionRT[0]
                decision, respProvided = "Less", True
                slower.color = "blue"
                slower.draw()
                win.flip()
                if parameters["setup"] in ["behavioral", "test"]:
                    parameters["oxiTask"].readInWaiting()
                    parameters["oxiTask"].channels["Channel_0"][-1] = 4
                # Show feedback for .5 seconds if enough time
                remain = parameters["respMax"] - trialdur
                pauseFeedback = 0.5 if (remain > 0.5) else remain
                core.wait(pauseFeedback)
                break
            elif buttons == [0, 0, 1]:
                decisionRT = decisionRT[-1]
                decision, respProvided = "More", True
                faster.color = "blue"
                faster.draw()
                win.flip()
                if parameters["setup"] in ["behavioral", "test"]:
                    parameters["oxiTask"].readInWaiting()
                    parameters["oxiTask"].channels["Channel_0"][-1] = 4
                # Show feedback for .5 seconds if enough time
                remain = parameters["respMax"] - trialdur
                pauseFeedback = 0.5 if (remain > 0.5) else remain
                core.wait(pauseFeedback)
                break
            elif trialdur > parameters["respMax"]:  # if too long
                respProvided = False
                decisionRT = None
                break
            else:
                slower.draw()
                faster.draw()
                win.flip()
        responseMadeTrigger = time.time()
        this_hr.stop()

        # Check for response provided by the participant
        if respProvided is False:
            # Record participant response (+/-)
            message = visual.TextStim(
                win,
                height=parameters["textSize"],
                text="Too late",
                color="red",
                pos=(0.0, -0.2),
            )
            message.draw()
            win.flip()
            core.wait(0.5)
        else:
            # Is the answer Correct?
            isCorrect = True if (decision == condition) else False
            # Feedback
            if feedback is True:
                textFeedback = "False" if isCorrect == 0 else "Correct"
                colorFeedback = "red" if isCorrect == 0 else "green"
                acc = visual.TextStim(
                    win,
                    height=parameters["textSize"],
                    pos=(0.0, -0.2),
                    color=colorFeedback,
                    text=textFeedback,
                )
                acc.draw()
                win.flip()
                core.wait(1)

    return (
        responseMadeTrigger,
        responseTrigger,
        respProvided,
        decision,
        decisionRT,
        isCorrect,
    )


def confidenceRatingTask(
    parameters: dict, win: Optional[visual.Window] = None
) -> Tuple[Optional[float], Optional[float], bool, Optional[float]]:
    """Confidence rating scale, using keyboard or mouse inputs.

    Parameters
    ----------
    parameters : dict
        Parameters dictionnary.
    win : psychopy window instance.
        The window where to show the task.
    """
    print("...starting confidence rating.")

    if win is None:
        win = parameters["win"]

    # Initialise default values
    confidence, confidenceRT = None, None

    if parameters["device"] == "keyboard":

        markerStart = np.random.choice(
            np.arange(parameters["confScale"][0], parameters["confScale"][1])
        )
        ratingScale = visual.RatingScale(
            win,
            low=parameters["confScale"][0],
            high=parameters["confScale"][1],
            noMouse=True,
            labels=parameters["labelsRating"],
            acceptKeys="down",
            markerStart=markerStart,
        )

        message = visual.TextStim(
            win, height=parameters["textSize"], text=parameters["texts"]["Confidence"]
        )

        # Wait for response
        ratingProvided = False
        clock = core.Clock()
        while clock.getTime() < parameters["maxRatingTime"]:
            if not ratingScale.noResponse:
                ratingScale.markerColor = (0, 0, 1)
                if clock.getTime() > parameters["minRatingTime"]:
                    ratingProvided = True
                    break
            ratingScale.draw()
            message.draw()
            win.flip()

        confidence = ratingScale.getRating()
        confidenceRT = ratingScale.getRT()

    elif parameters["device"] == "mouse":

        # Use the mouse position to update the slider position
        # The mouse movement is limited to a rectangle above the Slider
        # To avoid being dragged out of the screen (in case of multi screens)
        # and to avoid interferences with the Slider when clicking.
        win.mouseVisible = False
        parameters["myMouse"].setPos((np.random.uniform(-0.25, 0.25), 0.2))
        parameters["myMouse"].clickReset()
        message = visual.TextStim(
            win,
            height=parameters["textSize"],
            pos=(0, 0.2),
            text=parameters["texts"]["Confidence"],
        )
        slider = visual.Slider(
            win=win,
            name="slider",
            pos=(0, -0.2),
            size=(0.7, 0.1),
            labels=["Guess", "Certain"],
            granularity=1,
            ticks=(0, 100),
            style=("rating"),
            color="LightGray",
            flip=False,
            labelHeight=0.1 * 0.6,
        )
        slider.marker.size = (0.03, 0.03)
        clock = core.Clock()
        parameters["myMouse"].clickReset()
        buttons, confidenceRT = parameters["myMouse"].getPressed(getTime=True)

        while True:
            win.mouseVisible = False
            trialdur = clock.getTime()
            buttons, confidenceRT = parameters["myMouse"].getPressed(getTime=True)

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

            # Update marker position in Slider
            p = newX / 0.5
            slider.markerPos = 50 + (p * 50)

            # Check if response provided
            if (buttons == [1, 0, 0]) & (trialdur > parameters["minRatingTime"]):
                confidence, confidenceRT, ratingProvided = (
                    slider.markerPos,
                    clock.getTime(),
                    True,
                )
                print(
                    f"...Confidence level: {confidence}"
                    + f" with response time {round(confidenceRT)}"
                )
                # Change marker color after response provided
                slider.marker.color = "green"
                slider.draw()
                message.draw()
                win.flip()
                core.wait(0.2)
                break
            elif trialdur > parameters["maxRatingTime"]:  # if too long
                ratingProvided = False
                confidenceRT = parameters["myMouse"].clickReset()

                # Text feedback if no rating provided
                message = visual.TextStim(
                    win,
                    height=parameters["textSize"],
                    text="Too late",
                    color="red",
                    pos=(0.0, -0.2),
                )
                message.draw()
                win.flip()
                core.wait(0.5)
                break
            slider.draw()
            message.draw()
            win.flip()
    ratingEndTrigger = time.time()
    win.flip()

    return confidence, confidenceRT, ratingProvided, ratingEndTrigger
