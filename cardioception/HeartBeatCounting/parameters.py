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
    parameters['note'] = sound.backend_sounddevice.SoundDeviceSound(secs=0.5)

    # Open window
    parameters['win'] = visual.Window(screen=parameters['screenNb'],
                                      fullscr=True,
                                      units='height')

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
        "After the tone, try to count your heart beats"
        " by concentrating on your body feelings")
    parameters['texts']['Training'] = (
        "After the tone, try to count your heart beats"
        " by concentrating on your body feelings")
    parameters['texts']['nCount'] = "How many heartbeats did you count?"
    parameters['texts']['confidence'] = (
        "How confident are you about your estimation?")

    # Tutorial instructions
    parameters['texts']['Tutorial1'] = (
                "During this experiment, we will ask you to"
                " count your heartbeats for a certain amount of time.")
    parameters['texts']['Tutorial2'] = (
        "You will encounter two kinds of condition: the first one will be"
        " signalled by this \"rest\" icon. Your task here will just be to rest"
        " quietly for a certain amount of time.")
    parameters['texts']['Tutorial3'] = (
        "The second condition will be signalled by this"
        " \"heartbeat\" icon. You will then have to try"
        " to count your heartbeat.")
    parameters['texts']['Tutorial4'] = (
        "The beginning and the end of the task will be signalled by two tones"
        " like the ones you hear: one prolonged tone at the beginning and two"
        " faster tones at the end.")
    parameters['texts']['Tutorial5'] = (
        "After this period, you will be asked to estimate the exact number of"
        " heartbeat you counted during this period. Please enter your response"
        " using the number pad and press return when done. You can also"
        " correct your estimation using backspace.")
    parameters['texts']['Tutorial6'] = (
        "Once your response has been provided, you will be asked to estimate"
        " your level of confidence with this estimation. A large number here"
        " means that you are confident with your estimation, a small number"
        " means that you are not confident. You should use the RIGHT and LEFT"
        " key to select your response and the DOWN key to confirm.")
    parameters['texts']['Tutorial7'] = (
        "These two conditions will alternate during the task and the amount"
        " of time will vary.")

    return parameters
