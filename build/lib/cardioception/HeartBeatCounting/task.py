# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from psychopy import visual, event
import pandas as pd
import numpy as np
from cardioception.recording import Oximeter


def sequence(parameters, win=None):
    """Run the entire task sequence.
    """
    if win is None:
        win = parameters['win']

    results_df = pd.DataFrame([])
    for condition, duration, nTrial in zip(
            parameters['Conditions'], parameters['Times'],
            range(0, len(parameters['Conditions']))):

        nCount, confidence, confidenceRT = trial(condition, duration, nTrial,
                                                 parameters, win)

        # Store results in a DataFrame
        results_df = results_df.append(
                    pd.DataFrame({'nTrial': nTrial,
                                  'Reported': nCount,
                                  'Confidence': confidence,
                                  'ConfidenceRT': confidenceRT},
                                 index=[0]))

    # Save results
    results_df.to_csv(parameters['results'] + parameters['subjectID'] + '.txt')


def trial(condition, duration, nTrial, parameters, win):
    """Run one trial.

    Parameters
    ----------
    condition : str
        The trial condition, can be `Rest` or `Count`.
    duration : int
        The lenght of the recording (in seconds).
    ntrial : int
        Trial number.
    parameters : dict
        Task parameters.
    win : psychopy window
        Instance of Psychopy window.

    Returns
    -------

    """
    # Ask the participant to press 'Space' (default) to start the trial
    messageStart = visual.TextStim(win, units='height', height=0.1,
                                   text='Press space to continue')
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'], maxWait=8)
    win.flip()

    oxi = Oximeter(serial=parameters['serial'], sfreq=75)
    oxi.setup()
    oxi.read(duration=2)

    # Show instructions
    message = visual.TextStim(win, text=parameters[condition], units='height',
                              height=0.05)
    message.draw()
    win.flip()

    # Wait for a beat to start the task
    oxi.waitBeat()

    # Sound signaling trial start
    parameters['note'].play()
    parameters['note'].stop()
    oxi.readInWaiting()
    oxi.triggers[-1] = 3

    # Record for a desired time length
    oxi.read(duration=duration)

    # Sound signaling trial stop
    parameters['note'].play()
    parameters['note'].stop()
    oxi.triggers[-1] = 3

    # Hide instructions
    win.flip()

    # Save recording as np array
    np.save(parameters['path'] + '/Results/' + parameters['subjectID']
            + '_' + str(nTrial),
            np.asarray(oxi.recording))

    ###############################
    # Record participant estimation
    ###############################

    # Ask the participant to press 'Space' (default) to start the trial
    messageCount = visual.TextStim(win, units='height', height=0.1, 
                                   pos=(0.2, 0), text=parameters['nCount'])
    messageCount.draw()
    win.flip()
    
    nCounts = ''
    while True:
        
        # Record new key
        key = event.waitKeys()
        if key[0] == 'backspace':
            if nCounts:
                nCounts = nCounts[:-1]
        elif key[0] == 'return':
            break
        elif key[0][:3] == 'num':
            nCounts += key[0][-1]

        # Show the text on the screen
        recordedText = visual.TextStim(win, units='height', height=0.1,
                                       text=nCounts)
        recordedText.draw()
        messageCount.draw()
        win.flip()
    nCounts = int(nCounts)

    ##############
    # Rating scale
    ##############
    if condition == 'Count':
        if parameters['rating'] is True:
            ratingScale = visual.RatingScale(win)
            message = visual.TextStim(win, text=parameters['Confidence'])

            while ratingScale.noResponse:
                message.draw()
                ratingScale.draw()
                win.flip()
                confidence = ratingScale.getRating()
                confidenceRT = ratingScale.getRT()
        else:
            confidence, confidenceRT = None, None

    return nCounts, confidence, confidenceRT
