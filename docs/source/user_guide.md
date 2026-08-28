---
myst:
  html_meta:
    description: "How to install Cardioception, set up a recording device and run the Heart Rate Discrimination and Heartbeat Counting tasks in PsychoPy."
    keywords: "cardioception user guide, heart rate discrimination, heartbeat counting, PsychoPy, pulse oximeter, interoception task"
---

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

Cardioception requires **Python 3.10 or 3.11**. The upper bound is `pywinhook`, which publishes wheels only up to 3.11; PsychoPy itself allows 3.12. See the [installation guide](installation.md) for step-by-step instructions.

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

Other devices can be added by writing a recorder and passing it in:

```python
parameters = getParameters(..., recorder=MyRecorder())
```

This bypasses `setup` entirely, so nothing touches a serial port. The recorder has to provide a real-time estimate of cardiac frequency during the trial, because that is what sets the tone frequency: a device that only records for later analysis cannot drive the HRD on its own. See `cardioception.devices.ReplayRecorder` for a worked example, which is also what the test suite runs against.

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

### The two tasks

**The Heart Rate Discrimination task** {cite:p}`2022:legrand` is an adaptive psychophysical measure in which participants estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. Manipulating the difference between the true heart rate and the presented tone gives the bias (threshold) and precision (slope) of the psychometric function, estimated either online or offline, together with metacognitive performance. See [Theory](measuring.md) for what these quantities mean.

**The Heartbeat Counting task** {cite:p}`1981:schandry,1978:dale` asks participants to attend to their heartbeats over intervals of various lengths and count the beats they feel. An accuracy score compares the reported number with the true number, following Hart et al. {cite:p}`2013:hart`:

```{math}
   Accuracy = 1-\frac{\left | N_{real} - N_{reported} \right |}{\frac{N_{real} + N_{reported}}{2}}
```

By default cardioception implements a 20-second training trial followed by 6 experimental trials (25, 30, 35, 40, 45 and 50 s) in randomised order. Trial length, condition (`'Rest'`, `'Count'`, `'Training'`) and randomisation are set in the parameters dictionary; the version is selected with `"taskVersion"`. With the default settings the task takes about 4 minutes. We keep this task because much of the literature rests on it, but for new studies we recommend the HRD — [Theory](measuring.md) explains why.

### Staircase procedures

If you run the task in behavioural mode, the Nonin pulse oximeter is read from the port provided. Two staircase procedures are implemented, controlled through the `stairType` parameter.

#### Psi

The default. This uses Kontsevich and Tyler's {cite:p}`1999:kontsevich` psi-method to estimate the point of subjective equality for faster versus slower cardiac feedback, based on a cumulative Gaussian psychometric function. Tones are presented at the relative $\Delta$-BPM and this stimulus intensity is adjusted between $\Delta$-BPM = [-40 40]. The staircase is response-coded, so the function converges on the point of subjective equality between faster and slower stimuli. The threshold is then an estimate of subjective cardiac bias, and the slope an estimate of interoceptive precision. Nuisance parameters (guess and lapse rate) are fixed at values corresponding to a standard 1-alternative forced choice paradigm.

```{important}
Psi converges on the participant's point of subjective equality — their bias — not on a target level of accuracy. That is what the task is designed to measure, but it has consequences for any measure scored against the true heart rate. See the [metacognition tutorial](tutorials/metacognition.md).
```

#### nUp/nDown

A classical adaptive thresholding procedure {cite:p}`1962:cornsweet`. The staircase adjusts the absolute difference between the frequency of the auditory feedback stimulus and the estimated heart rate during the listening interval (absolute $\Delta$-BPM), and responses are coded by accuracy relative to the ground truth heart rate. It converges on the smallest difference a participant can reliably discriminate, according to the stepping rule; a 1-down 2-up procedure converges at ~71% accuracy at the limit. Two or more randomly interleaved staircases can start at low versus high values.

This is a simple and reasonably robust way to estimate the accuracy of interoceptive belief, but it should **not** be used to estimate precision (slope). Use Psi for that.

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
