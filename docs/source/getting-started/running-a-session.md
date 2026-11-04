---
myst:
  html_meta:
    description: "How to run a Cardioception session: the parameters and task submodules, a script, the ready-made wrappers, instruction languages and a Windows shortcut."
    keywords: "cardioception, run a session, PsychoPy script, wrappers, heart rate discrimination, heartbeat counting, interoception task"
---

# Running a session

Each task has a `parameters` submodule holding the experiment's parameters and a `task` submodule holding the Psychopy script. Most adaptations can be made by passing arguments to the parameters function. See the API documentation for details.

Each task's own page covers its procedure: [the HRD](../tasks/hrd/running.md), [the HBC](../tasks/hbc.md), [the PAT](../tasks/pat.md#running-the-task) and [the HSD](../tasks/hsd/running.md).

## Using a script

Once the package is installed, you can run a task (here the Heart Rate Discrimination task) with the following code snippet:

```python
from cardioception.HRD.parameters import getParameters
from cardioception.HRD import task

# Set global task parameters
parameters = getParameters(
    participant='Subject_01', session='Test', serialPort=None,
    setup='behavioral', nTrials=10, screenNb=0)

# Run task
task.run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()
```

This minimal example runs the Heart Rate Discrimination task with 10 trials and a Psi staircase.

Standard scripts are available in the [wrappers](https://github.com/embodied-computation-group/Cardioception/tree/master/wrappers) folder. Copy the one you need into your local task folder and edit it there. A task can then be run by executing its wrapper file, for example from a terminal.

The instructions are shown in the language passed as `language`. The Heart Rate Discrimination task accepts `"english"` (the default), `"danish"`, `"danish_children"`, `"french"` or `"german"`, and the Heartbeat Counting task accepts `"english"` (the default) or `"german"`. The confidence scale's end labels follow the language unless you pass your own `confidenceScale`. An unknown language stops the task before a window opens, with an error that lists the languages there are.

## Creating a shortcut (Windows)

Once you have adapted the scripts, you can create a shortcut (on the Desktop, say) so the task starts with a click, without any coding or command line interaction.

On Windows, create a `.bat` file containing the following:

```bash
call [path to your environment */conda.bat] activate
[path to your local */python.exe] [path to your wrapper */hrd.py]
pause
```

```{note}
If you use the [conda route](installation.md#the-conda-route), activate the *cardioception* environment rather than the *base* one.
```
