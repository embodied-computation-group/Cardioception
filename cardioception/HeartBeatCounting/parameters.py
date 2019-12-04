# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
import numpy as np
from psychopy import visual, sound


def getParameters(subjectID, subjectNumber, serialPort):
    """Create task parameters.

    Parameters
    ----------
    subjectID : str
        Subject identifiant.
    subjectNumber : int
        Participant number.
    serialPort: str
        The USB port where the pulse oximeter is plugged.

    Attributes
    ----------
    restPeriod : boolean
        If `True`, a resting period will be proposed before the task.
    restLength : int
        The length of the resting period (seconds). Default is 300 seconds.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    randomize : boolean
        If `True` (default), will randomize the order of the conditions. If
        taskVersion is not None, will use the default task parameter instead.
    startKey : str
        The key to press to start the task and go to next steps.
    rating : boolean
        If `True` (default), will add a rating scale after the evaluation.
    confScale : list
        The range of the confidence rating scale.
    labelsRating : list
        The labels of the confidence rating scale.
    taskVersion : str | None
        Task version to run. Can be 'Garfinkel', 'Shandry' or None.
    times : array of int
        Length of trials, in seconds.
    conditions : array of str
        The conditions. Can be 'Rest', 'Training' or 'Count'.
    subjectID : str
        Subject identifiant.
    subjectNumber : int
        Subject reference number.
    path : str
        The task working directory.
    results : str
        The subject result directory.
    note : psychopy sound instance
        The sound played at trial start and trial end.
    win : Psychopy window
        The window where to run the task.
    serial : PySerial instance
        The serial port used to record the PPG activity.
    restLogo : psychopy visual
        Image presented during resting conditions.
    heartLogo : psychopy visual
        Image presented during resting conditions.
    texts : dict
        Dictionnary containing the texts to be presented.
    """
    parameters = dict()
    parameters['restPeriod'] = True
    parameters['restLength'] = 10
    parameters['screenNb'] = 0
    parameters['randomize'] = True,
    parameters['startKey'] = 'space',
    parameters['rating'] = True,
    parameters['confScale'] = [1, 7],
    parameters['labelsRating'] = ['Guess', 'Certain']
    parameters['taskVersion'] = 'Garfinkel'

    # Experimental design
    if parameters['taskVersion'] == 'Garfinkel':
        parameters['times'] = np.array([25, 30, 35, 40, 45, 50])
        np.random.shuffle(parameters['times'])
        parameters['times'] = np.insert(parameters['times'], 0, 20)
        parameters['conditions'] = ['Training', 'Count', 'Count', 'Count',
                                    'Count', 'Count', 'Count']

    elif parameters['taskVersion'] == 'Shandry':
        parameters['times'] = np.array([60, 25, 30, 35, 30, 45])
        parameters['conditions'] = ['Rest', 'Count', 'Rest', 'Count', 'Rest',
                                    'Count']

    # Set default path /Results/ 'Subject ID' /
    parameters['subjectID'] = subjectID
    parameters['subjectNumber'] = subjectNumber

    parameters['path'] = os.getcwd()
    parameters['results'] = parameters['path'] + '/Results/' + subjectID + '/'
    # Create Results directory of not already exists
    if not os.path.exists(parameters['results']):
        os.makedirs(parameters['results'])

    # Set note played at trial start
    parameters['noteStart'] = \
        sound.Sound(parameters['path'] + '/Sounds/start.wav')
    parameters['noteEnd'] = \
        sound.Sound(parameters['path'] + '/Sounds/stop.wav')

    # Open window
    parameters['win'] = visual.Window(screen=parameters['screenNb'],
                                      fullscr=True,
                                      units='height')
    parameters['win'].mouseVisible = False

    # Serial port - Create the recording instance
    parameters['serial'] = serial.Serial(serialPort)

    parameters['restLogo'] = visual.ImageStim(
                        win=parameters['win'],
                        units='height',
                        image=parameters['path'] + '/Images/rest.png',
                        pos=(0.0, -0.2))
    parameters['restLogo'].size *= 0.15
    parameters['heartLogo'] = visual.ImageStim(
                            win=parameters['win'],
                            units='height',
                            image=parameters['path'] + '/Images/heartbeat.png',
                            pos=(0.0, -0.2))
    parameters['heartLogo'].size *= 0.05

    #######
    # Texts
    #######

    # Task instructions
    parameters['texts'] = dict()
    parameters['texts']['Rest'] = 'Please sit quitely unitil the next session'
    parameters['texts']['Count'] = (
        "After you hear start, try to count your heartbeats"
        " by concentrating on your body feelings")
    parameters['texts']['Training'] = (
        "After the tone, try to count your heartbeats"
        " by concentrating on your body feelings")
    parameters['texts']['nCount'] = "How many heartbeats did you count?"
    parameters['texts']['confidence'] = (
        "How confident are you about your count?")

    # Tutorial instructions
    parameters['texts']['Tutorial1'] = (
                "During this experiment, we will ask you to silently"
                " count your heartbeats for different intervals of time.")
    parameters['texts']['Tutorial2'] = (
         "When you see this \"heart\" icon, you will silently count your"
         " heartbeats by focusing on your body sensations.")
    parameters['texts']['Tutorial3'] = (
        "Sometime, you will also encounter this \"rest\" icon."
        " In this case your task will just be to sit quietly until the next"
        " session.")
    parameters['texts']['Tutorial4'] = (
        "The beginning and the end of the task will be signalled when you hear"
        " the words 'start'' and 'stop'. While counting your heartbeats, you"
        " may close your eyes if you find that helpful. Please keep your hand"
        " still during the counting period, to avoid interfering with"
        " the heartbeat recording.")
    parameters['texts']['Tutorial5'] = (
        "After the counting part of the task, you will be asked to report the"
        " exact number of heartbeats you felt during the interval between"
        " 'start' and 'stop'. Please do not try to estimate the number of"
        " heartbeats, but instead only report the heartbeats you actually felt"
        " during the interval. You will input your response using the number"
        " pad and press return when done. You can also correct your response"
        " using backspace.")
    parameters['texts']['Tutorial6'] = (
        "Once you have made your response, you will estimate your subjective"
        " feeling of confidence in how accurate your count was"
        " for that interval. A large number here means that you are totally"
        " certain you counted the exact number of heartbeats that occured,"
        " and a small number means that you are totally uncertain in the"
        " number of heartbeats. You should use the RIGHT and LEFT"
        " key to select your response and the DOWN key to confirm.")
    parameters['texts']['Tutorial7'] = (
        "Before the main task begins there is a short resting period of"
        " five minutes, during which we will calibrate the heartbeat"
        " recording. During this period, please sit quietly with your"
        " hands still to avoid intefering with the calibration."
        " Afterwards the counting task will begin, and will take about"
        " 6 minutes in total. You will now complete a short practice task."
        " Please ask the experimenter if you have any questions before"
        " continuing to the main experiment.")

    return parameters
