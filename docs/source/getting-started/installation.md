---
myst:
  html_meta:
    description: "Install cardioception-toolbox with pip or conda, from a machine with nothing installed to a Heart Rate Discrimination task you can run."
    keywords: "install cardioception, cardioception-toolbox, pip, conda, PsychoPy, heart rate discrimination"
---

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

Expect this to take a few minutes. Cardioception itself is a small download,
about 8 MB, but it pulls in PsychoPy and its Qt stack, so several hundred MB
will cross the network in total. On disk the package expands to roughly 140 MB,
almost all of it the 370 pre-generated tone files the Heart Rate Discrimination
task plays: they compress well in the wheel and do not on disk.

```text
Successfully installed cardioception-toolbox-0.7.0 psychopy-2026.2.2 systole-core-0.3.1 ...
```

```{note}
The distribution is named `cardioception-toolbox`. The import name is still
`cardioception`, so existing scripts do not change.
```

````{important}
Until the next release, PyPI has the 0.7 line (0.7.2), and that is what the
command above installs. This documentation describes the rewritten package,
with the new output layout and the Heartbeat Synchrony Discrimination task
and the Phase Adjustment Task, both in beta. It reaches PyPI with the next
release; until then, install it from the `dev` branch:

```bash
pip install git+https://github.com/embodied-computation-group/Cardioception.git@dev
```

The [changelog](https://github.com/embodied-computation-group/Cardioception/blob/HEAD/CHANGELOG.md) lists what changes from 0.7.x and how to migrate analysis
scripts.
````

To read ECG or PPG from a [Lab Streaming Layer](https://labstreaminglayer.org/)
stream instead of the Nonin oximeter, install the optional dependency as well:

```bash
pip install "cardioception-toolbox[lsl]"
```

The [Recording devices](recording-devices.md#ecg-or-ppg-over-lsl) page explains how to point the
task at the stream.

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

Plug the pulse oximeter in and confirm the computer can see a real signal
before you try to collect data:

```bash
python -m cardioception.check_device
```

It finds the port on its own when there is only one, records for twenty
seconds, and tells you plainly what it saw:

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

It exits 0 only for a clean signal, so it can be used in a startup script.

```{important}
**Read the amplitude, not the beat count.** With an empty sensor the peak
detector still reports beats, and they look entirely reasonable. A real
measurement on an empty Nonin gave 67 BPM from 16 detected beats, on a trace
spanning a single ADC unit. Nothing about the beat count gave it away; the
amplitude of 1.0 did.
```

The three cases it distinguishes:

| Verdict | What it means |
|---|---|
| `no finger in the sensor` | Amplitude below 20. The trace is flat and any beats are noise. |
| `signal present but detection unreliable` | Real signal, but the intervals between beats are too scattered to trust. Reseat the sensor, keep the hand still and below heart level. |
| `clean physiological signal` | Amplitude in the hundreds, intervals between 0.4 and 1.2 s with little spread. Ready. |

Useful options: `--list` prints the serial ports and exits, `--port COM3` picks
one when several are attached, and `--duration` changes the recording length.

## You are ready

Continue to [Running a session](running-a-session.md) to run a session, and to the
[tutorials](../tasks/hrd/tutorials/index.md) for what to do with the data afterwards.

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

(legacy-versions)=
## Legacy versions

This documentation describes the current version. Older ones stay available
for studies that started on them.

The 0.7 line, the last before the 2026 rewrite, is kept as the `legacy/0.7`
branch and the `v0.7.2` tag. Install it from PyPI or from the branch:

```bash
pip install cardioception-toolbox==0.7.2
pip install git+https://github.com/embodied-computation-group/Cardioception@legacy/0.7
```

The 0.4 line dates from the period of the Heart Rate Discrimination paper
{cite:p}`2022:legrand` and is tagged `v0.4.0`, `v0.4.1`, `v0.4.2`, `v0.4.3`,
`v0.4.4` and `v0.4.5`. The first four were tagged in 2021, the last two in 2023
and 2025. The repository does not record which of them matches the code used in
the paper. They pin the dependencies of their time (`v0.4.5` requires PsychoPy
2020.1.2), so expect to need an older Python. Install one from its tag, for
example:

```bash
pip install git+https://github.com/embodied-computation-group/Cardioception@v0.4.3
```

These versions write their output to the old flat layout,
`data/<participant><session>/`, with participant and session joined together,
rather than to `data/sub-<participant>/ses-<session>/run-<timestamp>/`. The
migration notes in the
[changelog](https://github.com/embodied-computation-group/Cardioception/blob/HEAD/CHANGELOG.md)
describe the change and what it means for analysis scripts.

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
