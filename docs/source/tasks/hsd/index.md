---
myst:
  html_meta:
    description: "The Heartbeat Synchrony Discrimination task in Cardioception: what it measures, what a trial looks like, what you need, how to run it, the files it saves and how to read the posterior."
    keywords: "heartbeat synchrony discrimination, HSD, heartbeat detection, Bayesian adaptive, ECG, Lab Streaming Layer, LabRecorder, cardioception"
---

# Heartbeat Synchrony Discrimination task

```{admonition} Beta
:class: warning

The Heartbeat Synchrony Discrimination task (HSD) is close to feature complete and still being validated. Its stopping rule is provisional. The [design page](design.md) holds the method, the simulations and the hardware dry run.
```

The HSD is an adaptive version of the heartbeat detection task of Brener, Liu and Ring {cite:p}`1993:brener`. It estimates where in the cardiac cycle a person feels their heartbeat (`mu`, in ms after the R-wave), how sharply (`sigma`), and how much more often they answer "synchronous" there than away from it, which is the sensitivity measure. Confidence is rated on every trial.

## What a trial looks like

Each trial plays five tones, each a chosen delay after an R-wave detected online in the ECG. The participant answers whether the tones felt synchronous with their heartbeat, UP for yes and DOWN for no, within 5 s, then rates their confidence in ten steps from "Guess" to "Certain" with the LEFT and RIGHT keys and confirms with DOWN. A trial without an answer shows "Too late" and does not count.

```{figure} ../../images/hsd_trial.png
:alt: Four screens of an HSD trial, a fixation cross; "Listen" while five tones play; the question "Were the tones synchronous with your heartbeat?" with UP for synchronous and DOWN for not; and a confidence scale from Guess to Certain.

One HSD trial, from screenshots of the running task.
```

After each answer the next delay is chosen where it is most informative about `mu`, with one trial in ten drawn at random. The delay is set on one of two axes, chosen per session with `axis`. On the absolute axis, the default, candidates run from 80 to 600 ms after the R-wave in 20 ms steps; none below the 130 ms floor is played, so the shortest delay is 140 ms. On the phase axis the delay is a fraction of the anticipated interbeat interval, from 0.10 to 0.75 in steps of 0.025, so it scales with heart rate.

The session stops once the 95 percent credible interval of `mu` is no wider than 100 ms (0.17 of the period on the phase axis), after at least 15 trials, and never later than 60. Expect most sessions to run to 60; the dry run did, in 7 minutes. A session starts with three instruction screens and three practice trials that do not update the estimate, and there is a break every 20 trials.

## What you need

- An ECG streamed over Lab Streaming Layer. Every tone is timed from an R-wave, so a pulse oximeter cannot drive the task. Install the dependency with `pip install cardioception-toolbox[lsl]`. For a PLUX hub, [Recording devices](../../getting-started/recording-devices.md#a-plux-hub) covers the bridge, the channel label and the electrodes.
- A sound card. Tones are played through PsychPortAudio, PsychoPy's psychtoolbox audio backend.
- [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder). The task keeps no copy of the ECG, so record the ECG stream and the `HSD` marker stream: the XDF file is the session's recording.
- The same speakers or headphones in every session, because the latency bias below includes the delay of the audio output.

## Running it

Start the bridge, or the device's own streaming program, then run `wrappers/hsd_lsl.py` or your copy of it:

```
python hsd_lsl.py
```

A dialog asks for:

| Field | Default | What it sets |
|---|---|---|
| participant | `Participant` | The participant identifier |
| session | `HSD` | The session identifier |
| LSL stream | `PLUX` | The name of the ECG stream |
| Channel | none | The label of the ECG channel. It must be given: the label is not the same on every hub, and the task does not start without it. A label the stream does not have stops the task with an error that lists the stream's channels |
| Axis | `absolute` | `absolute` or `phase` |
| Device | `keyboard` | The response device, keyboard only so far |
| Language | `english` | The instructions, English only so far |

When the dialog closes, the task opens the `HSD` marker stream. In LabRecorder, update the stream list, select the ECG stream and `HSD`, and start recording while the first instruction screen is up. The wrapper runs at most 60 trials (`nTrials=60`).

The same in a script:

```python
from cardioception.devices import LSLRecorder
from cardioception.HSD.parameters import getParameters
from cardioception.HSD.task import run

recorder = LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg", marker_stream="HSD")
parameters = getParameters(
    participant="Subject_01", session="HSD", setup="behavioral",
    axis="absolute", nTrials=60, recorder=recorder)
try:
    run(parameters, confidenceRating=True, runTutorial=True)
finally:
    parameters["tonePlayer"].close()
    recorder.close()
```

With `setup="behavioral"` the beats are found online by `cardioception.devices.beat_source.LSLBeatSource` and the tones scheduled by `cardioception.devices.tone_player.TonePlayer`, both shared with the Phase Adjustment Task. There is no replay setup: `setup="test"` needs a `beat_source=` and a `tone_player=` of your own, which is how the headless tests run.

Escape ends the session with its files saved. The task also stops itself, saving first, after three trials in a row in which no tone could be delivered, which means the beat source has lost the heart.

## The main settings

`getParameters` takes `axis`, `nTrials` (which replaces `maxTrials` and may not be below `minTrials`), `nBreaking` (20), `language`, `resultPath`, `overwrite` and `seed`. Everything about the stimulus and the stopping rule is on a `TaskConfig`, passed as `config=`:

```python
from cardioception.HSD.config import TaskConfig

config = TaskConfig(ciWidth=80.0, minTrials=20, maxTrials=90)
parameters = getParameters(..., config=config)
```

| Field | Default | Meaning |
|---|---|---|
| `nTones`, `minTones` | 5, 3 | Tones per trial, and the fewest a trial must deliver to update the estimate |
| `absoluteDelays` | 80 to 600 by 20 ms | The candidate delays on the absolute axis |
| `phaseDelays` | 0.10 to 0.75 by 0.025 | The candidates on the phase axis, as fractions of the period |
| `minDelay` | 0.13 s | The floor: no shorter physical delay is played |
| `maxPeriodFraction`, `ceilingMargin` | 0.75, 0.10 | The ceiling, as a fraction of the interbeat interval, and the margin taken off it |
| `latencyBias` | 0.05 s | The delay the recordings cannot see, subtracted from every tone's target |
| `audioLead` | 0.05 s | How far ahead a tone is scheduled |
| `explore` | 0.1 | The share of trials whose delay is drawn at random |
| `minTrials`, `maxTrials` | 15, 60 | Bounds on the session length |
| `ciWidth`, `ciWidthPhase` | 100 ms, 0.17 | The credible interval width at which to stop |
| `respMax`, `minRatingTime`, `maxRatingTime` | 5, 0.5, 5 s | Time limits on the answer and the rating |

The floor and the ceiling matter most. The ECG transport and the speaker add a roughly constant 30 to 70 ms that no recording can see, so every tone is scheduled `latencyBias` early and no delay below `minDelay` is played. Set `minDelay` from the lag your setup shows; the [design page](design.md#realized-delays-and-per-trial-constraints) has the measurements and what the floor costs in accuracy. The longest delay on a trial is limited to 0.675 of the current interbeat interval (0.75 less the 10 percent margin), so that a tone is not heard as belonging to the next beat; 600 ms is allowed only when the period is over 0.89 s. A beat whose period has shortened past the ceiling is skipped and a later one used, up to twice `nTones` beats per trial.

## What it saves

A session writes to `data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/`, under `resultPath` when it is given. Every clock time is on one clock, `pylsl.local_clock`, shared by the beat source, the tone player and the marker stream.

| File | Contents |
|---|---|
| `*_final.txt` | One row per trial: requested and realized delay, tones delivered and skipped, decision, confidence, the posterior after the trial and the clock times |
| `*_tones.txt` | One row per beat a tone was tried on: R-wave time, target, onset and realized delay |
| `*_beats.txt` | Every beat detected during the session, filed under the trial whose markers carry it |
| `*_posterior.npy` | The posterior after each trial, trials by grid, in single precision |
| `*_engine.json` | The engine's state and trial history, enough to re-analyze the session |
| `manifest.json` | The task, axis, configuration, clock and devices, written before the first trial |
| `*_behaviour.txt`, `*_parameters.pickle`, `session.log` | The rows written after every trial, the parameters at the end, and the session's log |

The run directory holds no ECG: that is in the LabRecorder file. The task's triggers go to the `HSD` marker stream as JSON, one string per marker, with a marker for every beat, every tone scheduled, played or skipped, and every decision and rating.

## Reading the results

The practice trials are not in `*_final.txt`. The columns that matter:

| Column | Meaning |
|---|---|
| `RequestedDelay` | The delay the engine asked for: ms after the R-wave on the absolute axis, a fraction of the interbeat interval on the phase axis |
| `RealizedCorrected` | The mean delay of the trial's tones as the tone player reports them, with the latency bias added back. This is the stimulus to analyze. The true delay of each tone comes from the LabRecorder file |
| `RealizedDelay` | The same without the latency bias, so 50 ms below `RequestedDelay` on the absolute axis |
| `Decision` | `Synchronous`, `NotSynchronous`, or empty when no key was pressed in time |
| `Confidence` | The rating on the scale shown, 1 to 10 by default. `ConfidenceUnit` holds it on 0 to 1 |
| `Used`, `UnusedReason` | Whether the trial updated the posterior, and if not why: `no_tone`, `few_tones`, `no_decision` or `update_failed` |
| `nDelivered`, `nSkipped`, `Aborted`, `Explored` | Tones played and refused, a train that could not be delivered, and a delay drawn at random |
| `MuMean`, `MuCILow`, `MuCIHigh` | Where the heartbeat is felt: the posterior mean of `mu` after this trial and its 95 percent credible interval, which the stopping rule reads. A wide interval means the location is not yet known |
| `SigmaMean` | How sharply the sensation is timed. It is recovered less well than `mu`, and jitter in the ECG transport widens it |
| `FloorMean`, `PeakMean` | The rate of "synchronous" answers away from the sensation and at it. Their difference is the sensitivity: someone who cannot feel their heartbeat answers at the same rate at every delay, and the difference is near zero. The floor alone is a bias towards answering "synchronous" |
| `MuConditional` | True when the `Mu` and `Sigma` columns are conditioned on the envelope rising; False when the posterior put less than 0.01 on a rise, and they are then the plain marginals |
| `DetectionBF`, `DetectionEvidence` | The Bayes factor, and the posterior probability, for an envelope that rises by more than 0.2 across the delays presented so far |

`DetectionBF` is a sanity check, never a classification. The rise is measured across the delays presented, so a bump outside them, or one too wide to change across them, counts as flat. The prior puts about half its mass on a rise (0.47 over 140 to 500 ms), so read `DetectionEvidence` against that, or read the Bayes factor, which removes the prior.

As for the HRD, the online posterior is a monitoring aid, not an analysis. No offline model has been published yet. Fit any later model to the trial history, `RealizedCorrected` against `Decision` on the rows with `Used` true, which `*_engine.json` also holds.

## Where to go next

- [HSD design and validation](design.md): the model, the delay placement, the simulations, the hardware dry run and the roadmap.
- [Recording devices](../../getting-started/recording-devices.md): the PLUX bridge and LabRecorder.
- [API](../../reference/api.rst): every field of `TaskConfig` and every argument of `getParameters`.

```{toctree}
---
hidden:
---
design.md
```
