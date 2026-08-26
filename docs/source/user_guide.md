# User guide

## Installation

### Using pip

```{important}
Install the package as **`cardioception-toolbox`**:

    pip install cardioception-toolbox

This is the official package, maintained by the Embodied Computation Group at Aarhus University. It is the version described in this documentation and used in our publications. Make sure the package name you install is exactly `cardioception-toolbox`.
```

The import name is still `cardioception`, so existing scripts do not need to be edited:

```python
from cardioception.HRD import task
```

### Using GitHub

The current development branch can be installed using:

  `pip install git+https://github.com/embodied-computation-group/Cardioception.git`

This will install the official version maintained by the Embodied Computation Group.

### Set up a conda environment

The `environment.yml` file at the root of the directory describes a complete environment for the task. From the Anaconda prompt, create it with:

  `conda env create -f environment.yml`

This creates a `cardioception` environment, which you can then activate with:

  `conda activate cardioception`

```{note}
If you are using the shortcut method described below, activate the *cardioception* environment rather than the *base* one.
```

## Dependencies

Cardioception requires **Python 3.9**, and only 3.9. `systole-core` needs 3.9 or later, while the pinned PsychoPy cannot be imported on 3.10 or later, so the two constraints meet at a single version. `pip` will refuse to install on anything else. See [issue #92](https://github.com/embodied-computation-group/Cardioception/issues/92) for the plan to widen this.

Make sure that you have the following packages installed and up to date before running cardioception:

* [psychopy](https://www.psychopy.org/) can be installed with `pip install psychopy`.
* [systole](https://github.com/embodied-computation-group/systole) can be installed with `pip install systole-core`.

The other main dependencies are:

* [numpy](https://numpy.org/) (>=1.18,<=1.23)
* [scipy](https://www.scipy.org/) (>=1.3.0)
* [pandas](https://pandas.pydata.org/) (>=1.0.3)
* [pyserial](https://pypi.org/project/pyserial/) (>=3.4)

The functions that build the HTML reports also require:

* [papermill](https://papermill.readthedocs.io/en/latest/) (>=2.3.1)
* [matplotlib](https://matplotlib.org/) (>=3.3.3)
* [seaborn](https://seaborn.pydata.org/) (>=0.11.1)
* [pingouin](https://pingouin-stats.org/) (>=0.3.10)
* [metadpy](https://github.com/EmbodiedComputationGroup/metadpy) (>=0.1.0)
* [pymc](https://www.pymc.io/welcome.html) (>=5.0)

```{note}
The versions listed here are the ones we use when testing and running cardioception locally, and are usually the most recent. For several packages, older versions work as well.
```

Cardioception copies the images and sound files the tasks need (~ 160 Mo). Uninstalling the package removes them.

## Physiological recording

Both the Heartbeat Counting task (HBC) and the Heart Rate Discrimination task (HRD) need a physiological recording device during the task, either to estimate the heart rate or to count the number of heartbeats in a given time window. Cardioception natively supports:

* The [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/) 
* Remote Data Access (RDA) via BrainVision Recorder together with [Brain product ExG amplifier](https://www.brainproducts.com/).

You can add other devices by writing a recording class that interfaces with your own hardware (ECG, pulse oximeters, or any kind of recording that gives a precise estimate of the cardiac frequency).

## Running the tasks

Each task has a `parameters` submodule holding the experimental parameters and a `task` submodule holding the Psychopy script. Most adaptations can be made by passing arguments to the parameters function. See the API documentation for details.

### Using a script

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

### Creating a shortcut (Windows)

Once you have adapted the scripts, you can create a shortcut (on the Desktop, say) so the task starts with a click, without any coding or command line interaction.

On Windows, create a `.bat` file containing the following:

```bash
call [path to your environment */conda.bat] activate
[path to your local */python.exe] [path to your wrapper */hrd.py]
pause
```

## Creating HTML reports

Results are saved in the `'resultPath'` folder defined in the parameters dictionary. Each task comes with a notebook covering the main results, quality checks, and basic preprocessing steps. To generate the HTML report:

```python
from cardioception.reports import report

resultPath = "./"  # the folder containing the result files
reportPath = "./"  # the folder where you want to save the HTML report

report(resultPath, reportPath, task='HRD')
```

This writes the HTML report for the Heart Rate Discrimination task into `reportPath`, using the result files found in `resultPath`. It requires [papermill](https://papermill.readthedocs.io/en/latest/).
