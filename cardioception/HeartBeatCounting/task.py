# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from psychopy import visual, event, core
import pandas as pd
import numpy as np


def run(parameters, confidenceRating=True, runTutorial=True, win=None):
    """Run the entire task sequence.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    confidenceRating : bool
        Whether the trial show include a confidence rating scale.
    tutorial : bool
        If *True*, will present a tutorial with 10 training trial with feedback
        and 5 trials with confidence rating.
    win : `psychopy.visual.Window`
        Window where to present stimuli.
    """
    if win is None:
        win = parameters['win']

    # Run tutorial
    if runTutorial is True:
        tutorial(parameters)

    # Rest
    if parameters['restPeriod'] is True:
        rest(parameters, duration=parameters['restLength'])

    for condition, duration, nTrial in zip(
            parameters['conditions'], parameters['times'],
            range(0, len(parameters['conditions']))):

        nCount, confidence, confidenceRT = trial(condition, duration, nTrial,
                                                 parameters, win)

        # Store results in a DataFrame
        parameters['results_df'] = parameters['results_df'].append(
                    pd.DataFrame({'nTrial': [nTrial],
                                  'Reported': [nCount],
                                  'Condition': [condition],
                                  'Duration': [duration],
                                  'Confidence': [confidence],
                                  'ConfidenceRT': [confidenceRT]}),
                    ignore_index=True)

        # Save the results at each iteration
        parameters['results_df'].to_csv(
                        parameters['results'] + '/' +
                        parameters['participant'] +
                        parameters['session'] + '.txt')

    # Save results
    parameters['results_df'].to_csv(
                    parameters['results'] + '/' +
                    parameters['participant'] +
                    parameters['session'] + '_final.txt')

    # End of the task
    end = visual.TextStim(
        win, height=parameters['textSize'], pos=(0.0, 0.0),
        text='You have completed the task. Thank you for your participation.')
    end.draw()
    win.flip()
    core.wait(3)


def trial(condition, duration, nTrial, parameters, win):
    """Run one trial.

    Parameters
    ----------
    condition : str
        The trial condition, can be *Rest* or *Count*.
    duration : int
        The lenght of the recording (in seconds).
    ntrial : int
        Trial number.
    parameters : dict
        Task parameters.
    win : `psychopy.visual.Window`
        Window where to present stimuli.

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

    parameters['oxiTask'].setup()
    parameters['oxiTask'].read(duration=2)

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
    parameters['oxiTask'].waitBeat()
    core.wait(3)

    # Sound signaling trial start
    if (condition == 'Count') | (condition == 'Training'):
        parameters['oxiTask'].readInWaiting()
        # Add event marker
        parameters['oxiTask'].channels['Channel_0'][-1] = 1
        parameters['noteStart'].play()
        core.wait(1)

    # Record for a desired time length
    parameters['oxiTask'].read(duration=duration-1)

    # Sound signaling trial stop
    if (condition == 'Count') | (condition == 'Training'):
        # Add event marker
        parameters['oxiTask'].readInWaiting()
        parameters['oxiTask'].channels['Channel_0'][-1] = 2
        parameters['noteEnd'].play()
        core.wait(3)
        parameters['oxiTask'].readInWaiting()

    # Hide instructions
    win.flip()

    # Save recording
    parameters['oxiTask'].save(parameters['results'] + '/' +
                               parameters['participant'] + str(nTrial)
                               + '_' + str(nTrial))

    ###############################
    # Record participant estimation
    ###############################
    if (condition == 'Count') | (condition == 'Training'):
        # Ask the participant to press 'Space' (default) to start the trial
        messageCount = visual.TextStim(win, height=parameters['textSize'],
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
                        win, height=parameters['textSize'],
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
    """Run tutorial for the Heartbeat Counting Task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : `psychopy.visual.Window`
        Window where to present stimuli.
    """
    if win is None:
        win = parameters['win']

    # Tutorial 1
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial1'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 2
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   pos=(0.0, 0.2),
                                   text=parameters['texts']['Tutorial2'])
    messageStart.draw()
    parameters['heartLogo'].draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 3
    if parameters['taskVersion'] == 'Shandry':

        messageStart = visual.TextStim(win, height=parameters['textSize'],
                                       pos=(0.0, 0.2),
                                       text=parameters['texts']['Tutorial3'])
        messageStart.draw()
        parameters['restLogo'].draw()
        press = visual.TextStim(win,
                                height=parameters['textSize'],
                                text='Please press SPACE to continue',
                                pos=(0.0, -0.4))
        press.draw()
        win.flip()
        event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 4
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial4'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()

    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 5
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial5'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 6
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial6'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 7
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial7'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Tutorial 8
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial8'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])

    # Practice trial
    nCount, confidence, confidenceRT = trial('Count', 15, 0,  parameters, win)

    # Tutorial 9
    messageStart = visual.TextStim(win, height=parameters['textSize'],
                                   text=parameters['texts']['Tutorial9'])
    messageStart.draw()
    press = visual.TextStim(win,
                            height=parameters['textSize'],
                            text='Please press SPACE to continue',
                            pos=(0.0, -0.4))
    press.draw()
    win.flip()
    event.waitKeys(keyList=parameters['startKey'])


def rest(parameters, duration=300, win=None):
    """Run tutorial for the Heart Beat Counting Task.

    Parameters
    ----------
    parameters : dict
        Task parameters.
    win : `psychopy.visual.Window`
        Window where to present stimuli.
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
    parameters['oxiTask'].setup()
    parameters['oxiTask'].read(duration=duration)

    # Save recording
    parameters['oxiTask'].save(parameters['results'] + '/' +
                               parameters['participant'] + '_Rest')
