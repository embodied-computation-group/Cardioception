# Cardioception hands-on workshop

Two notebooks that take a room of PhD students from "what does the HRD measure?" to a
fitted hierarchical model, collecting real data from a volunteer along the way.

| Notebook | Kernel | Covers |
|---|---|---|
| `01_running_the_hrd.ipynb` | **Python (cardioception)** | The measurement model, installation, designing your own task, running it live |
| `02_analysing_the_hrd.ipynb` | **R (cardioception)** | Session inspection, fitting the psychometric model, the 512-participant group models |

The split is not arbitrary. Cardioception is a PsychoPy package, so data collection is
Python. The models in `tutorials/` are `brms` models from the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception),
and there is no maintained Python equivalent — so modelling is R.

## Before the session

Both kernels must be registered. From the repository root:

```bash
# Python side
python3 -m venv cardioception-env
./cardioception-env/bin/python -m pip install cardioception-toolbox jupyterlab ipykernel ipywidgets
./cardioception-env/bin/python -m ipykernel install --user \
    --name cardioception --display-name "Python (cardioception)"

# R side (needs brms, cmdstanr with a working CmdStan, ordbetareg, tidyverse, IRkernel)
PATH="$PWD/cardioception-env/bin:$PATH" Rscript -e \
    'IRkernel::installspec(name="ir-cardioception", displayname="R (cardioception)")'
```

Check both appear:

```bash
./cardioception-env/bin/jupyter kernelspec list
```

Then launch from **inside this directory** — the notebooks resolve the repository as
`..`, so paths break if you start elsewhere:

```bash
cd tutorials/workshop
../cardioception-env/bin/jupyter lab
```

## Hardware

Notebook 1 Part 3 needs a pulse oximeter (Nonin 3012LP Xpod with 8000SM sensors, or
BrainVision RDA). Verify it before the session starts:

```bash
python -m cardioception.check_device                 # list ports
python -m cardioception.check_device --port <PORT>   # 20 s recording, judged
```

Do not skip this. On an empty sensor the peak detector still reports a plausible heart
rate, so a session can look fine and contain nothing. `check_device` catches that by
checking signal *amplitude* first.

**Without hardware**, set `setup="test"` in the design cell. The task then replays a
pre-recorded pulse signal and everything else works unchanged.

## If the live run fails

Notebook 2 falls back to the bundled example session
(`docs/source/examples/templates/data/HRD/HRD_final.txt`) whenever no session of your own
is found in `tutorials/workshop/data/`. The workshop continues either way — worth knowing when a
volunteer's oximeter misbehaves in front of an audience.

## Timing

Roughly 2–2.5 hours with discussion:

| Part | Content | Time |
|---|---|---|
| 0 | What the task measures + the simulation widget | 25 min |
| 1 | Installation and device check | 15 min |
| 2 | Designing an experiment | 15 min |
| 3 | Live volunteer run | 15 min |
| 4 | Inspecting the session | 20 min |
| 5 | Fitting the psychometric model | 30 min |
| 6 | The hierarchical group model | 25 min |

Part 5 samples for one to three minutes, plus Stan compilation on the first run.
**Run that cell once before the session** so the compiled model is cached and the room
is not watching a progress bar.

## Files

```
PREINSTALL.md               Send this to attendees a week ahead
GETTING_STARTED.md          For attendees new to Python (linked from PREINSTALL)
preflight.py                One command that reports what is missing
01_running_the_hrd.ipynb    Python notebook (parts 0-3)
02_analysing_the_hrd.ipynb  R notebook (parts 4-6)
build_nb1.py                Regenerates notebook 1
build_nb2.py                Regenerates notebook 2
data/                       Where live sessions land (created at run time)
```

## Running it with a room of people

Send `PREINSTALL.md` out about a week ahead. It ends with `preflight.py`, which prints a
per-component report and exactly what to fix, so problems surface before the session
rather than during it. Ask people to send you the output if it does not say
"Everything is ready".

Everything degrades gracefully, which is what makes this survivable at scale:

| Broken | Still works |
|---|---|
| CmdStan only | Everything, with precomputed model fits |
| R entirely | Notebook 1 in full |
| PsychoPy only | Notebook 2, on the bundled example session |

**Everyone can run the task itself**, with or without hardware — `setup="test"` replays a
pre-recorded pulse signal. Only the live volunteer demonstration needs an oximeter.

The notebooks are generated from the `build_*.py` scripts. Edit those and re-run them
rather than patching the `.ipynb` files by hand, so the source of truth stays diffable.

## Citing

- Legrand et al. (2022). *The heart rate discrimination task.* Biological Psychology. [doi:10.1016/j.biopsycho.2021.108239](https://doi.org/10.1016/j.biopsycho.2021.108239)
- Courtin et al. (2026). *Hierarchical Interoception toolbox.* Behavior Research Methods. [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
