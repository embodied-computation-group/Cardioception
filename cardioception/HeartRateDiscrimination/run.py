# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartRateDiscrimination.parameters import getParameters
from cardioception.HeartRateDiscrimination.task import run
from psychopy import gui

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("Subject ID:")
g.show()
subject = g.data[0]

# Set global task parameters here
parameters = getParameters(subject)

# parameters['win'].close()
# from cardioception.recording import Oximeter
# oxiTask = Oximeter(serial=parameters['serial'], sfreq=75, add_channels=1)
# oxiTask.setup()
# oxiTask.read(duration=1)

# Run task
results_df = run(parameters, win=parameters['win'], confidenceRating=True,
                 runTutorial=False)
# Save results
results_df.to_csv(parameters['results'] + '/' + subject + '.txt')
parameters['win'].close()
