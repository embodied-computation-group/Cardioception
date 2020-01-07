# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
import numpy as np
from psychopy import data, visual


def getParameters(subjectID, subjectNumber, serialPort):
    """Create task parameters.
    Many task parameters, aesthetics, and options are controlled by the parameters
    dictonary defined herein. These are intended to provide flexibility and modularity to
    task. In many cases, unique versions of the task (e.g., with or without
    confidence ratings or choice feedback) can be created simply by changing
    these parameters, with no further interaction with the underlying task code.

    Parameters
    ----------
    subject : str
        Subject ID.
    subjectNumber : int
        Participant number.
    serialPort: str
        The USB port where the pulse oximeter is plugged. Should be written as
        a string e.g., 'Com3', 'Com4'

    Attributes
    ----------
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
        The number of trial to run.
    nBeatsLim : int
        The number of beats to record at each trials.
    nStaircase : int
        Number of staircase used. Can be 1 or 2. If 2, implements a randomized
        interleved staircase procedure following Cornsweet, 1976.
    Condition : 1d-array
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
    win : Psychopy window
        The window where to run the task.
    listenLogo, heartLogo : Psychopy visual instance
        Image used for the inference and recording phases, respectively.
    textSize : float
        Text size.
    HRcutOff : list
        Cut off for extreme heart rate values during recording.
    """
    parameters = dict()
    parameters['confScale'] = [1, 7]
    parameters['labelsRating'] = ['Guess', 'Certain']
    parameters['screenNb'] = 0
    parameters['monitor'] = 'testMonitor'
    parameters['nFeedback'] = 10
    parameters['nConfidence'] = 5
    parameters['respMax'] = 8
    parameters['minRatingTime'] = 1
    parameters['maxRatingTime'] = 4
    parameters['startKey'] = 'space'
    parameters['allowedKeys'] = ['up', 'down']
    parameters['nTrials'] = 150
    parameters['nBeatsLim'] = 5
    parameters['nStaircase'] = 2

    # Create condition randomized vector
    parameters['Conditions'] = np.hstack(
            [np.array(['More'] * round(parameters['nTrials']/2)),
             np.array(['Less'] * round(parameters['nTrials']/2))])
    np.random.shuffle(parameters['Conditions'])  # Shuffle vector

    # Create staircase condition vector
    parameters['staircaseConditions'] = np.array([])
    for i in range(parameters['nStaircase']):
        parameters['staircaseConditions'] = \
            np.hstack([parameters['staircaseConditions'],
                      np.array([i] * round(parameters['nTrials']/2))])
    np.random.shuffle(parameters['staircaseConditions'])  # Shuffle vector

    # Ensure same length
    while len(parameters['staircaseConditions']) < parameters['nTrials']:
        parameters['staircaseConditions'] = \
            np.append(parameters['staircaseConditions'][0],
                      parameters['staircaseConditions'])

    # Default parameters for the basic staircase are set here. Please see
    # PsychoPy Staircase Handler Documentation for full options. By default,
    # the task implements a 2 down 1 up staircase with a logarythmic stepsize
    # function for alpha. If randomized, interleaved staircases are used (see
    # options in parameters dictionary), one is initalized 'high' and the other
    # 'low'.

    parameters['stairCase'] = []
    parameters['stairCase'].append(
        data.StairHandler(
                    startVal=40, nTrials=parameters['nTrials'], nUp=1,
                    nDown=2, stepSizes=[20, 12, 12, 7, 4, 3, 2, 1],
                    stepType='lin', minVal=1, maxVal=100))
    if parameters['nStaircase'] == 2:
        parameters['stairCase'].append(
            data.StairHandler(
                        startVal=5, nTrials=parameters['nTrials'], nUp=1,
                        nDown=2, stepSizes=[20, 12, 12, 7, 4, 3, 2, 1],
                        stepType='lin', minVal=1, maxVal=100))
    # Open seral port for Oximeter
    parameters['serial'] = serial.Serial(serialPort)

    # Set default path /Results/ 'Subject ID' /
    parameters['subject'] = subjectID
    parameters['subjectNumber'] = subjectNumber
    parameters['path'] = os.getcwd()
    parameters['results'] = parameters['path'] + '/Results/' + subjectID

    # Create Results directory if not already exists
    if not os.path.exists(parameters['results']):
        os.makedirs(parameters['results'])

    # Texts
    parameters['texts'] = {
        'Estimation': """Do you think the tone frequency
        was higher or lower than your heart rate?""",
        'Confidence':
            ('How confident are you about your estimation?'
             'Use the RIGHT/LEFT keys to select and the DOWN key to confirm')}

    parameters['Tutorial1'] = (
        "During this experiment, we are going to record your heart rate and"
        " generate sounds reflecting your cardiac activity.")

    parameters['Tutorial2'] = (
        "When this heart icon is presented, you will have to focus on your"
        " cardiac activity while it is recorded for 5 seconds.")

    parameters['Tutorial3'] = (
        "After this procedure, you will see the listening and"
        " response icons. You will then have to focus on the tone frequency"
        " and decide if it is faster (UP key) or slower (DOWN key) than your"
        " recorded heart rate in the listening interval. The tone"
        " frequency will ALWAYS be slower or faster than your heart rate"
        " as previously recorded. Please guess if you are unsure.")

    parameters['Tutorial4'] = (
        "Once you have provided your decision, you will also be asked to"
        " provide your level of confidence. A high number here means that"
        " you are totally certain in your choice, a small number means that"
        " you are guessing. You should use the RIGHT and LEFT key to"
        " select your response and the DOWN key to confirm.")

    parameters['Tutorial5'] = (
        "This sequence will be repeated during the task. At times the task may"
        " be very difficult; the difference between your true heart rate and"
        " the presented tones may be very small. This means that you"
        " should try to use the entire length of the confidence scale to"
        " to reflect your subjective uncertainty on each trial. As the task"
        " difficulty will change over time, it is rare that will be totally"
        " confident or totally uncertain")

    # Open window
    parameters['win'] = visual.Window(monitor=parameters['monitor'],
                                      screen=parameters['screenNb'],
                                      fullscr=True, units='height')
    parameters['win'].mouseVisible = False

    # Image loading
    parameters['listenLogo'] = visual.ImageStim(
        win=parameters['win'],
        units='height',
        image=parameters['path'] + '/Images/listenResponse.png',
        pos=(0.0, -0.2))
    parameters['listenLogo'].size *= 0.1
    parameters['heartLogo'] = visual.ImageStim(
        win=parameters['win'],
        units='height',
        image=parameters['path'] + '/Images/heartbeat.png',
        pos=(0.0, -0.2))
    parameters['heartLogo'].size *= 0.05

    parameters['textSize'] = 0.04
    parameters['HRcutOff'] = [40, 120]

    return parameters
