# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
import numpy as np
from psychopy import data, visual


def getParameters(subject):
    """Create task parameters.

    Parameters
    ----------
    subject : str
        Subject ID.

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
        The number of trial with feedback during the tutorial phace (no
        confidence rating).
    nConfidence : int
        The number of trial with feedback during the tutorial phace (no
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
    Condition : 1d-array
        Array of 0s and 1s encoding the conditions (1 : Higher, 0 : Lower). The
        length of the array is defined by `parameters['nTrials']`. If
        `parameters['nTrials']` is odd, will use `parameters['nTrials']` - 1
        to enseure an equal nuber of Higher and Lower conditions.
    stairCase : instance of Psychopy StairHandler
        The staircase object used to adjust the alpha value.
    serial : PySerial instance
        The serial port used to record the PPG activity.
    subject : str
        The subject ID.
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
    parameters['maxRatingTime'] = 3
    parameters['startKey'] = 'space'
    parameters['allowedKeys'] = ['up', 'down']
    parameters['nTrials'] = 5
    parameters['nBeatsLim'] = 5
    parameters['nStaircase'] = 2

    # Create randomized condition vector
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
    parameters['serial'] = serial.Serial('COM8')

    # Set default path /Results/ 'Subject ID' /
    parameters['subject'] = subject
    parameters['path'] = os.getcwd()
    parameters['results'] = parameters['path'] + '/Results/' + subject

    # Create Results directory of not already exists
    if not os.path.exists(parameters['results']):
        os.makedirs(parameters['results'])

    # Texts
    parameters['texts'] = {
        'Estimation': """Do you think the flash frequency
        was higher or lower than your heart rate?""",
        'Confidence': 'How confident are you about your estimation?'}

    parameters['Tutorial1'] = (
        "During this experiment, we are going to record your heart rate and"
        " generate sounds reflecting your cardiac activity.")

    parameters['Tutorial2'] = (
        "When this heart icon is presented, you will have to focus on your"
        " cardiac activity while it is recorded for 5 seconds.")

    parameters['Tutorial3'] = (
        "After this procedure, you will be presented with the listening and"
        " response icons. You will then have to focus on the beats frequency"
        " and decide if it is faster than your heart rate as is was previously"
        " recorded (UP key) or slower (DOWN key). This beating frequency will"
        " ALWAYS be slower or faster than your heart rate as previously"
        " recorded.")

    parameters['Tutorial4'] = (
        "Once you have provided your estimation, you will also be asked to"
        " provide your level of confidence. A large number here means that"
        " you are confident with your estimation, a small number means that"
        " you are not confident. You should use the RIGHT and LEFT key to"
        " select your response and the DOWN key to confirm.")

    parameters['Tutorial5'] = (
        "This sequence will be repeated during the task. As you will improve"
        " your ability to discriminate between FASTER and SLOWER conditions,"
        " the difficulty will also adaptively improve, meaning that the"
        " difference between your True heart rate and the beats you hear will"
        " get smaller and smaller.")

    # Open window
    parameters['win'] = visual.Window(monitor=parameters['monitor'],
                                      screen=parameters['screenNb'],
                                      fullscr=True, units='height')

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

    return parameters
