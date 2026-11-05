---
myst:
  html_meta:
    description: "What every Cardioception session has in common: the ready-made wrappers, where the data goes, the run manifest, instruction languages, confidence scales and a Windows shortcut."
    keywords: "cardioception, run a session, wrappers, output files, manifest, confidence scale, language, interoception task"
---

# Running a session

Every task is run the same way. Its `parameters` submodule builds a dictionary from keyword arguments, and its `task` submodule runs the session from that dictionary. Each task page shows the call for its own task; this page covers what the tasks share.

## The wrappers

The [wrappers](https://github.com/embodied-computation-group/Cardioception/tree/master/wrappers) folder of the repository has a ready-to-run script for each task. Each opens a dialog for the session settings, then runs the task with the defaults of the published version:

```bash
python wrappers/hrd.py
```

| Wrapper | Task | Device | Dialog fields |
|---|---|---|---|
| `hrd.py` | HRD | pulse oximeter | participant, session, serial port, setup, response device, language |
| `hrd_lsl.py` | HRD | ECG or PPG over LSL | participant, session, stream, channel, signal type, response device, language |
| `hbc.py` | HBC | pulse oximeter | participant, session, serial port, setup, language |
| `pat_lsl.py` | PAT | ECG over LSL | participant, session, stream, channel, mode, exteroceptive control, language |
| `hsd_lsl.py` | HSD | ECG over LSL | participant, session, stream, channel, axis, response device, language |

Copy the one you need into your own folder and edit it there.

## Where the data goes

Each run gets its own directory under `data/` in the working directory, or under `resultPath` when it is given:

```text
data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/
  manifest.json
  session.log
  sub-<participant>_ses-<session>_run-<timestamp>_final.txt
  ...
```

The timestamp makes the directory unique, so a repeated session never overwrites an earlier one, and every file name carries participant, session and run, so a file still identifies itself after being copied out.

`manifest.json` is written when the parameters are built, before the first trial: the task and package version, the start time, the seed, the device, language and setup, the confidence scale and the recording device. An aborted session therefore still has a record of its settings. `session.log` holds the console messages with timestamps.

`*_final.txt` has one row per trial and is written when the task ends. The HRD, HBC and HSD also save the rows so far to `*_behaviour.txt` after every trial. The other files, the physiological recordings, the staircase posteriors and the parameters, differ by task and are listed on each task page.

The seed of the session's random generator is drawn when none is given and recorded in the manifest. Passing it back as `seed=` draws the same session again.

## Languages

The instructions are shown in the language passed as `language`, which names a YAML file in the task's `texts/` folder:

| Task | Languages |
|---|---|
| HRD | `english`, `danish`, `danish_children`, `french`, `german` |
| HBC | `english`, `german` |
| PAT | `english`, `danish` |
| HSD | `english` |

`english` is the default everywhere. Each task's `languages.available()` returns the list, and an unknown language raises an error before any window opens. To add a language, copy `english.yaml`, translate the values and pass the new file's name.

## Confidence scales

Confidence is rated on a `cardioception.scales.ConfidenceScale`. Four are shipped:

| Scale | Kind | Range |
|---|---|---|
| `VAS_0_100` | continuous slider | 0 to 100 |
| `DISCRETE_1_7` | discrete | 1 to 7 |
| `DISCRETE_1_10` | discrete | 1 to 10 |
| `VAS_SIGNED_100` | continuous, signed | -100 to 100 |

The HRD defaults to `VAS_0_100` with the mouse and `DISCRETE_1_10` with the keyboard; the HBC to `DISCRETE_1_7`; the PAT and HSD to `DISCRETE_1_10`. A default scale takes its end labels from the chosen language. Pass `confidenceScale=` to use another, with `with_labels` to set the labels:

```python
from cardioception.scales import VAS_0_100

parameters = getParameters(..., confidenceScale=VAS_0_100.with_labels(["Guess", "Certain"]))
```

Every row of the results carries the rating on its own scale, the same rating on 0 to 1 as `ConfidenceUnit`, and the scale's definition (`ConfidenceScale`, `ConfidenceLow`, `ConfidenceHigh`, `ConfidenceGranularity`, `ConfidenceLevels`, `ConfidenceSigned`), so sessions rated on different scales can be pooled without the parameters file.

## A Windows shortcut

Once a wrapper is edited, a `.bat` file starts the task with a double click. With the virtual environment from the installation:

```bat
call C:\Users\you\cardio\cardioception-env\Scripts\activate.bat
python C:\Users\you\cardio\hrd.py
pause
```

With conda, activate the `cardioception` environment rather than the base one:

```bat
call C:\Users\you\miniconda3\condabin\conda.bat activate cardioception
python C:\Users\you\cardio\hrd.py
pause
```

## Next step

Go to the page of the task you are running: [Heart Rate Discrimination](../tasks/hrd/index.md), [Heartbeat Counting](../tasks/hbc.md), [Phase Adjustment Task](../tasks/pat.md) or [Heartbeat Synchrony Discrimination](../tasks/hsd/index.md). [The tasks](../tasks/index.md) sets them side by side.
