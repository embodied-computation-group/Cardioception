# Installation

From a machine with nothing installed to a task you can run, in five steps.

Each step prints something. Compare what you get against what is shown here
rather than assuming it worked, because most of the ways this goes wrong are
quiet ones.

```{note}
Cardioception needs **Python 3.10 or 3.11**. The upper bound is not PsychoPy,
which allows 3.12, but `pywinhook`: it publishes wheels only up to 3.11, and
without one it has to be compiled from source on Windows, which needs a C
toolchain most people do not have. `pip` refuses anything outside that range
rather than failing halfway through an install.
```

## 1. Install Python 3.10 or 3.11

Download it from [python.org/downloads](https://www.python.org/downloads/) and
pick a 3.10 or 3.11 release. On Windows, tick **Add Python to PATH** in the
installer.

If you already use Anaconda, skip to [the conda route](#the-conda-route) instead.

Check which version you have:

```bash
python --version
```

```text
Python 3.10.11
```

Anything outside 3.10 and 3.11 means you are running a different interpreter.
On Windows, `py -3.10 --version` selects one explicitly.

## 2. Make a virtual environment

This keeps the task's packages separate from everything else on the machine, so
installing Cardioception cannot break another project and another project cannot
break Cardioception.

```bash
python -m venv cardioception-env
```

Then activate it. The command differs by platform:

```bash
cardioception-env\Scripts\activate     # Windows
source cardioception-env/bin/activate  # macOS and Linux
```

Your prompt gains a `(cardioception-env)` prefix. It has to be there every time
you run the task; if you close the terminal, activate it again.

```{warning}
On Windows, keep this folder somewhere short, such as `C:\Users\you\cardio`.
Some dependencies create deeply nested paths, and Windows refuses paths over 260
characters unless long path support is enabled. A long project path produces a
confusing failure part-way through installation.
```

## 3. Install Cardioception

```bash
pip install cardioception-toolbox
```

Expect this to take a few minutes and to download roughly 140 MB, most of it the
370 pre-generated tone files the Heart Rate Discrimination task plays.

```text
Successfully installed cardioception-toolbox-0.6.1 psychopy-2026.2.2 systole-core-0.3.1 ...
```

```{note}
The distribution is named `cardioception-toolbox`. The import name is still
`cardioception`, so existing scripts do not change.
```

## 4. Check that it imports

The install can succeed while the package still fails to load, so check
directly:

```bash
python -c "from cardioception.HRD import task; print('HRD ok')"
python -c "from cardioception.HBC import task; print('HBC ok')"
```

```text
HRD ok
HBC ok
```

If either raises, go to [Troubleshooting](#troubleshooting) below. The error
text usually names the cause precisely.

## 5. Check the recording device

Plug the pulse oximeter in and confirm the computer can see it before you try to
collect data. A beat count on its own is not enough: with an empty sensor the
peak detector still reports beats, so a session can look fine and contain
nothing.

Find the port first:

```bash
python -c "from serial.tools import list_ports; [print(p.device, p.description) for p in list_ports.comports()]"
```

```text
COM3 USB Serial Port (COM3)
```

On macOS and Linux the name looks like `/dev/tty.usbserial-XXXX` or
`/dev/ttyUSB0` instead.

Then record for a few seconds **with a finger in the sensor** and look at the
signal rather than the beat count:

```python
import numpy as np, serial
from systole.recording import Oximeter

ser = serial.Serial("COM3", baudrate=9600, timeout=1/75, stopbits=1)
oxi = Oximeter(serial=ser, sfreq=75, add_channels=1)
oxi.setup()
oxi.read(duration=20)
ser.close()

rec = np.asarray(oxi.recording, dtype=float)
idx = np.where(np.asarray(oxi.peaks))[0]
amplitude = np.percentile(rec, 95) - np.percentile(rec, 5)
print(f"amplitude {amplitude:.1f}, beats {len(idx)}")
if len(idx) > 2:
    ibi = np.diff(idx) / 75
    print(f"heart rate {60/ibi.mean():.0f} BPM, interval sd {ibi.std():.3f} s")
```

Read **amplitude first**, then the intervals:

| What you see | What it means |
|---|---|
| amplitude near 1, intervals scattered | No finger in the sensor. The trace is flat and the reported beats are noise. |
| amplitude large, interval sd above about 0.15 s | Finger present but detection is unreliable. Reseat the sensor and keep the hand still. |
| amplitude large, intervals between roughly 0.5 and 1.2 s with small spread | A clean physiological signal. You are ready. |

For reference, an empty sensor measured on our setup gave an amplitude of 1.0
across a raw range of 99 to 100, and still reported 10 beats in 20 seconds with
an interval spread of 2.1 seconds. Beat count alone would not have caught it.

## You are ready

Continue to the [user guide](user_guide.md) to run a session, and to the
[tutorials](tutorials/index.md) for what to do with the data afterwards.

To run without any hardware, both tasks accept `setup="test"`, which skips the
oximeter and opens a windowed rather than fullscreen display.

(the-conda-route)=
## The conda route

`environment.yml` at the root of the repository is an alternative to steps 1 to
3, not an addition to them. Use it if you already have Anaconda or Miniconda
installed, in which case it is the shorter path: it pins the interpreter to 3.10
for you and installs `pywinhook` from conda-forge, which on Windows saves
building it from source.

```bash
git clone https://github.com/embodied-computation-group/Cardioception.git
cd Cardioception
conda env create -f environment.yml
conda activate cardioception
```

Then carry on from step 4. `environment_linux.yml` is the same thing with PyMC added for the analysis
notebooks.

If you do not already use conda, do not install it just for this. The venv route
above works and involves one fewer tool.

(troubleshooting)=
## Troubleshooting

These are the errors that actually come up, with what causes them.

| Error | Cause and fix |
|---|---|
| `ERROR: Package requires a different Python: 3.x not in '>=3.10,<3.12'` | Working as intended. Install 3.10 or 3.11 and build the environment from it. |
| `error: command 'swig.exe' failed` | Python 3.12 or later on Windows, where `pywinhook` has no wheel and tries to build from source. Use 3.10 or 3.11, or take the conda route, which supplies it prebuilt. |
| `ModuleNotFoundError: No module named 'pkg_resources'` | An older Cardioception with PsychoPy 2022.2.5, which imported it. Upgrade, or pin `setuptools<81`. |
| `OverflowError: line number table is too long` | An older PsychoPy on Python 3.10 or later. Upgrade Cardioception. |
| `Could not install packages due to an OSError: [Errno 2] No such file or directory: '...'` with a very long path | The Windows 260-character path limit. Move the environment somewhere shallower, or enable long path support. |
| `Can't connect to HTTPS URL because the SSL module is not available` | The virtual environment was built from an Anaconda interpreter. Build it from a python.org install, or use the conda route instead of `venv`. |
| `SerialException: could not open port` | Wrong port name, or another program is holding the device. Close anything else reading it and re-run the port listing above. |
| Task runs but the recording is flat | Almost always the sensor rather than the software. Re-run step 5 and read the amplitude. |

If none of these match, please
[open an issue](https://github.com/embodied-computation-group/Cardioception/issues)
with the full error, your operating system, and the output of
`python --version` and `pip list`.
