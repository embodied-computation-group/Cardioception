---
myst:
  html_meta:
    description: "The Phase Adjustment Task (PAT) in Cardioception: an ECG-triggered heartbeat synchrony task over LSL, its output files, and how to score phase consistency."
    keywords: "phase adjustment task, PAT, PAT-ECG, heartbeat perception, cardiac interoception, mean resultant length, ECG, LSL, cardioception"
---

# Phase Adjustment Task

The Phase Adjustment Task (PAT) {cite:p}`2021:plans` measures how consistently a person can place a tone at the same point of their own cardiac cycle. Participants hear one tone per heartbeat. They turn a dial that moves the tone earlier or later after each heartbeat until tone and heartbeat feel simultaneous, then press space to lock in their choice. There is no correct answer on a single trial: what is scored is whether the choices cluster at one phase of the cycle across trials, more than they would by chance.

Cardioception's version follows the ECG-based implementation of {cite:t}`2026:hodgetts` (PAT-ECG), which triggers the tones from the R-wave of the electrocardiogram rather than from a finger pulse, adds an online relative-delay (phase) mode and an exteroceptive control task, and scores every participant on a grid of eight consistency measures. The PAT 2.0 refinements of {cite:t}`2026:palmer` provide the fixed-mapping score and the Monte Carlo thresholds.

```{note}
**Beta.** The PAT module is new and runs only with an ECG streamed over Lab Streaming Layer (LSL). The original PAT-ECG uses a hardware R-wave trigger and a Teensy microcontroller; this port detects the R-wave in software, which changes the timing budget. Read the [timing section](#timing-and-latency) before you plan a study.
```

## What the task measures

Each trial yields a chosen delay `d` (ms from the R-wave to the tone), a heart period `p` (ms) and a confidence rating `w` (1 to 10). The delay becomes a phase angle `theta = 2 pi d / p`, and consistency is the mean resultant length (MRL) of the angles over trials:

```
R   = | (1/n) sum_r exp(i theta_r) |
R_w = | sum_r w_r exp(i theta_r) | / sum_r w_r      (confidence-weighted)
```

`R` runs from 0 (choices spread evenly round the cycle) to 1 (every trial at exactly the same phase). Someone who feels their heartbeat at a stable moment, and can match a tone to it, should score high. Someone guessing should score near the chance level for their number of trials, about 0.33 for 28 trials.

## Two scheduling modes

`mode` in `getParameters` sets what the dial controls. Both modes reset the dial to one of four start phases (0, 90, 180 or 270 degrees) at the start of each trial, drawn in shuffled blocks of four without an immediate repeat, so the participant cannot find the answer by remembering a dial position.

- **Relative mode** (`mode="relative"`, the default). The dial is a phase, in degrees of the anticipated heart period, and wraps at 360. The anticipated period is the mean of the last three R-R intervals. On each beat the tone is played at `phase / 360 * anticipated period` after the R-wave, so the tone keeps its place in the cycle when the heart speeds up or slows down. This is the mode of the PAT-ECG demonstration study. One notch of the mouse wheel moves the phase by `dialGainDeg` (10 degrees by default).
- **Absolute mode** (`mode="absolute"`). The dial is a delay in ms after the R-wave, as in the phone-based PAT. It wraps at the anticipated period and the delay is clamped to the current period: a dial at 950 ms when the period shrinks to 900 ms plays at 900 ms (phase 0), the markers and the row say so, and the next notch moves on from 900 ms. One notch moves it by `dialGainMs` (25 ms by default).

{cite:t}`2026:hodgetts` suggest running both modes when the heart period varies a lot between trials (during exercise or recovery, for instance), because they separate phase-locked from delay-locked perception.

## Exteroceptive control task

With `extero=True` the "heartbeat" is a 50 Hz vibration burst on the back of the non-dominant hand, and the participant matches the tone to the vibration with the same dial and procedure. It is a familiarization task and a screener: someone who cannot synchronize two plain external signals has probably not understood the task or is not engaging with it. {cite:t}`2026:hodgetts` excluded the 7 of 91 participants who scored below the chance threshold here.

The vibration period is set by `exteroPeriod`: `"simulated"` (the default) gives a variable series like a resting heart (base period 0.9 to 1.1 s with respiratory, slow and noise components, clamped to 0.55 to 1.5 s, smoothed over three beats), a number gives a fixed period in seconds (the paper used 1 s), and a sequence of periods replays it, for example a participant's own R-R intervals from the PAT. No ECG is needed for this variant.

## Hardware on our setup

- **ECG**: the PLUX hub with a chest ECG lead, streamed to LSL as `PLUX` by the hub bridge. [Recording devices](../getting-started/recording-devices.md#a-plux-hub) covers the bridge, the channel label and the electrode placement.
- **Audio**: headphones or speakers on the stimulus PC. Tones are 1000 Hz, 30 ms, with 5 ms ramps, on the left channel. The task plays them through PsychPortAudio (`psychtoolbox.audio`) directly, at latency class 1, which reports the true onset of every tone.
- **Tactor** (exteroceptive variant only): a vibrotactile transducer (Dayton Audio TT25-16 or similar) driven from the **right** audio channel through a small amplifier. Tone and vibration come from the same stereo stream, so they are locked to the sample. The burst is silent unless `vibrationVolume` is set above its default of 0, so ordinary speakers or headphones never carry it. The tactor also buzzes faintly; that is expected.
- **Dial**: the mouse wheel, held in the dominant hand. The left and right arrow keys move it too. Space, with the other hand, ends the trial.
- **Recording**: [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder) with the `PLUX` stream and the task's marker stream (`PAT`, set by `markerStream`), so the ECG and every beat, tone and key press land on one clock in one XDF file.

## Running the task

Install with the LSL extra, `pip install cardioception-toolbox[lsl]`. Start the PLUX bridge and LabRecorder, then run the wrapper from the repository root:

```
python wrappers/pat_lsl.py
```

It asks for:

| Field | Default | What it sets |
|---|---|---|
| participant | `Participant` | The participant identifier |
| session | `PAT` | The session identifier; `Extero` is appended for the exteroceptive run |
| LSL stream | `PLUX` | The name of the ECG stream |
| Channel | none | The label of the ECG channel in that stream. It must be given: the task does not start without it, unless the exteroceptive variant is ticked |
| Mode | `relative` | `relative` or `absolute` |
| Extero (vibration) | off | Run the exteroceptive variant, which needs no ECG |
| Language | `english` | The instructions, from the languages in `cardioception/PAT/texts` |

It then runs the instructions, the tutorial, 8 practice trials and 28 main trials, with a break every 10 trials. The same in a script, with the channel your stream has:

```python
from cardioception.devices import LSLRecorder
from cardioception.PAT.parameters import getParameters
from cardioception.PAT.task import run

# The task opens its own "PAT" marker stream, so the recorder opens none
recorder = LSLRecorder(
    name="PLUX", channel="ECG1", signal_type="ecg", marker_stream=None
)
parameters = getParameters(
    participant="sub01", session="001", recorder=recorder, mode="relative"
)
try:
    run(parameters, runTutorial=True, confidenceRating=True)
finally:
    parameters["win"].close()
    parameters["engine"].close()  # stops the beat detector, releases the sound card
    recorder.close()
```

The defaults of `getParameters` are those of the paper, except where noted:

| Parameter | Default | Meaning |
|---|---|---|
| `mode` | `"relative"` | What the dial controls (see above) |
| `nTrials`, `nPractice` | 28, 8 | Main and practice trials |
| `startPhases` | 0, 90, 180, 270 | Start phases of the dial, in degrees |
| `device` | `"keyboard"` | Rate confidence with the wheel and the arrow keys, space to confirm (`"keyboard"`), or with the mouse, a click to confirm (`"mouse"`). The dial is the wheel either way |
| `confidenceScale` | `DISCRETE_1_10` | The confidence scale (see below) |
| `language` | `"english"` | `"english"` or `"danish"` |
| `dialGainDeg`, `dialGainMs` | 10, 25 | Degrees per wheel notch in relative mode, ms per notch in absolute mode |
| `latencyBias`, `audioLead` | 0.05, 0.05 s | See [timing](#timing-and-latency) |
| `minToneGap` | 0.3 s | A tone less than this after the previous one is skipped. At least `toneDuration` plus 0.05 s |
| `showDial` | `True` | The ring and pointer around the fixation cross |
| `exteroPeriod` | `"simulated"` | The vibration's period in the exteroceptive variant |
| `vibrationVolume` | 0 | The vibration burst is silent unless raised |
| `seed` | drawn | Seeds the session's random generator; recorded in the manifest |
| `resultPath` | `data` | Root of the run directories |
| `overwrite` | `False` | Allow writing into a run directory that already holds results |
| `triggers` | none | `{event: callable}` for `trialStart`, `confidenceStart`, `confidenceStop` and `trialStop` |
| `markerStream` | `"PAT"` | The LSL marker stream the task opens |

The confidence rating has no time limit (`parameters["maxRatingTime"]` is `None`), as in the paper. A trial does: if space has not ended it after `parameters["maxTrialTime"]` seconds (60 by default), it ends without a choice and its row is marked `timeout`. Space works only once a tone has been heard, so without this a lost ECG would leave Esc as the only way out. The console warns the experimenter after `parameters["noBeatWarning"]` seconds (3) without a beat.

For the exteroceptive variant pass `extero=True` and no recorder is needed. The paper ran the exteroceptive task (8 + 28 trials, about 10 minutes) before the PAT (8 + 28 trials, about 30 minutes). Between 15 and 20 trials already separate consistent responders from chance; gains beyond 20 are small {cite:p}`2026:palmer`.

Instructions to the participant matter. Ask them to focus on one consistent body location, to sit still, breathe normally and not tense their muscles, which would amplify the heartbeat sensation. The experimenter sees a one-line status every second in the console (trial, heart rate, phase, tones anchored on real and predicted beats). Press Esc at any prompt to stop; what has been collected is saved. Esc during a trial, before space, drops that trial: the marker stream gets an `abort` marker rather than a `press`, the trial has no row in `final.txt`, and its tones are left out of `tones.txt` (the marker stream still has them).

## Output files

Each run gets its own directory, `data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/` (under `resultPath` instead of `data` when it is given), so a second run of the same session never overwrites the first. Every results file carries the three identifiers in its name, `sub-<participant>_ses-<session>_run-<timestamp>_<kind>.txt`:

| File | Written | Content |
|---|---|---|
| `manifest.json` | when the session is set up | participant, session, run, seed, version, device, language, mode, exteroceptive or not, trial counts and the confidence scale |
| `session.log` | as the task runs | the console messages, with timestamps |
| `..._parameters.txt` | when the task starts | the settings, one per line |
| `..._final.txt` | after every trial | one row per trial, tab separated |
| `..._tones.txt` | after every trial | one row per tone or vibration, tab separated |

The wrapper appends `Extero` to the session label of the exteroceptive run, so both runs of a session sit side by side. The seed of the session's random generator, which draws the start phases, the simulated heart of the exteroceptive task and the starting position of the confidence marker, is in the manifest; pass it back as `seed` to draw the same session again.

`final.txt`, one row per trial:

| Column | Meaning |
|---|---|
| `Trial`, `Block` | Trial number, and `practice` or `main` |
| `TrialStatus` | `ok`; `stale` when the press came more than 1.5 anticipated periods after the last R-wave (the ECG was lost, so `AnticipatedPeriodMs` is NaN, and so is `ChosenDelayMs` in relative mode or `ChosenPhaseDeg` in absolute mode); `timeout` when `maxTrialTime` ran out with no press (both chosen columns NaN, no rating asked). The scores use `ok` trials only |
| `Mode`, `Extero` | Scheduling mode, and whether this was the exteroceptive variant |
| `StartPhaseDeg` | Where the dial started |
| `ChosenPhaseDeg`, `ChosenDelayMs` | The choice at the space press, as a phase and as ms after the R-wave. `ChosenDelayMs` is the dial's delay, before `latencyBias` is subtracted from the tone's target |
| `AnticipatedPeriodMs` | The anticipated period at the last beat before the press: the mean of the last three R-R intervals, or in the exteroceptive variant the exact interval to the next virtual beat |
| `ObservedPeriodMs` | The R-R interval containing the press, known once the next R-wave arrives; NaN if it did not arrive within 3 s |
| `LastRTime`, `PressTime` | The last R-wave before the press and the press itself, in LSL seconds |
| `LastToneIndex`, `LastToneAnchor`, `LastToneRTime` | The last tone that sounded before the press: its `ToneIndex` in `tones.txt`, its anchor (`real` or `predicted`) and the R-wave it was timed from |
| `LastToneDelayMs` | The delay that tone was actually played at after the R-wave of its own cycle, with `latencyBias` added back so it reads like `ChosenDelayMs`. Equal to the dial for a `real` tone; for a `predicted` tone it is measured from the R-wave that followed the one it was timed from, and is NaN if that R-wave never came |
| `Confidence`, `ConfidenceRT` | The rating on the session's scale, from 1 (not at all) to 10 (extremely) by default, and its response time; empty when no rating was given |
| `ConfidenceUnit` | The same rating on 0 to 1, so sessions rated on different scales can be pooled |
| `Device` | `keyboard` (wheel and arrow keys) or `mouse` |
| `ConfidenceScale`, `ConfidenceLow`, `ConfidenceHigh`, `ConfidenceGranularity`, `ConfidenceLevels`, `ConfidenceSigned` | The scale the rating was given on, written on every row so the file explains itself |
| `nTonesReal`, `nTonesPredicted`, `nTonesSkipped` | Tones anchored on the detected beat, on the predicted next beat, and skipped by the double-tone guard |
| `TrialDuration`, `nDialMoves` | Seconds from trial start to press, and number of dial movements |
| `WallTime` | Computer clock time of the press |

`tones.txt`, one row per tone or vibration: `ToneIndex` (a running number across the session, which `LastToneIndex` refers to), `Trial`, `Block`, `RTime` (the R-wave it was timed from, LSL seconds), `PeriodS` (anticipated period), `PhaseDeg` and `DelayMs` (the dial), `Target` (when it was meant to sound), `Anchor` (`real`, `predicted` or `virtual`), `Onset` (the onset PsychPortAudio reported, NaN if none) and `Kind` (`tone` or `vibration`). Together with the ECG in the XDF file this gives the true R-to-tone interval of every tone, which the original PAT-ECG did not log.

## Confidence scale

`confidenceScale` takes a `cardioception.scales.ConfidenceScale`. The default, `DISCRETE_1_10`, is the 1 to 10 of the paper, labelled with the language's end labels (`Not at all` and `Extremely` in English). A scale passed in keeps its own labels, and its ends are the numbers the instructions name:

```python
from cardioception.scales import VAS_0_100

parameters = getParameters(..., confidenceScale=VAS_0_100.with_labels(["Not at all", "Extremely"]))
```

The confidence-weighted scores use the raw rating as the weight, not `ConfidenceUnit`: on the 1 to 10 scale `ConfidenceUnit` is 0 for a rating of 1, which would leave those trials out of the weighted score.

## Language

The participant's texts live in `cardioception/PAT/texts/<language>.yaml`, English and Danish so far, loaded by `cardioception.PAT.languages.get_texts` and checked for completeness when the session is set up. `cardioception.PAT.languages.available()` lists them, and the wrapper offers that list. A text can differ by rating device and by the exteroceptive variant; `{low}` and `{high}` stand for the ends of the confidence scale, and the instructions page that reads `{dial}` becomes the page describing the dial, or the one without it when `showDial=False`. To add a language, copy `english.yaml` and translate the values, not the keys or the placeholders.

## Running without a participant

`cardioception.PAT._autopilot.PATAutopilot` is a simulated participant for tests and dry runs. It is given the phase at which it feels the heartbeat, aims each trial at that phase plus Gaussian noise, rolls the wheel a notch at a time towards it, presses once it has settled, and rates its confidence at random. With `beat_source=` and `tone_player=` in place of the ECG and the sound card, a whole session runs headless:

```python
from cardioception.PAT._autopilot import PATAutopilot

parameters = getParameters(
    participant="pilot", extero=True, fullscr=False, seed=1,
    markerStream=None, tone_player=my_silent_player,
)
parameters["autopilot"] = PATAutopilot(parameters["rng"], target=120.0, spread=10.0)
run(parameters)
```

Here `my_silent_player` is any object with the tone player's `schedule(when, kind)` and `poll_onsets()` that reports each sound as played; `tests/test_pat_headless.py` has one, and runs an interoceptive session the same way with a virtual heart as `beat_source`.

## Scoring

`cardioception.PAT.scoring` holds the scores. It needs only numpy and pandas:

```python
from glob import glob

import pandas as pd
from cardioception.PAT.scoring import consistency_grid, extero_threshold

(path,) = glob("data/sub-sub01/ses-001/run-*/*_final.txt")
final = pd.read_csv(path, sep="\t")
grid = consistency_grid(final)
print(grid)
```

Only rows with `Block == "main"` count. `consistency_grid` returns eight rows, the 2 x 2 x 2 grid of {cite:t}`2026:hodgetts`:

| Factor | Levels |
|---|---|
| `mapping` | `variable`: each trial's angle uses its own period (phase-based consistency). `fixed`: every trial uses the participant's median period (delay-based consistency); trials whose delay exceeds that median are dropped. |
| `period` | `anticipated`: the period the task used online. `observed`: the R-R interval that contained the press. |
| `weighting` | `none`, or `confidence`: each trial weighted by its rating. |

The scores use `ChosenDelayMs`, the dial at the press. That is the delay the participant heard only when the last tone was anchored on a `real` beat. A `predicted` tone was timed from the R-wave before, one anticipated period ahead, so when the heart period changes from one beat to the next it sounds earlier or later than the dial says, by tens of ms at resting heart rate variability. To score what was heard instead, use `LastToneDelayMs`, or join `LastToneIndex` to `ToneIndex` in `tones.txt` and measure each tone's `Onset` from the R-waves in the XDF file.

Each row gives `n_trials` (trials scored), `n_dropped` (main trials left out because their `TrialStatus` is not `ok`), `score` (the MRL), `threshold` and `interoceptive` (`score > threshold`). Before scoring, trials that are `stale` or `timeout` are dropped, then trials with a missing period, then trials whose period lies more than 5 robust standard deviations (1.4826 times the median absolute deviation) from the participant's median period, separately for each period type. In the paper this removed under 1 % of trials. The robust standard deviation is floored at 1 ms, so a run with a fixed period, where the median absolute deviation is 0, loses no trial to float noise.

The threshold is the participant's own chance level: 100,000 simulated participants with the same number of valid trials choose delays uniformly over the period, and the threshold is the 95th percentile of their MRL. A delay uniform over a period is a phase uniform over the cycle, whatever the period, so the threshold depends on the number of trials (and the weights), not on the participant's periods or the mapping. Weighted cells keep the participant's confidence ratings as weights in the simulation, so unequal ratings raise the threshold a little. The simulations use a fixed seed (`seed=0`), so the same file always gives the same grid. `n_sim` and `seed` can be changed.

How to read the grid:

- **Interoceptive** is a descriptive label: the choices were more consistent than 95 % of random responders with the same trials would be. The score itself can be used as a continuous measure.
- **Variable and fixed mapping** ask different questions. A high variable-mapping score means the tone was kept at a stable phase of the cycle; a high fixed-mapping score means it was kept at a stable delay after the R-wave. At rest, with stable heart periods, the two mostly agree. Report both.
- **Anticipated and observed period** rarely disagree. In the paper the anticipated period was a few ms longer than the observed one, and the choice changed the classification of two borderline participants.
- **Confidence weighting** changes little, because confidence varies mostly between people rather than between trials.

For comparison, {cite:t}`2026:hodgetts` classified 14 of 84 participants (16.7 %) as interoceptive on at least one of the eight routes and 10 on all eight, in line with the 17 % found with the phone-based PAT.

For the exteroceptive screen, score the exteroceptive `final.txt` with the same function. `extero_threshold(28)` gives the threshold for 28 trials at a fixed 1000 ms period: 0.326 with 100,000 runs, the R = 0.33 of the paper.

## Timing and latency

In the original PAT-ECG an analogue R-wave detector triggers the microcontroller, so the tone is microseconds behind the R-wave. Here the ECG travels from the PLUX hub over Bluetooth to LSL, and Python finds the R-wave online. Measured on our stimulus PC:

- **The beat is known about 20 ms after the R-peak** (95th percentile 31 ms).
- **Audio onsets** reported by PsychPortAudio are within about 1 ms of the target, provided the tone is scheduled at least `audioLead` (50 ms) ahead.

Each tone's target is `R + delay - latencyBias`. If that is at least `audioLead` after the moment the beat is known, the tone is timed from that beat (anchor `real`). Otherwise it is too late for this cycle, and the tone is timed from the *predicted* next R-wave, one anticipated period later (anchor `predicted`). With the defaults the boundary sits about 120 to 137 ms after the R-wave: about 20 ms until the beat is known, then up to one frame (17 ms at 60 Hz) until the engine sees it, since it is polled once per screen refresh, plus `audioLead` and `latencyBias`. That is roughly the first 35 to 40 degrees of the cycle at 50 beats per minute and 60 to 65 at 80. Predicted tones scatter more than real ones, because the true next cycle differs from the three-beat mean. `tones.txt` records which anchor each tone used.

`latencyBias` (default 0.05 s) is a constant subtracted from every target. It stands for the physical delay that LSL timestamps cannot see: the Bluetooth transfer before the samples are stamped (20 to 40 ms) and the path from the reported audio onset to the sound reaching the ear. Together these come to roughly 30 to 70 ms on our setup. A constant bias shifts every tone by the same amount, so it leaves fixed-mapping consistency unchanged and variable-mapping consistency almost unchanged. It does matter for the *mean* phase a participant chooses; report the bias whenever you report that.

Space stops new tones, not the ones already handed to the sound card, so up to about 1.1 s of tones (at most one period plus `audioLead`) can follow the press. This is a design choice: the choice is the dial at the press, whatever is heard after it, and those tones are logged in `tones.txt` like any other. After the press the task waits for the next R-wave, which gives `ObservedPeriodMs`, and for the onsets of those last tones, at most 3 s. The fixation cross stays on screen during that wait, the window keeps refreshing, and Esc ends it at once; the trial is then kept, without a rating, and the task stops.

Further checks of the timing chain are in `bench/README.md` in the repository.
