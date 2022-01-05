[![GitHub license](https://img.shields.io/github/license/embodied-computation-group/Cardioception)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![GitHub release](https://img.shields.io/github/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit) [![pip](https://badge.fury.io/py/cardioception.svg)](https://badge.fury.io/py/cardioception) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/) [![Gitter](https://badges.gitter.im/Cardioception/community.svg)](https://gitter.im/Cardioception/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

***

# Cardioception

<img src="/images/logo.png" align="left" alt="metadPy" height="230" HSPACE=30>

The Cardioception Python Package - Measuring Interoception with Psychopy - implements two measures of cardiac interoception (cardioception):
1. The **Heartbeat counting task** developed by Rainer Schandry<sup>1,2</sup>. This task cardiac measures interoception by asking participants to count their heartbeats for a given period of time. An accuracy score is then derived by comparing the reported number of heartbeats and the true number of heartbeats.
2. The **Heart Rate Discrimination Task** <sup>3</sup> implementing an adaptive psychophysical measure of cardiac interoception where participants have to estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. By manipulating the difference between the true heart rate and the presented tone using different staircase procedures, the bias (threshold) and precision (slope) of the psychometric function can be estimated either online or offline (see *Analyses* below), together with metacognitive efficiency.

These tasks can run using minimal experimental settings: a computer and a recording device to monitor the heart rate of the participant. The default version of the task use the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). This sensor can be plugged directly into the stim PC via USB and will work with Cardioception without any additional coding required. 

The tasks can also integrate easily with other recording devices and experimental settings (ECG, M/EEG, fMRI...). See *Sending triggers* below for details.

## How to cite?

If you are using cardioception in a publication we ask you to cite the following paper:

>Legrand, N., Nikolova, N., Correa, C., Brændholt, M., Stuckert, A., Kildahl, N., Vejlø, M., Fardo, F., &amp; Allen, M. (2021). The Heart Rate Discrimination Task: A psychophysical method to estimate the accuracy and precision of interoceptive beliefs. Biological Psychology, 108239. https://doi.org/10.1016/j.biopsycho.2021.108239 

If you are using [systole](https://systole-docs.github.io/) to interact with your recording device (this is the default behavior in cardioception), you might also cite the following reference:

> Legrand, N., & Allen, M. (2020). Systole: V 0.1.2—September 2020 (0.1.2) [Computer software]. Zenodo. https://doi.org/10.5281/ZENODO.3607912

## Do you need help?

If you have questions regarding the tasks, want to report a bug or discuss data analysis, please ask on our public [![Gitter](https://badges.gitter.im/Cardioception/community.svg)](https://gitter.im/Cardioception/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge).

# Installation
**Using the Python Package Index**
* The most recent version can be installed uing:
    `pip install cardioception`
* The current development branch can be installed using 
  `pip install git+https://github.com/embodied-computation-group/Cardioception.git`

**Downloading the ZIP file**

<img src="/images/downloadZIP.png" align="left" alt="metadPy" height="200" HSPACE=30>

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

## Sending triggers

The package includes function calls at the beginning and the end of each meaningful trial phase (trial start/end, listening start/end, decision start/end, and confidence rating start/end). These function calls are embedded in the `"triggers"` parameter dictionary.

```python
from cardioception.HRD.parameters import getParameters

parameters = getParameters()
parameters["triggers"]
```
`
{'trialStart': None,
 'trialStop': None,
 'listeningStart': None,
 'listeningStop': None,
 'decisionStart': None,
 'decisionStop': None,
 'confidenceStart': None,
 'confidenceStop': None}
 `

By default, keys are initialized with `None` (no triggers sent). But these values can be overwritten with callable implementing the proper trigger message fitting your setup. This can be done by creating a new function and applying it to the relevant dictionary key.

```python
def sendTrigger(x):
  # Function connecting to your device and sending the
  # required value. For illustration, we are using a simple print call.
  print(f'Send a trigger with value {x}')


# Here we use this function to send triggers with value 1 
# at the begining of the listening phase
# and with value 2 at the end of the listening phase
parameters["triggers"]["listeningStart"] = sendTrigger("1")
parameters["triggers"]["listeningStop"] = sendTrigger("2")
```

Note that we are using the function call (`sendTrigger("1")`) and not the function itself (`sendTrigger`) here.

# Run the tasks

Each task contains a `parameters` and a `task` submodule describing the experimental parameters and the Psychopy script respectively. Several changes and adaptation can be parametrized just by passing arguments to the parameters functions. Please refer to the API documentation for details.

## From the command line

*(forthcoming)*
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

**Creating a shortcut**

Once you have adapted the scripts, you can create a shortcut (e.g in the Desktop) so the task can be executed just by clicking on it without any coding or command lines interactions.

If you are using Windows, you can simply create a `.bat` file containing the following:

```
call [path to your environment */conda.bat] activate
[path to your local */python.exe] [path to your wrapper */hrd.py]
pause
```

# Tasks

## The Heartbeat Counting task

<img src= "images/HeartBeatCounting.png">

This module is an implementation of the classic "heartbeat counting task" (HCT)<sup>1,2</sup> in which participants attend to their heartbeats in intervals of various lengths. Afterward, the participant indicates the number of counted heartbeats, and a score is computed to represent their accuracy. In the original version<sup>1</sup>, the task started with a resting period of 60 seconds and consisted of three estimation session (25, 35, and 45 seconds) interleaved with resting periods of 30 seconds in the following order:

By default, this task implements the version used in recent publications <sup>4, 5</sup> in which a training trial of 20 seconds is proposed, after which the 6 experimental trials of different time windows (25, 30, 35,40, 45 and 50s) occurred in a randomized order. The trial length, the condition ('Rest', 'Count', 'Training'), and the randomization can be controlled in the parameters dictionary.

## The Heart Rate Discrimination task

<img src= "images/HeartRateDiscrimination.png">

This task implements an adaptive psychophysical procedure for estimating participants' ability to discriminate their heart rate. On each trial, participants attend to their heartbeat sensations for five seconds and estimate their average heart rate. Immediately following this period, a cardiac feedback stimulus of 5 tones is played at a particular BPM frequency. The frequency is determined as their estimated average BPM plus or minus an intensity value that is updated by an adaptive staircase procedure (up/down or psi).

# Analyses

## Task reports

The results are saved in the `'resultPath'` folder defined in the parameters dictionary. For each task, we provide a comprehensive notebook detailing the main results, quality checks, and basic preprocessing steps. You can automatically generate the HTML reports using the following code snippet:

```python
from cardioception.reports import report

resultPath = "./"  # the folder containing the result files
reportPath = "./"  # the folder where you want to save the HTML report

report(resultPath, reportPath, task='HRD')
```

This code will generate the HTML reports for the Heart Rate Discrimination task in the `reportPath` folder using the results files located in `resultPath`. This will require [papermill](https://papermill.readthedocs.io/en/latest/).

You can also analyze the results in [Google Colab](https://colab.research.google.com/) using one of the following link and upload the content of your result folder.

| Notebook | Colab | nbViewer |
| --- | ---| --- |
| Heartbeat Counting task report | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartBeatCounting.ipynb) |  [![View the notebook](https://img.shields.io/badge/render-nbviewer-orange.svg)](https://nbviewer.jupyter.org/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartBeatCounting.ipynb)
| Heart Rate Discrimination task report | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartRateDiscrimination.ipynb) |  [![View the notebook](https://img.shields.io/badge/render-nbviewer-orange.svg)](https://nbviewer.jupyter.org/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartRateDiscrimination.ipynb)

## Bayesian modeling

More advanced subject and group-level Bayesian modeling approaches are described in the following notebooks.

| Notebook | Colab | nbViewer |
| --- | ---| --- |
| Fitting psychometric function with PyMC3 - Subject-level | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/main/code/psychophysics_subjectLevel.ipynb?flush_cache=true) |  [![View the notebook](https://img.shields.io/badge/render-nbviewer-orange.svg)](https://nbviewer.jupyter.org/github/embodied-computation-group/Cardioception/blob/main/code/psychophysics_subjectLevel.ipynb?flush_cache=true)
| Fitting psychometric function with PyMC3 - Group-level | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/main/code/psychophysics_groupLevel.ipynb?flush_cache=true) |  [![View the notebook](https://img.shields.io/badge/render-nbviewer-orange.svg)](https://nbviewer.jupyter.org/github/embodied-computation-group/Cardioception/blob/main/code/psychophysics_groupLevel.ipynb?flush_cache=true)

# References

1. Dale, A., & Anderson, D. (1978). Information Variables in Voluntary Control and Classical Conditioning of Heart Rate: Field Dependence and Heart-Rate Perception. Perceptual and Motor Skills, 47(1), 79–85. https://doi.org/10.2466/pms.1978.47.1.79
2. Schandry, R. (1981). Heart Beat Perception and Emotional Experience. Psychophysiology, 18(4), 483–488. https://doi.org/10.1111/j.1469-8986.1981.tb02486.x
3. Legrand, N., Nikolova, N., Correa, C., Brændholt, M., Stuckert, A., Kildahl, N., Vejlø, M., Fardo, F., & Allen, M. (2021). The heart rate discrimination task: a psychophysical method to estimate the accuracy and precision of interoceptive beliefs. bioRxiv 2021.02.18.431871. https://doi.org/10.1101/2021.02.18.431871
4. Leganes-Fonteneau, M., Cheang, Y., Lam, Y., Garfinkel, S., & Duka, T. (2019). Interoceptive awareness is associated with acute alcohol-induced changes in subjective effects. Pharmacology Biochemistry and Behavior, 181, 69–76. https://doi.org/10.1016/j.pbb.2019.03.007
5. Hart, N., McGowan, J., Minati, L., & Critchley, H. D. (2013). Emotional Regulation and Bodily Sensation: Interoceptive Awareness Is Intact in Borderline Personality Disorder. Journal of Personality Disorders, 27(4), 506–518. https://doi.org/10.1521/pedi_2012_26_049

# Development
This package was created and is maintained by [Nicolas Legrand](https://legrandnico.github.io/) and [Micah Allen](https://micahallen.org/) from the [ECG group](https://the-ecg.org/).

<img src = "images/LabLogo.png" height ="100"><img src = "images/AU.png" height ="100">

# Credit
Some icons used in the Figures or presented during the tasks were downloaded from **Flaticon** [www.flaticon.com](www.flaticon.com).
