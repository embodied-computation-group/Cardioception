# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import serial
from psychopy import visual, sound


def getParameters(subjectID, subjectNumber):
    """Create task parameters.

    Parameters
    ----------
    subjectID : str
        Subject identifiant.
    subjectNumber : int
        Participant number.
    """
    parameters = {'screenNb': 0,
                  'report': True,  # Create reports for each trials
                  'randomize': True,
                  'startKey': 'space',
                  'rating': True,
                  'confScale': [1, 7],
                  'labelsRating': ['Guess', 'Certain']}

    # Texts
    parameters['Rest'] = 'Please sit quitely unitil the next session'
    parameters['Count'] = """After the tone, try to count your heart beats
                           by concentrating on you body feelings"""
    parameters['Confidence'] = 'How confident are you about your estimation?'
    parameters['nCount'] = 'How many heartbeats did you count?'

    # Tutorial instructions
    parameters['Tutorial1'] = "During this experiment, we will ask you to count your heartbeats for a certain amount of time."
    parameters['Tutorial2'] = "You will encounter two kinds of condition: the first one will be signalled by this \"rest\" icon. Your task here will just be to rest quietly for a certain amount of time."
    parameters['Tutorial3'] = "The second condition will be signalled by this \"heartbeat icon\". You will then have to try to count your heartbeat. "
    parameters['Tutorial4'] = "The beginning and the end of the task will be signalled by two tones like the ones you hear: one prolonged tone at the beginning and two faster tones at the end."
    parameters['Tutorial5'] = "After this period, you will be asked to estimate the exact number of heartbeat you counted during this period. Please enter your response using the number pad and press \"return\" when done. You can also correct your estimation using \"backspace\"."
    parameters['Tutorial6'] = "Once your response has been provided, you will be asked to estimate your level of confidence with this estimation. A large number here means that you are confident with your estimation, a small number means that you are not confident. You should use the RIGHT and LEFT key to select your response and the DOWN key to confirm."
    parameters['Tutorial7'] = "These two conditions will alternate during the task and the amount of time will vary."

    # Experimental design
    parameters['Conditions'] = ['Rest', 'Rest', 'Count', 'Rest',
                                'Count', 'Rest', 'Count', 'Rest']
    parameters['Times'] = [60, 25, 30, 35, 30, 45, 60]

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
    # Serial port
    # Create the recording instance
    parameters['serial'] = serial.Serial('COM4')

    parameters['restLogo'] = visual.ImageStim(
                        win=parameters['win'],
                        image=parameters['path'] + '/Images/rest.png',
                        pos=(0.0, -0.2))
    parameters['restLogo'].size *= 0.15

    parameters['heartLogo'] = visual.ImageStim(
                            win=parameters['win'],
                            image=parameters['path'] + '/Images/heartbeat.png',
                            pos=(0.0, -0.2))
    parameters['heartLogo'].size *= 0.8

    return parameters
