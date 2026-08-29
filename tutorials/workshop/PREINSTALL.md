# Before the Cardioception workshop — please install this in advance

You will be running the Heart Rate Discrimination task on your own laptop and
analysing the data you collect. That needs a Python environment and an R environment.
**Please do this before the session** — it involves some large downloads and one step
that compiles for 10–20 minutes, and we cannot wait for 30 people to do that in the room.

> **Never installed Python before?** Read
> [GETTING_STARTED.md](GETTING_STARTED.md) first — it explains the handful of concepts
> these instructions assume, with the R equivalent of each. Fifteen minutes, and the
> commands below stop looking like magic.

**Time:** 30–45 minutes, most of it unattended downloading.
**Disk:** about 4 GB (PsychoPy ~1.5 GB, CmdStan ~2 GB).
**You do not need a pulse oximeter.** The task runs against a pre-recorded pulse signal,
so everyone can run the real experiment on their own machine.

When you are done, one command tells you whether it worked. If you only have time for
one thing, do Steps 1–2 and 5 — you will still be able to follow most of the workshop.

---

## Step 1 — Python 3.10 or 3.11

**Not 3.12 or newer.** PsychoPy's dependencies do not build above 3.11.

Check what you have:

```bash
python3 --version
```

If it is outside 3.10–3.11, install one:

- **macOS / Windows:** [python.org/downloads](https://www.python.org/downloads/) — pick 3.11
- **Linux:** `sudo apt install python3.11 python3.11-venv`
- **conda users:** `conda create -n cardioception python=3.11` then `conda activate cardioception`, and skip the `venv` line below

## Step 2 — The Python environment

From wherever you keep projects:

```bash
# macOS / Linux
python3 -m venv cardioception-env
./cardioception-env/bin/python -m pip install --upgrade pip
./cardioception-env/bin/python -m pip install cardioception-toolbox jupyterlab ipykernel ipywidgets
./cardioception-env/bin/python -m ipykernel install --user \
    --name cardioception --display-name "Python (cardioception)"
```

```powershell
# Windows (PowerShell)
python -m venv cardioception-env
cardioception-env\Scripts\python -m pip install --upgrade pip
cardioception-env\Scripts\python -m pip install cardioception-toolbox jupyterlab ipykernel ipywidgets
cardioception-env\Scripts\python -m ipykernel install --user `
    --name cardioception --display-name "Python (cardioception)"
```

This downloads about 1.5 GB, including 370 pre-generated tone files the task plays.

> **Note the deliberate use of full paths** (`./cardioception-env/bin/python`) rather than
> activating the environment. If your shell aliases `python` — lazy conda initialisers do
> this — then `python` after `activate` can still resolve to the alias and fail with a
> confusing error, even though the environment is fine. Full paths sidestep it entirely.

## Step 3 — R, and the modelling packages

The analysis half uses `brms`. Install **R 4.2 or newer** from
[cran.r-project.org](https://cran.r-project.org/). RStudio is *not* required — everything
runs in Jupyter — but it is fine to have.

Then, in an R console:

```r
install.packages(c("brms", "tidyverse", "posterior", "patchwork", "IRkernel"))

# cmdstanr comes from the Stan repository, not CRAN
install.packages("cmdstanr",
  repos = c("https://stan-dev.r-universe.dev", getOption("repos")))

# This one compiles. Expect 10-20 minutes. Run it and go and get coffee.
cmdstanr::install_cmdstan(cores = 2)
```

`install_cmdstan()` needs a C++ toolchain:

- **macOS:** run `xcode-select --install` in a terminal first
- **Windows:** install [RTools](https://cran.r-project.org/bin/windows/Rtools/) matching your R version
- **Linux:** `sudo apt install build-essential`

Finally, register R as a Jupyter kernel. It needs to find the `jupyter` command, which is
in the Python environment from Step 2:

```bash
# macOS / Linux - adjust the path to where you made the environment
PATH="$PWD/cardioception-env/bin:$PATH" Rscript -e \
    'IRkernel::installspec(name="ir-cardioception", displayname="R (cardioception)")'
```

```powershell
# Windows (PowerShell)
$env:PATH = "$PWD\cardioception-env\Scripts;$env:PATH"
Rscript -e 'IRkernel::installspec(name="ir-cardioception", displayname="R (cardioception)")'
```

> **If `install_cmdstan()` defeats you, stop and move on.** The notebook detects a missing
> CmdStan and loads precomputed model results instead. You will see every figure and
> number; you just will not sample the model yourself. That is a perfectly good workshop.

## Step 4 — Get the materials

```bash
git clone https://github.com/embodied-computation-group/Cardioception.git
cd Cardioception/tutorials/workshop
```

## Step 5 — Check it worked

```bash
# macOS / Linux  (path to wherever your environment is)
/path/to/cardioception-env/bin/python preflight.py

# Windows
C:\path\to\cardioception-env\Scripts\python preflight.py
```

It prints one line per component and, at the end, exactly what to fix:

```
[  ok  ] Python      version 3.11.9
[  ok  ] Python pkg  cardioception 0.7.1
[  ok  ] Media       370 tone files present
[  ok  ] Task        cardioception.HRD.task imports
[  ok  ] Jupyter     kernel 'cardioception' registered
[  ok  ] Jupyter     kernel 'ir-cardioception' registered
[  ok  ] CmdStan     compiles a test model
------------------------------------------------------------------------
  Everything is ready. Nothing to do before the workshop.
```

**If it says "Everything is ready", you are done.** Otherwise it lists each problem with
the command that fixes it.

## Step 6 — Optional, but it saves everyone time

Open JupyterLab and run the first few cells so the heavy imports are cached:

```bash
cd Cardioception/tutorials/workshop
/path/to/cardioception-env/bin/jupyter lab
```

Open `01_running_the_hrd.ipynb`, check the kernel says **Python (cardioception)** in the
top right, and run the first two code cells. The first PsychoPy import takes 20–30 seconds;
after that it is quick.

---

## Things that commonly go wrong

| Symptom | Cause and fix |
|---|---|
| `command not found: _initialize_conda` after activating | A shell alias is shadowing `python`. Use the full path `./cardioception-env/bin/python` |
| `ERROR: Could not find a version that satisfies psychopy` | Python is 3.12+. Go back to Step 1 |
| `IRkernel::installspec()` says jupyter not found | The `jupyter` command is not on PATH. Use the `PATH=...` form in Step 3 |
| `install_cmdstan()` fails to compile | Missing C++ toolchain — see Step 3. Or skip it; the notebook falls back |
| Kernel dropdown has no R option | Step 3's `installspec` did not run. Re-run it and restart JupyterLab |
| Install runs out of disk | You need ~4 GB. CmdStan alone is ~2 GB |
| macOS: task window never appears | Grant your terminal **Input Monitoring** in System Settings → Privacy & Security |

## If you get stuck

**Do not spend more than 30 minutes on this.** Send the full output of `preflight.py` to
the organiser and arrive 15 minutes early — it is almost always a two-minute fix in person.

The workshop degrades gracefully by design:

| If this is broken | You can still do |
|---|---|
| CmdStan only | Everything, with precomputed model fits |
| R entirely | Notebook 1 in full — the task, the theory, running the experiment |
| PsychoPy only | Notebook 2 in full, using the bundled example session |

## What you will actually do on the day

1. Build intuition for the psychometric model on simulated data you control
2. Design a task, then **run the real experiment on your own laptop**
3. Inspect the session and decide whether you would keep it
4. Fit the psychometric model, with priors and sampler diagnostics
5. See the same model across 512 participants, and what changes at that scale

See you there.
