# User guide

## Installation

### Using the Python Package Index

* The most recent version can be installed uing:

  `pip install cardioception`

* The current development branch can be installed using:

  `pip install git+https://github.com/embodied-computation-group/Cardioception.git`

### Set up a conda environment

The task can be installed in a new environment using the `environment.yml` file that you can find at the root of the directory. Using the Anaconda prompt, you can create a new environment with:

  `conda env create -f environment.yml`

This will create a new `cardioception` environment that you can later activate using:

  `conda activate cardioception`

```{note} If you are using the shortcut method described bellow, you will have to activate the *cardioception* environment instead of the *base* one.
```

## Dependencies

Cardioception has been tested with Python 3.7. We recommend to use the last install of Anaconda for Python 3.7 or latest (see [this link](https://www.anaconda.com/products/individual#download-section)).

Make sure that you have the following packages installed and up to date before running cardioception:

* [psychopy](https://www.psychopy.org/) can be installed with `pip install psychopy`.
* [systole](https://systole-docs.github.io/) can be installed with `pip install systole`.

The other main dependencies are:

* [numpy](https://numpy.org/) (>=1.18,<=1.23)
* [scipy](https://www.scipy.org/) (>=1.3.0)
* [pandas](https://pandas.pydata.org/) (>=1.0.3)
* [pyserial](https://pypi.org/project/pyserial/) (>=3.4)

In addition, some function for HTML reports will require:

* [papermill](https://papermill.readthedocs.io/en/latest/) (>=2.3.1)
* [matplotlib](https://matplotlib.org/) (>=3.3.3)
* [seaborn](https://seaborn.pydata.org/) (>=0.11.1)
* [pingouin](https://pingouin-stats.org/) (>=0.3.10)
* [metadpy](https://github.com/EmbodiedComputationGroup/metadpy) (>=0.1.0)
* [pymc](https://www.pymc.io/welcome.html) (>=5.0)

```{note}
The version provided here are the ones used when testing and runing cardioception locally, and are often the last ones. For several packages however, older version might also be compatibles. 
```

Cardioception will automatically copy the images and sound files necessary to run the task correctly (~ 160 Mo). These files will be removed if you uninstall the package using `pip uninstall cardioception`.

## Physiological recording

Both the Heartbeat counting task (HBC) and the heart rate discrimination task (HRD) require access to physiological recording device during the task to estimate the heart rate or count the number of heartbeats in a given time window. Cardioception natively supports:

* The [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/) 
* Remote Data Access (RDA) via BrainVision Recorder together with [Brain product ExG amplifier](https://www.brainproducts.com/>).

The package can easily be extended and integrate other recording devices by providing another recording class that will interface with your own devices (ECG, pulse oximeters, or any king of recording that will offer precise estimation of the cardiac frequency).

## Running the tasks

Each task contains a `parameters` and a `task` submodule describing the experimental parameters and the Psychopy script respectively. Several changes and adaptation can be parametrized just by passing arguments to the parameters functions. Please refer to the API documentation for details.

### Using a script

Once the package has been installed, you can run the task (e.g. here the Heart rate Discrimination task) using the following code snippet:

```python
from cardioception.HRD.parameters import getParameters
from cardioception.HRD import task

# Set global task parameters
parameters = parameters.getParameters(
    participant='Subject_01', session='Test', serialPort=None,
    setup='behavioral', nTrials=10, screenNb=0)

# Run task
task.run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()
```

This minimal example will run the Heart Rate Discrimination task with a total of 10 trials using a Psi staircase.

We provide standard scripts in the [wrappers](https://github.com/embodied-computation-group/Cardioception/tree/master/wrappers) folder that can be adapted to your needs. We recommend copying this script in your local task folder if you want to parametrize it to fit your needs. The tasks can then easily be executed by running the corresponding wrapper file (e.g in a terminal).

### Creating a shortcut (Windows)

Once you have adapted the scripts, you can create a shortcut (e.g in the Desktop) so the task can be executed just by clicking on it without any coding or command lines interactions.

If you are using Windows, you can simply create a `.bat` file containing the following:

```bash
call [path to your environment */conda.bat] activate
[path to your local */python.exe] [path to your wrapper */hrd.py]
pause
```

## Creating HTML reports

The results are saved in the `'resultPath'` folder defined in the parameters dictionary. For each task, we provide a comprehensive notebook detailing the main results, quality checks, and basic preprocessing steps. You can automatically generate the HTML reports using the following code snippet:

```python
from cardioception.reports import report

resultPath = "./"  # the folder containing the result files
reportPath = "./"  # the folder where you want to save the HTML report

report(resultPath, reportPath, task='HRD')
```

This code will generate the HTML reports for the Heart Rate Discrimination task in the `reportPath` folder using the results files located in `resultPath`. This will require [papermill](https://papermill.readthedocs.io/en/latest/).
