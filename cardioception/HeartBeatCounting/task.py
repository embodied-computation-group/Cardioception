# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from psychopy import visual, event, core
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
            parameters['conditions'], parameters['times'],
            range(0, len(parameters['conditions']))):

        nCount, confidence, confidenceRT = trial(condition, duration, nTrial,
                                                 parameters, win)

        # Store results in a DataFrame
        results_df = results_df.append(
                    pd.DataFrame({'nTrial': nTrial,
                                  'Reported': nCount,
                                  'Condition': condition,
                                  'Duration': duration,
                                  'Confidence': confidence,
                                  'ConfidenceRT': confidenceRT},
                                 ignore_index=True))

    # Save results
    results_df.to_csv(
        parameters['results'] + '/' + parameters['subjectID'] + '.txt')


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
    nCount : int
        The number of heartbeat estimated by the participant.
    confidence : int
        The confidence in the estimation of the heartbeat provided by the
        participant.
    confidenceRT : float
        The response time to provide confidence rating.
    """

    # Initialize default values
    confidence, confidenceRT, nCounts = None, None, None

    # Ask the participant to press 'Space' (default) to start the trial
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text='Press space to continue')
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])
    win.flip()

    oxi = Oximeter(serial=parameters['serial'], sfreq=75, add_channels=1)
    oxi.setup()
    oxi.read(duration=2)

    # Show instructions
    if condition == 'Rest':
        message = visual.TextStim(win, text=parameters['texts']['Rest'],
                                  pos=(0.0, 0.2),
                                  height=parameters['textSize'])
        message.draw()
        parameters['restLogo'].draw()
    elif (condition == 'Count') | (condition == 'Training'):
        message = visual.TextStim(win, text=parameters['texts']['Count'],
                                  pos=(0.0, 0.2),
                                  height=parameters['textSize'])
        message.draw()
        parameters['heartLogo'].draw()
    win.flip()

    # Wait for a beat to start the task
    oxi.waitBeat()
    core.wait(3)

    # Sound signaling trial start
    if (condition == 'Count') | (condition == 'Training'):
        oxi.readInWaiting()
        # Add event marker
        oxi.channels['Channel_0'][-1] = 1
        parameters['noteStart'].play()

    # Record for a desired time length
    oxi.read(duration=duration)

    # Sound signaling trial stop
    if (condition == 'Count') | (condition == 'Training'):
        # Add event marker
        oxi.readInWaiting()
        oxi.channels['Channel_0'][-1] = 2
        parameters['noteEnd'].play()
        core.wait(3)
        oxi.readInWaiting()

    # Hide instructions
    win.flip()

    # Save recording as np array
    np.save(parameters['results'] + parameters['subjectID']
            + '_' + str(nTrial),
            np.asarray([oxi.recording, oxi.peaks, oxi.channels['Channel_0']]))

    ###############################
    # Record participant estimation
    ###############################
    if (condition == 'Count') | (condition == 'Training'):
        # Ask the participant to press 'Space' (default) to start the trial
        messageCount = visual.TextStim(win, height=parameters['textSize'],
                                       color=(0.0, 0.0, 1.0),
                                       pos=(0, 0.2),
                                       text=parameters['texts']['nCount'])
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
                if all(char.isdigit() for char in nCounts):
                    nCounts = int(nCounts)
                    break
                else:
                    messageError = visual.TextStim(
                        win, height=0.05,
                        color=(0.0, 0.0, 1.0),
                        pos=(0, 0.2),
                        text="You should only provide numbers")
                    messageError.draw()
                    win.flip()
                    core.wait(2)
            else:
                nCounts += [s for s in key[0] if s.isdigit()][0]

            # Show the text on the screen
            recordedText = visual.TextStim(win,
                                           height=parameters['textSize'],
                                           text=nCounts)
            recordedText.draw()
            messageCount.draw()
            win.flip()

        ##############
        # Rating scale
        ##############
        if parameters['rating'] is True:
            markerStart = np.random.choice(
                                np.arange(parameters['confScale'][0],
                                          parameters['confScale'][1]))
            ratingScale = visual.RatingScale(win,
                                             low=parameters['confScale'][0],
                                             high=parameters['confScale'][1],
                                             noMouse=True,
                                             labels=parameters['labelsRating'],
                                             acceptKeys='down',
                                             markerStart=markerStart)
            message = visual.TextStim(win,
                                      text=parameters['texts']['confidence'],
                                      height=parameters['textSize'])
            while ratingScale.noResponse:
                message.draw()
                ratingScale.draw()
                win.flip()
            confidence = ratingScale.getRating()
            confidenceRT = ratingScale.getRT()

    return nCounts, confidence, confidenceRT


def tutorial(parameters, win=None):
    """Run tutorial for the Heart Beat Counting Task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : psychopy window
        Instance of Psychopy window.
    """
    if win is None:
        win = parameters['win']

    # Tutorial 1
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial1'])
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 2
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   pos=(0.0, 0.2),
                                   text=parameters['texts']['Tutorial2'])
    messageStart.draw()
    parameters['heartLogo'].draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 3
    if parameters['taskVersion'] == 'Shandry':

        messageStart = visual.TextStim(win, height=parameters['textSize'],
                                       pos=(0.0, 0.2),
                                       text=parameters['texts']['Tutorial3'])
        messageStart.draw()
        parameters['restLogo'].draw()
        win.flip()
        event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 4
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial4'])
    messageStart.draw()
    win.flip()

    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 5
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial5'])
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 6
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial6'])
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 7
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial7'])
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 8
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial8'])
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Practice trial
    nCount, confidence, confidenceRT = trial('Count', 15, 0,  parameters, win)

    # Tutorial 9
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial9'])
    messageStart.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])


def rest(parameters, win=None):
    """Run tutorial for the Heart Beat Counting Task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : psychopy window
        Instance of Psychopy window.
    """
    if win is None:
        win = parameters['win']

    # Show instructions
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   pos=(0.0, 0.2),
                                   text=("Calibrating... Please sit quietly"
                                         " until the end of the recording."))
    messageStart.draw()
    parameters['restLogo'].draw()
    win.flip()

    # Record PPG signal
    oxi = Oximeter(serial=parameters['serial'], sfreq=75, add_channels=1)
    oxi.setup()
    oxi.read(duration=parameters['restLength'])

    # Save recording
    np.save(parameters['results'] + parameters['subjectID'] + '_Rest',
            np.asarray([oxi.recording, oxi.peaks, oxi.channels['Channel_0']]))
