# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import time
from psychopy import visual, event, core, sound
import pandas as pd
import numpy as np
from systole.detection import oxi_peaks
from systole.recording import BrainVisionExG


def waitMouseClic(parameters):
    mouse = event.Mouse(win=parameters['win'])
    while True:
        bt = mouse.getPressed()
        if bt == [1, 0, 0]: 
            break

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
    # Show tutorial and training trials
    if runTutorial is True:
        tutorial(parameters, win)

    if stairCase is None:
        stairCase = parameters['stairCase']

    results_df, i = pd.DataFrame([]), 0  # Final DataFrame and trial count
    for i, condition, modality in zip(np.arange(0, parameters['nTrials']),
                                      parameters['Conditions'],
                                      parameters['Modality']):

        # Wait for key press if this is the first trial
        if i == 0:
            # Ask the participant to press LEFT button (default) to start
            messageStart = visual.TextStim(
                                    win,
                                    height=parameters['textSize'],
                                    text='Press LEFT button to continue')
            messageStart.draw()  # Show instructions
            win.flip()
            waitMouseClic(parameters)

        # Is this an interoception or exteroception condition
        if modality == 'Intero':
            if parameters['stairType'] == 'UpDown':
                thisTrial = parameters['stairCase'].next()
                stairCond = thisTrial[1]['label']
                intensity = thisTrial[0]
            elif parameters['stairType'] == 'psi':
                intensity = parameters['stairCase'][condition].next()
                stairCond = condition
        elif modality == 'Extero':
            if parameters['stairType'] == 'UpDown':
                thisTrial = parameters['exteroStairCase'].next()
                stairCond = thisTrial[1]['label']
                intensity = thisTrial[0]
            elif parameters['stairType'] == 'psi':
                intensity = parameters['exteroStairCase'][condition].next()
                stairCond = condition

        # Start trial
        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                          parameters, condition, intensity, modality, win=win,
                          confidenceRating=confidenceRating)

        # Is the answer Correct? Update the staircase model
        if (estimation == 'up') & (condition == 'More'):
            if stairCase is not None:
                if parameters['stairType'] == 'UpDown':
                    parameters['stairCase'].addResponse(1)
                elif parameters['stairType'] == 'psi':
                    parameters['stairCase'][condition].addResponse(1)
            accuracy = 1
        elif (estimation == 'down') & (condition == 'Less'):
            if stairCase is not None:
                if parameters['stairType'] == 'UpDown':
                    parameters['stairCase'].addResponse(1)
                elif parameters['stairType'] == 'psi':
                    parameters['stairCase'][condition].addResponse(1)
            accuracy = 1
        else:
            if stairCase is not None:
                if parameters['stairType'] == 'UpDown':
                    parameters['stairCase'].addResponse(0)
                elif parameters['stairType'] == 'psi':
                    parameters['stairCase'][condition].addResponse(0)
            accuracy = 0

        # Store results
        results_df = results_df.append([
                    pd.DataFrame({'Condition': [condition],
                                  'Modallity': [modality],
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
                            text=('Break. You can rest as long as you want.'
                                  'Just press LEFT button when you want'
                                  ' to resume the task.'))
            message.draw()
            win.flip()
            waitMouseClic(parameters)

            # Fixation cross
            fixation = visual.GratingStim(win=win, mask='cross', size=0.1,
                                          pos=[0, 0], sf=0)
            fixation.draw()
            win.flip()

    # save data as multiple formats
    if parameters['stairType'] == 'psi':
        parameters['stairCase'].saveAsExcel(
            parameters['results'] + '/' + parameters['subject'])
        parameters['stairCase'].saveAsPickle(
            parameters['results'] + '/' + parameters['subject'])
    elif parameters['stairType'] == 'UpDown':
        parameters['stairCase']['low'].saveAsExcel(
            parameters['results'] + '/' + parameters['subject'])
        parameters['stairCase']['low'].saveAsPickle(
            parameters['results'] + '/' + parameters['subject'])
        parameters['stairCase']['high'].saveAsExcel(
            parameters['results'] + '/' + parameters['subject'])
        parameters['stairCase']['high'].saveAsPickle(
            parameters['results'] + '/' + parameters['subject'])

    return results_df


def trial(parameters, condition, intensity, modality, win=None,
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
    modality : str
        The modality, can be 'Intero' or 'Extro' if an exteroceptive control
        condition has been added.
    stairCase : Instance of staircase handler.
        Staircase procedure used during the task. If `feedback=True`, stairCase
        should be None.
    win :`psychopy.visual.window` or *None*
        Where to draw the task.
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

    if modality == 'Intero':

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

        startTrigger = time.time()

        # Recording
        while True:

            # Read ExG
            recording = BrainVisionExG(ip='10.60.88.162').read(5)
            segment = np.array(recording['PLETH'])   
            signal, peaks = oxi_peaks(segment, sfreq=parameters['sfreq'],
                                      clipping=False)

            # Get actual heart Rate
            average_hr = int((60000/np.diff(np.where(peaks)[0])).mean())
            #average_hr = 60
            #print(average_hr)

            # Prevent crash if NaN value
            if np.isnan(average_hr):
                message = visual.TextStim(
                              win, height=parameters['textSize'],
                              text=('Please make sure the signal'
                                    'is correctly recorded.'))
                message.draw()
                win.flip()
                core.wait(2)

            else:
                # Check for extreme heart rate values, if crosses theshold,
                # hold the task until resolved. Cutoff values determined in
                # parameters to correspond to biologically unlikely values.
                if ((average_hr > parameters['HRcutOff'][0]) &
                   (average_hr < parameters['HRcutOff'][1])):
                    break
                else:
                    message = visual.TextStim(
                          win, height=parameters['textSize'],
                          text=('Please do not move your hand'
                                ' during the recording'))
                    message.draw()
                    win.flip()
                    core.wait(2)

    elif modality == 'Extero':

        ###########
        # Recording
        ###########
        messageRecord = visual.TextStim(win,
                                        height=parameters['textSize'],
                                        pos=(0.0, 0.2),
                                        text='Listen to the tones')
        messageRecord.draw()

        parameters['listenLogo'].draw()
        win.flip()

        startTrigger = time.time()

        # Random selection of HR frequency
        average_hr = np.random.choice(np.arange(40, 100))

        # Play the corresponding beat file
        file = parameters['path'] + '/sounds/' + str(average_hr) + '.wav'

        # Play selected BPM frequency
        this_hr = sound.Sound(file)
        this_hr.play()
        core.wait(this_hr.getDuration() + 0.5)
        this_hr.stop()

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
    # When using the psi method, the stimulus intensity is encoded in real
    # value and should not be modified
    alpha = int(intensity)
    if condition == 'Less':
        if parameters['stairType'] != 'psi':
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
    soundTrigger = time.time()

    win.flip()
    this_hr.play()

    ###########
    # Responses
    ###########

    clock = core.Clock()
    mouse = event.Mouse(win=parameters['win'])
    while clock.getTime() < parameters['respMax']:
        bt, t = mouse.getPressed(getTime=True)
        if (bt == [1, 0, 0]) or (bt == [0, 0, 1]): 
            break
    this_hr.stop()

    # End trigger
    soundTrigger2 = time.time()

    # Check for response provided by the participant
    if bt == [0, 0, 0]:
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
        if bt == [1, 0, 0]:
            estimation = 'Less'
        elif bt == [0, 0, 1]:
            estimation = 'More'
        estimationRT = t

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
                ratingTrigger = time.time()

#                markerStart = np.random.choice(
#                                np.arange(parameters['confScale'][0],
#                                          parameters['confScale'][1]))
                
#                ratingScale = visual.Slider(
#                        win, ticks=(1, 100),
#                        labels=('Not at all confident', 'Extremely confident'),
#                        granularity=1, color='white')
#                
#                while not ratingScale.rating:
#                    ratingScale.draw()
#                    win.flip()
#
#                message = visual.TextStim(
#                            win,
#                            height=parameters['textSize'],
#                            text=parameters['texts']['Confidence'])
#
#                confidence = ratingScale.getRating()
#                confidenceRT = ratingScale.getRT()
                confidence, confidenceRT = 1, 2

    # End trigger
    endTrigger = time.time()

    return average_hr, estimation, estimationRT, confidence,\
        confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
        soundTrigger2, ratingTrigger, endTrigger


def tutorial(parameters, win):
    """Run tutorial before task run.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : instance of `psychopy.visual.Window`
        Where to draw the task.
    """
    # Introduction
    intro = visual.TextStim(win,
                            height=parameters['textSize'],
                            text=parameters['Tutorial1'])
    intro.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press LEFT button to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    waitMouseClic(parameters)
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
                            text='Please press LEFT button to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    waitMouseClic(parameters)
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
                            text='Please press LEFT button to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    waitMouseClic(parameters)
    win.flip()

    # Run 10 training trials with feedback
    for i in range(parameters['nFeedback']):

        # Ramdom selection of condition
        condition = np.random.choice(['More', 'Less'])
        intensity = 20

        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                        parameters, condition, intensity, 'Intero', win=win,
                        feedback=True, confidenceRating=False)

    # Confidence rating
    confidence = visual.TextStim(win,
                                 height=parameters['textSize'],
                                 text=parameters['Tutorial4'])
    confidence.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press LEFT button to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    waitMouseClic(parameters)
    win.flip()

    # Run 5 training trials with confidence rating
    for i in range(parameters['nConfidence']):

        # Ramdom selection of condition
        condition = np.random.choice(['More', 'Less'])
        intensity = 20

        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                        parameters, condition, intensity, 'Intero', win=win,
                        confidenceRating=True)

    # Task
    taskPresentation = visual.TextStim(win,
                                       height=parameters['textSize'],
                                       text=parameters['Tutorial5'])
    taskPresentation.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press LEFT button to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    waitMouseClic(parameters)
    win.flip()
