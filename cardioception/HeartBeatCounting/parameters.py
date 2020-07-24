# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
import numpy as np
import pandas as pd
from psychopy import visual, sound, core
from systole import serialSim
from systole.recording import findOximeter, Oximeter


def getParameters(participant='SubjectTest', session='001', serialPort=None,
                  taskVersion='Garfinkel', setup='behavioral', screenNb=0,
                  fullscr=True):
    """Create Heartbeat Counting task parameters.

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
    taskVersion : str or None
        Task version to run. Can be 'Garfinkel', 'Shandry', 'test' or None.
    setup : str
        Context of oximeter recording. Behavioral will record through a Nonin
        pulse oximeter, *fMRI* will record through BrainVision amplifier
        through TCP/IP conneciton. *test* will use pre-recorded pulse time
        series (for testing only).

    Attributes
    ----------
    restPeriod : bool
        If *True*, a resting period will be proposed before the task.
    restLength : int
        The length of the resting period (seconds). Default is 300 seconds.
    screenNb : int
        The screen number (Psychopy parameter). Default set to 0.
    randomize : bool
        If `True` (default), will randomize the order of the conditions. If
        taskVersion is not None, will use the default task parameter instead.
    startKey : str
        The key to press to start the task and go to next steps.
    rating : bool
        If `True` (default), will add a rating scale after the evaluation.
    confScale : list
        The range of the confidence rating scale.
    labelsRating : list
        The labels of the confidence rating scale.
    taskVersion : str or None
        Task version to run. Can be 'Garfinkel', 'Shandry' or None.
    times : 1d array-like of int
        Length of trials, in seconds.
    conditions : 1d array-like of str
        The conditions. Can be 'Rest', 'Training' or 'Count'.
    subjectID : str
        Subject identifiant.
    subjectNumber : int
        Subject reference number.
    path : str
        The task working directory.
    results : str
        The subject result directory.
    note : `psychopy.sound`
        The sound played at trial start and trial end.
    win : `psychopy.visual.Window`
        Window where to present stimuli.
    serial : `serial.Serial`
        The serial port used to record the PPG activity.
    restLogo : `psychopy.visual.ImageStim`
        Image presented during resting conditions.
    heartLogo : `psychopy.visual.ImageStim`
        Image presented during resting conditions.
    texts : dict
        Dictionnary containing the texts to be presented.
    textSize : float
        Text size.
    """
    parameters = dict()
    parameters['restPeriod'] = True
    parameters['restLength'] = 30
    parameters['randomize'] = True
    parameters['startKey'] = 'space'
    parameters['rating'] = True
    parameters['confScale'] = [1, 7]
    parameters['labelsRating'] = ['Guess', 'Certain']
    parameters['taskVersion'] = taskVersion
    parameters['results_df'] = pd.DataFrame({})

    # Experimental design - can choose between a version based on recent
    # papers from Sarah Garfinkel's group, or the classic Schandry approach.
    # The primary difference ebtween the two is the order of trials and the
    # use of resting periods between trials.
    if parameters['taskVersion'] == 'Garfinkel':
        parameters['times'] = np.array([25, 30, 35, 40, 45, 50])
        np.random.shuffle(parameters['times'])
        parameters['conditions'] = ['Count', 'Count', 'Count',
                                    'Count', 'Count', 'Count']

    elif parameters['taskVersion'] == 'Schandry':
        parameters['times'] = np.array([60, 25, 30, 35, 30, 45])
        parameters['conditions'] = ['Rest', 'Count', 'Rest', 'Count', 'Rest',
                                    'Count']

    elif parameters['taskVersion'] == 'test':
        parameters['times'] = np.array([5, 5])
        parameters['conditions'] = ['Rest', 'Count']
    else:
        raise ValueError('Invalid task condition')

    # Set default path /Results/ 'Subject ID' /
    # Set default path /Results/ 'Subject ID' /
    parameters['participant'] = participant
    parameters['session'] = session
    parameters['path'] = os.getcwd()
    parameters['results'] = \
        parameters['path'] + '/data/' + participant + session

    # Create Results directory of not already exists
    if not os.path.exists(parameters['results']):
        os.makedirs(parameters['results'])

    # Set note played at trial start
    parameters['noteStart'] = \
        sound.Sound(parameters['path'] + '/Sounds/start.wav')
    parameters['noteEnd'] = \
        sound.Sound(parameters['path'] + '/Sounds/stop.wav')

    # Open window
    parameters['win'] = visual.Window(screen=screenNb, fullscr=fullscr,
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

    # Task instructions
    parameters['texts'] = dict()
    parameters['texts']['Rest'] = 'Please sit quietly until the next session'
    parameters['texts']['Count'] = (
        "After you hear START, try to count your heartbeats"
        " by concentrating on your body feelings."
        " Stop counting when you hear STOP")
    parameters['texts']['Training'] = (
        "After you hear START, try to count your heartbeats"
        " by concentrating on your body feelings"
        " Stop counting when you hear STOP")
    parameters['texts']['nCount'] = (
        'How many heartbeats did you count?'
        ' Write a number and press ENTER to validate.')
    parameters['texts']['confidence'] = (
        "How confident are you about your count?"
        'Use the RIGHT/LEFT keys to select and the DOWN key to confirm')

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
        " the words 'START'' and 'STOP'. While counting your heartbeats, you"
        " may close your eyes if you find that helpful. Please keep your hand"
        " still during the counting period, to avoid interfering with"
        " the heartbeat recording.")
    parameters['texts']['Tutorial5'] = (
        "After the counting part of the task, you will be asked to report the"
        " exact number of heartbeats you felt during the interval between"
        " 'START' and 'STOP'. Please do not try to estimate the number of"
        " heartbeats, but instead only report the heartbeats you actually felt"
        " during the interval. You will input your response using the number"
        " pad and press return when done. You can also correct your response"
        " using backspace.")
    parameters['texts']['Tutorial6'] = (
        "Once you have made your response, you will estimate your subjective"
        " feeling of confidence in how accurate your count was"
        " for that interval. A large number here means that you are totally"
        " certain you counted the exact number of heartbeats that occured,"
        " and a small number means that you are totally uncertain or felt that"
        " you were guessing about the"
        " number of heartbeats. You should use the RIGHT and LEFT"
        " key to select your response and the DOWN key to confirm.")
    parameters['texts']['Tutorial7'] = (
        "Before the main task begins there is a short resting period of"
        " several minutes, during which we will calibrate the heartbeat"
        " recording. During this period, please sit quietly with your"
        " hands still to avoid interfering with the calibration."
        " Afterwards, the counting task will begin, and will take about"
        " 6 minutes in total.")
    parameters['texts']['Tutorial8'] = (
        "You will now complete a short practice task."
        " Please ask the experimenter if you have any questions before"
        " continuing to the main experiment.")
    parameters['texts']['Tutorial9'] = (
        "Good job! If you have any question, ask the experimenter now,"
        " otherwise press SPACE to continue to the experiment.")
    parameters['textSize'] = 0.04

    return parameters
