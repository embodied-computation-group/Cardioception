# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
import numpy as np
import pandas as pd
from psychopy import data, visual, core, event
from systole import serialSim
from systole.recording import findOximeter, Oximeter


def getParameters(participant='SubjectTest', session='001', serialPort=None,
                  setup='behavioral', exteroception=True, psiCatchTrials=0.0,
                  nTrials=160, BrainVisionIP=None, device='mouse',
                  screenNb=0, fullscr=True, nTrialsUpDown=80, resultPath=None):
    """Create Heart Rate Discrimination task parameters.

    Many task parameters, aesthetics, and options are controlled by the
    parameters dictonary defined herein. These are intended to provide
    flexibility and modularity to task. In many cases, unique versions of the
    task (e.g., with or without confidence ratings or choice feedback) can be
    created simply by changing these parameters, with no further interaction
    with the underlying task code.

    Parameters
    ----------
    BrainVisionIP : str
        The IP address of the recording computer (fMRI version only).
    device : str
        Select how the participant provide responses. Can be 'mouse' or
        'keyboard'.
    exteroception : bool
        If *True*, an exteroceptive condition with be interleaved with the
        interoceptive condition (either block or randomized design).
    fullscr : bool
        If *True*, activate full screen mode.
    nStaircase : int
        Number of staircase to use per condition (exteroceptive and
        interoceptive).
    nTrials : int
        Number of trials to run (UpDown + psi staircase).
    nTrialsUpDown : int
        Number of trials to run using a 1Up-1Down staircase for threshold
        estimation.
    participant : str
        Subject ID. Default is 'Participant'.
    psiCatchTrials : float
        Ratio of Psi trials allocated to extreme values (+20 or -20 bpm with
        some jitter) to control for range of stimuli presented. The default is
        `0.0` (no catch trials). If not `0.0`, recomended value is `0.2`.
    resultPath : str or None
        Where to save the results.
    screenNb : int
        Select screen number.
    serialPort: str
        The USB port where the pulse oximeter is plugged. Should be written as
        a string e.g., `'COM3'`, `'COM4'`. If set to *None*, the pulse oximeter
        will be automatically detected. using the
        :py:func:`systole.recording.findOximeter()` function.
    session : int
        Session number. Default to '001'.
    setup : str
        Context of oximeter recording. Behavioral will record through a Nonin
        pulse oximeter, `'fMRI'` will record through BrainVision amplifier
        through TCP/IP conneciton. *test* will use pre-recorded pulse time
        series (for testing only).

    Attributes
    ----------
    allowedKeys : list of str
        The possible response keys.
    confScale : list
        The range of the confidence rating scale.
    device : str
        The device used for response and rating scale. Can be 'keyboard' or
        'mouse'.
    HRcutOff : list
        Cut off for extreme heart rate values during recording.
    labelsRating : list
        The labels of the confidence rating scale.
    lambdaExtero : 3d numpy array
        Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the exteroceptive condition.
    lambdaIntero : 3d numpy array
        Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the interoceptive condition.
    listenLogo, heartLogo : Psychopy visual instance
        Image used for the inference and recording phases, respectively.
    maxRatingTime : float
        The maximum time for a confidence rating (in seconds).
    minRatingTime : float
        The minimum time before a rating can be provided during the confidence
        rating (in seconds).
    monitor : str
        The monitor used to present the task (Psychopy parameter).
    nBeatsLim : int
        The number of beats to record at each trials. Only working with a
        behavioral setup with a Nonin USB pulse oximeter.
    nBreaking : int
        Number of trials to run before the break.
    nConfidence : int
        The number of trial with feedback during the tutorial phase (no
        feedback).
    nFeedback : int
        The number of trial with feedback during the tutorial phase (no
        confidence rating).
    nTrials : int
        The number of trial to run in each condition, interoception and
        exteroception (if selected).
    participant : str
        Subject ID. Default is 'Participant'.
    path : str
        The task working directory.
    serial : PySerial instance
        The serial port used to record the PPG activity.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    signal_df : pandas.DataFrame instance
        Dataframe where the pulse signal recorded during the interoception
        condition will be stored.
    stairCase : dict
        The staircase instances for 'psi' and 'UpDown'. Each entry contain
        dictionnary for 'Intero' and 'Extero conditions' (if relevant).
    startKey : str
        The key to press to start the task and go to next steps.
    respMax : float
        The maximum time for decision (in seconds).
    results : str
        The result directory.
    session : int
        Session number. Default to '001'.
    setup : str
        The context of recording. Can be 'behavioral', 'fMRI' or 'test'.
    texts : dict
        Long text elements.
    textSize : float
        Scalling parameter for text size.
    win : Psychopy window instance
        The window where to run the task.
    """
    parameters = dict()
    parameters['nTrialsUpDown'] = nTrialsUpDown
    parameters['ExteroCondition'] = exteroception
    parameters['device'] = device
    if parameters['device'] == 'keyboard':
        parameters['confScale'] = [1, 7]
    parameters['labelsRating'] = ['Guess', 'Certain']
    parameters['screenNb'] = screenNb
    parameters['monitor'] = 'testMonitor'
    parameters['nFeedback'] = 5
    parameters['nConfidence'] = 5
    parameters['respMax'] = 8
    parameters['minRatingTime'] = .5
    parameters['maxRatingTime'] = 5
    parameters['startKey'] = 'space'
    parameters['allowedKeys'] = ['up', 'down']
    parameters['nTrials'] = nTrials
    parameters['nBeatsLim'] = 5
    parameters['nBreaking'] = 20
    parameters['lambdaIntero'] = []  # Save the history of lambda values
    parameters['lambdaExtero'] = []  # Save the history of lambda values

    parameters['signal_df'] = pd.DataFrame([])
    parameters['results_df'] = pd.DataFrame([])

    # Set default path /Results/ 'Subject ID' /
    parameters['participant'] = participant
    parameters['session'] = session
    parameters['path'] = os.getcwd()
    if resultPath is None:
        parameters['results'] = \
            parameters['path'] + '/data/' + participant + session
    else:
        parameters['results'] = None
    # Create Results directory if not already exists
    if not os.path.exists(parameters['results']):
        os.makedirs(parameters['results'])

    # Create and randomize condition vectors separately for each staircase
    parameters['staircaisePosteriors'] = {}
    parameters['staircaisePosteriors']['Intero'] = []
    if exteroception is True:
        parameters['staircaisePosteriors']['Extero'] = []
        # Create condition randomized vector for UpDown staircases
        updown = np.hstack(
            [np.array(['Extero'] *
             round(parameters['nTrialsUpDown']/2)),
             np.array(['Intero'] *
             round(parameters['nTrialsUpDown']/2))])

        # Create condition randomized vector for psi staircases
        nPsitrials = round((parameters['nTrials'] -
                            parameters['nTrialsUpDown'])/2)
        psi = np.hstack(
            [np.array(['Extero'] * nPsitrials),
             np.array(['Intero'] * nPsitrials)])
        # Vector encoding the type of trial (psi, up/down or catch)
        parameters['catchTrials'] = np.hstack(
            [np.array(['UpDown'] * parameters['nTrialsUpDown']),
             np.array(['psi'] * int((nPsitrials * 2 * (1-psiCatchTrials)))),
             np.array(['psiCatchTrial'] * 2 *
                      int((nPsitrials * psiCatchTrials)))])
        parameters['Modality'] = np.hstack([updown, psi])

        # Firt we shuffle only up/down trials
        shuffler = np.random.permutation(parameters['nTrialsUpDown'])
        parameters['Modality'][:parameters['nTrialsUpDown']] = \
            parameters['Modality'][shuffler]
        parameters['catchTrials'][:parameters['nTrialsUpDown']] = \
            parameters['catchTrials'][shuffler]

        # Then we shuffle all trials except first 1/2 of up/down
        # If no up/down trials are provided, this equal full shuffling
        # Oherwise, this ensures that task start with up/down to avoid bias
        shuffler = np.random.permutation(
            np.arange(int(parameters['nTrialsUpDown']/2),
                      parameters['nTrials']))
        parameters['Modality'][int(parameters['nTrialsUpDown']/2):] = \
            parameters['Modality'][shuffler]
        parameters['catchTrials'][int(parameters['nTrialsUpDown']/2):] = \
            parameters['catchTrials'][shuffler]

    elif exteroception is False:
        # Create condition randomized vector for UpDown staircases
        updown = np.hstack(
            [np.array(['Intero'] *
             round(parameters['nTrialsUpDown']*2))])

        # Create condition randomized vector for psi staircases
        psi = np.hstack(
            [np.array(['Intero'] * round(parameters['nTrials']))])
        parameters['Modality'] = np.hstack([updown, psi])

    # Default parameters for the basic staircase are set here. Please see
    # PsychoPy Staircase Handler Documentation for full options. By default,
    # the task implements a staircase using Psi method.
    # If UpDown is selected, 1 or 2 interleaved staircases are used (see
    # options in parameters dictionary), one is initalized 'high' and the other
    # 'low'.
    parameters['stairCase'] = {'psi': {}, 'UpDown': {}}

    conditions = [
        {'label': 'low', 'startVal': -40.5, 'nUp': 1, 'nDown': 1,
         'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
         'stepType': 'lin', 'minVal': -40.5, 'maxVal': 40.5},
        {'label': 'high', 'startVal': 40.5, 'nUp': 1, 'nDown': 1,
         'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
         'stepType': 'lin', 'minVal': -40.5, 'maxVal': 40.5},
        ]
    parameters['stairCase']['UpDown']['Intero'] = data.MultiStairHandler(
                                conditions=conditions,
                                nTrials=parameters['nTrialsUpDown'])

    parameters['stairCase']['psi']['Intero'] = data.PsiHandler(
        nTrials=nTrials, intensRange=[-40.5, 40.5],
        alphaRange=[-40.5, 40.5], betaRange=[0.1, 20],
        intensPrecision=1, alphaPrecision=1, betaPrecision=0.1,
        delta=0.02, stepType='lin', expectedMin=0)

    if exteroception is True:
        conditions = [
            {'label': 'low', 'startVal': -40.5, 'nUp': 1, 'nDown': 1,
             'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
             'stepType': 'lin', 'minVal': -40.5, 'maxVal': 40.5},
            {'label': 'high', 'startVal': 40.5, 'nUp': 1, 'nDown': 1,
             'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
             'stepType': 'lin', 'minVal': -40.5, 'maxVal': 40.5},
            ]
        parameters['stairCase']['UpDown']['Extero'] = \
            data.MultiStairHandler(conditions=conditions,
                                   nTrials=parameters['nTrialsUpDown'])

        parameters['stairCase']['psi']['Extero'] = data.PsiHandler(
            nTrials=nTrials, intensRange=[-40.5, 40.5],
            alphaRange=[-40.5, 40.5], betaRange=[0.1, 20],
            intensPrecision=1, alphaPrecision=1, betaPrecision=0.1,
            delta=0.02, stepType='lin', expectedMin=0)

    parameters['setup'] = setup
    if setup == 'behavioral':
        # PPG recording
        if serialPort is None:
            serialPort = findOximeter()
            if serialPort is None:
                print('Cannot find the Pulse Oximeter automatically, please',
                      ' enter port reference in the GUI')
                core.quit()

        port = serial.Serial(serialPort)
        parameters['oxiTask'] = Oximeter(serial=port, sfreq=75, add_channels=1)
        parameters['oxiTask'].setup().read(duration=1)
    elif setup == 'test':
        # Use pre-recorded pulse time series for testing
        port = serialSim()
        parameters['oxiTask'] = Oximeter(serial=port, sfreq=75, add_channels=1)
        parameters['oxiTask'].setup().read(duration=1)
    elif setup == 'fMRI':
        parameters['fMRItrigger'] = ['5']  # Keys to listen for fMRI trigger

    #######
    # Texts
    #######
    btnext = 'press SPACE' if parameters['device'] == 'keyboard' else 'click the mouse'
    parameters['texts'] = {
            'textTaskStart': "The task is now going to start, get ready.",
            'textBreaks': f"Break. You can rest as long as you want. Just {btnext} when you want to resume the task.",
            'textNext': f'Please {btnext} to continue',
            'textWaitTrigger': "Waiting for fMRI trigger...",
            'Decision': {'Intero': """Are these beeps faster or slower than your heart?""",
                           'Extero': """Are these beeps faster or slower than the previous?"""},
            'Confidence': """How confident are you in your choice?"""}

    parameters['Tutorial1'] = (
        "During this experiment, we will record your pulse and play beeps based on your heart rate.")

    parameters['Tutorial2'] = (
        "When you see this icon, try to focus on your heartbeat for 5 seconds. Try not to move, as we are recording your pulse in this period")

    moreResp = 'UP key' if parameters['device'] == 'keyboard' else 'RIGHT mouse button'
    lessResp = 'DOWN key' if parameters['device'] == 'keyboard' else 'LEFT mouse button'
    parameters['Tutorial3'] = (
        f"""After this 'heart listening' period, you will see the response icons and hear a series of beeps.

As quickly and accurately as possible, you will listen to these beeps and decide if they are faster ({moreResp}) or slower ({lessResp}) than your own heart rate.

The beeps will ALWAYS be slower or faster than your heart. Please guess, even if you are unsure.""")

    if parameters['ExteroCondition'] is True:
        parameters['Tutorial3bis'] = (
            f"""For some trials, instead of seeing the heart icon, you will see a listening icon.

You will then have to listen to a first set of beeps, instead of your heart.""")

        parameters['Tutorial3ter'] = (
            f"""After these first beeps, you will see the response icons appear, and a second set of beeps will play.

As quickly and accurately as possible, you will listen to these beeps and decide if they are faster ({moreResp}) or slower ({lessResp}) than the first set of beeps.

The second series of beeps will ALWAYS be slower or faster than the first series. Please guess, even if you are unsure.""")


    parameters['Tutorial4'] = (
        """Once you have provided your decision, you will also be asked to rate how confident you feel in your decision.

Here, the maximum rating (100) means that you are totally certain in your choice, and the smallest rating (0) means that you felt that you were guessing.

You should use mouse to select your rating""")

    parameters['Tutorial5'] = (
        """This sequence will be repeated during the task.

At times the task may be very difficult; the difference between your true heart rate and the presented beeps may be very small.

This means that you should try to use the entire length of the confidence scale to reflect your subjective uncertainty on each trial.

As the task difficulty will change over time, it is rare that you will be totally confident or totally uncertain.
This concludes the tutorial. If you have any questions, please ask the experimenter now.
Otherwise, press any key to continue to the main task. """)

    # Open window
    if parameters['setup'] == 'test':
        fullscr = False
    parameters['win'] = visual.Window(monitor=parameters['monitor'],
                                      screen=parameters['screenNb'],
                                      fullscr=fullscr, units='height')
    parameters['win'].mouseVisible = False

    ###############
    # Image loading
    ###############
    parameters['listenLogo'] = visual.ImageStim(
        win=parameters['win'],
        units='height',
        image=os.path.dirname(__file__) + '/Images/listen.png',
        pos=(0.0, 0.0))
    parameters['listenLogo'].size *= 0.1

    parameters['heartLogo'] = visual.ImageStim(
        win=parameters['win'],
        units='height',
        image=os.path.dirname(__file__) + '/Images/heartbeat.png',
        pos=(0.0, 0.0))
    parameters['heartLogo'].size *= 0.04
    parameters['textSize'] = 0.04
    parameters['HRcutOff'] = [40, 120]
    parameters["BrainVisionIP"] = BrainVisionIP
    if parameters['device'] == 'keyboard':
        parameters['confScale'] = [1, 10]
    elif parameters['device'] == 'mouse':
        parameters['myMouse'] = event.Mouse()

    return parameters
