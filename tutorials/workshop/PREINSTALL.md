# Prepare for the Cardioception workshop

During the workshop we will run the Heart Rate Discrimination task and analyze a
completed session. Please prepare your laptop before the session. The installation
takes approximately 30 to 45 minutes, mainly for downloads and compilation, and uses
about 4 GB of disk space.

If the terminal, virtual environments, or Jupyter kernels are unfamiliar, read
[GETTING_STARTED.md](GETTING_STARTED.md) first. It introduces only the concepts needed
for these instructions.

No recording hardware is required for the workshop exercises. The software includes a
test mode that replays a stored pulse signal. We will use a pulse oximeter for the live
demonstration and a bundled deidentified session for analysis if live collection is not
available.

## 1. Check Python

Cardioception supports Python 3.10 and 3.11.

```bash
python3 --version
```

The upper limit comes from `pywinhook`, which provides wheels only through Python 3.11.
PsychoPy itself supports newer Python versions. If necessary, install Python 3.11 from
[python.org](https://www.python.org/downloads/). On Windows, select **Add Python to
PATH** in the installer.

Platform-specific alternatives are:

```bash
# macOS with Homebrew
brew install python@3.11

# Ubuntu or Debian
sudo apt install python3.11 python3.11-venv
```

After installation, use the command that reports Python 3.11 in Step 3. For example,
Homebrew commonly provides `python3.11` rather than changing the existing `python3`.

If you already use conda, you may instead create and activate a Python 3.11
environment. Use the activated environment in place of the virtual-environment paths
below.

## 2. Download the workshop materials

If you do not already have the repository:

```bash
git clone https://github.com/embodied-computation-group/Cardioception.git
cd Cardioception
```

Run the remaining terminal commands from the repository root unless a step says
otherwise.

## 3. Create the Python environment

On macOS or Linux:

```bash
python3 -m venv cardioception-env
./cardioception-env/bin/python -m pip install --upgrade pip
./cardioception-env/bin/python -m pip install cardioception-toolbox jupyterlab ipykernel ipywidgets
./cardioception-env/bin/python -m ipykernel install --user \
    --name cardioception --display-name "Python (cardioception)"
```

On Windows PowerShell:

```powershell
python -m venv cardioception-env
cardioception-env\Scripts\python -m pip install --upgrade pip
cardioception-env\Scripts\python -m pip install cardioception-toolbox jupyterlab ipykernel ipywidgets
cardioception-env\Scripts\python -m ipykernel install --user `
    --name cardioception --display-name "Python (cardioception)"
```

The PyPI distribution is `cardioception-toolbox`; the Python import is
`cardioception`. Do not install the unrelated distribution named `cardioception`.

We use full paths to the environment’s Python so that each command targets the same
interpreter. This avoids a common problem in which a shell alias or conda initialization
selects a different Python after activation.

## 4. Install R and the modelling packages

Install R 4.2 or newer from [CRAN](https://cran.r-project.org/). RStudio is optional
because the workshop runs R inside JupyterLab.

In an R console, run:

```r
install.packages(c(
  "brms", "tidyverse", "posterior", "patchwork", "IRkernel"
))

install.packages(
  "cmdstanr",
  repos = c("https://stan-dev.r-universe.dev", getOption("repos"))
)
```

CmdStan is optional but allows you to sample the single-participant model during the
workshop. It requires a C++ toolchain:

- macOS: run `xcode-select --install` in the terminal
- Windows: install the version of [RTools](https://cran.r-project.org/bin/windows/Rtools/)
  that matches your R version
- Ubuntu or Debian: run `sudo apt install build-essential`

Then install CmdStan from R. Compilation commonly takes 10 to 20 minutes.

```r
cmdstanr::install_cmdstan(cores = 2)
```

If this step fails, continue with the installation. The notebook will load a
precomputed posterior instead.

Register the R kernel from the repository root. On macOS or Linux:

```bash
PATH="$PWD/cardioception-env/bin:$PATH" Rscript -e \
    'IRkernel::installspec(name="ir-cardioception", displayname="R (cardioception)")'
```

On Windows PowerShell:

```powershell
$env:PATH = "$PWD\cardioception-env\Scripts;$env:PATH"
Rscript -e 'IRkernel::installspec(name="ir-cardioception", displayname="R (cardioception)")'
```

## 5. Run the preflight check

On macOS or Linux:

```bash
cd tutorials/workshop
../../cardioception-env/bin/python preflight.py
```

On Windows PowerShell:

```powershell
cd tutorials\workshop
..\..\cardioception-env\Scripts\python preflight.py
```

The script checks the Python version and packages, both Jupyter kernels, the R
packages, and the CmdStan toolchain. A complete setup ends with:

```text
------------------------------------------------------------------------
  Everything is ready. Nothing to do before the workshop.
```

Warnings about CmdStan are acceptable. A failure is followed by the relevant repair
command. If a required check still fails after 30 minutes of troubleshooting, send the
complete output to the organiser and arrive 15 minutes early.

## 6. Open and browse the notebooks

From `tutorials/workshop`, start JupyterLab:

```bash
../../cardioception-env/bin/jupyter lab
```

On Windows:

```powershell
..\..\cardioception-env\Scripts\jupyter lab
```

Open each notebook and browse its headings, explanations, and exercises. This brief
preview will make the sequence and terminology familiar before the workshop. You do
not need to complete the notebooks in advance.

In `01_running_the_hrd.ipynb`, confirm that the kernel is **Python
(cardioception)** and run the first two code cells. The first PsychoPy-related import
may take some time. Notebooks 2 and 3 should use **R (cardioception)**.

## Common installation problems

| Symptom | Likely cause and response |
|---|---|
| The package requires Python `<3.12` | Recreate the environment with Python 3.10 or 3.11 |
| `command not found: _initialize_conda` | A shell alias is shadowing Python; use the full environment path shown above |
| `IRkernel::installspec()` cannot find Jupyter | Repeat the registration command with the environment directory on `PATH` |
| CmdStan does not compile | Install the platform C++ toolchain, or continue with the precomputed fit |
| The R kernel is absent | Repeat `IRkernel::installspec()` and restart JupyterLab |
| The installation runs out of disk space | Free approximately 4 GB, mainly for PsychoPy and CmdStan |
| A task window does not respond on macOS | Allow the terminal application under System Settings, Privacy & Security, Input Monitoring |

## What we will do in the workshop

We will:

1. connect HRD trials to the psychometric response model;
2. examine how adaptive stimulus placement changes the information in a session;
3. configure and run a short task demonstration;
4. inspect a completed session before fitting it;
5. fit a psychometric function with empirically informed priors; and
6. interpret the same model fitted hierarchically across participants.

The optional final notebook uses simulation results to compare combinations of
participant numbers and trial numbers for a planned study.
