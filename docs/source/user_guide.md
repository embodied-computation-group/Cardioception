---
myst:
  html_meta:
    description: "How to install Cardioception, set up a recording device and run the Heart Rate Discrimination and Heartbeat Counting tasks, and the experimental Heartbeat Synchrony Discrimination task, in PsychoPy."
    keywords: "cardioception user guide, heart rate discrimination, heartbeat counting, heartbeat synchrony, PsychoPy, pulse oximeter, interoception task"
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
* Any ECG or PPG device that streams over [Lab Streaming Layer](https://labstreaminglayer.org/) (LSL), through `cardioception.devices.LSLRecorder`

The experimental Heartbeat Synchrony Discrimination task (HSD) times each tone from the R-wave, so it needs an ECG over LSL; see [its section](#heartbeat-synchrony-discrimination) below.

### ECG or PPG over LSL

Install the optional dependency with `pip install cardioception-toolbox[lsl]`. Start the device's own streaming program, then name the stream and the channel holding the heart signal:

```python
from cardioception.devices import LSLRecorder
from cardioception.HRD.parameters import getParameters

recorder = LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg")
parameters = getParameters(..., recorder=recorder)
```

`channel` is an index or a label from the stream's channel metadata. With `signal_type="ecg"` the beats come from systole's `ecg_peaks` (sleepecg detector), each moved to the R peak, at the stream's own rate, and the tutorial skips the pulse oximeter and finger instructions. The heart rate is then computed from the beats exactly as for the oximeter.

The trigger codes the task writes are also sent to an LSL marker stream, `Cardioception` by default (`marker_stream=` to rename, `None` to turn off), labelled by name (`TRIAL_START`, `LISTENING_START`, ...). Record that stream and the device's with [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder) to get the physiology and the task events on one clock. Cardioception's own signal files are written as before, with each sample's LSL timestamp added.

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

The instructions are shown in the language passed as `language`. The Heart Rate Discrimination task accepts `"english"` (the default), `"danish"`, `"danish_children"`, `"french"` or `"german"`, and the Heartbeat Counting task accepts `"english"` (the default) or `"german"`. The confidence scale's end labels follow the language unless you pass your own `confidenceScale`. An unknown language stops the task before a window opens, with an error that lists the languages there are.

### The tasks

**The Heart Rate Discrimination task** {cite:p}`2022:legrand` is an adaptive psychophysical measure in which participants estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. Manipulating the difference between the true heart rate and the presented tone gives the bias (threshold) and precision (slope) of the psychometric function, estimated either online or offline, together with metacognitive performance. See [Theory](measuring.md) for what these quantities mean.

**The Heartbeat Counting task** {cite:p}`1981:schandry,1978:dale` asks participants to attend to their heartbeats over intervals of various lengths and count the beats they feel. An accuracy score compares the reported number with the true number, following Hart et al. {cite:p}`2013:hart`:

```{math}
   Accuracy = 1-\frac{\left | N_{real} - N_{reported} \right |}{\frac{N_{real} + N_{reported}}{2}}
```

By default cardioception implements a 20-second training trial followed by 6 experimental trials (25, 30, 35, 40, 45 and 50 s) in randomised order. Trial length, condition (`'Rest'`, `'Count'`, `'Training'`) and randomisation are set in the parameters dictionary; the version is selected with `"taskVersion"`. With the default settings the task takes about 4 minutes. We keep this task because much of the literature rests on it, but for new studies we recommend the HRD. [Theory](measuring.md) explains why.

**The Heartbeat Synchrony Discrimination task** is experimental. It is an adaptive Bayesian version of the heartbeat detection task {cite:p}`1993:brener`: participants hear tones a chosen delay after each R-wave and judge whether they were synchronous with their heartbeat, and the delays are placed to estimate where in the cardiac cycle the heartbeat is felt and how sharply. It needs an ECG over LSL. [How to run it](#heartbeat-synchrony-discrimination) is below, and the [design page](hsd_design.md) describes the method and the evidence so far.

### Staircase procedures

If you run the task in behavioural mode, the Nonin pulse oximeter is read from the port provided.

#### Psi

The only staircase. This uses Kontsevich and Tyler's {cite:p}`1999:kontsevich` psi-method to estimate the point of subjective equality for faster versus slower cardiac feedback, based on a cumulative Gaussian psychometric function. Tones are presented at the relative $\Delta$-BPM and this stimulus intensity is adjusted between $\Delta$-BPM = [-40 40]. The staircase is response-coded, so the function converges on the point of subjective equality between faster and slower stimuli. The threshold is then an estimate of subjective cardiac bias, and the slope an estimate of interoceptive precision. Nuisance parameters (guess and lapse rate) are fixed at values corresponding to a standard 1-alternative forced choice paradigm.

```{important}
Psi converges on the participant's point of subjective equality, their bias, not on a target level of accuracy. That is what the task is designed to measure, but it has consequences for any measure scored against the true heart rate. See the [metacognition tutorial](tutorials/metacognition.md).
```

```{admonition} The nUp/nDown staircase was removed in 0.8.0
:class: warning

`stairType="updown"` now raises. It described itself as a 1-down 2-up
procedure converging at ~71% accuracy, but the conditions it built used
`nUp=1, nDown=1`, which converges at 50%, chance on a two-alternative task.
The two never matched, no published Cardioception data used it, and it could
not estimate the slope. Use Psi.
```

### Heartbeat Synchrony Discrimination

```{admonition} Experimental
:class: warning

The Heartbeat Synchrony Discrimination task (HSD) is new. It has been run on
hardware once, in a 60-trial [dry run](hsd_design.md#hardware-dry-run) with one
participant, and has not been validated in a study. Its stopping rule is
provisional. The [design page](hsd_design.md) sets out the method and the
evidence so far.
```

The HSD is an adaptive version of the heartbeat detection task of Brener, Liu and Ring {cite:p}`1993:brener`. Each trial plays five tones, each a chosen delay after a detected R-wave, and the participant answers with the keyboard whether the tones felt synchronous with their heartbeat (UP) or not (DOWN), then rates their confidence. After each answer the next delay is chosen where it is most informative about where in the cardiac cycle the heartbeat is felt (`mu`) and how sharply (`sigma`). The session stops once the credible interval of `mu` is narrow enough, after at least `minTrials` trials, or after `nTrials`.

The delay can be set on one of two axes, chosen per session with `axis`:

- `axis="absolute"` (the default): milliseconds after the R-wave, from 130 to 600 ms (see the latency floor below). The longest delay on a given trial is limited to just under three quarters of the current interbeat interval, so a tone is not heard as belonging to the next beat.
- `axis="phase"`: a fraction of the anticipated interbeat interval, so the delay scales with heart rate.

#### What you need

- **An ECG streamed over LSL.** Every tone is timed from an R-wave detected online, so the task needs an ECG; a pulse oximeter cannot drive it. Install the LSL dependency with `pip install cardioception-toolbox[lsl]`. The tones are played with PsychPortAudio, PsychoPy's psychtoolbox audio backend.
- **For a PLUX hub, the PLUX bridge.** `plux_lsl.py`, from the `plux-lsl` repository, streams the hub over LSL under the name `PLUX`, which is the wrapper's default. Start it with `python plux_lsl.py --ports 1` before the task.
- **LabRecorder, recommended.** The task keeps no copy of the ECG. Record the ECG stream and the `HSD` marker stream with [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder): the XDF file is the session's recording, and the ground truth against which the timing can be checked.
- **The same speakers or headphones in every session.** The latency bias described below includes the delay of the audio output.

#### Running a session

1. Start the bridge, or the device's own streaming program.
2. Run `wrappers/hsd_lsl.py`, or your copy of it. A dialog asks for:

   | Field | Default | What it sets |
   |---|---|---|
   | participant | `Participant` | The participant identifier |
   | session | `HSD` | The session identifier |
   | LSL stream | `PLUX` | The name of the ECG stream |
   | Channel | none | The label of the ECG channel in that stream. It must be given: the task does not start without it |
   | Axis | `absolute` | `absolute` or `phase` |
   | Device | `keyboard` | The response device, keyboard only so far |
   | Language | `english` | The instructions, English only so far |

   The channel has no default because its label is not the same on every hub: the PLUX bridge has given `ECG1` on one hub and `ECG2` on another. A label the stream does not have stops the task before anything is written, with an error that lists the stream's channels. The wrapper runs at most 60 trials (`nTrials=60`).
3. When the dialog closes, the task opens the `HSD` marker stream. In LabRecorder, update the stream list, select the ECG stream and `HSD`, and start recording while the first instruction screen is still up.
4. The participant reads three instruction screens, does three practice trials, which do not update the estimate, and then the task starts. There is a break every 20 trials (`nBreaking`).

The keys:

| Key | Screen | Meaning |
|---|---|---|
| SPACE | Instructions and breaks | Continue |
| UP | After the tones | Synchronous |
| DOWN | After the tones | Not synchronous |
| LEFT and RIGHT | Confidence scale | Move the marker, in ten steps from "Guess" to "Certain" |
| DOWN | Confidence scale | Confirm the rating |
| Escape | Any time during a trial | End the session |

The participant has 5 s to answer (`TaskConfig.respMax`). A trial without an answer shows "Too late" and does not update the estimate. The rating scale gives up after 5 s (`maxRatingTime`) and records no rating. Escape ends the session with its files saved: they are written before the task closes, so every trial run so far is kept. The task also stops itself, saving first, after three trials in a row in which no tone could be delivered, which means the beat source has lost the heart.

#### From a script

The wrapper amounts to:

```python
from cardioception.devices import LSLRecorder
from cardioception.HSD.parameters import getParameters
from cardioception.HSD.task import run

recorder = LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg", marker_stream="HSD")
parameters = getParameters(
    participant="Subject_01", session="HSD", setup="behavioral",
    axis="absolute", nTrials=60, recorder=recorder)
run(parameters, confidenceRating=True, runTutorial=True)
```

```{important}
With `setup="behavioral"` the beats are found online in the ECG by `cardioception.devices.beat_source.LSLBeatSource`, and the tones are scheduled on the audio device by `cardioception.devices.tone_player.TonePlayer` (PsychPortAudio, latency class 1). Both are shared with the phase adjustment task. A script can pass its own `beat_source=` and `tone_player=` to `getParameters` instead, which is what the headless tests do.
```

#### What a session saves

Results go to `data/sub-<participant>/ses-<session>/run-<timestamp>/` under the current folder, or under `resultPath`. Every clock time the task records is on one clock, `pylsl.local_clock` when pylsl is installed, which the beat source, the tone player and the LSL marker stream share. The run directory holds:

| File | Contents |
|---|---|
| `*_final.txt` | One row per trial: requested and realized delay, tones delivered and skipped, decision, confidence, the posterior summary after the trial and the clock times |
| `*_tones.txt` | One row per beat a tone was tried on: R-wave time, target, onset and realized delay |
| `*_beats.txt` | Every beat detected during the session, including those between trains, filed under the trial whose markers carry it |
| `*_posterior.npy` | The posterior after each trial, trials by grid, in single precision (float32) |
| `*_engine.json` | The engine's state and trial history, enough to re-analyze the session |
| `manifest.json` | The task, axis, configuration, clock and devices, written before the first trial |
| `*_behaviour.txt`, `*_parameters.pickle`, `session.log` | The rows written after every trial, the parameters at the end, and the session's log |

The run directory holds no ECG. The beat source is the only reader of the LSL stream, so the task keeps no copy of the signal: the ECG is in the LabRecorder file. The HSD writes no trigger codes into a `Channel_0` as the HRD does. Its triggers go to the `HSD` marker stream as JSON instead, one string per marker (for example `{"kind": "trigger", "name": "TRIAL_START", "code": 1, "trial": 0}`), together with a marker for every beat, every tone scheduled, played or skipped, and every decision and rating. The beat and tone markers use the field names of the phase adjustment task's dry run.

#### The latency bias and the 130 ms floor

The ECG transport and the speaker add a roughly constant 30 to 70 ms that no recording can see, so the task schedules every tone a latency bias early, 50 ms by default (`TaskConfig.latencyBias`), so that the participant hears it at the requested delay after the true R-wave. Because a beat is known only up to 31 ms after its stamped R-wave and a tone must be scheduled 50 ms ahead, the shortest delay the task can play is 31 + 50 + 50 = 131 ms, and no delay below the 130 ms floor (`TaskConfig.minDelay`) is presented; the [design page](hsd_design.md#realized-delays-and-per-trial-constraints) has the measurements, and [what the floor costs](hsd_design.md#results-at-the-130-ms-floor) in accuracy.

#### The stopping rule

A session stops at the first of two points: once the 95 percent credible interval of `mu` is no wider than `TaskConfig.ciWidth` (100 ms on the absolute axis; `ciWidthPhase`, 0.17 of the period, on the phase axis), provided at least `minTrials` trials (15) have updated the estimate; or after `maxTrials` trials in all (60, which `nTrials` sets). These values are provisional. In the simulations a 100 ms interval took about 40 trials in median for observers who answer consistently and about 80 for noisy ones, so expect many sessions to run to the maximum, as the dry run did. To change them, pass a configuration:

```python
from cardioception.HSD.config import TaskConfig

config = TaskConfig(ciWidth=80.0, minTrials=20, maxTrials=90)
parameters = getParameters(..., config=config)
```

`nTrials`, when given, replaces `maxTrials` and may not be below `minTrials`. The wrapper passes `nTrials=60`, so edit it there.

#### Reading the results

`*_final.txt` has one row per trial; the practice trials are not in it. The columns that matter most:

| Column | Meaning |
|---|---|
| `RequestedDelay` | The delay the engine asked for: ms after the R-wave on the absolute axis, a fraction of the interbeat interval on the phase axis. It is the physical delay the participant should hear |
| `RealizedCorrected` | The mean delay of the trial's tones as played, measured against the stamped R-wave with the latency bias added back. The engine was updated with this value, and it is the stimulus to analyze |
| `RealizedDelay` | The same measurement without the correction. On the absolute axis it sits 50 ms below `RequestedDelay`, by design |
| `Decision` | `Synchronous`, `NotSynchronous`, or empty when no key was pressed in time |
| `Confidence` | The rating on the scale shown, 1 to 10 by default. `ConfidenceUnit` holds the same rating on 0 to 1 |
| `MuMean`, `MuCILow`, `MuCIHigh` | The posterior mean of `mu` after this trial, and its 95 percent credible interval |
| `SigmaMean` | The posterior mean of `sigma` |
| `FloorMean`, `PeakMean` | The posterior means of the floor and the peak of the envelope |
| `DetectionBF` | The Bayes factor, posterior odds over prior odds, for a rise of more than 0.2 from floor to peak. `DetectionEvidence` is the posterior probability of that rise |

`nDelivered` and `nSkipped` count the tones played and refused on the trial, `Aborted` marks a train that could not be delivered, and `Explored` marks a delay drawn at random rather than by information gain. `Used` marks the trials that updated the posterior, and `UnusedReason` says why the others did not: no tone (`no_tone`), fewer than `TaskConfig.minTones` tones, 3 by default (`few_tones`), or no decision (`no_decision`). On the phase axis the two realized columns are different quantities; the docstring of `cardioception.HSD._outcome` explains how.

The posterior columns of the last row are the session's online estimate. As for the HRD, they are a monitoring aid, not an analysis: a later model should be fitted to the trial history, `RealizedCorrected` against `Decision` on the rows with `Used` true, which `*_engine.json` also holds.

#### Interpreting the posterior

- **Location**, `mu` (`MuMean`, with `MuCILow` to `MuCIHigh`): where in the cardiac cycle the heartbeat is felt, in ms after the R-wave. Read it with its interval; a wide interval means the location is not yet known.
- **Width**, `sigma` (`SigmaMean`): how sharply the sensation is timed. It is recovered less well than `mu` (in the simulations its error fell only from about 36 ms at 20 trials to 23 to 28 ms at 120), and jitter in the ECG transport widens it.
- **Contrast**, `PeakMean` minus `FloorMean`: how much more often the participant answers "synchronous" at the sensation than away from it. This is the sensitivity measure. Someone who cannot feel their heartbeat answers at the same rate at every delay, and their contrast is near zero.
- **Floor**, `FloorMean`: the rate of "synchronous" answers far from the sensation, a bias towards answering "synchronous" whatever the delay.
- **Detection Bayes factor**, `DetectionBF`: a sanity check, never a classification. The prior already puts about 0.92 of its mass on a rise of more than 0.2, so a `DetectionEvidence` of 0.92 means the data have not moved it, and a Bayes factor near 1 says the same thing. A flat responder can also be fitted by a very wide `sigma` or a `mu` at the edge of the grid.

A located `mu` with a Bayes factor near 1 is possible. In the dry run, `mu` came out at 272 ms (150 to 400 ms) while the Bayes factor stayed near 1, because "synchronous" answers at the longest delays were absorbed as a floor of 0.32, leaving a contrast of 0.43.

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
