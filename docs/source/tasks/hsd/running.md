---
myst:
  html_meta:
    description: "How to run the Heartbeat Synchrony Discrimination task: what you need, the wrapper and its dialog, the files a session saves, the stopping rule and how to read the posterior."
    keywords: "heartbeat synchrony discrimination, HSD, heartbeat detection, ECG, Lab Streaming Layer, LabRecorder, cardioception"
---

# Running the HSD

```{admonition} Beta
:class: warning

The Heartbeat Synchrony Discrimination task (HSD) is new. It has been run on
hardware in a [dry run](design.md#hardware-dry-run) and has not been
validated in a study. Its stopping rule is
provisional. The [design page](design.md) sets out the method and the
evidence so far.
```

The HSD is an adaptive version of the heartbeat detection task of Brener, Liu and Ring {cite:p}`1993:brener`. Each trial plays five tones, each a chosen delay after a detected R-wave, and the participant answers with the keyboard whether the tones felt synchronous with their heartbeat (UP) or not (DOWN), then rates their confidence. After each answer the next delay is chosen where it is most informative about where in the cardiac cycle the heartbeat is felt (`mu`) and how sharply (`sigma`). The session stops once the credible interval of `mu` is narrow enough, after at least `minTrials` trials, or after `nTrials`.

The delay can be set on one of two axes, chosen per session with `axis`:

- `axis="absolute"` (the default): milliseconds after the R-wave. The candidates run from 80 to 600 ms in 20 ms steps, and the shortest presented is 140 ms, the first above the 130 ms floor (see the latency floor below). The longest delay on a given trial is limited to about 0.68 of the current interbeat interval (0.75 less a 10 percent margin), so that a tone is not heard as belonging to the next beat; 600 ms is allowed only when the period is over 0.89 s.
- `axis="phase"`: a fraction of the anticipated interbeat interval, so the delay scales with heart rate.

## What you need

- **An ECG streamed over LSL.** Every tone is timed from an R-wave detected online, so the task needs an ECG; a pulse oximeter cannot drive it. Install the LSL dependency with `pip install cardioception-toolbox[lsl]`. The tones are played with PsychPortAudio, PsychoPy's psychtoolbox audio backend.
- **For a PLUX hub, the PLUX bridge.** See [Recording devices](../../getting-started/recording-devices.md#a-plux-hub).
- **LabRecorder, recommended.** The task keeps no copy of the ECG. Record the ECG stream and the `HSD` marker stream with [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder): the XDF file is the session's recording, and the ground truth against which the timing can be checked.
- **The same speakers or headphones in every session.** The latency bias described below includes the delay of the audio output.

## Running a session

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

   The channel has no default because its label is not the same on every hub (see [Recording devices](../../getting-started/recording-devices.md#a-plux-hub)). A label the stream does not have stops the task before anything is written, with an error that lists the stream's channels. The wrapper runs at most 60 trials (`nTrials=60`).
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

## From a script

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
With `setup="behavioral"` the beats are found online in the ECG by `cardioception.devices.beat_source.LSLBeatSource`, and the tones are scheduled on the audio device by `cardioception.devices.tone_player.TonePlayer` (PsychPortAudio, latency class 1). Both are shared with the Phase Adjustment Task. A script can pass its own `beat_source=` and `tone_player=` to `getParameters` instead, which is what the headless tests do.
```

## What a session saves

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

The run directory holds no ECG. The beat source is the only reader of the LSL stream, so the task keeps no copy of the signal: the ECG is in the LabRecorder file. The HSD writes no trigger codes into a `Channel_0` as the HRD does. Its triggers go to the `HSD` marker stream as JSON instead, one string per marker (for example `{"kind": "trigger", "name": "TRIAL_START", "code": 1, "trial": 0}`), together with a marker for every beat, every tone scheduled, played or skipped, and every decision and rating. The beat and tone markers use the field names of the Phase Adjustment Task's dry run.

## The latency bias and the 130 ms floor

The ECG transport and the speaker add a roughly constant 30 to 70 ms that no recording can see, so the task schedules every tone a latency bias early, 50 ms by default (`TaskConfig.latencyBias`), so that the participant hears it at the requested delay after the true R-wave. No delay below the 130 ms floor (`TaskConfig.minDelay`) is presented. Set `minDelay` from the lag your setup shows; the [design page](design.md#realized-delays-and-per-trial-constraints) has the measurements, and [what the floor costs](design.md#results-as-the-task-runs) in accuracy.

## The stopping rule

A session stops at the first of two points: once the 95 percent credible interval of `mu` is no wider than `TaskConfig.ciWidth` (100 ms on the absolute axis; `ciWidthPhase`, 0.17 of the period, on the phase axis), provided at least `minTrials` trials (15) have updated the estimate; or after `maxTrials` trials in all (60, which `nTrials` sets). These values are provisional: expect most sessions to run to the maximum, as the dry run did. The [design page](design.md#realized-delays-and-per-trial-constraints) has the simulation figures. To change them, pass a configuration:

```python
from cardioception.HSD.config import TaskConfig

config = TaskConfig(ciWidth=80.0, minTrials=20, maxTrials=90)
parameters = getParameters(..., config=config)
```

`nTrials`, when given, replaces `maxTrials` and may not be below `minTrials`. The wrapper passes `nTrials=60`, so edit it there.

## Reading the results

`*_final.txt` has one row per trial; the practice trials are not in it. The columns that matter most:

| Column | Meaning |
|---|---|
| `RequestedDelay` | The delay the engine asked for: ms after the R-wave on the absolute axis, a fraction of the interbeat interval on the phase axis. It is the physical delay the participant should hear |
| `RealizedCorrected` | The mean delay of the trial's tones from the start time the tone player reports, against the stamped R-wave, with the latency bias added back. The engine was updated with this value. The reported start is the scheduled one, so it equals `RequestedDelay` unless a tone started late; the true delay of each tone comes from the LabRecorder file offline |
| `RealizedDelay` | The same value without the latency bias. On the absolute axis it sits 50 ms below `RequestedDelay`, by design |
| `Decision` | `Synchronous`, `NotSynchronous`, or empty when no key was pressed in time |
| `Confidence` | The rating on the scale shown, 1 to 10 by default. `ConfidenceUnit` holds the same rating on 0 to 1 |
| `MuMean`, `MuCILow`, `MuCIHigh` | The posterior mean of `mu` after this trial, and its 95 percent credible interval, given that the envelope rises (conditioned on a rise of more than 0.2). The stopping rule reads this interval |
| `SigmaMean` | The posterior mean of `sigma`, also given a rise |
| `MuConditional` | True when the `Mu` and `Sigma` columns are conditioned on a rise; False when the posterior put less than 0.01 on a rise, and they are then the plain marginal ones |
| `FloorMean`, `PeakMean` | The posterior means of the floor and the peak of the envelope |
| `DetectionBF` | The Bayes factor, posterior odds over prior odds, for an envelope that rises by more than 0.2 across the delays presented so far. `DetectionEvidence` is the posterior probability of that rise |

`nDelivered` and `nSkipped` count the tones played and refused on the trial, `Aborted` marks a train that could not be delivered, and `Explored` marks a delay drawn at random rather than by information gain. `Used` marks the trials that updated the posterior, and `UnusedReason` says why the others did not: no tone (`no_tone`), fewer than `TaskConfig.minTones` tones, 3 by default (`few_tones`), or no decision (`no_decision`). On the phase axis the two realized columns are different quantities; the docstring of `cardioception.HSD._outcome` explains how.

The posterior columns of the last row are the session's online estimate. As for the HRD, they are a monitoring aid, not an analysis: a later model should be fitted to the trial history, `RealizedCorrected` against `Decision` on the rows with `Used` true, which `*_engine.json` also holds.

## Interpreting the posterior

- **Location**, `mu` (`MuMean`, with `MuCILow` to `MuCIHigh`): where in the cardiac cycle the heartbeat is felt, in ms after the R-wave. Read it with its interval; a wide interval means the location is not yet known.
- **Width**, `sigma` (`SigmaMean`): how sharply the sensation is timed. It is recovered less well than `mu`, and jitter in the ECG transport widens it.
- **Contrast**, `PeakMean` minus `FloorMean`: how much more often the participant answers "synchronous" at the sensation than away from it. This is the sensitivity measure. Someone who cannot feel their heartbeat answers at the same rate at every delay, and their contrast is near zero.
- **Floor**, `FloorMean`: the rate of "synchronous" answers far from the sensation, a bias towards answering "synchronous" whatever the delay.
- **Detection Bayes factor**, `DetectionBF`: a sanity check, never a classification. The rise is measured across the delays presented, so a bump outside them, or one too wide to change across them, counts as flat, and a flat envelope is possible at any rate of answering "synchronous", from almost never to almost always. The prior puts about half its mass on a rise of more than 0.2 (0.47 over 140 to 500 ms), so read `DetectionEvidence` against that, or read the Bayes factor, which removes the prior. The [design page](design.md#detection-evidence) has its performance in the simulations.

A located `mu` with a weak Bayes factor is possible; the [hardware dry run](design.md#hardware-dry-run) is an example.
