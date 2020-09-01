    # Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from task import run
from parameters import getParameters
from psychopy import gui

# Create a GUI and ask for high-evel experiment parameters
g = gui.Dlg()
g.addField("participant", initial='Participant')
g.addField("session", initial='HBC')
g.addField("Serial Port:", initial='COM3')
g.addField("Setup:", initial='behavioral')
g.show()

# Get parameters
# Set global task parameters here
parameters = getParameters(
    participant=g.data[0], session=g.data[1], serialPort=g.data[2],
    setup=g.data[3], screenNb=0)

# Run task
run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()

# Saving in AUX drives
try:
    from zipfile import ZipFile
    import os
    
    sub = parameters['participant']
    sess = parameters['session']
    resultsPath = f'C:/Users/stimuser/Desktop/data/{sub}{sess}/'
    resultsFiles = os.listdir(resultsPath)
    
    if not os.path.exists(f'Z:/MINDLAB2019_Visceral-Mind/1_VMP_aux/sub_{sub}/'):
        os.makedirs(f'Z:/MINDLAB2019_Visceral-Mind/1_VMP_aux/sub_{sub}/')

    # Create a ZipFile Object
    zipPath = f'Z:/MINDLAB2019_Visceral-Mind/1_VMP_aux/sub_{sub}/HBC.zip'
    with ZipFile(zipPath, 'w') as zipObj2:
        for file in resultsFiles:
           # Add multiple files to the zip
           zipObj2.write(resultsPath + '/' + file)
except:
    print('Cant save to AUX drive')

