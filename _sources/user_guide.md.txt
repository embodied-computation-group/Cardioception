
## Do you need help?

If you have questions regarding the tasks, want to report a bug or discuss data analysis, please ask on our public [![Gitter](https://badges.gitter.im/Cardioception/community.svg)](https://gitter.im/Cardioception/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge).

# Installation
**Using the Python Package Index**
* The most recent version can be installed uing:
    `pip install cardioception`
* The current development branch can be installed using 
  `pip install git+https://github.com/embodied-computation-group/Cardioception.git`

**Downloading the ZIP file**

<img src="./images/downloadZIP.png" align="left" alt="metadPy" height="200" HSPACE=30>

You can also download the most recent version by downloading the repository as a .zip file.

After extracting the content of the file, the package can be installed via the command line by running `pip install .`. Note that this command should be executed when your terminal run inside the extracted folder. You can navigate through your local folder using the command `cd [path to your folder]`.

<br clear="left"/>

## Dependencies

Cardioception has been tested with Python 3.7. We recommend to use the last install of Anaconda for Python 3.7 or latest (see https://www.anaconda.com/products/individual#download-section).

Make sure that you have the following packages installed and up to date before running cardioception:

* [psychopy](https://www.psychopy.org/) can be installed with `pip install psychopy`.

* [systole](https://systole-docs.github.io/) can be installed with `pip install systole`.

The other main dependencies are:

* [numpy](https://numpy.org/) (>=1.19.4)
* [scipy](https://www.scipy.org/) (>=1.3.0)
* [pandas](https://pandas.pydata.org/) (>=1.0.3)
* [pyserial](https://pypi.org/project/pyserial/) (>=3.4)

In addition, some function for HTML reports will require:

* [papermill](https://papermill.readthedocs.io/en/latest/) (>=2.3.1)
* [matplotlib](https://matplotlib.org/) (>=3.3.3)
* [seaborn](https://seaborn.pydata.org/) (>=0.11.1)
* [pingouin](https://pingouin-stats.org/) (>=0.3.10)
* [metadPy](https://github.com/LegrandNico/metadPy) (>=0.01)

**NOTE**
The version provided here are the ones used when testing and runing cardioception locally, and are often the last ones. For several packages however, older version might also be compatibles. 

Cardioception will automatically copy the images and sound files necessary to run the task correctly (~ 160 Mo). These files will be removed if you uninstall the package using `pip uninstall cardioception`.

# Package modularity
## Physiological recording

Both the Heartbeat counting task (HBC) and the heart rate discrimination task (HRD) require access to physiological recording device during the task to estimate the heart rate or count the number of heartbeats in a given time window. Cardioception natively supports:
* The [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/) 
* Remote Data Access (RDA) via BrainVision Recorder together with [Brain product ExG amplifier](https://www.brainproducts.com/>).

The package can easily be extended and integrate other recording devices by providing another recording class that will interface with your own devices (ECG, pulse oximeters, or any king of recording that will offer precise estimation of the cardiac frequency).

# Run the tasks

Each task contains a `parameters` and a `task` submodule describing the experimental parameters and the Psychopy script respectively. Several changes and adaptation can be parametrized just by passing arguments to the parameters functions. Please refer to the API documentation for details.

## Using a script

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

## Creating a shortcut (Windows)

Once you have adapted the scripts, you can create a shortcut (e.g in the Desktop) so the task can be executed just by clicking on it without any coding or command lines interactions.

If you are using Windows, you can simply create a `.bat` file containing the following:

```
call [path to your environment */conda.bat] activate
[path to your local */python.exe] [path to your wrapper */hrd.py]
pause
```

# Tasks

## The Heartbeat Counting task

<img src= "./images/HeartBeatCounting.png">

This module is an implementation of the classic "heartbeat counting task" (HCT)<sup>1,2</sup> in which participants attend to their heartbeats in intervals of various lengths. Afterward, the participant indicates the number of counted heartbeats, and a score is computed to represent their accuracy. In the original version<sup>1</sup>, the task started with a resting period of 60 seconds and consisted of three estimation session (25, 35, and 45 seconds) interleaved with resting periods of 30 seconds in the following order:

By default, this task implements the version used in recent publications <sup>4, 5</sup> in which a training trial of 20 seconds is proposed, after which the 6 experimental trials of different time windows (25, 30, 35,40, 45 and 50s) occurred in a randomized order. The trial length, the condition ('Rest', 'Count', 'Training'), and the randomization can be controlled in the parameters dictionary.

## The Heart Rate Discrimination task

<img src= "./images/HeartRateDiscrimination.png">

This task implements an adaptive psychophysical procedure for estimating participants' ability to discriminate their heart rate. On each trial, participants attend to their heartbeat sensations for five seconds and estimate their average heart rate. Immediately following this period, a cardiac feedback stimulus of 5 tones is played at a particular BPM frequency. The frequency is determined as their estimated average BPM plus or minus an intensity value that is updated by an adaptive staircase procedure (up/down or psi).
