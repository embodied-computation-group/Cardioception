# Cardioception hands-on workshop

This workshop introduces the Heart Rate Discrimination task (HRD) as a measurement
and modelling workflow. We begin with the response model, configure and run the task,
inspect a completed session, and finish with single-participant and hierarchical
psychometric models. An optional third notebook covers study planning with the power
simulations from the Hierarchical Interoception toolbox.

The workshop is intended for PhD students who know the basic concepts of
interoception but may be new to psychophysics, PsychoPy, or hierarchical Bayesian
modelling.

| Notebook | Kernel | Content |
|---|---|---|
| `01_running_the_hrd.ipynb` | **Python (cardioception)** | Measurement model, adaptive sampling, task configuration, and data collection |
| `02_analysing_the_hrd.ipynb` | **R (cardioception)** | Session inspection, a single-participant fit, and hierarchical group models |
| `03_power_analysis.ipynb` | **R (cardioception)** | Optional module on participants, trials, effect size, and power |

Cardioception uses Python and PsychoPy for data collection. The accompanying models
are implemented in R with `brms` and the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception).
The two kernels reflect that division of work.

## Preparing the teaching machine

Follow [PREINSTALL.md](PREINSTALL.md) to create the Python environment, install the R
packages, and register both kernels. From the repository root, confirm that they are
available:

```bash
./cardioception-env/bin/jupyter kernelspec list
```

Launch JupyterLab from the workshop directory. Several cells use this directory for
data and cached results.

```bash
cd tutorials/workshop
../../cardioception-env/bin/jupyter lab
```

On Windows, use:

```powershell
cd tutorials\workshop
..\..\cardioception-env\Scripts\jupyter lab
```

Run the single-participant model in notebook 2 once before the session. The first run
compiles the Stan model and can take several minutes. Later runs use the cached fit.
Models for typical study samples often complete within minutes; the 512-participant
worked models take hours and are supplied as precomputed summaries.

## Hardware and demonstration data

Valid interoceptive data require a cardiac recording. Cardioception supports the Nonin
3012LP Xpod and BrainVision Recorder over Remote Data Access without additional
recording code. Check a pulse oximeter before the workshop:

```bash
python -m cardioception.check_device --list
python -m cardioception.check_device --port <PORT>
```

The second command records for 20 seconds and checks both signal amplitude and beat
detection. A plausible heart-rate estimate is not sufficient because an empty sensor
can produce plausible false peaks.

Without hardware, `setup="test"` replays a stored pulse signal. This mode is useful for
checking the installation, learning the task, and rehearsing a study. It does not
measure the user’s cardiac perception, because the reference signal does not come from
their body. Notebook 2 therefore uses the live volunteer session when available and
otherwise loads the deidentified example session bundled with the repository.

## Suggested schedule

The core workshop takes approximately 2 to 2.5 hours, including discussion.

| Part | Content | Time |
|---|---|---:|
| 0 | The HRD response model and adaptive sampling | 25 min |
| 1 | Environment and recording check | 10 min |
| 2 | Configure a study | 20 min |
| 3 | Run a short demonstration session | 15 min |
| 4 | Inspect the session | 20 min |
| 5 | Fit one psychometric function | 30 min |
| 6 | Interpret a hierarchical group model | 25 min |
| Optional | Plan a study with the power simulations | 20 min |

The demonstration session is deliberately short. Its estimates illustrate the model
and its uncertainty; they should not be treated as stable participant-level
measurements.

After the adaptive-sampling exercise in notebook 1, pause and open the
[psychophysical model tutorial](https://www.the-ecg.org/Cardioception/tutorials/psychophysics.html#part-ii-adaptive-measurement-with-psi).
Its animation shows the Psi posterior and implied response function after every trial,
which is clearer in the rendered documentation than in a static workshop cell.

## Teaching contingencies

The workshop materials have explicit fallbacks:

| Unavailable component | Workshop path |
|---|---|
| Pulse oximeter | Rehearse in `setup="test"`; analyze the bundled session |
| CmdStan | Load the precomputed single-participant posterior |
| R | Complete notebook 1 and follow the rendered outputs in notebook 2 |
| PsychoPy | Begin with notebook 2 and the bundled session |

Send [PREINSTALL.md](PREINSTALL.md) about one week in advance. Attendees run
`preflight.py` at the end and send the complete output if a required component fails.
The draft message is in [EMAIL.md](EMAIL.md).

## Source files

The notebooks are generated. Edit the build scripts and regenerate the notebooks so
that the source remains readable and the cell identifiers remain deterministic.

| Source | Generated file |
|---|---|
| `build_nb1.py` | `01_running_the_hrd.ipynb` |
| `build_nb2.py` | `02_analysing_the_hrd.ipynb` |
| `build_nb3.py` | `03_power_analysis.ipynb` |

From `tutorials/workshop`:

```bash
../../cardioception-env/bin/python build_nb1.py
../../cardioception-env/bin/python build_nb2.py
../../cardioception-env/bin/python build_nb3.py
```

Live participant data belong in `tutorials/workshop/data/`, which is ignored by Git.
Do not add participant data to this public repository.

## References

- Legrand et al. (2022). *The heart rate discrimination task.* Biological Psychology.
  [doi:10.1016/j.biopsycho.2021.108239](https://doi.org/10.1016/j.biopsycho.2021.108239)
- Courtin et al. (2026). *Hierarchical Bayesian modelling of interoceptive
  psychophysics.* Behavior Research Methods.
  [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
