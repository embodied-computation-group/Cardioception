# First time install notes (Windows)

Notes from installing and running the HRD task from scratch on a clean Windows 11 machine
with a Nonin 3012LP Xpod pulse oximeter attached. Recorded so the installation docs can be
improved. Each item lists the symptom a first time user sees, the cause, and the fix.

Eight distinct roadblocks came up between `pip install` and a running task. Three of them
are defects in this repository or in the published package rather than local environment
problems, and those are marked as such.

## Test machine

| | |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| Interpreters present | 3.13.7, 3.12, 3.10.11, and Anaconda base 3.8.5 |
| conda | 4.9.2 (November 2020) |
| Device | Nonin 3012LP Xpod, FTDI USB serial, enumerated as COM3 |

## The headline problem: only Python 3.9 works

The supported range is far narrower than the docs suggest, and it is squeezed from both
ends. The README says only "We test against Python 3.9".

| Version | Result |
|---|---|
| 3.13 | Install fails. numpy 1.23 has no wheel and building it raises `AttributeError: module 'pkgutil' has no attribute 'ImpImporter'`. |
| 3.12 | Install fails, same numpy 1.23 source build. |
| 3.10, 3.11 | Installs cleanly, then `from psychopy import visual` raises `OverflowError: line number table is too long`. The task cannot start. |
| 3.9 | Works. The version `environment.yml` pins. |
| 3.8 | PsychoPy is fine, but the published wheel cannot be imported at all. See roadblock 6. |

So a user installing from PyPI has exactly one usable interpreter, 3.9, and the documented
route to getting one is `conda env create`, which is roadblock 1. Nothing in the packaging
enforces this: `setup.py` declares no `python_requires`, so pip will happily install on
3.13 and fail confusingly later.

Recommendation: add `python_requires=">=3.8,<3.10"` to `setup.py` and state the constraint
plainly in the README.

## Roadblock 1: the documented conda path fails

The README's primary instruction is `conda env create -f environment.yml`. It fails at
once:

```
CondaHTTPError: HTTP 000 CONNECTION FAILED for url
<https://repo.anaconda.com/pkgs/main/win-64/repodata.json>
```

The message blames the network, so a user will go and check their firewall. The network is
fine. Fetching that exact URL from PowerShell returns HTTP 200, as do pypi.org and
conda.anaconda.org. The cause is the local conda: version 4.9.2 ships an OpenSSL that can
no longer negotiate with the repository. Roadblock 4 is the same defect showing up again.

Fix: update conda before creating the environment, or skip conda and use a virtual
environment.

## Roadblock 2: unbounded setuptools breaks PsychoPy (repository defect)

`requirements.txt` asks for `setuptools>=38.4` with no upper bound, so a fresh install
today resolves to setuptools 84. setuptools deprecated `pkg_resources` in 81 and removed
it in 84, and PsychoPy 2022.2.5 imports it. Every PsychoPy import then fails:

```
ModuleNotFoundError: No module named 'pkg_resources'
```

This affects every new install on every platform, so it is worth fixing rather than
documenting. Pin `setuptools<81` in `requirements.txt`.

## Roadblock 3: Python 3.10 installs but cannot import

```
File "psychopy/tools/linebreak.py", line 12, in <module>
  from psychopy.tools.linebreak_class import linebreak_class
OverflowError: line number table is too long
```

`psychopy/tools/linebreak_class.py` is a generated Unicode table of 333,244 lines and
4.7 MB. PEP 626 changed the line number table format in Python 3.10 and this file
overflows it. The failure appears at `from psychopy import visual`, so the task dies at
import after an install that reported success. This is the most misleading failure of the
set.

## Roadblock 4: a venv built from Anaconda's interpreter has no SSL

Creating a virtual environment from `anaconda3\python.exe` produces an environment where
nothing can reach the network:

```
Can't connect to HTTPS URL because the SSL module is not available.
```

Anaconda keeps `libssl` and `libcrypto` in `anaconda3\Library\bin`, which a venv does not
put on PATH. Prepending that directory fixes it, and `import ssl` then reports
OpenSSL 1.1.1h.

```powershell
$env:PATH = "$env:USERPROFILE\anaconda3\Library\bin;" + $env:PATH
```

Worth stressing that this bites twice: once when pip cannot download, and again at run
time, because `setup="test"` fetches sample data over HTTPS.

## Roadblock 5: ffpyplayer will not build on Python 3.8

`ffpyplayer` is the one dependency with no wheel for the version pip picks, so it builds
from source, and it fails twice. First the build directory embeds the full temporary
source path inside itself and crosses the 260 character `MAX_PATH` limit:

```
error: could not create 'build\temp.win-amd64-cpython-38\Release\Users\Micah\AppData\
Local\Temp\pip-install-6q9s6p37\ffpyplayer_685b40...\clib':
The filename or extension is too long
```

`LongPathsEnabled` is 0 on this machine, and enabling it needs administrator rights and
changes system behaviour. Building from a short temporary directory avoids it:

```powershell
$env:TMP = "C:\pb"; $env:TEMP = "C:\pb"
```

That gets further, and then the compile itself fails:

```
ffconfig.h(5): fatal error C1083: Cannot open include file: 'SDL_version.h'
```

Building ffpyplayer needs the SDL2 and FFmpeg development headers, which no first time
user should be asked to install. Nor is it warranted: ffpyplayer is PsychoPy's movie
playback backend and neither Cardioception task plays movies.

The real cause is narrow. Only the newest ffpyplayer, 4.5.3, lacks a Python 3.8 wheel;
4.5.2 has one. pip does not fall back to an older version after a build failure, so it
never tries. Forcing a wheel resolves it in one step:

```
pip install --only-binary=:all: ffpyplayer
```

## Roadblock 6: the published wheel cannot be imported on Python 3.8 (packaging defect)

The wheel on PyPI is stale relative to the repository, and the difference is fatal.

| | `_resources.py` |
|---|---|
| repository `master` | `import importlib` and `os.path.join`, works on 3.8 |
| PyPI wheel 0.6.1 | `from importlib.resources import files`, which is 3.9 and later only |

On 3.8 the published package raises at import:

```
ImportError: cannot import name 'files' from 'importlib.resources'
```

`importlib.resources.files` is precisely the API that `AGENTS.md` warns against. The fix is
already committed to `master` but has never been released, so `pip install
cardioception-toolbox` ships code that violates the project's own rule. This is what
reduces the supported set to Python 3.9 alone. Cutting a release from current `master`
would restore 3.8.

## Roadblock 7: passing resultPath crashes getParameters (repository defect)

In `cardioception/HRD/parameters.py` the branches are inverted:

```python
if resultPath is None:
    parameters["resultPath"] = parameters["path"] + "/data/" + participant + session
else:
    parameters["resultPath"] = None      # should be resultPath
```

Supplying the documented `resultPath` argument sets it to `None`, and the next line raises
`TypeError: stat: path should be string, bytes, os.PathLike or integer, not NoneType`.
Users who omit the argument never see it, which is why it has survived. The equivalent
code in `HBC/parameters.py` is correct. Fixed on this branch.

## Roadblock 8: setup="test" is broken with current systole

`setup="test"` is the no hardware path, and it is the natural first thing to try. It calls
`serialSim()`, which downloads a sample PPG trace, and the URL is dead:

```
404 Client Error: Not Found for url
https://github.com/LegrandNico/systole/raw/master/systole/datasets//ppg.npy
```

`environment.yml` pins `systole==0.2.4`, but `requirements.txt` asks only for
`systole>=0.2.3`, so a pip install takes 0.3.0 and gets the broken path. The two files
disagree, and the looser one wins. Note also that this makes the test mode require an
internet connection, which is worth stating in the docs.

## Finding the serial port

The Nonin enumerated as COM3, which happens to match the `serialPort="COM3"` default in
`getParameters`, so no configuration was needed. That is luck rather than design, and the
docs should say how to look it up:

```powershell
Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'COM\d+' } |
    Select-Object Name, Manufacturer
```

which prints `USB Serial Port (COM3)`, `FTDI`.

Reading the port directly confirms the device streams at the expected rate: 376 bytes
arrive in one second, matching the Xpod's 75 frames per second at 5 bytes per frame.

## A recipe that works

On this machine, from nothing, avoiding conda entirely:

```powershell
# 1. Anaconda's OpenSSL, needed for pip and at run time
$env:PATH = "$env:USERPROFILE\anaconda3\Library\bin;" + $env:PATH

# 2. short build directory, avoids MAX_PATH
New-Item -ItemType Directory -Force C:\pb | Out-Null
$env:TMP = "C:\pb"; $env:TEMP = "C:\pb"

# 3. an environment on a supported interpreter
& "$env:USERPROFILE\anaconda3\python.exe" -m venv C:\venvs\cardio
$py = "C:\venvs\cardio\Scripts\python.exe"
& $py -m pip install --upgrade "pip<25"

# 4. the dependency that has no source build
& $py -m pip install --only-binary=:all: ffpyplayer

# 5. the package, with setuptools held below the pkg_resources removal
& $py -m pip install cardioception-toolbox "setuptools<81"
```

On Python 3.8 step 5 must install from a checkout of `master` rather than from PyPI, until
a release carrying the `_resources.py` fix goes out. On Python 3.9 the PyPI package works.

## What actually ran

With the above in place, `getParameters(setup="behavioral", serialPort="COM3")` returns a
complete parameters dictionary, the PsychoPy window opens and closes cleanly, and the
oximeter records. The task is ready for a participant.
