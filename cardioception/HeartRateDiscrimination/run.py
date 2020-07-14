# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

from parameters import getParameters
from task import run
from psychopy import gui

# Create a GUI and store subject ID
g = gui.Dlg()
g.addField("participant", initial='test')
g.addField("session", initial='001')
g.addField("Serial Port:", initial=None)
g.addField("Setup:", initial='behavioral')
g.addField("stairType:", initial='psi')
g.addField("BrainVisionIP:", initial='10.60.88.162')
g.show()

# Set global task parameters here
parameters = getParameters(g.data[0], g.data[1], g.data[2],  g.data[3],
                           g.data[4],  g.data[5])

# Run task
results_df = run(parameters, win=parameters['win'], confidenceRating=True,
                 runTutorial=True)

# Save results
results_df.to_csv(parameters['results'] + '/' + g.data[0] + '.txt')
parameters['win'].close()
