[![GitHub license](https://img.shields.io/github/license/embodied-computation-group/Cardioception)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![GitHub release](https://img.shields.io/github/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit) [![pip](https://badge.fury.io/py/cardioception.svg)](https://badge.fury.io/py/cardioception) [![travis](https://travis-ci.com/embodied-computation-group/Cardioception.svg?token=nsE8eGgm9VmJ11Ep64Di&branch=master)](https://travis-ci.com/embodied-computation-group/Cardioception) [![codecov](https://codecov.io/gh/embodied-computation-group/Cardioception/branch/master/graph/badge.svg)](https://codecov.io/gh/embodied-computation-group/Cardioception) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)


# Cardioception

The Cardioception Python Package - Measuring Interoception with Psychopy - implements two measures of cardiac interoception (cardioception):
1. The *Heartbeat counting task* developed by Rainer Schandry<sup>1,2</sup>
2. a novel *Heart Rate Discrimination Task* implementing an adaptive psychophysical measure for measuring cardioception.

Currently the toolbox natively supports the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/) as well as Remote Data Access (RDA) via BrainVision Recorder together with Brain product ExG amplifier [](https://www.brainproducts.com/>).

# Installation

* Cardioception can be installed using pip:
  `pip install cardioception`.

## Dependencies

We recommend to use the last install of Anaconda for Python 3.8 or latest (see https://www.anaconda.com/products/individual#download-section).

The following packages should be installed:

* [Psychopy](https://www.psychopy.org/) can be installed using pip:
  `pip install psychopy`.

* [Systole](https://systole-docs.github.io/) can be installed using pip:
  `pip install systole`.

Notes: Cardioception will automatically copy the images and sound files necessary to run the task correctly (~ 200 Mo). These files will be removed if you uninstall the package using `pip uninstall cardioception`.

## Run tasks

Each task contains a `parameters` and a `task` submodule describing the experimental parameters and the Psychopy script respectively. Once the package has been installed, you can run the task (e.g. here the Heart rate Discrimination task) using the following code snippet:

```python
from cardioception.HRD import parameters, task

# Set global task parameters
parameters = parameters.getParameters(
    participant='Subject_01', session='Test', serialPort=None,
    setup='behavioral', nTrials=10, nTrialsUpDown=4, screenNb=0)

# Run task
task.run(parameters, confidenceRating=True, runTutorial=True)

parameters['win'].close()
```

This will run the Heart Rate Discrimination task wth a total of 10 trials (4 using an 1-Up/1-Down starcase, and 6 using a Psi staircase).
## Creating a shortcut

The tasks can easily be executed by running the corresponding `launcher.py` file in a console. It is also possible to create a shortcut (eg. in the Desktop) to facilitate its use in experimental context.

In Windows, you can simply create a `.bat` file containing the following:

```
conda activate
[path to your local Python .exe] [path to your launcher.py]
pause
```

# Tasks

## The Heartbeat Counting task

<img src= "images/HeartBeatCounting.png">

This module is an implementation of the classic "heartbeat counting task" (HCT)<sup>1,2</sup> in which participants attend to their heartbeats in intervals of various length. Afterwards the participant indicates the number of counted heartbeats and a score is computed to represent their accuracy. In the original version<sup>1</sup>, the task started with a resting period of 60 seconds and consisted in three estimation session (25, 35 and 45 seconds) interleaved with resting periods of 30 seconds in the following order:

By default, this task implement the version used in recent publications <sup>3</sup> in which a training trial of 20s is proposed, after which the 6 experimental trials of different time-windows (25, 30, 35,40, 45 and 50s) occurred in a randomized order. The trial length, the condition ('Rest', 'Count', 'Training') and the randomization can be controlled in the parameters dictionary.


## The Heartbeat Discrimination task


## The Heart Rate Discrimination task

<img src= "images/HeartRateDiscrimination.png">

This task implements an adaptive psychophysical procedure for estimating participant ability to discriminate their own heart-rate. On each trial, participants attend to their heartbeat sensations for five seconds and estimate their average heartrate. Immediately following this period, a cardiac feedback stimulus of 5 tones is played at a particular BPM frequency. The frequency is determined as their estimate average BPM plus or minus an intensity value that is updated by an adaptive staircase procedure (up/down or psi).

# Analyses

By default, the results will be saved in the `data` folder contained in each task folder.

The `notebooks` folder includes Jupyter notebooks documenting the recommended analyses steps for each tasks that can be used to generate reports.

# Generate reports

The notebooks provided in the `/notebooks` folder can be used as templates to generate reports for each participants using the following code snippet. This will require the last version of [papermill](https://papermill.readthedocs.io/en/latest/).

```python
import papermill as pm
import subprocess
import os

dataPath = ''  # Folder where are stored the results
reportsPath = ''  # Folder where to store the reports
notebookTemplate = ''  # Notebook template (eg. HeartRateDiscrimination.ipynb)

subjects = os.listdir(dataPath)
for sub in subjects:

    pm.execute_notebook(notebookTemplate, reportsPath + sub + '.ipynb',
                        parameters=dict(subject=sub, path=dataPath))

    command = f'jupyter nbconvert {reportsPath}{sub}.ipynb --output ' + \
        '{reportsPath}{sub}_report.html --no-input --to html'
    subprocess.call(command)
```

# References

1. Dale, A., & Anderson, D. (1978). Information Variables in Voluntary Control and Classical Conditioning of Heart Rate: Field Dependence and Heart-Rate Perception. Perceptual and Motor Skills, 47(1), 79–85. https://doi.org/10.2466/pms.1978.47.1.79

2. Schandry, R. (1981). Heart Beat Perception and Emotional Experience. Psychophysiology, 18(4), 483–488. https://doi.org/10.1111/j.1469-8986.1981.tb02486.x

3. Leganes-Fonteneau, M., Cheang, Y., Lam, Y., Garfinkel, S., & Duka, T. (2019). Interoceptive awareness is associated with acute alcohol-induced changes in subjective effects. Pharmacology Biochemistry and Behavior, 181, 69–76. https://doi.org/10.1016/j.pbb.2019.03.007

4. Hart, N., McGowan, J., Minati, L., & Critchley, H. D. (2013). Emotional Regulation and Bodily Sensation: Interoceptive Awareness Is Intact in Borderline Personality Disorder. Journal of Personality Disorders, 27(4), 506–518. https://doi.org/10.1521/pedi_2012_26_049

# Development
This package was created and is maintained by [Nicolas Legrand](https://legrandnico.github.io/) and [Micah Allen](https://micahallen.org/) from the [ECG group](https://the-ecg.org/).

<img src = "images/LabLogo.png" height ="100"><img src = "images/AU.png" height ="100">

# Credit
Some icons used in the Figures or presented during the tasks were downloaded from **Flaticon** [www.flaticon.com](www.flaticon.com).
