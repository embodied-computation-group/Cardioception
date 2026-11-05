---
myst:
  html_meta:
    description: "The Heartbeat Counting task in Cardioception: what it measures, what a trial looks like, how to run it, its versions, the files it saves and the Hart et al. accuracy score."
    keywords: "heartbeat counting task, heartbeat tracking, Schandry, Garfinkel, interoceptive accuracy, cardioception"
---

# Heartbeat Counting task

The Heartbeat Counting task (HBC) {cite:p}`1981:schandry,1978:dale` compares the number of heartbeats a person reports over a fixed window with the number recorded. The score is usually taken to index interoceptive accuracy. The task is established, and the package keeps it because much of the literature rests on it. A good score can come from a plausible estimate of heart rate rather than from feeling beats; [what heartbeat counting can establish](theory.md#what-heartbeat-counting-can-establish) sets out the evidence.

## What a trial looks like

A tone marks the start of the window. The participant silently counts the heartbeats they feel while the pulse is recorded. A second tone marks the end. They then type the number they counted and press enter, and rate their confidence from 1 ("Guess") to 7 ("Certain") on the keyboard.

```{figure} ../images/HeartBeatCounting.png
:alt: The HBC trial sequence, the instruction to count after the tone, the counting window with the heart rate recorded, the typed count, and a confidence rating from 1 to 7. The trial lengths 25, 30, 35, 40, 45 and 50 s are shown in random order.

One HBC trial. The window lengths and the 1 to 7 confidence scale are the defaults.
```

The default version, `taskVersion="Garfinkel"`, runs six counting windows of 25, 30, 35, 40, 45 and 50 s in random order. `taskVersion="Schandry"` runs three windows of 25, 35 and 45 s after a minute of rest, separated by 30 s rests, in that fixed order. With `runTutorial=True` the session starts with instruction screens, and in every version a 30 s rest with the pulse recorded precedes the first window. The default version takes about 4 minutes.

## What you need

- A pulse oximeter on a USB port (the Nonin 3012LP Xpod by default), or an ECG or PPG device streaming over Lab Streaming Layer. [Recording devices](../getting-started/recording-devices.md) covers both and how to check the oximeter before a session.
- Speakers or headphones for the start and stop tones.
- A keyboard.

## Running it

Copy `wrappers/hbc.py` from the repository next to your data folder and run it:

```
python hbc.py
```

A dialog asks for the participant and session identifiers, the serial port the oximeter is on (`python -m cardioception.check_device --list` lists the ports), the setup and the language. The same in a script:

```python
from cardioception.HBC.parameters import getParameters
from cardioception.HBC.task import run

parameters = getParameters(
    participant="Subject_01", session="HBC", serialPort="COM3",
    setup="behavioral", taskVersion="Garfinkel")
run(parameters, runTutorial=True)
parameters["win"].close()
```

With an LSL device, pass `recorder=LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg")` instead of a port, as on the [HRD page](hrd/index.md#running-it). `setup="test"` replays a recorded pulse, for checking a script without a device. Escape ends the session.

## The main settings

| Argument | Default | Meaning |
|---|---|---|
| `taskVersion` | `"Garfinkel"` | `"Garfinkel"`, `"Schandry"`, or `"test"` (a 5 s rest and a 5 s count) |
| `language` | `"english"` | `"english"` or `"german"`; `cardioception.HBC.languages.available()` lists them |
| `confidenceScale` | `DISCRETE_1_7` | A `cardioception.scales.ConfidenceScale`. The end labels follow the language |
| `setup` | `"behavioral"` | `"behavioral"` reads the oximeter; `"test"` replays a recorded pulse |
| `serialPort` | `"COM3"` | The port the oximeter is on |
| `resultPath` | `data` | Root of the run directories |
| `overwrite` | `False` | Allow writing into a run directory that already holds results |
| `seed` | drawn | Seeds the order of the windows; recorded in the manifest |
| `triggers` | none | `{event: callable}` for `trialStart`, `listeningStart`, `listeningStop`, `confidenceStart`, `confidenceStop` and `trialStop` |

The window lengths and conditions are `parameters["times"]` and `parameters["conditions"]` (`"Rest"` or `"Count"`); a custom schedule is set by editing them after `getParameters` returns.

## What it saves

A session writes to `data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/`, under `resultPath` when it is given.

| File | Contents |
|---|---|
| `*_final.txt` | One row per window |
| `*_ppg-rest.txt`, `*_ppg-<n>.txt` | The pulse recorded during the rest and during window `n`, with the trigger codes in `Channel_0` (1 at the start tone, 2 at the stop tone) |
| `manifest.json` | The settings, the seed and the version, written before the first trial |
| `*_behaviour.txt`, `session.log` | The rows written after every window, and the session's log |

The columns of `*_final.txt`:

| Column | Meaning |
|---|---|
| `nTrial` | The window number, from 0 |
| `Condition` | `Rest` or `Count` |
| `Duration` | The length of the window in seconds |
| `Reported` | The number the participant typed |
| `Confidence`, `ConfidenceRT` | The rating on the scale shown, and its response time. `ConfidenceUnit` holds the rating on 0 to 1, and the scale columns describe the scale |

The task does not count the recorded beats. The true count of each window comes from its pulse file.

## Scoring

Detect the beats in each `*_ppg-<n>.txt` file, count them, and score each window with the accuracy of {cite:t}`2013:hart`:

```{math}
   Accuracy = 1-\frac{\left | N_{real} - N_{reported} \right |}{\frac{N_{real} + N_{reported}}{2}}
```

The [legacy report notebook](hrd/reports.md) computes this score with `report(..., task="HBC")`. A score near 1 is consistent with feeling every beat, and also with knowing one's resting heart rate; the score cannot separate the two.

## Where to go next

- [What heartbeat counting can establish](theory.md#what-heartbeat-counting-can-establish): the evidence on what a counting score identifies.
- [HTML reports (legacy)](hrd/reports.md): the notebook report of a session.
- [API](../reference/api.rst): every argument of `getParameters`.
