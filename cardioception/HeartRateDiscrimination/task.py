# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import time
import pickle
from psychopy import visual, event, core, sound
import pandas as pd
import numpy as np
from systole.recording import BrainVisionExG
from systole.detection import oxi_peaks


def run(parameters, win=None, confidenceRating=True, runTutorial=False):
    """Run the Heart Rate Discrimination task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
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
    if win is None:
        win = parameters['win']

    if parameters['setup'] in ['behavioral', 'test']:
        parameters['oxiTask'].setup().read(duration=1)

    # Show tutorial and training trials
    if runTutorial is True:
        tutorial(parameters, win)

    for nTrial, condition, modality in zip(np.arange(0, parameters['nTrials']),
                                           parameters['Conditions'],
                                           parameters['Modality']):

        # Wait for key press if this is the first trial
        if nTrial == 0:
            # Ask the participant to press 'Space' (default) to start
            messageStart = visual.TextStim(win,
                                           height=parameters['textSize'],
                                           text='Press space to continue')
            messageStart.draw()  # Show instructions
            win.flip()
            event.waitKeys(keyList=parameters['startKey'])

        # Is this an interoception or exteroception condition
        if parameters['stairType'] == 'UpDown':
            thisTrial = parameters['stairCase'][modality].next()
            stairCond = thisTrial[1]['label']
            alpha = thisTrial[0]
        elif parameters['stairType'] == 'psi':
            alpha = parameters['stairCase'][modality].next()
            stairCond = condition

        # Start trial
        listenBPM, responseBPM, estimation, estimationRT, confidence,\
            confidenceRT, alpha, accuracy, respProvided, ratingProvided, \
            startTrigger, soundTrigger, responseMadeTrigger,\
            ratingStartTrigger, ratingEndTrigger, endTrigger = trial(
                  parameters, condition, alpha, modality, win=win,
                  confidenceRating=confidenceRating, nTrial=nTrial)

        # Update the staircase
        if parameters['stairType'] == 'UpDown':
            # Check if response if correct
            accuracy = 1 if estimation == condition else 0
            parameters['stairCase'][parameters['Modality']]\
                .addResponse(accuracy)
        elif parameters['stairType'] == 'psi':
            # Check if response is 'More'
            accuracy = 1 if estimation == 'More' else 0
            parameters['stairCase'][parameters['Modality']]\
                .addResponse(accuracy)

            # Store posteriors in list
            parameters[
                'staircaisePosteriors'][parameters[
                    'Modality']].append(
                        parameters['stairCase'][parameters['Modality']]
                        ._psi._probLambda[0, :, :, 0])

            # Save estimated threshold and slope
            estimatedThreshold, estimatedSlope = \
                parameters[
                    'stairCase'][parameters['Modality']].estimateLambda()

        print(f'...Initial BPM: {listenBPM} - Staircase value: {alpha} '
              '- Response: {estimation} ({accuracy})')

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
                                  'EstimationProvided': [respProvided],
                                  'MissedRating': [ratingProvided],
                                  'nTrials': [nTrial],
                                  'EstimatedThreshold': [estimatedThreshold],
                                  'EstimatedSlope': [estimatedSlope],
                                  'StartListening': [startTrigger],
                                  'StartDecision': [soundTrigger],
                                  'ResponseMade': [responseMadeTrigger],
                                  'RatingStart': [ratingStartTrigger],
                                  'RatingEnds': [ratingEndTrigger],
                                  'endTrigger': [endTrigger],
                                  })], ignore_index=True)

        # Save the results at each iteration
        parameters['results_df'].to_csv(
                        parameters['results'] + '/' +
                        parameters['participant'] +
                        parameters['session'] + '.txt')

        # Breaks
        if (nTrial % parameters['nBreaking'] == 0) & (nTrial != 0):
            message = visual.TextStim(
                            win, height=parameters['textSize'],
                            text=('Break. You can rest as long as'
                                  ' you want. Just press SPACE when you want'
                                  ' to resume the task.'))
            message.draw()
            win.flip()
            parameters['oxiTask'].save(
                parameters['results'] + '/' +
                parameters['participant'] + str(nTrial))
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
                parameters['results'] + '/' + parameters['participant'])
        except:
            print('Error while saving as Excel')
        try:
            parameters['stairCase'].saveAsPickle(
                parameters['results'] + '/' + parameters['participant'])
        except:
            print('Error while saving as Pickle')
    elif parameters['stairType'] == 'psi':
        try:
            parameters['stairCase'].saveAsExcel(
                parameters['results'] + '/' + parameters['participant'])
        except:
            print('Error while saving as Excel')
        try:
            parameters['stairCase'].saveAsPickle(
                parameters['results'] + '/' + parameters['participant'])
        except:
            print('Error while saving as Pickle')

    # Save the final results
    print('Saving final results in .txt file...')
    parameters['results_df'].to_csv(
                    parameters['results'] + '/' +
                    parameters['participant'] +
                    parameters['session'] + '_final.txt')

    # Save the final signals file
    print('Saving PPG signal data frame...')
    parameters['signal_df'].to_csv(
        parameters['results'] + '/' +
        parameters['participant'] + '_signal.txt')

    # Save posterios (if relevant)
    if parameters['stairType'] == 'psi':
        print('Saving posterior distributions...')
        for k in set(parameters['Modality']):
            np.save(
                parameters['results'] + '/' +
                parameters['participant'] + k + '_posterior.npy',
                np.array(parameters['staircaisePosteriors'][k]))

    # Save parameters
    print('Saving Parameters in pickle...')
    save_parameter = parameters.copy()
    for k in ['win', 'heartLogo', 'listenLogo', 'listenResponse', 'stairCase',
              'oxiTask', 'myMouse']:
        del save_parameter[k]
    with open(save_parameter['results'] + '/' +
              save_parameter['participant'] + '_parameters.pickle',
              'wb') as handle:
        pickle.dump(save_parameter, handle, protocol=pickle.HIGHEST_PROTOCOL)


def trial(parameters, condition, alpha, modality, win=None,
          confidenceRating=True, feedback=False, nTrial=0):
    """Run one trial.

    Parameters
    ----------
    parameter : dict
        Task parameters.
    condition : str
        Can be 'Higher' or 'Lower'.
    alpha : float
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
    print(f'...Intensity: {alpha} - Modality: {modality}')

    # Restart the trial until participant provide response on time
    confidence, confidenceRT, accuracy, ratingProvided = \
        None, None, None, None

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
                    ip=parameters['BrainVisionIP'],
                    sfreq=1000).read(5)['PLETH']
                signal, peaks = oxi_peaks(signal, sfreq=1000,
                                          clipping=False)
            elif parameters['setup'] in ['behavioral', 'test']:
                # Read PPG
                signal = parameters['oxiTask'].read(
                    duration=5.0).recording[-75*6:]
                signal, peaks = oxi_peaks(signal, sfreq=75)

            # Get actual heart Rate
            bpm = [15]

            bpm = 60000/np.diff(np.where(peaks[-5000:])[0])

            print(f'...bpm: {[round(i) for i in bpm]}')

            # Prevent crash if NaN value
            if np.isnan(bpm).any() or (bpm is None):
                message = visual.TextStim(
                              win, height=parameters['textSize'],
                              text=('Please make sure the oximeter'
                                    'is correctly clipped to your finger.'),
                              color='red')
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
                          text=('Please stay still during the recording'),
                          color='red')
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
        listenFile = \
            os.path.dirname(__file__) + '/sounds/' + str(listenBPM) + '.wav'
        print(f'...loading file (Listen): {listenFile}')

        # Play selected BPM frequency
        listenSound = sound.Sound(listenFile)
        listenSound.play()
        core.wait(listenSound.getDuration() + 0.25)
        listenSound.stop()

    else:
        raise ValueError('Invalid condition')

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
    if parameters['stairType'] == 'UpDown':
        if condition == 'Less':
            alpha = -alpha

    # Check for extreme alpha values, e.g. if alpha changes massively from
    # trial to trial.
    if (listenBPM + alpha) < 15:
        responseBPM = '15.0'
    elif (listenBPM + alpha) > 199:
        responseBPM = '199.0'
    else:
        responseBPM = str(listenBPM + alpha)
    responseFile =\
        os.path.dirname(__file__) + '/sounds/' + responseBPM + '.wav'
    print(f'...loading file (Response): {responseFile}')

    # Play selected BPM frequency
    responseSound = sound.Sound(responseFile)
    parameters['listenLogo'].autoDraw = True
    # Record participant response (+/-)
    message = visual.TextStim(
        win, height=parameters['textSize'], pos=(0, 0.4),
        text=parameters['texts']['Estimation'][modality])
    message.autoDraw = True

    if parameters['device'] == 'keyboard':
        responseText = 'Use DOWN key for lower - UP key for higher.'
    elif parameters['device'] == 'mouse':
        responseText = 'Use LEFT button for lower - RIGHT button for higher.'

    press = visual.TextStim(win, height=parameters['textSize'],
                            text=responseText, pos=(0.0, -0.4))
    press.autoDraw = True

    if parameters['setup'] in ['behavioral', 'test']:
        # Sound trigger
        parameters['oxiTask'].readInWaiting()
        parameters['oxiTask'].channels['Channel_0'][-1] = 2
    soundTrigger = time.time()
    win.flip()

    #####################
    # Esimation Responses
    #####################
    responseMadeTrigger, responseTrigger, respProvided, estimation,\
        estimationRT, accuracy = responseEstimation(
            responseSound, parameters, feedback, condition)
    press.autoDraw = False
    message.autoDraw = False
    parameters['listenLogo'].autoDraw = False

    ###################
    # Confidence Rating
    ###################

    # Record participant confidence
    if (confidenceRating is True) & (respProvided is True):

        if parameters['setup'] in ['behavioral', 'test']:
            # Start trigger
            parameters['oxiTask'].readInWaiting()
            parameters['oxiTask'].channels['Channel_0'][-1] = 4  # Trigger

        # Confidence rating scale
        ratingStartTrigger = time.time()
        confidence, confidenceRT, ratingProvided, ratingEndTrigger = \
            confidenceRatingTask(parameters)
    else:
        ratingStartTrigger, ratingEndTrigger = None, None

    # End trigger
    if parameters['setup'] in ['behavioral', 'test']:
        parameters['oxiTask'].readInWaiting()
        parameters['oxiTask'].channels['Channel_0'][-1] = 5  # Start trigger
    endTrigger = time.time()

    # Store PPG signal
    this_df = None
    if modality == 'Intero':
        # Save physio signal
        this_df = pd.DataFrame({
            'signal': signal,
            'nTrial': pd.Series([nTrial] * len(signal), dtype="category")})

        parameters['signal_df'] = parameters['signal_df'].append(
            this_df, ignore_index=True)

    return listenBPM, responseBPM, estimation, estimationRT, confidence,\
        confidenceRT, alpha, accuracy, respProvided, ratingProvided, \
        startTrigger, soundTrigger, responseMadeTrigger, ratingStartTrigger, \
        ratingEndTrigger, endTrigger


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
        alpha = -20.0 if condition == 'Less' else 20.0

        listenBPM, responseBPM, estimation, estimationRT, confidence,\
            confidenceRT, alpha, accuracy, respProvided, ratingProvided, \
            startTrigger, soundTrigger, responseMadeTrigger,\
            ratingStartTrigger, ratingEndTrigger, endTrigger = trial(
                parameters, condition, alpha, 'Intero', win=win,
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
        alpha = -20.0 if condition == 'Less' else 20.0

        listenBPM, responseBPM, estimation, estimationRT, confidence,\
            confidenceRT, alpha, accuracy, respProvided, ratingProvided, \
            startTrigger, soundTrigger, responseMadeTrigger,\
            ratingStartTrigger, ratingEndTrigger, endTrigger = trial(
                parameters, condition, alpha, 'Intero', win=win,
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


def responseEstimation(this_hr, parameters, feedback, condition, win=None):
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
    print('...starting estimation phase.')

    if win is None:
        win = parameters['win']

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
            parameters['oxiTask'].channels['Channel_0'][-1] = 2  # Trigger
        responseMaideTrigger = time.time()

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

        accuracy = None
        # Initialise response feedback
        less = visual.TextStim(win, height=parameters['textSize'],
                               color='white', text='Less', pos=(-0.2, 0.2))
        more = visual.TextStim(win, height=parameters['textSize'],
                               color='white', text='More', pos=(0.2, 0.2))
        less.draw()
        more.draw()
        win.flip()
        # Stat trigger
        if parameters['setup'] in ['behavioral', 'test']:
            parameters['oxiTask'].readInWaiting()
            parameters['oxiTask'].channels['Channel_0'][-1] = 3  # Trigger
        this_hr.play()
        clock = core.Clock()
        clock.reset()
        parameters['myMouse'].clickReset()
        buttons, estimationRT = parameters['myMouse'].getPressed(getTime=True)
        while True:
            buttons, estimationRT = \
                parameters['myMouse'].getPressed(getTime=True)
            trialdur = clock.getTime()
            if parameters['setup'] in ['behavioral', 'test']:
                parameters['oxiTask'].readInWaiting()
            if buttons == [1, 0, 0]:
                estimationRT = estimationRT[0]
                estimation, respProvided = 'Less', True
                less.color = 'blue'
                less.draw()
                win.flip()
                if parameters['setup'] in ['behavioral', 'test']:
                    parameters['oxiTask'].readInWaiting()
                    parameters['oxiTask'].channels['Channel_0'][-1] = 4
                # Show feedback for .5 seconds if enough time
                remain = parameters['respMax'] - trialdur
                pauseFeedback = 0.5 if (remain > .5) else remain
                core.wait(pauseFeedback)
                break
            elif buttons == [0, 0, 1]:
                estimationRT = estimationRT[-1]
                estimation, respProvided = 'More', True
                more.color = 'blue'
                more.draw()
                win.flip()
                if parameters['setup'] in ['behavioral', 'test']:
                    parameters['oxiTask'].readInWaiting()
                    parameters['oxiTask'].channels['Channel_0'][-1] = 4
                # Show feedback for .5 seconds if enough time
                remain = parameters['respMax'] - trialdur
                pauseFeedback = 0.5 if (remain > .5) else remain
                core.wait(pauseFeedback)
                break
            elif trialdur > parameters['respMax']:  # if too long
                respProvided = False
                estimationRT = None
                break
            else:
                less.draw()
                more.draw()
                win.flip()
        responseMaideTrigger = time.time()
        this_hr.stop()

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

    return responseMaideTrigger, responseTrigger, respProvided, estimation, \
        estimationRT, accuracy


def confidenceRatingTask(parameters, win=None):
    """Confidence rating scale, using keyboard or mouse inputs.
    """
    print('...starting confidence rating.')

    if win is None:
        win = parameters['win']

    # Initialise default values
    confidence, confidenceRT = None, None

    if parameters['device'] == 'keyboard':

        markerStart = np.random.choice(np.arange(parameters['confScale'][0],
                                                 parameters['confScale'][1]))
        ratingScale = visual.RatingScale(
                         win, low=parameters['confScale'][0],
                         high=parameters['confScale'][1],
                         noMouse=True, labels=parameters['labelsRating'],
                         acceptKeys='down', markerStart=markerStart)

        message = visual.TextStim(win, height=parameters['textSize'],
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

        # Use the mouse position to update the slider position
        parameters['myMouse'].setPos((np.random.uniform(-.25, .25), -.4))
        parameters['myMouse'].clickReset()
        message = visual.TextStim(
            win, height=parameters['textSize'], pos=(0, 0.2),
            text=parameters['texts']['Confidence'])
        slider = visual.Slider(
            win=win, name='slider', pos=(0, -0.2), size=(.7, 0.1),
            labels=['low', 'high'], granularity=1, ticks=(1, 100),
            style=('rating'), color='LightGray', flip=False, labelHeight=.1)
        slider.marker.size = (.03, .03)
        clock = core.Clock()
        parameters['myMouse'].clickReset()
        buttons, confidenceRT = parameters['myMouse'].getPressed(getTime=True)
        while True:
            trialdur = clock.getTime()
            buttons, confidenceRT = \
                parameters['myMouse'].getPressed(getTime=True)

            # Mouse position (keep in window if needed)
            newPos = parameters['myMouse'].getPos()
            if newPos[0] < -.5:
                newX = -.5
            elif newPos[0] > .5:
                newX = .5
            else:
                newX = newPos[0]
            if newPos[1] < -0.4:
                newY = -0.4
            elif newPos[1] > 0:
                newY = 0
            else:
                newY = newPos[1]
            parameters['myMouse'].setPos((newX, newY))
            p = newX/0.5
            slider.markerPos = 50 + (p*50)
            if (buttons == [1, 0, 0]) &\
                    (trialdur > parameters['minRatingTime']):
                confidence, confidenceRT, ratingProvided = \
                    slider.markerPos, clock.getTime(), True
                print(f'...Confidence level: {confidence}' +
                      ' with response time {round(confidenceRT)}')
                break
            elif trialdur > parameters['maxRatingTime']:  # if too long
                ratingProvided = False
                confidenceRT = parameters['myMouse'].clickReset()
                break
            slider.draw()
            message.draw()
            win.flip()
    ratingEndTrigger = time.time()
    win.flip()

    return confidence, confidenceRT, ratingProvided, ratingEndTrigger
