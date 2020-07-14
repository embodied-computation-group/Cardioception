# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import time
import pickle
from psychopy import visual, event, core, sound
import pandas as pd
import numpy as np
from systole.recording import BrainVisionExG
from systole.detection import oxi_peaks


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
    if parameters['setup'] in ['behavioral', 'test']:
        parameters['oxiTask'].setup().read(duration=1)

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
            # Ask the participant to press 'Space' (default) to start
            messageStart = visual.TextStim(win,
                                           height=parameters['textSize'],
                                           text='Press space to continue')
            messageStart.draw()  # Show instructions
            win.flip()
            event.waitKeys(keyList=parameters['startKey'])

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
        listenBPM, responseBPM, estimation, estimationRT, confidence, \
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
        parameters['results_df'] = parameters['results_df'].append([
                    pd.DataFrame({'Condition': [condition],
                                  'Modallity': [modality],
                                  'StairCond': [stairCond],
                                  'Estimation': [estimation],
                                  'EstimationRT': [estimationRT],
                                  'Confidence': [confidence],
                                  'ConfidenceRT': [confidenceRT],
                                  'Alpha': [alpha],
                                  'listenBPM': [listenBPM],
                                  'responseBPM': [responseBPM],
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
        parameters['results_df'].to_csv(
                        parameters['results'] + '/' +
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
            parameters['oxiTask'].save(
                parameters['results'] + '/' + parameters['subject'] + str(i))
            event.waitKeys(keyList=parameters['startKey'])

            # Fixation cross
            fixation = visual.GratingStim(win=win, mask='cross', size=0.1,
                                          pos=[0, 0], sf=0)
            fixation.draw()
            win.flip()

            # Reset recording when ready
            parameters['oxiTask'].setup()
            parameters['oxiTask'].read(duration=1)

    # save data as multiple formats
    if parameters['stairType'] == 'UpDown':
        try:
            parameters['stairCase'].saveAsExcel(
                parameters['results'] + '/' + parameters['subject'])
        except:
            print('Error while saving as Excel')
        try:
            parameters['stairCase'].saveAsPickle(
                parameters['results'] + '/' + parameters['subject'])
        except:
            print('Error while saving as Pickle')
    elif parameters['stairType'] == 'psi':
        try:
            parameters['stairCase'].saveAsExcel(
                parameters['results'] + '/' + parameters['subject'])
        except:
            print('Error while saving as Excel')
        try:
            parameters['stairCase'].saveAsPickle(
                parameters['results'] + '/' + parameters['subject'])
        except:
            print('Error while saving as Pickle')

    # Save the final results file
    parameters['results_df'].to_csv(
        parameters['results'] + '/' +
        parameters['subject'] + '.txt')

    # Save the final signals file
    parameters['signal_df'].to_csv(
        parameters['results'] + '/' +
        parameters['subject'] + '_signal.txt')

    # Save the whole parameters dictionary
    with open('filename.pickle', 'wb') as handle:
        pickle.dump(parameters, handle, protocol=pickle.HIGHEST_PROTOCOL)


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
    print(f'Starting trial - Condition {condition}')
    print(f'...Intensity: {intensity} - Modality: {modality}')

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

        parameters['oxiTask'].channels['Channel_0'][-1] = 3  # Start trigger
        startTrigger = time.time()

        # Recording
        while True:

            if parameters['setup'] == 'fMRI':
                # Read ExG
                signal = BrainVisionExG(
                    ip=parameters['BrainVisionIP'], sfreq=1000).read(5)['PLETH']
                signal, peaks = oxi_peaks(signal, sfreq=1000,
                                          clipping=False)
            elif parameters['setup'] in ['behavioral', 'test']:
                # Read PPG
                parameters['oxiTask'].read(duration=5.0)

            # Get actual heart Rate
            bpm = [15]
            if parameters['setup'] in ['behavioral', 'test']:
                signal, peaks = \
                    oxi_peaks(parameters['oxiTask'].recording[-75*6:])

            signal, peaks = oxi_peaks(parameters['oxiTask'].recording)
            bpm = 60000/np.diff(np.where(peaks[-5000:])[0])
            print(f'...bpm: {[round(i) for i in bpm]}')

            # Prevent crash if NaN value
            if np.isnan(bpm).any() or (bpm is None):
                message = visual.TextStim(
                              win, height=parameters['textSize'],
                              text=('Please make sure the oximeter'
                                    'is correctly clipped to your finger.'))
                message.draw()
                win.flip()
                core.wait(2)

            else:
                # Check for extreme heart rate values, if crosses theshold,
                # hold the task until resolved. Cutoff values determined in
                # parameters to correspond to biologically unlikely values.
                if not ((np.any(bpm < parameters['HRcutOff'][0])) or
                        (np.any(bpm > parameters['HRcutOff'][1]))):
                    listenBPM = round(bpm.mean() * 2) / 2  # Round nearest .5
                    break
                else:
                    message = visual.TextStim(
                          win, height=parameters['textSize'],
                          text=('Please stay still during the recording'))
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

        if parameters['setup'] in ['behavioral', 'test']:
            parameters['oxiTask'].channels['Channel_0'][-1] = 3  # Trigger
        startTrigger = time.time()

        # Random selection of HR frequency
        listenBPM = np.random.choice(np.arange(40, 100, 0.5))

        # Play the corresponding beat file
        file = parameters['path'] + '/sounds/' + str(listenBPM) + '.wav'
        print(f'...loading file: {file}')

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
    if (listenBPM + alpha) < 15:
        responseBPM = '15.0'
    elif (listenBPM + alpha) > 199:
        responseBPM = '199.0'
    else:
        responseBPM = str(listenBPM + alpha)
    file = parameters['path'] + '/sounds/' + responseBPM + '.wav'
    print(f'...loading file: {file}')

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

    if parameters['setup'] in ['behavioral', 'test']:
        # Sound trigger
        parameters['oxiTask'].readInWaiting()
        parameters['oxiTask'].channels['Channel_0'][-1] = 2
    soundTrigger = time.time()

    win.flip()

    #####################
    # Esimation Responses
    #####################
    soundTrigger2, responseTrigger, missedEstimation, estimation,\
        estimationRT = responseEstimation(this_hr, parameters, win, feedback,
                                          condition)

    ###################
    # Confidence Rating
    ###################

    # Record participant confidence
    if confidenceRating is True:

        if parameters['setup'] in ['behavioral', 'test']:
            # Start trigger
            parameters['oxiTask'].readInWaiting()
            parameters['oxiTask'].channels['Channel_0'][-1] = 4  # Trigger

        # Confidence rating scale
        ratingTrigger = time.time()
        confidence, confidenceRT, missedRating = \
            confidenceRatingTask(parameters, win)

    # End trigger
    if parameters['setup'] in ['behavioral', 'test']:
        parameters['oxiTask'].readInWaiting()
        parameters['oxiTask'].channels['Channel_0'][-1] = 5  # Start trigger
    endTrigger = time.time()

    return listenBPM, responseBPM, estimation, estimationRT, confidence,\
        confidenceRT, alpha, accuracy, missedEstimation, missedRating, \
        startTrigger, soundTrigger, soundTrigger2, ratingTrigger, endTrigger


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
    parameters['oxiTask'].setup().read(duration=2)
    for i in range(parameters['nFeedback']):

        # Ramdom selection of condition
        condition = np.random.choice(['More', 'Less'])
        intensity = 20.0

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
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()

    parameters['oxiTask'].setup().read(duration=2)
    # Run 5 training trials with confidence rating
    for i in range(parameters['nConfidence']):

        # Ramdom selection of condition
        condition = np.random.choice(['More', 'Less'])
        intensity = 20.0

        average_hr, estimation, estimationRT, confidence, \
            confidenceRT, alpha, accuracy, missed, startTrigger, soundTrigger, \
            soundTrigger2, ratingTrigger, endTrigger = trial(
                        parameters, condition, intensity, 'intero', win=win,
                        confidenceRating=True)

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


def responseEstimation(this_hr, parameters, win, feedback, condition):
    """ Recording response during the estimation BPM.

    Parameters
    ----------
    this_hr : psychopy sound instance
        The sound .wav file to play.
    parameters : dict
        Parameters dictionnary.
    win : psychopy window instance.
        The window where to show the task.
    feedback : bool
        If *True*, provide feedback after decision.
    condition : str
        The trial condition ['More' or 'Less'] used to check response accuracy.
    """
    estimation, estimationRT = None, None
    responseTrigger = time.time()

    if parameters['device'] == 'keyboard':
        this_hr.play()
        clock = core.Clock()
        responseKey = event.waitKeys(keyList=parameters['allowedKeys'],
                                     maxWait=parameters['respMax'],
                                     timeStamped=clock)
        this_hr.stop()

        # End trigger
        if parameters['setup'] in ['behavioral', 'test']:
            parameters['oxiTask'].readInWaiting()
            parameters['oxiTask'].channels['Channel_0'][-1] = 2  # Start trigger
        soundTrigger2 = time.time()

        # Check for response provided by the participant
        if not responseKey:
            respProvided = False
            estimation, estimationRT = None, None
            # Record participant response (+/-)
            message = visual.TextStim(win, height=parameters['textSize'],
                                      text='Too late')
            message.draw()
            win.flip()
            core.wait(1)
        else:
            respProvided = True
            estimation = responseKey[0][0]
            estimationRT = responseKey[0][1]

            # Read oximeter
            if parameters['setup'] in ['behavioral', 'test']:
                parameters['oxiTask'].readInWaiting()

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
                    acc = visual.TextStim(win, height=parameters['textSize'],
                                          color='red', text='False')
                    acc.draw()
                    win.flip()
                    core.wait(2)
                elif accuracy == 1:
                    acc = visual.TextStim(win, height=parameters['textSize'],
                                          color='green', text='Correct')
                    acc.draw()
                    win.flip()
                    core.wait(2)

    if parameters['device'] == 'mouse':

        this_hr.play()
        clock = core.Clock()
        clock.reset()
        parameters['myMouse'].clickReset()
        buttons, estimationRT = parameters['myMouse'].getPressed(getTime=True)
        while buttons == [0, 0, 0]:
            buttons, estimationRT = \
                parameters['myMouse'].getPressed(getTime=True)
            trialdur = clock.getTime()
            if buttons == [1, 0, 0]:
                estimation, colorLess, respProvided = 'Less', 'blue', True
                break
            elif buttons == [0, 0, 1]:
                estimation, colorMore, respProvided = 'More', 'blue', True
                break
            elif trialdur > parameters['respMax']:  # if subject takes too long
                respProvided = False
                estimationRT = parameters['myMouse'].clickReset()
                break
        this_hr.stop()

        # End trigger
        if parameters['setup'] in ['behavioral', 'test']:
            parameters['oxiTask'].readInWaiting()
            parameters['oxiTask'].channels['Channel_0'][-1] = 2  # Trigger

        soundTrigger2 = time.time()

        # Check for response provided by the participant
        if respProvided is False:
            # Record participant response (+/-)
            message = visual.TextStim(win, height=parameters['textSize'],
                                      text='Too late')
            message.draw()
            win.flip()
            core.wait(1)
        else:

            if parameters['setup'] in ['behavioral', 'test']:
                # Read oximeter
                parameters['oxiTask'].readInWaiting()

            # Feedback
            if feedback is True:
                # Is the answer Correct?
                if (estimation == 'More') & (condition == 'More'):
                    accuracy = 1
                elif (estimation == 'Less') & (condition == 'Less'):
                    accuracy = 1
                else:
                    accuracy = 0
                if accuracy == 0:
                    acc = visual.TextStim(win, height=parameters['textSize'],
                                          color='red', text='False')
                    acc.draw()
                    win.flip()
                    core.wait(2)
                elif accuracy == 1:
                    acc = visual.TextStim(win, height=parameters['textSize'],
                                          color='green', text='Correct')
                    acc.draw()
                    win.flip()
                    core.wait(2)

    return soundTrigger2, responseTrigger, respProvided, estimation, \
        estimationRT


def confidenceRatingTask(parameters, win):
    """Confidence rating scale, using keyboard or mouse inputs.
    """
    if parameters['device'] == 'keyboard':

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
        respProvided = False
        clock = core.Clock()
        while clock.getTime() < parameters['maxRatingTime']:
            if not ratingScale.noResponse:
                ratingScale.markerColor = (0, 0, 1)
                if clock.getTime() > parameters['minRatingTime']:
                    respProvided = True
                    break
            ratingScale.draw()
            message.draw()
            win.flip()

        confidence = ratingScale.getRating()
        confidenceRT = ratingScale.getRT()

    elif parameters['device'] == 'mouse':

        parameters['myMouse'].setPos((0, -.4))
        parameters['myMouse'].clickReset()

        slider = visual.Slider(
            win=win, name='slider', size=(8.0, 0.5), pos=(0, -0.4),
            labels=['low', 'high'], granularity=0.1, ticks=(1, 100),
            style=('rating',), color='LightGray', font='HelveticaBold',
            flip=False, labelHeight=.5)

        clock = core.Clock()
        parameters['myMouse'].clickReset()
        buttons, confidenceRT = parameters['myMouse'].getPressed(getTime=True)
        while buttons == [0, 0, 0]:
            trialdur = clock.getTime()
            buttons, confidenceRT = \
                parameters['myMouse'].getPressed(getTime=True)

            # Mouse position
            newPos = parameters['myMouse'].getPos()
            p = newPos[0]/5
            slider.markerPos = 50 + (p*50)
            slider.draw()
            if buttons == [1, 0, 0]:
                confidence, confidenceRT, respProvided = \
                    p, clock.getTime(), True
                break
            elif trialdur > parameters['minRatingTime']:  # if too long
                respProvided = False
                confidenceRT = parameters['myMouse'].clickReset()
                break
            win.flip()

    return confidence, confidenceRT, respProvided
