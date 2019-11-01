# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from psychopy import visual, event
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def sequence(parameters, win=None):
    """Run the entire task sequence.
    """
    if win is None:
        win = parameters['win']

    oxi = Oximeter(serial=parameters['serial'], sfreq=75)
    oxi.setup()
    oxi.read(duration=1)

    for condition, time in zip(parameters['Conditions'], parameters['Times']):
        trial(condition, time, parameters, win, oxi)

def trial(condition, time, parameters, win, oxi):
    """Run one trial using the parameters provided in `row`.

    Parameters
    ----------
    row : Pandas row
        Trial description. Must contain a `Condition` and `Time` column.
    parameters : dict
        Task parameters.
    """
    # Ask the participant to press 'Space' (default) to start the trial
    messageStart = visual.TextStim(parameters[win, units='height', height=0.1,
                                   text='Press space to continue')
    parameters['win'].flip()
    event.waitKeys(keyList=parameters['startKey'])
    messageStart.autoDraw = False  # Hide instructions
    self.win.update()

    # Show instructions
    text = self.parameters[row.Condition.loc[0]]
    message = visual.TextStim(self.win, text=text, units='height',
                              height=0.1)
    message.autoDraw = True  # Show instructions
    self.win.flip()

    # Setup recorder
    oxi.setup()

    # Wait for a beat to start the task
    oxi.waitBeat()

    # Sound signaling trial start
    self.note.play()
    self.note.stop()

    # Record for a desired time length
    oxi.read(nSeconds=row.Time.loc[0])

    # Sound signaling trial stop
    self.note.play()
    self.note.stop()

    # Hide instructions
    message.autoDraw = False
    self.win.update()

    # Save recording as np array
    np.save(self.path + '/Results/' + self.subID
            + '_' + str(row['TrialNumber']),
            np.asarray(oxi.recording))

    # Store recording into task object
    self.recording.append(oxi.recording)

    # Analyse oxi data
    oxi.find_peaks()
    oxi_hb = len(oxi.peaks)

    if row['Condition'] == 'Count':
        if self.parameters.rating:
            ratingScale = visual.RatingScale(self.win)
            message = visual.TextStim(
                            self.win,
                            text=self.parameters['Confidence'])
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

        # Store results in a DataFrame
        self.results_df = self.results_df.append(
            pd.DataFrame({'Reported_beats': subj_hb,
                          'Actual_beats': oxi_hb,
                          'Confidence': confidence,
                          'DecisionTime': decisionTime},
                         index=[0]))

    # Save summary figure
    if self.parameters['report']:
        oxi.plot()
        plt.savefig(self.path + '/Results/Trial-' +
                    str(object=row['TrialNumber']) + '.png',
                    dpi=300)
