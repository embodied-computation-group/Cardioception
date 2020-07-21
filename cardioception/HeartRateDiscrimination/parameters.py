# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
import numpy as np
import pandas as pd
from psychopy import data, visual, core, event
from systole import serialSim
from systole.recording import findOximeter, Oximeter


def getParameters(participant='SubjectTest', session='001', serialPort=None,
                  setup='behavioral', stairType='psi', exteroception=True,
                  nTrials=160, BrainVisionIP=None, device='mouse',
                  screenNb=0):
    """Create Heart Rate Discrimination task parameters.

    Many task parameters, aesthetics, and options are controlled by the
    parameters dictonary defined herein. These are intended to provide
    flexibility and modularity to task. In many cases, unique versions of the
    task (e.g., with or without confidence ratings or choice feedback) can be
    created simply by changing these parameters, with no further interaction
    with the underlying task code.

    Parameters
    ----------
    participant : str
        Subject ID. Default is 'exteroStairCase'.
    session : int
        Session number. Default to '001'.
    serialPort: str
        The USB port where the pulse oximeter is plugged. Should be written as
        a string e.g., 'COM3', 'COM4'. If set to *None*, the pulse oximeter
        will be automatically detected. using the
        :py:func:`systole.recording.findOximeter()` function.
    setup : str
        Context of oximeter recording. Behavioral will record through a Nonin
        pulse oximeter, *fMRI* will record through BrainVision amplifier
        through TCP/IP conneciton. *test* will use pre-recorded pulse time
        series (for testing only).
    nStaircase : int
        Number of staircase to use per condition (exteroceptive and
        interoceptive).
    exteroception : bool
        If *True*, an exteroceptive condition with be interleaved with the
        interoceptive condition (either block or randomized design).
    extero_design : str
        If *exteroception* is *True*, define how to interleave the new trials.
        Can be 'block' or 'random'.
    stairType : str
        Staircase method. Can be 'psi' or 'UpDown'.
    nTrials : int
        Number of trials in total (all conditions confounded).

    Attributes
    ----------
    setup : str
        The context of recording. Can be 'behavioral', 'fMRI' or 'test'.
    device : str
        The device used for response and rating scale. Can be 'keyboard' or
        'mouse'.
    confScale : list
        The range of the confidence rating scale.
    labelsRating : list
        The labels of the confidence rating scale.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    monitor : str
        The monitor used to present the task (Psychopy parameter).
    nFeedback : int
        The number of trial with feedback during the tutorial phase (no
        confidence rating).
    nConfidence : int
        The number of trial with feedback during the tutorial phase (no
        feedback).
    respMax : float
        The maximum time for a confidence rating (in seconds).
    minRatingTime : float
        The minimum time before a rating can be provided during the confidence
        rating (in seconds).
    maxRatingTime : float
        The maximum time for a confidence rating (in seconds).
    startKey : str
        The key to press to start the task and go to next steps.
    allowedKeys : list of str
        The possible response keys.
    nTrials : int
        The number of trial to run in each condition, interoception and
        exteroception (if selected).
    nBeatsLim : int
        The number of beats to record at each trials. Only working with a
        behavioral setup with a Nonin USB pulse oximeter.
    nStaircase : int
        Number of staircase used. Can be 1 or 2. If 2, implements a randomized
        interleved staircase procedure following Cornsweet, 1976.
    nBreaking : int
        Number of trials to run before the break.
    Condition : 1d array-like
        Array of 0s and 1s encoding the conditions (1 : Higher, 0 : Lower). The
        length of the array is defined by `parameters['nTrials']`. If
        `parameters['nTrials']` is odd, will use `parameters['nTrials']` - 1
        to enseure an equal nuber of Higher and Lower conditions.
    stairCase : instance of Psychopy StairHandler
        The staircase object used to adjust the alpha value.
    serial : PySerial instance
        The serial port used to record the PPG activity.
    subjectID : str
        Subject identifier string.
    subjectNumber : int
        Subject reference number.
    path : str
        The task working directory.
    results : str
        The subject result directory.
    texts : dict
        The text to present during the estimation and confidence.
    Tutorial 1-5 : str
        Texts presented during the tutorial.
    win : Psychopy window instance
        The window where to run the task.
    listenLogo, heartLogo : Psychopy visual instance
        Image used for the inference and recording phases, respectively.
    textSize : float
        Text size.
    HRcutOff : list
        Cut off for extreme heart rate values during recording.
    lambdaIntero : 3d numpy array
        Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the interoceptive condition.
    lambdaExtero : 3d numpy array
        Posterior estimate of the psychophysics function parameters (slope and
        threshold) across trials for the exteroceptive condition.
    signal_df : pandas.DataFrame instance
        Dataframe where the pulse signal recorded during the interoception
        condition will be stored.
    """
    parameters = dict()
    parameters['ExteroCondition'] = exteroception
    parameters['setup'] = setup
    parameters['device'] = device
    if parameters['device'] == 'keyboard':
        parameters['confScale'] = [1, 7]
    parameters['labelsRating'] = ['Guess', 'Certain']
    parameters['screenNb'] = screenNb
    parameters['monitor'] = 'testMonitor'
    parameters['nFeedback'] = 10
    parameters['nConfidence'] = 5
    parameters['respMax'] = 8
    parameters['minRatingTime'] = .5
    parameters['maxRatingTime'] = 5
    parameters['startKey'] = 'space'
    parameters['allowedKeys'] = ['up', 'down']
    parameters['nTrials'] = nTrials
    parameters['nBeatsLim'] = 5
    parameters['nStaircase'] = None
    parameters['nBreaking'] = 25
    parameters['stairType'] = stairType
    parameters['lambdaIntero'] = []  # Save the history of lambda values
    parameters['lambdaExtero'] = []  # Save the history of lambda values

    parameters['signal_df'] = pd.DataFrame([])
    parameters['results_df'] = pd.DataFrame([])

    # Set default path /Results/ 'Subject ID' /
    parameters['participant'] = participant
    parameters['session'] = session
    parameters['path'] = os.getcwd()
    parameters['results'] = \
        parameters['path'] + '/data/' + participant + session
    # Create Results directory if not already exists
    if not os.path.exists(parameters['results']):
        os.makedirs(parameters['results'])

    # Create and randomize condition vectors
    if stairType == 'UpDown':
        if exteroception is False:
            # Create condition randomized vector
            parameters['Conditions'] = np.hstack(
                    [np.array(['More'] * round(parameters['nTrials']/2)),
                     np.array(['Less'] * round(parameters['nTrials']/2))])
    elif stairType == 'psi':
        parameters['Conditions'] = \
            np.array([None] * round(parameters['nTrials']/2))

    parameters['staircaisePosteriors'] = {}
    parameters['staircaisePosteriors']['Intero'] = []
    if exteroception is True:
        parameters['staircaisePosteriors']['Extero'] = []
        parameters['Conditions'] = np.tile(parameters['Conditions'], 2)
        # Create condition randomized vector
        parameters['Modality'] = np.hstack(
                [np.array(['Extero'] * round(parameters['nTrials']/2)),
                 np.array(['Intero'] * round(parameters['nTrials']/2))])
    elif exteroception is False:
        parameters['Modality'] = np.array(['Intero'] * parameters['nTrials'])

    rand = np.arange(0, len(parameters['Modality']))
    np.random.shuffle(rand)
    parameters['Modality'] = parameters['Modality'][rand]  # Shuffle vector
    parameters['Conditions'] = parameters['Conditions'][rand]  # Shuffle vector

    # Default parameters for the basic staircase are set here. Please see
    # PsychoPy Staircase Handler Documentation for full options. By default,
    # the task implements a staircase using Psi method.
    # If UpDown is selected, 1 or 2 interleaved staircases are used (see
    # options in parameters dictionary), one is initalized 'high' and the other
    # 'low'.
    parameters['stairCase'] = {}
    if stairType == 'UpDown':
        if parameters['nStaircase'] == 1:
            parameters['stairCase']['Intero'] = data.StairHandler(
                                startVal=40, nTrials=nTrials,
                                nUp=1, nDown=2,
                                stepSizes=[20, 12, 12, 7, 4, 3, 2, 1],
                                stepType='lin', minVal=1, maxVal=100)
        elif parameters['nStaircase'] == 2:
            if stairType == 'UpDown':
                conditions = [
                    {'label': 'low', 'startVal': 5, 'nUp': 1, 'nDown': 2,
                     'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
                     'stepType': 'lin', 'minVal': 1, 'maxVal': 100},
                    {'label': 'high', 'startVal': 40, 'nUp': 1, 'nDown': 2,
                     'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
                     'stepType': 'lin', 'minVal': 1, 'maxVal': 100},
                    ]
                parameters['stairCase']['Intero'] = data.MultiStairHandler(
                                            conditions=conditions,
                                            nTrials=nTrials)
        else:
            raise ValueError('Invalid number of Staircase')

    elif stairType == 'psi':
        parameters['stairCase']['Intero'] = data.PsiHandler(
            nTrials=nTrials, intensRange=[-40.5, 40.5],
            alphaRange=[-40.5, 40.5], betaRange=[0.1, 20],
            intensPrecision=1, alphaPrecision=1, betaPrecision=0.1,
            delta=0.02, stepType='lin', expectedMin=0)

    if exteroception is True:
        if stairType == 'UpDown':
            if parameters['nStaircase'] == 1:
                parameters['stairCase']['Extero'] = \
                    data.StairHandler(
                        startVal=40, nTrials=nTrials, nUp=1,
                        nDown=2, stepSizes=[20, 12, 12, 7, 4, 3, 2, 1],
                        stepType='lin', minVal=1, maxVal=100)
            elif parameters['nStaircase'] == 2:
                conditions = [
                    {'label': 'low', 'startVal': 5, 'nUp': 1, 'nDown': 2,
                     'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
                     'stepType': 'lin', 'minVal': 1, 'maxVal': 100},
                    {'label': 'high', 'startVal': 40, 'nUp': 1, 'nDown': 2,
                     'stepSizes': [20, 12, 12, 7, 4, 3, 2, 1],
                     'stepType': 'lin', 'minVal': 1, 'maxVal': 100},
                ]
                parameters['stairCase']['Extero'] = \
                    data.MultiStairHandler(conditions=conditions,
                                           nTrials=nTrials)
        elif stairType == 'psi':
            parameters['stairCase']['Extero'] = data.PsiHandler(
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
    btnext = 'SPACE' if parameters['device'] == 'keyboard' else 'any button'
    parameters['texts'] = {
            'textTaskStart': "The task is now going to start, get ready.",
            'textBreaks': f"Break. You can rest as long as you want. Just press {btnext} when you want to resume the task.",
            'textNext': f'Please press {btnext} to continue',
            'textWaitTrigger': "Waiting for fMRI trigger...",
            'Estimation': {'Intero': """Do you think the tone frequency was higher or lower than your heart rate?""",
                           'Extero': """Do you think the tone frequency was higher or lower than the previous one?"""},
            'Confidence': """How confident are you about your estimation?

        Use the RIGHT/LEFT keys to select and the DOWN key to confirm"""}

    parameters['Tutorial1'] = (
        "During this experiment, we are going to record your heart rate and generate sounds reflecting your cardiac activity.")

    parameters['Tutorial2'] = (
        "When this heart icon is presented, you will have to focus on your cardiac activity while it is recorded for 5 seconds.")

    moreResp = 'UP key' if parameters['device'] == 'keyboard' else 'RIGHT button'
    lessResp = 'DOWN key' if parameters['device'] == 'keyboard' else 'LEFT button'
    parameters['Tutorial3'] = (
        f"""After this procedure, you will see the listening and response icons.

        You will then have to focus on the tone frequency and decide if it is faster ({moreResp}) or slower ({lessResp}) than your recorded heart rate in the listening interval.

        The tone frequency will ALWAYS be slower or faster than your heart rate as previously recorded. Please guess if you are unsure.""")

    if parameters['ExteroCondition'] is True:
        parameters['Tutorial3bis'] = (
            f"""For some trials, instead of seeing the heart icon at the beginning, you will see a listening icon.

            You will then have to focus on the tone frequency you will hear.""")

        parameters['Tutorial3ter'] = (
            f"""After this procedure, you will see the listening and response icons, like for the previous ones.

            You will then have to focus on the tone frequency and decide if it is faster ({moreResp}) or slower ({lessResp}) than the previous one.

            The tone frequency will ALWAYS be slower or faster than the previous one. Please guess if you are unsure.""")


    parameters['Tutorial4'] = (
        """Once you have provided your decision, you will also be asked to provide your level of confidence.

        A high number here means that you are totally certain in your choice, a small number means that you are guessing.

        You should use the RIGHT and LEFT key to select your response and the DOWN key to confirm.""")

    parameters['Tutorial5'] = (
        """This sequence will be repeated during the task.

        At times the task may be very difficult; the difference between your true heart rate and the presented tones may be very small.

        This means that you should try to use the entire length of the confidence scale to reflect your subjective uncertainty on each trial.

        As the task difficulty will change over time, it is rare that will be totally confident or totally uncertain""")

    # Open window
    if parameters['setup'] == 'test':
        fullscr = False
    else:
        fullscr = True
    parameters['win'] = visual.Window(monitor=parameters['monitor'],
                                      screen=parameters['screenNb'],
                                      fullscr=fullscr, units='height')
    parameters['win'].mouseVisible = False

    ###############
    # Image loading
    ###############
    parameters['listenResponse'] = visual.ImageStim(
        win=parameters['win'],
        units='height',
        image=os.path.dirname(__file__) + '/Images/listenResponse.png',
        pos=(0.0, -0.2))
    parameters['listenResponse'].size *= 0.1

    parameters['listenLogo'] = visual.ImageStim(
        win=parameters['win'],
        units='height',
        image=os.path.dirname(__file__) + '/Images/listen.png',
        pos=(0.0, -0.2))
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
    if parameters['device'] == 'mouse':
        parameters['confScale'] = [1, 100]
        parameters['myMouse'] = event.Mouse()

    return parameters
