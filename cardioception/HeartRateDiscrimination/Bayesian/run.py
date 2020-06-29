# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from cardioception.HeartRateDiscrimination.Bayesian.parameters import getParameters
from cardioception.HeartRateDiscrimination.Bayesian.task import run
from psychopy import gui

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("Subject ID:")
g.addField("Subject Number:")
g.addField("Serial Port:")
g.show()
subject = g.data[0]

# Set global task parameters here
parameters = getParameters(g.data[0], g.data[1], g.data[2])

# Run task
results_df = run(parameters, win=parameters['win'], confidenceRating=True,
                 runTutorial=True)
# Save results
results_df.to_csv(parameters['results'] + '/' + subject + '.txt')
parameters['win'].close()
