# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import time
from psychopy import visual, event, core, sound
import pandas as pd
import numpy as np
from cardioception.recording import Oximeter
from cardioception.detection import oxi_peaks


def run(parameters, stairCase=None, win=None, confidenceRating=True,
        runTutorial=False):
    """Run the entire task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    stairCase : `psychopy.data.StairHandler` or
    `psychopy.data.MultiStairHandler` or None
        If *None*, will use default values:
            data.StairHandler(
                        startVal=40, nTrials=parameters['nTrials'], nUp=1,
                        nDown=2, stepSizes=[20, 12, 12, 7, 4, 3, 2, 1],
                        stepType='lin', minVal=1, maxVal=100))
    win : `psychopy.visual.window`
        Instance of Psychopy window.
    confidenceRating : bool
        Whether the trial show include a confidence rating scale.
    tutorial : bool
        If *True*, will present a tutorial with 10 training trial with feedback
        and 5 trials with confidence rating.

    Returns
    -------
    results_df : Pandas DataFrame
        Dataframe containing behavioral results.
    """
    oxiTraining = Oximeter(serial=parameters['serial'], sfreq=75,
                           add_channels=1)

    # Show tutorial and training trials
    if runTutorial is True:
        tutorial(parameters, win, oxiTraining)

    if stairCase is None:
        stairCase = parameters['stairCase']

    oxiTask = Oximeter(serial=parameters['serial'], sfreq=75, add_channels=1)
    oxiTask.setup()
    oxiTask.read(duration=1)

    results_df, i = pd.DataFrame([]), 0  # Final DataFrame and trial count
    for i, condition in enumerate(parameters['Conditions']):

        if i == 0:
            # Ask the participant to press 'Space' (default) to start
            messageStart = visual.TextStim(win,
                                           height=parameters['textSize'],
                                           text='Press space to continue')
            messageStart.draw()  # Show instructions
            win.flip()
            event.waitKeys(keyList=parameters['startKey'])

        try:
            thisTrial = parameters['stairCase'].next()
        except StopIteration:  # we got a StopIteration error
            print('End of the trial')

        # Select the staircase
        stairCond = thisTrial[1]['label']
        intensity = thisTrial[0]

        # Start trial
        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                              parameters, condition, intensity, win=win,
                              oxi=oxiTask, confidenceRating=confidenceRating)

        # Is the answer Correct? Update the staircase model
        if (estimation == 'up') & (condition == 'More'):
            if stairCase is not None:
                parameters['stairCase'].addResponse(1)
            accuracy = 1
        elif (estimation == 'down') & (condition == 'Less'):
            if stairCase is not None:
                parameters['stairCase'].addResponse(1)
            accuracy = 1
        else:
            if stairCase is not None:
                parameters['stairCase'].addResponse(0)
            accuracy = 0

        # Store results
        results_df = results_df.append([
                    pd.DataFrame({'Condition': [condition],
                                  'StairCond': [stairCond],
                                  'Estimation': [estimation],
                                  'EstimationRT': [estimationRT],
                                  'Confidence': [confidence],
                                  'ConfidenceRT': [confidenceRT],
                                  'Alpha': [alpha],
                                  'HR': [average_hr],
                                  'Accuracy': [accuracy],
                                  'Missed': [missed],
                                  'nTrials': [i],
                                  'startTrigger': [startTrigger],
                                  'soundTrigger': [soundTrigger],
                                  'soundTrigger2': [soundTrigger2],
                                  'ratingTrigger': [ratingTrigger],
                                  'endTrigger': [endTrigger],
                                  })], ignore_index=True)

        # Save the results at each iteration
        results_df.to_csv(parameters['results'] + '/' +
                          parameters['subject'] + '.txt')

        # Breaks
        if (i % parameters['nBreaking'] == 0) & (i != 0):
            message = visual.TextStim(
                            win, height=parameters['textSize'],
                            text=('Break. You can rest as long as'
                                  ' you want. Just press SPACE when you want'
                                  ' to resume the task.'))
            message.draw()
            win.flip()
            oxiTask.save(parameters['results'] + '/' + parameters['subject'] +
                         str(i))
            event.waitKeys(keyList=parameters['startKey'])

            # Fixation cross
            fixation = visual.GratingStim(win=win, mask='cross', size=0.1,
                                          pos=[0, 0], sf=0)
            fixation.draw()
            win.flip()

            # Reset recording when ready
            oxiTask.setup()
            oxiTask.read(duration=1)

    # save data as multiple formats
    parameters['stairCase'].saveAsExcel(
        parameters['results'] + '/' + parameters['subject'])
    parameters['stairCase'].saveAsPickle(
        parameters['results'] + '/' + parameters['subject'])

    return results_df


def trial(parameters, condition, intensity, win=None, oxi=None,
          confidenceRating=True, feedback=False):
    """Run one trial.

    Parameters
    ----------
    parameter : dict
        Task parameters.
    condition : str
        Can be 'Higher' or 'Lower'.
    intensity : float
        The intensity of the stimulus, from the staircase procedure.
    stairCase : Instance of staircase handler.
        Staircase procedure used during the task. If `feedback=True`, stairCase
        should be None.
    win :`psychopy.visual.window` or *None*
        Where to draw the task.
    oxi : Instance of `cardioception.recording.Oximeter` or None
        Recording device. Default is *None*.
    confidenceRating : boolean
        If *False*, do not display confidence rating scale.
    feedback : boolean
        If *True*, will provide feedback.

    Returns
    -------
    average_hr : int
        The average heart rate recorded during the rest periode.
    condition : str
        The condition of the trial. Can be 'More' (the beats are faster than
        the heart rate) or 'Less' (the beats are slower than the heart rate).
    estimation : str
        The participant estimation. Can be 'up' (the participant indicates the
        beats are faster than the recorded heart rate) or 'down' (the
        participant indicates the beats are slower than recorded heart rate).
    estimationRT : float
        The response time from sound start to choice.
    confidence : int
        If confidenceRating is *True*, the confidence of the participant. The
        range of the scale is defined in `parameters['confScale']`. Default is
        [1, 7].
    confidenceRT : float
        The response time (RT) for the confidence rating scale.
    alpha : int
        The difference between the true heart rate and the delivered tone BPM.
        Alpha is defined by the stairCase.intensities values and is updated
        on each trial.
    accuracy : int
        .. ACCEPTS: [ 0 | 1 ]
        *0* for incorrect response, *1* for correct responses.
    missed : boolean
        If *True*, the trial did not terminate correctly (e.g., participant was
        too slow to provide the estimation or the confidence).
    """
    # Restart the trial until participant provide response on time
    confidence, confidenceRT, accuracy, ratingTrigger = None, None, None, None

    # Fixation cross
    fixation = visual.GratingStim(win=win, mask='cross', size=0.1,
                                  pos=[0, 0], sf=0)
    fixation.draw()
    win.flip()
    core.wait(0.25)

    ###########
    # Recording
    ###########
    messageRecord = visual.TextStim(win,
                                    height=parameters['textSize'],
                                    pos=(0.0, 0.2),
                                    text='Listen to your Heart')
    messageRecord.draw()

    parameters['heartLogo'].draw()
    win.flip()

    oxi.channels['Channel_0'][-1] = 3  # Start trigger
    startTrigger = time.time()

    # Recording
    while True:

        # Read PPG
        oxi.read(duration=5.0)

        # Get actual heart Rate
        signal, peaks = oxi_peaks(oxi.recording)
        average_hr = int(60000/np.diff(np.where(peaks[-5000:])[0]).mean())

        # Prevent crash if NaN value
        if np.isnan(average_hr):
            message = visual.TextStim(win, height=parameters['textSize'],
                                      text=('Please make sure the oximeter'
                                      'is correctly clipped to your finger.'))
            message.draw()
            win.flip()
            core.wait(2)

        else:
            # Check for extreme heart rate values, if crosses theshold, hold
            # the task until resolved. Cutoff values determined in parameters
            # to correspond to biologically unlikely values.
            if ((average_hr > parameters['HRcutOff'][0]) &
               (average_hr < parameters['HRcutOff'][1])):
                break
            else:
                message = visual.TextStim(win, height=parameters['textSize'],
                                          text=('Please do not move your hand'
                                                ' during the recording'))
                message.draw()
                win.flip()
                core.wait(2)

    # Fixation cross
    fixation = visual.GratingStim(win=win, mask='cross', size=0.1,
                                  pos=[0, 0], sf=0)
    fixation.draw()
    win.flip()
    core.wait(0.25)

    #######
    # Sound
    #######

    # Random selection of the condition (for training trials)
    if condition is None:
        condition = np.random.choice(['More', 'Less'])

    # Generate actual stimulus frequency
    alpha = int(intensity)
    if condition == 'Less':
        alpha = -alpha

    # Check for extreme alpha values, e.g. if alpha changes massively from
    # trial to trial.
    if (average_hr + alpha) < 15:
        hr = '15'
    elif (average_hr + alpha) > 199:
        hr = '199'
    else:
        hr = str(average_hr + alpha)
    file = parameters['path'] + '/sounds/' + hr + '.wav'

    # Play selected BPM frequency
    this_hr = sound.Sound(file)
    parameters['listenLogo'].draw()
    # Record participant response (+/-)
    message = visual.TextStim(win, height=parameters['textSize'],
                              text=parameters['texts']['Estimation'])
    message.draw()

    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Use DOWN key for lower, UP key for higher.',
                            pos=(0.0, -0.4))
    press.draw()

    # Sound trigger
    oxi.readInWaiting()
    oxi.channels['Channel_0'][-1] = 2
    soundTrigger = time.time()

    win.flip()
    this_hr.play()

    ###########
    # Responses
    ###########

    clock = core.Clock()
    responseKey = event.waitKeys(keyList=parameters['allowedKeys'],
                                 maxWait=parameters['respMax'],
                                 timeStamped=clock)
    this_hr.stop()

    # End trigger
    oxi.readInWaiting()
    oxi.channels['Channel_0'][-1] = 2  # Start trigger
    soundTrigger2 = time.time()

    # Check for response provided by the participant
    if not responseKey:
        missed = True
        estimation, estimationRT = None, None
        # Record participant response (+/-)
        message = visual.TextStim(win, height=parameters['textSize'],
                                  text='Too late')
        message.draw()
        win.flip()
        core.wait(1)
    else:
        missed = False
        estimation = responseKey[0][0]
        estimationRT = responseKey[0][1]

        # Read oximeter
        oxi.readInWaiting()

        # Feedback
        if feedback is True:
            # Is the answer Correct?
            if (estimation == 'up') & (condition == 'More'):
                accuracy = 1
            elif (estimation == 'down') & (condition == 'Less'):
                accuracy = 1
            else:
                accuracy = 0
            if accuracy == 0:
                acc = visual.TextStim(win,
                                      height=parameters['textSize'],
                                      color='red',
                                      text='False')
                acc.draw()
                win.flip()
                core.wait(2)
            elif accuracy == 1:
                acc = visual.TextStim(win,
                                      height=parameters['textSize'],
                                      color='green',
                                      text='Correct')
                acc.draw()
                win.flip()
                core.wait(2)
        else:

            ###################
            # Confidence rating
            ###################

            # Record participant confidence
            if confidenceRating is True:

                # Start trigger
                oxi.readInWaiting()
                oxi.channels['Channel_0'][-1] = 4  # Start trigger
                ratingTrigger = time.time()

                markerStart = np.random.choice(
                                np.arange(parameters['confScale'][0],
                                          parameters['confScale'][1]))
                ratingScale = visual.RatingScale(
                                 win,
                                 low=parameters['confScale'][0],
                                 high=parameters['confScale'][1],
                                 noMouse=True,
                                 labels=parameters['labelsRating'],
                                 acceptKeys='down',
                                 markerStart=markerStart)

                message = visual.TextStim(
                            win,
                            height=parameters['textSize'],
                            text=parameters['texts']['Confidence'])

                # Wait for response
                clock = core.Clock()
                while clock.getTime() < parameters['maxRatingTime']:
                    if not ratingScale.noResponse:
                        ratingScale.markerColor = (0, 0, 1)
                        if clock.getTime() > parameters['minRatingTime']:
                            break
                    ratingScale.draw()
                    message.draw()
                    win.flip()

                confidence = ratingScale.getRating()
                confidenceRT = ratingScale.getRT()

    # End trigger
    oxi.readInWaiting()
    oxi.channels['Channel_0'][-1] = 5  # Start trigger
    endTrigger = time.time()

    return average_hr, estimation, estimationRT, confidence,\
        confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
        soundTrigger2, ratingTrigger, endTrigger


def tutorial(parameters, win, oxi=None):
    """Run tutorial before task run.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : instance of `psychopy.visual.Window`
        Where to draw the task.
    oxi : instance of `cardioception.recording.Oximeter` or None
        Recording device. Default is *None*.
    """
    # Introduction
    intro = visual.TextStim(win,
                            height=parameters['textSize'],
                            text=parameters['Tutorial1'])
    intro.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()

    # Heartrate recording
    recording = visual.TextStim(win,
                                height=parameters['textSize'],
                                pos=(0.0, 0.2),
                                text=parameters['Tutorial2'])
    recording.draw()
    parameters['heartLogo'].draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()

    # Listen and response
    listenResponse = visual.TextStim(win,
                                     height=parameters['textSize'],
                                     pos=(0.0, 0.2),
                                     text=parameters['Tutorial3'])
    listenResponse.draw()
    parameters['listenLogo'].draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()

    # Run 10 training trials with feedback
    oxi.setup()
    oxi.read(duration=2)
    for i in range(parameters['nFeedback']):

        # Ramdom selection of condition
        condition = np.random.choice(['More', 'Less'])
        intensity = 20

        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                                parameters, condition, intensity, win=win,
                                oxi=oxi, feedback=True, confidenceRating=False)

    # Confidence rating
    confidence = visual.TextStim(win,
                                 height=parameters['textSize'],
                                 text=parameters['Tutorial4'])
    confidence.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()

    oxi.setup()
    oxi.read(duration=2)
    # Run 5 training trials with confidence rating
    for i in range(parameters['nConfidence']):

        # Ramdom selection of condition
        condition = np.random.choice(['More', 'Less'])
        intensity = 20

        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                                parameters, condition, intensity, win=win,
                                oxi=oxi, confidenceRating=True)

    # Task
    taskPresentation = visual.TextStim(win,
                                       height=parameters['textSize'],
                                       text=parameters['Tutorial5'])
    taskPresentation.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()
