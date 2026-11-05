---
myst:
  html_meta:
    description: "The Heart Rate Discrimination task in Cardioception: what it measures, what a trial looks like, how to run it, its settings, the files it saves and how to read them."
    keywords: "heart rate discrimination, HRD, Psi staircase, psychophysics, cardiac interoception, metacognition, cardioception, PsychoPy"
---

# Heart Rate Discrimination task

The Heart Rate Discrimination task (HRD) {cite:p}`2022:legrand` measures how a person judges their own heart rate. On each trial the participant hears tones slightly faster or slower than their heart and says which. The threshold of the resulting psychometric function is their bias, its slope their precision, and the confidence rating on every trial measures their metacognition. The task is established. The [theory page](theory.md) sets out what it can and cannot establish.

## What a trial looks like

A trial begins with a fixation cross for 0.25 s. The participant then attends to their heartbeat for 5 s while the pulse is recorded and the heart rate measured. They hear a sequence of tones at that rate plus or minus a difference, `Alpha`, in beats per minute, and answer whether the tones were faster or slower than their heart, with the mouse buttons or the up and down arrow keys. They have 5 s to answer. They then rate their confidence, on a 0 to 100 slider with the mouse or in ten steps with the keyboard. The rating takes between 0.5 and 5 s.

Half the trials by default are an exteroceptive control. The participant listens for 5 s to a tone sequence at a random rate between 40 and 100 BPM instead of their heart, then judges a second sequence against it. Everything else is the same.

```{figure} ../../images/HeartRateDiscrimination.png
:alt: Panel a, the interoceptive and exteroceptive trial sequences, fixation, listening, decision and confidence rating. Panel b, the Psi staircase traces for both conditions over 80 trials, with the fitted psychometric functions and their threshold and slope.

The HRD trial (a) and the Psi staircase with the psychometric functions it estimates (b). Panel a shows the exteroceptive listening window as 3 to 7 s and the decision window as up to 8 s; the current defaults are 5 s for both listening windows and 5 s to decide.
```

A Psi staircase {cite:p}`1999:kontsevich`, one per condition, chooses `Alpha` on each trial between -50.5 and 50.5 ΔBPM, where the answer is most informative about the participant's threshold and slope. A trial with no answer in time is written with `DecisionProvided` false, does not update the staircase, and is put back at the end of the queue (`onMissedTrial="represent"`, at most three presentations).

A session starts with a tutorial when `runTutorial=True`: instruction screens, five practice trials per condition with feedback at an easy difference of 20 BPM (`nFeedback`), then eight per condition with a confidence rating and no feedback (`nConfidence`). The main task runs 120 trials by default, 60 per condition, with a break every 20. The four example sessions in the documentation took 20 to 22 minutes without the tutorial.

## What you need

- A pulse oximeter on a USB port (the Nonin 3012LP Xpod by default), or an ECG or PPG device streaming over Lab Streaming Layer. [Recording devices](../../getting-started/recording-devices.md) covers both and how to check the oximeter before a session.
- Headphones or speakers.
- A mouse or a keyboard.

## Running it

The repository ships a wrapper for the oximeter, `wrappers/hrd.py`, and one for LSL, `wrappers/hrd_lsl.py`. Copy the one you need next to your data folder and run it:

```
python hrd.py
```

A dialog asks for:

| Field | Default | What it sets |
|---|---|---|
| participant | `Participant` | The participant identifier |
| session | `HRD` | The session identifier |
| Serial port | `COM5` | The port the oximeter is on. `python -m cardioception.check_device --list` lists the ports |
| Setup | `behavioral` | `behavioral` reads the oximeter; `test` replays a recorded pulse, for checking a script without a device |
| Device | `mouse` | `mouse` or `keyboard` for the answers and the rating |
| Language | `english` | The instructions |

The LSL wrapper asks for the stream name, the channel label and the signal type (`ecg` or `ppg`) instead of the port and setup.

The same in a script:

```python
from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run

parameters = getParameters(
    participant="Subject_01", session="HRD", serialPort="COM3",
    setup="behavioral", nTrials=120, exteroception=True)
run(parameters, confidenceRating=True, runTutorial=True)
parameters["win"].close()
```

With an LSL device, pass a recorder instead of a port and close it at the end:

```python
from cardioception.devices import LSLRecorder

recorder = LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg")
parameters = getParameters(participant="Subject_01", session="HRD", recorder=recorder)
run(parameters, confidenceRating=True, runTutorial=True)
parameters["win"].close()
recorder.close()
```

Escape ends the session; what has been collected is saved.

## The main settings

The arguments of `getParameters` that change the task:

| Argument | Default | Meaning |
|---|---|---|
| `nTrials` | 120 | Trials in all. With `exteroception=True` half are interoceptive and half exteroceptive |
| `exteroception` | `True` | Include the exteroceptive control condition |
| `device` | `"mouse"` | `"mouse"` or `"keyboard"` |
| `language` | `"english"` | `"english"`, `"danish"`, `"danish_children"`, `"french"` or `"german"`. The wrappers offer a subset |
| `confidenceScale` | by device | A `cardioception.scales.ConfidenceScale`: 0 to 100 for the mouse, ten steps for the keyboard. The end labels follow the language |
| `catchTrials` | 0.0 | Share of trials at an extreme difference of about 20 BPM, to control the range of stimuli. 0.2 if used |
| `onMissedTrial` | `"represent"` | Re-present a trial with no answer (`"represent"`, up to `maxRepresentations`, 3) or move on (`"skip"`) |
| `nBreaking` | 20 | Trials between breaks |
| `resultPath` | `data` | Root of the run directories |
| `overwrite` | `False` | Allow writing into a run directory that already holds results |
| `seed` | drawn | Seeds the session's random generator; recorded in the manifest |
| `stairType` | `"psi"` | The only staircase. The nUp/nDown staircase was removed in 1.0.0, so `"updown"` raises; the [changelog](../../reference/changelog.md) explains why |

Timing and the staircase bounds are on a `TaskConfig`, passed as `config=`:

| Field | Default | Meaning |
|---|---|---|
| `listeningDuration` | 5.0 s | The listening window in both conditions |
| `respMax` | 5.0 s | Time to answer |
| `minRatingTime`, `maxRatingTime` | 0.5, 5.0 s | Bounds on the confidence rating |
| `HRcutOff` | 40 to 120 BPM | A heart rate outside this range is treated as artefact and the window retaken, up to `maxHeartRateAttempts` (10) times |
| `exteroBPMRange` | 40 to 100 by 0.5 | The rates the exteroceptive reference is drawn from |
| `intensRange`, `alphaRange` | -50.5 to 50.5 | The stimuli the staircase may present, and the thresholds it considers, in ΔBPM |
| `delta` | 0.02 | The lapse rate, held fixed |

The staircase is response-coded, so it converges on the point of subjective equality between faster and slower, which is the participant's bias, not on a target level of accuracy. That is what the task is designed to measure, but it has consequences for any measure scored against the true heart rate; see the [metacognition tutorial](tutorials/metacognition.md). Tones exist for 15 to 199 BPM, so a rate outside that range is clamped and the staircase is told the clamped value.

## What it saves

A session writes to `data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/`, under `resultPath` when it is given. Every file name carries the three identifiers.

| File | Contents |
|---|---|
| `*_final.txt` | One row per trial |
| `*_signal.txt` | The pulse recorded in every interoceptive listening window, with the trial number and each sample's time |
| `*_ppg-<n>.txt` | The oximeter recording, saved at every break and at the end, with the trigger codes in `Channel_0` |
| `*_posterior-Intero.npy`, `*_posterior-Extero.npy` | The staircase posterior after each trial |
| `manifest.json` | The settings, the seed and the version, written before the first trial |
| `*_behaviour.txt`, `*_parameters.pickle`, `session.log` | The rows written after every trial, the parameters at the end, and the session's log |

The columns of `*_final.txt` that matter:

| Column | Meaning |
|---|---|
| `Modality` | `Intero` or `Extero` |
| `listenBPM`, `responseBPM`, `Alpha` | The reference rate, the rate of the tones, and their difference in ΔBPM |
| `Decision` | `More` or `Less` |
| `ResponseCorrect` | Whether the decision matched the sign of `Alpha` |
| `Confidence` | The rating on the scale shown. `ConfidenceUnit` holds it on 0 to 1 |
| `DecisionProvided`, `RatingProvided` | Whether the answer and the rating were given in time |
| `EstimatedThreshold`, `EstimatedSlope` | The staircase's own running estimates |

The [inspecting data tutorial](tutorials/inspecting-data.md#the-trial-table) describes every column.

## Reading the results

`EstimatedThreshold` and `EstimatedSlope` are a by-product of the staircase. Plot them to check that a session converged. They are not an analysis and must not be used as a dependent variable in a group-level test.

Fit the trials instead, `Decision` against `Alpha` by `Modality`, with the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception) {cite:p}`2026:courtin`. The [tutorials](tutorials/index.md) go from opening a session to a hierarchical model with confidence ratings.

## Where to go next

- [Theory](theory.md): why the HRD measures beliefs about heart rate, and what you may conclude from it.
- [Tutorials](tutorials/index.md): inspecting a session, fitting psychometric functions, hierarchical models and metacognition.
- [HTML reports (legacy)](reports.md): the notebook report of a session.
- [API](../../reference/api.rst): every argument of `getParameters` and every field of `TaskConfig`.

```{toctree}
---
hidden:
---
Theory <theory.md>
Tutorials <tutorials/index.md>
HTML reports (legacy) <reports.md>
```
