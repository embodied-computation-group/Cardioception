# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from psychopy import visual, event
import pandas as pd
import numpy as np
from cardioception.recording import Oximeter
import matplotlib.pyplot as plt


def sequence(parameters, win=None):
    """Run the entire task sequence.
    """
    if win is None:
        win = parameters['win']

    for condition, time, nTrial in zip(
            parameters['Conditions'], parameters['Times'],
            range(0, len(parameters['Conditions']))):

        nCount, confidence, confidenceRT = trial(condition, time, nTrial,
                                                 parameters, win)

        # Store results in a DataFrame
        results_df = results_df.append(
                    pd.DataFrame({'Reported': nCount,
                                  'Confidence': confidence,
                                  'DecisionTime': decisionTime},
                                 index=[0]))

    # Save results
    results_df.to_csv(parameters['results'] + parameters['nsub'] + '.txt')


def trial(condition, time, parameters, win):
    """Run one trial.

    Parameters
    ----------
    condition : str
        The trial condition, can be `Rest` or `Count`.
    time : int
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
    messageStart = visual.TextStim(parameters[win, units='height', height=0.1,
                                   text='Press space to continue')
    win.flip()
    event.waitKeys(keyList=parameters['startKey'], maxWait=8)
    win.flip()

    oxi = Oximeter(serial=parameters['serial'], sfreq=75)
    oxi.setup()
    oxi.read(duration=1)

    # Show instructions
    message = visual.TextStim(win, text= parameters[condition], units='height',
                              height=0.1)
    win.flip()

    # Wait for a beat to start the task
    oxi.waitBeat()

    # Sound signaling trial start
    parameters['note'].play()
    parameters['note'].stop()
    oxi.readInWaiting()
    oxi.triggers[-1] = 3

    # Record for a desired time length
    oxi.read(nSeconds=times)

    # Sound signaling trial stop
    parametetrs['note'].play()
    parametetrs['note'].stop()
    oxi.triggers[-1] = 3

    # Hide instructions
    win.flip()

    # Save recording as np array
    np.save(parameters['path'] + '/Results/' + parameters['sub']
            + '_' + str(nTrial),
            np.asarray(oxi.recording))

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
                self.win.flip()
                confidence = ratingScale.getRating()
                decisionTime = ratingScale.getRT()
        else:
            confidence, decisionTime = None, None

        # Get subject heart count estimation
        subj_hb = oxi.peaks
