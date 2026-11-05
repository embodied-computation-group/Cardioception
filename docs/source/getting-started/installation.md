---
myst:
  html_meta:
    description: "Install cardioception-toolbox with pip or conda, from a machine with nothing installed to a checked pulse signal."
    keywords: "install cardioception, cardioception-toolbox, pip, conda, PsychoPy, pulse oximeter"
---

# Installation

From a machine with nothing installed to a first session and a checked pulse signal, in six steps. Each step prints something; compare what you get with what is shown here.

Cardioception needs Python 3.10 or 3.11. The upper bound is `pywinhook`, which ships wheels only up to 3.11; `pip` refuses any other version before it starts.

## 1. Install Python 3.10 or 3.11

Download it from [python.org/downloads](https://www.python.org/downloads/). Pick 3.11.9 or 3.10.11: later point releases of 3.10 and 3.11 are source-only and have no Windows installer. On Windows, tick **Add Python to PATH** in the installer. If you already use Anaconda, skip to [the conda route](#the-conda-route) instead.

```bash
python --version
```

```text
Python 3.10.11
```

Anything outside 3.10 and 3.11 means you are running a different interpreter. On Windows, `py -3.10 --version` selects one explicitly.

## 2. Make a virtual environment

```bash
python -m venv cardioception-env
cardioception-env\Scripts\activate     # Windows
source cardioception-env/bin/activate  # macOS and Linux
```

Your prompt gains a `(cardioception-env)` prefix. It has to be there every time you run a task; if you close the terminal, activate the environment again.

```{warning}
On Windows, keep this folder somewhere short, such as `C:\Users\you\cardio`. Some dependencies create deeply nested paths, and Windows refuses paths over 260 characters unless long path support is enabled.
```

## 3. Install Cardioception

```bash
pip install cardioception-toolbox
```

```text
Successfully installed cardioception-toolbox-1.0.0 psychopy-2026.2.2 systole-core-0.3.1 ...
```

Expect this to take a few minutes: the package is small, but it pulls in PsychoPy and its Qt stack. On disk it expands to roughly 140 MB, almost all of it the pre-generated tone files the Heart Rate Discrimination task plays. The distribution is named `cardioception-toolbox`; the import name is `cardioception`.

To read ECG or PPG from a [Lab Streaming Layer](https://labstreaminglayer.org/) stream, install the extra as well:

```bash
pip install "cardioception-toolbox[lsl]"
```

The development version installs from the `dev` branch with `pip install git+https://github.com/embodied-computation-group/Cardioception.git@dev`.

## 4. Check that it imports

The install can succeed while the package still fails to load, so check directly:

```bash
python -c "from cardioception.HRD import task; print('ok')"
```

```text
ok
```

If this raises, go to [Troubleshooting](#troubleshooting). The error text usually names the cause.

## 5. Run a task without hardware

Save this as `try_hrd.py` and run it with `python try_hrd.py`. `setup="test"` replays a recorded pulse, so no device is needed:

```python
from cardioception.HRD.parameters import getParameters
from cardioception.HRD import task

parameters = getParameters(participant="sub01", session="pilot", setup="test", nTrials=10)
task.run(parameters, confidenceRating=True, runTutorial=False)
parameters["win"].close()
```

A window opens and runs ten trials; answer with the mouse buttons. PsychoPy's audio backend can ignore the system volume, so turn the speakers or headphones down first. The results land in `data/sub-sub01/ses-pilot/run-<timestamp>/`.

## 6. Check the pulse signal

This step is for the USB pulse oximeter. For an ECG or PPG device over LSL, skip it and go to [Recording devices](recording-devices.md#ecg-or-ppg-over-lsl).

Plug the oximeter in, put a finger in the sensor and confirm the computer sees a real signal:

```bash
python -m cardioception.check_device
```

```text
Using the only serial port found: COM3 (USB Serial Port (COM3))
Recording 20 s from COM3. Keep a finger in the sensor.

  samples            1500 (20.0 s)
  signal amplitude   242.7      (needs > 20)
  beats detected     29
  heart rate         87 BPM
  beat intervals     0.60 to 0.80 s, sd 0.045   (needs sd < 0.15)

  VERDICT: clean physiological signal
  Ready to collect data.
```

Read the amplitude, not the beat count: an empty sensor still yields plausible beats, and only the amplitude gives it away. The [Recording devices](recording-devices.md) page lists the verdicts and the options, and covers ECG and PPG over LSL, which this check does not test.

## Next step

Continue to [Recording devices](recording-devices.md) to connect the device your tasks will use.

(the-conda-route)=
## The conda route

`environment.yml` at the root of the repository replaces steps 1 to 3 on Windows for people who already have Anaconda or Miniconda. It pins the interpreter to 3.10 and installs `pywinhook` from conda-forge, which saves building it from source. `pywinhook` exists only for Windows, so on Linux use `environment_linux.yml`, which leaves it out and adds PyMC and metadpy for the legacy report notebooks. There is no file for macOS; use the venv route there.

```bash
git clone https://github.com/embodied-computation-group/Cardioception.git
cd Cardioception
conda env create -f environment.yml
conda activate cardioception
```

Then carry on from step 4. If you do not already use conda, the venv route above involves one fewer tool.

(legacy-versions)=
## Legacy versions

Older versions stay available for studies that started on them.

The 0.7 line, the last before the 2026 rewrite, is kept as the `legacy/0.7` branch and the `v0.7.2` tag:

```bash
pip install cardioception-toolbox==0.7.2
```

The 0.4 line dates from the period of the Heart Rate Discrimination paper {cite:p}`2022:legrand` and is tagged `v0.4.0` to `v0.4.5`. The paper's data were collected between July and November 2020 with development code that declared version 0.3.0, before any release was tagged, and the HRD changed between the two sessions. The paper's analysis code and data are in [CardioceptionPaper](https://github.com/embodied-computation-group/CardioceptionPaper); `v0.4.0` (April 2021) is the first tagged release after it. The 0.4 releases pin the dependencies of their time (`v0.4.5` requires PsychoPy 2020.1.2), so expect to need an older Python:

```bash
pip install git+https://github.com/embodied-computation-group/Cardioception@v0.4.3
```

These versions write to the old flat layout, `data/<participant><session>/`, rather than to the per-run directories described under [Running a session](running-a-session.md#where-the-data-goes). The [changelog](../reference/changelog.md) describes the change and what it means for analysis scripts.

(troubleshooting)=
## Troubleshooting

| Error | Cause and fix |
|---|---|
| `ERROR: Package requires a different Python: 3.x not in '>=3.10,<3.12'` | Working as intended. Install 3.10 or 3.11 and build the environment from it. |
| `error: command 'swig.exe' failed` | Python 3.12 or later on Windows, where `pywinhook` has no wheel and tries to build from source. Use 3.10 or 3.11, or take the conda route, which supplies it prebuilt. |
| `ModuleNotFoundError: No module named 'pkg_resources'` | An older Cardioception with PsychoPy 2022.2.5, which imported it. Upgrade, or pin `setuptools<81`. |
| `OverflowError: line number table is too long` | An older PsychoPy on Python 3.10 or later. Upgrade Cardioception. |
| `Could not install packages due to an OSError: [Errno 2] No such file or directory: '...'` with a very long path | The Windows 260-character path limit. Move the environment somewhere shallower, or enable long path support. |
| `Can't connect to HTTPS URL because the SSL module is not available` | The virtual environment was built from an Anaconda interpreter. Build it from a python.org install, or use the conda route instead of `venv`. |
| `SerialException: could not open port` | Wrong port name, or another program is holding the device. Close anything else reading it and run `python -m cardioception.check_device --list`. |
| Task runs but the recording is flat | Almost always the sensor rather than the software. Re-run step 6 and read the amplitude. |

If none of these match, [open an issue](https://github.com/embodied-computation-group/Cardioception/issues) with the full error, your operating system, and the output of `python --version` and `pip list`.
