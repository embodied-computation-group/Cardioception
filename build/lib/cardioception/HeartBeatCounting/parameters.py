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
    parameters = {'screenNb': 2,
                  'report': True,  # Create reports for each trials
                  'randomize': True,
                  'startKey': 'space',
                  'rating': True}

    # Texts
    parameters['Rest'] = 'Please sit quitely unitil the next session'
    parameters['Count'] = """After the tone, try to count your heart beats
                           by concentrating on you body feelings"""
    parameters['Confidence'] = 'How confident are you about your estimation?'
    parameters['nCount'] = 'How many heartbeats did you count?'

    # Experimental design
    parameters['Conditions'] = ['Rest', 'Rest', 'Count', 'Rest',
                                'Count', 'Rest', 'Count', 'Rest']
    parameters['Times'] = [5, 5, 5, 5, 5, 5, 5]  # [60, 25, 30, 35, 30, 45, 60]

    # Set default path /Results/ 'Subject ID' /
    parameters['subjectID'] = subjectID
    parameters['subjectNumber'] = subjectNumber

    parameters['path'] = os.getcwd()
    parameters['results'] = parameters['path'] + '/' + subjectID
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
    parameters['serial'] = serial.Serial('COM4',
                                         baudrate=9600,
                                         timeout=1/75,
                                         stopbits=1,
                                         parity=serial.PARITY_NONE)

    return parameters
