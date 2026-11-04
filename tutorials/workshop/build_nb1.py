"""Build the hands-on Python notebook (parts 0-3)."""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: c.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# The Heart Rate Discrimination task: measurement and data collection

In this notebook we work from the HRD response model to a short task session. We will:

1. define the stimulus and response used by the psychometric function;
2. distinguish threshold, discrimination precision, and lapse rate;
3. examine how Psi selects informative stimuli;
4. check the Cardioception installation and recording setup;
5. configure a study and run a short demonstration.

Notebook 2, `02_analysing_the_hrd.ipynb`, continues with session inspection,
single-participant estimation, and hierarchical group models.

**Kernel:** `Python (cardioception)`. Select it in the upper-right corner before
running the first cell.
""")

# ----------------------------------------------------------------- Part 0
md(r"""
## Part 0. What the task measures

### The trial

On each trial the participant:

1. **listens to their own heart for 5 seconds** and forms an estimate of its rate;
2. hears **five tones** played at some frequency;
3. judges whether the tones were **faster or slower** than their heart;
4. rates their **confidence** in that judgement on a 0 to 100 visual analogue scale.

The tone rate is not arbitrary. It is set relative to the participant's *measured*
heart rate on that trial:

$$x_i = \text{tone rate} - \text{reference rate} \quad (\Delta\text{BPM})$$

For an interoceptive trial the reference is the heart rate measured by the pulse
oximeter during the listening window. For an exteroceptive (auditory control)
trial it is the rate of a first tone sequence. Negative $x$ means the tones were
slower than the reference.

The response is coded

$$y_i = \begin{cases} 1 & \text{"faster"} \\ 0 & \text{"slower"} \end{cases}$$

### Responses and accuracy answer different questions

We model $P(y=1)$, the probability of a "faster" response. We do not model
objective accuracy.

Imagine a participant who believes their heart is beating 10 BPM slower than it
actually is. When the tones are played at exactly their true heart rate, those tones
sound *fast* to them, and they will say "faster". Their responses will only split
50/50 when the tones are around **−10 ΔBPM**. That 50/50 point is their subjective
match, which is the quantity represented by the threshold.

Now score those same responses for correctness. Accuracy is *lowest* near their
subjective threshold and rises in both directions, so it is a **V-shape, not a
sigmoid**. Fitting accuracy would discard the sign of the bias that the HRD was
designed to recover.

Run the cell below to see both views of the *same* simulated participant.
""")

co(r"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

def p_faster(x, alpha, sigma, lapse=0.02):
    '''Probability of a "faster" response. The model of the HRD.

    alpha  threshold / point of subjective equality, in dBPM
    sigma  SD of the underlying Gaussian, in dBPM (smaller = finer discrimination)
    lapse  probability of a stimulus-independent (random) response
    '''
    return lapse / 2 + (1 - lapse) * norm.cdf((x - alpha) / sigma)

x = np.linspace(-40, 40, 400)
ALPHA_TRUE, SIGMA_TRUE = -10.0, 8.0          # a participant who underestimates by 10 BPM
p = p_faster(x, ALPHA_TRUE, SIGMA_TRUE)

# Objective accuracy: "faster" is correct when x > 0, "slower" when x < 0.
accuracy = np.where(x > 0, p, 1 - p)

fig, axes = plt.subplots(1, 2, figsize=(11, 4))

axes[0].plot(x, p, color="#A8455F", lw=2.5)
axes[0].axvline(ALPHA_TRUE, ls="--", color="#1f3352", lw=1.2)
axes[0].axhline(0.5, ls=":", color="#a4acb8", lw=1)
axes[0].annotate(f"threshold\n{ALPHA_TRUE:+.0f} dBPM", xy=(ALPHA_TRUE, 0.5),
                 xytext=(-38, 0.75), fontsize=9, color="#1f3352")
axes[0].set(xlabel="Stimulus intensity (dBPM)", ylabel='P("faster")',
            title="What we model: response probability", ylim=(0, 1))

axes[1].plot(x, accuracy, color="#2F6F8F", lw=2.5)
axes[1].axvline(ALPHA_TRUE, ls="--", color="#1f3352", lw=1.2)
axes[1].axhline(0.5, ls=":", color="#a4acb8", lw=1)
axes[1].set(xlabel="Stimulus intensity (dBPM)", ylabel="P(correct)",
            title="What we do NOT model: objective accuracy", ylim=(0, 1))

for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()

print("Accuracy is lowest at the participant's subjective threshold,")
print(f"not at zero. Their bias of {ALPHA_TRUE:+.0f} dBPM is invisible in the accuracy curve.")
""")

md(r"""
### The three parameters

The psychometric function has three free parameters, and they are deliberately
separated because they answer different scientific questions.

| Parameter | Scale | What it means |
|---|---|---|
| $\alpha$ | ΔBPM | **Threshold** (point of subjective equality). Where the participant's belief about their heart rate sits. $\alpha < 0$ = underestimation. |
| $\sigma$ | ΔBPM | **Slope / precision.** How sharply responses switch from "slower" to "faster". Smaller $\sigma$ = finer discrimination. |
| $\lambda$ | probability | **Lapse rate.** Stimulus-independent responding, including inattention or response errors. Pulls both asymptotes toward 0.5. |

The model estimates bias and precision separately. This is a central advantage over
heartbeat-counting scores, which do not distinguish these sources of variation. An
experimental effect may alter one psychometric parameter without altering the other.

> **Interpretive scope.** Threshold and slope describe *judgements about
> heart rate*. They are not pure measures of ascending cardiac afferent signal.
> Participants can draw on somatic cues, prior beliefs about what a normal resting
> pulse feels like, time estimation, and memory of the listening interval. The
> exteroceptive condition helps identify general temporal-comparison biases, but it
> does not make the interoceptive estimate process-pure.

### A simulated adaptive session

The widget below generates trial-level responses from parameters that we control. For
adaptive placement, it maintains a posterior over threshold and sigma and selects the
next stimulus by expected information gain. This is the same decision principle as
Psi, implemented on a coarser grid so that it remains responsive in a notebook.

Use the controls to examine five features of the design:

1. Change $\alpha$ while holding $\sigma$ fixed. The curve moves horizontally.
2. Change $\sigma$ while holding $\alpha$ fixed. The transition changes width around
   the same 50% point.
3. Reduce the number of trials and change the random seed. The posterior estimate
   becomes more variable.
4. Increase the true lapse rate. The adaptive model continues to assume the task
   value of 0.02, so this deliberately introduces model mismatch.
5. Compare adaptive and uniform placement with the same participant and trial count.
""")

co(r"""
import ipywidgets as widgets

def binary_entropy(prob):
    prob = np.clip(prob, 1e-12, 1 - 1e-12)
    return -(prob * np.log2(prob) + (1 - prob) * np.log2(1 - prob))

def simulate_experiment(alpha=-9.0, sigma=8.0, lapse=0.02, n_trials=60,
                        placement="adaptive", seed=1):
    rng = np.random.default_rng(seed)

    # A deliberately coarse teaching grid. Cardioception uses the finer grid below.
    stimulus_grid = np.arange(-40, 41, 2, dtype=float)
    alpha_grid = np.arange(-40, 41, 2, dtype=float)
    sigma_grid = np.arange(2, 26, 1, dtype=float)
    grid_alpha, grid_sigma = np.meshgrid(alpha_grid, sigma_grid, indexing="ij")

    # The online staircase assumes a lapse rate of 0.02.
    online_lapse = 0.02
    response_prob = p_faster(
        stimulus_grid[:, None, None],
        grid_alpha[None, :, :],
        grid_sigma[None, :, :],
        online_lapse,
    )
    posterior = np.ones_like(grid_alpha, dtype=float)
    posterior /= posterior.sum()

    xs, ys = [], []
    for _ in range(n_trials):
        if placement == "adaptive":
            # Mutual information between the next response and the parameter grid.
            predictive = np.sum(response_prob * posterior[None, :, :], axis=(1, 2))
            expected_noise = np.sum(
                binary_entropy(response_prob) * posterior[None, :, :], axis=(1, 2)
            )
            intensity_index = int(np.argmax(binary_entropy(predictive) - expected_noise))
        else:
            intensity_index = int(rng.integers(len(stimulus_grid)))

        stimulus = stimulus_grid[intensity_index]
        response = rng.random() < p_faster(stimulus, alpha, sigma, lapse)
        likelihood = response_prob[intensity_index]
        if not response:
            likelihood = 1 - likelihood
        posterior *= likelihood
        posterior /= posterior.sum()
        xs.append(stimulus)
        ys.append(response)

    xs, ys = np.asarray(xs), np.asarray(ys)
    a_hat = np.sum(posterior * grid_alpha)
    s_hat = np.sum(posterior * grid_sigma)

    # Bin responses for display only. Estimation uses every exact intensity.
    edges = np.arange(-42, 47, 6.0)
    idx = np.digitize(xs, edges) - 1
    bx, by, bn = [], [], []
    for b in np.unique(idx):
        selected = idx == b
        bx.append(xs[selected].mean())
        by.append(ys[selected].mean())
        bn.append(selected.sum())

    posterior_curve = np.sum(
        p_faster(
            x[:, None, None], grid_alpha[None, :, :], grid_sigma[None, :, :],
            online_lapse,
        ) * posterior[None, :, :],
        axis=(1, 2),
    )

    fig, axes = plt.subplots(
        1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [2, 1]}
    )
    ax = axes[0]
    ax.plot(x, p_faster(x, alpha, sigma, lapse), color="#1f3352", lw=2.5,
            label=f"true: alpha={alpha:+.1f}, sigma={sigma:.1f}")
    ax.plot(x, posterior_curve, color="#A8455F", lw=2, ls="--",
            label=f"posterior: alpha={a_hat:+.1f}, sigma={s_hat:.1f}")
    ax.scatter(bx, by, s=np.asarray(bn) * 14, color="#A8455F", alpha=0.55,
               edgecolor="white", zorder=3, label="simulated responses")
    ax.axvline(alpha, ls=":", color="#1f3352", lw=1)
    ax.axhline(0.5, ls=":", color="#a4acb8", lw=1)
    ax.set(xlabel="Stimulus intensity (dBPM)", ylabel='P("faster")',
           ylim=(-0.04, 1.04), xlim=(-42, 42))
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", fontsize=8, frameon=False)

    axes[1].hist(xs, bins=np.arange(-42, 47, 6), color="#2F6F8F", alpha=0.75)
    axes[1].axvline(alpha, ls="--", color="#1f3352", lw=1.2)
    axes[1].set(xlabel="Stimulus intensity (dBPM)", ylabel="Trials",
                title="Stimulus allocation", xlim=(-42, 42))
    axes[1].spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.show()

    print(f"threshold  true {alpha:+6.1f}   posterior mean {a_hat:+6.1f} dBPM")
    print(f"sigma      true {sigma:6.1f}   posterior mean {s_hat:6.1f} dBPM")
    print(f"\n{n_trials} trials. Change the seed to simulate another response sequence.")

widgets.interact(
    simulate_experiment,
    alpha=widgets.FloatSlider(min=-30, max=30, step=1, value=-9,
                              description="threshold a", continuous_update=False),
    sigma=widgets.FloatSlider(min=1, max=25, step=0.5, value=8,
                              description="sigma", continuous_update=False),
    lapse=widgets.FloatSlider(min=0.0, max=0.4, step=0.02, value=0.02,
                              description="lapse", continuous_update=False),
    n_trials=widgets.IntSlider(min=10, max=200, step=10, value=60,
                               description="n trials", continuous_update=False),
    placement=widgets.Dropdown(options=["adaptive", "uniform"],
                               value="adaptive", description="placement"),
    seed=widgets.IntSlider(min=1, max=50, step=1, value=1,
                           description="seed", continuous_update=False),
);
""")

md(r"""
### How the task chooses what to play: the Psi staircase

We could present a fixed grid of intensities, but most of those trials would be
uninformative. Once a response is almost certain, another observation at that
intensity changes the parameter estimates very little.

Instead Cardioception runs **Psi**, an adaptive Bayesian procedure. It maintains a
joint posterior over threshold and slope, and on each trial picks the intensity
expected to reduce uncertainty in that posterior.

| Quantity | Range | Resolution |
|---|---:|---:|
| stimulus $x$ | −50.5 to 50.5 ΔBPM | 1 ΔBPM |
| threshold $\alpha$ | −50.5 to 50.5 ΔBPM | 1 ΔBPM |
| Psi slope $\sigma$ | 0.1 to 25 ΔBPM | 0.1 ΔBPM |

The online lapse rate is fixed at 0.02.

Two practical consequences return in notebook 2:

- **The stimulus distribution is not uniform.** Psi often samples near the current
  threshold estimate, but it also samples farther into the tails when those trials
  are informative about slope. A healthy trace does not need to become flat.
- **The online estimate is not the final answer.** Psi is optimised for choosing the
  *next* stimulus, and it fixes the lapse rate. We refit offline with `brms`, where
  lapse is free and we keep full posterior uncertainty.

> **Slope parameterization.** PsychoPy's online Psi reports $\sigma$, where
> **larger = worse** discrimination. The offline `brms`
> model estimates $\beta = -\log\sigma$, where **larger = better**. They point in
> opposite directions. Legrand et al. (2022) use the Psi convention. We therefore state
> the parameterization whenever we report slope.

### Follow the posterior trial by trial

At this point we pause the notebook and open the
[psychophysical model tutorial](https://www.the-ecg.org/Cardioception/tutorials/psychophysics.html#part-ii-adaptive-measurement-with-psi).
Its animation follows the joint Psi posterior and the implied psychometric function
after every adaptive trial in a completed HRD session. The animation also shows why an
unexpected response can move or widen the posterior without indicating a software
failure.
""")

md(r"""
Return to the widget and switch **placement** to `uniform`, keeping the participant,
trial count, and seed fixed. Compare the posterior estimates and the stimulus
histogram. Repeat the comparison with another seed before drawing a conclusion from a
single simulated session.
""")

# ----------------------------------------------------------------- Part 1
md(r"""
---
## Part 1. Check the environment and recording device

The pre-installation guide contains the platform-specific setup instructions. Here we
confirm that the selected notebook kernel can import the packages and find the media
files used by the task.

Cardioception requires Python 3.10 or 3.11. The upper limit comes from `pywinhook`,
not PsychoPy. The PyPI distribution is named `cardioception-toolbox`, while the Python
import remains `cardioception`.

Run the next cell and compare the displayed interpreter with the environment created
for the workshop. A different path usually means that the notebook is using the wrong
kernel.
""")

co(r"""
import importlib, platform, sys, shutil
from pathlib import Path

print(f"Python  {platform.python_version()}   ({sys.executable})")
ok_py = (3, 10) <= sys.version_info[:2] <= (3, 11)
print("        " + ("OK" if ok_py else "OUT OF RANGE - need 3.10 or 3.11"))
print()

for mod in ["cardioception", "psychopy", "systole", "serial", "numpy", "pandas"]:
    try:
        m = importlib.import_module(mod)
        print(f"  {mod:<15} {getattr(m, '__version__', 'installed')}")
    except ImportError as e:
        print(f"  {mod:<15} MISSING  ({e})")

print()
import cardioception
pkg = Path(cardioception.__file__).parent
sounds = list((pkg / 'HRD' / 'Sounds').glob('*.wav'))
print(f"Package   {pkg}")
print(f"Tone files  {len(sounds)}  (expect 370)")
""")

md(r"""
### Check the recording device

Two setups work without extra code: the **Nonin 3012LP Xpod USB pulse oximeter**
(with 8000SM soft-clip sensors), and BrainVision Recorder over Remote Data Access.
Anything else needs a recording class that supplies the same interface. The task
requires a reliable estimate of cardiac frequency.

Before collecting any data, verify the oximeter is producing a *real* signal:

```bash
python -m cardioception.check_device                 # lists serial ports
python -m cardioception.check_device --port <PORT>   # records 20 s and judges it
```

The beat count alone is not a sufficient check. On an empty sensor the peak detector
can report beats at a plausible rate. Signal amplitude distinguishes this case: a
finger typically gives a swing of hundreds of ADC units, whereas an empty sensor gives
one or two.

Here is output from an empty sensor. It reports 67 BPM but is rejected because the
signal amplitude is negligible:

```
  signal amplitude   1.0      (needs > 20)
  beats detected     22
  heart rate         67 BPM
  beat intervals     0.20 to 2.44 s, sd 0.752   (needs sd < 0.15)
  VERDICT: no finger in the sensor
```

And the same sensor, properly seated on a finger:

```
  signal amplitude   246.0    (needs > 20)
  beats detected     27
  heart rate         80 BPM
  beat intervals     0.71 to 0.81 s, sd 0.028   (needs sd < 0.15)
  VERDICT: clean physiological signal
```

If the result is "signal present but detection unreliable," reseat the
clip so the emitter sits flat on the fingerpad, keep the hand still and below heart
level, and run the check again.
""")

co(r"""
# Find candidate serial ports from inside the notebook.
from serial.tools import list_ports

ports = list(list_ports.comports())
if not ports:
    print("No serial ports found. Is the oximeter plugged in?")
for p in ports:
    marker = "  <-- likely the oximeter" if "oximeter" in (p.description or "").lower() else ""
    print(f"  {p.device:<32} {p.description}{marker}")

print()
print("Then, in a terminal (not here - it needs 20 s of live recording):")
print("  python -m cardioception.check_device --port <PORT>")
""")

# ----------------------------------------------------------------- Part 2
md(r"""
---
## Part 2. Configure an experiment

A task splits into two submodules:

- **`parameters`** contains the experimental settings (`getParameters()`)
- **`task`** runs the PsychoPy experiment (`task.run()`)

Almost every setting we may want to change is an argument to `getParameters`.
The ones that matter scientifically:

| Argument | Default | What it controls |
|---|---|---|
| `nTrials` | 120 | **Total** trials, *including* both modalities |
| `exteroception` | `True` | Adds the auditory control condition, splitting `nTrials` in half |
| `stairType` | `'psi'` | `'psi'` (adaptive Bayesian) or `'updown'` |
| `catchTrials` | 0.0 | Fraction assigned to predetermined intensities in the response-function tails |
| `device` | `'mouse'` | `'mouse'` or `'keyboard'` |
| `setup` | `'behavioral'` | `'behavioral'` = real oximeter; `'test'` = **pre-recorded signal, no hardware** |
| `nBreaking` | 20 | Trials between rest breaks |
| `language` | `'english'` | also `'danish'`, `'danish_children'`, `'french'` |
| `resultPath` | `None` | Where data goes. **Set this.** |
| `screenNb` / `fullscr` | 0 / `True` | Which monitor, and whether to take it over |

### Three design decisions

**How many trials?** `nTrials` is the *total*. With `exteroception=True`, `nTrials=120`
gives 60 interoceptive and 60 exteroceptive trials, not 120 of each. Threshold and
slope have different data requirements, and the appropriate trial count depends on the
effect and analysis. We return to that decision in the power-analysis notebook. An odd
`nTrials` with `exteroception=True` produces one additional Extero trial, so an even
number gives a balanced design.

**Do we need the auditory control?** It uses half the trials and allows us to test whether
an effect is *specific to interoception* rather than a general bias in comparing
tone sequences to a remembered rate. Its inclusion should follow from the contrast
needed for the research question. For a short software demonstration, a single modality
keeps the session brief.

**Use `setup='test'` for rehearsal.** It replays a pre-recorded pulse signal, so the
task runs without an oximeter. This is useful for checking the design and learning the
procedure. It does not yield a valid measure of the user’s interoceptive performance,
because the cardiac reference is not their own signal. Use `setup='behavioral'` with a
checked recording device for data collection.

Set the demonstration design below. This cell describes it without opening a window.
""")

co(r"""
# ---- Workshop design --------------------------------------------------
DESIGN = dict(
    participant   = "Volunteer_01",
    session       = "Workshop",
    nTrials       = 20,          # total, across both modalities
    exteroception = False,       # False = all trials cardiac
    stairType     = "psi",
    catchTrials   = 0.0,
    device        = "mouse",
    language      = "english",
    setup         = "test",      # "test" = simulated pulse, no hardware needed
)                                #  use "behavioral" with a checked oximeter
# ------------------------------------------------------------------------

def describe(d):
    n = d["nTrials"]
    if d["exteroception"]:
        intero, extero = n // 2, n // 2 + n % 2
        split = f"{intero} interoceptive + {extero} exteroceptive"
        if n % 2:
            split += "   [!] odd nTrials cannot split evenly"
    else:
        intero, extero = n, 0
        split = f"{intero} interoceptive (no auditory control)"

    catch = int(n * d["catchTrials"])
    # ~5 s listening + ~5 s tones + decision + confidence + ISI, plus breaks
    secs = n * 22 + (n // 20) * 30
    print(f"Design: {d['participant']} / {d['session']}")
    print(f"  trials            {n}  ->  {split}")
    if catch:
        print(f"  catch trials      {catch} at predetermined tail intensities")
    print(f"  staircase         {d['stairType']}")
    print(f"  responses via     {d['device']}")
    print(f"  recording         {d['setup']}"
          + ("   (pre-recorded signal, no hardware needed)" if d["setup"] == "test" else ""))
    print(f"  rough duration    ~{secs // 60} min, excluding the tutorial")
    print()
    if intero and intero < 30:
        print(f"  [i] {intero} interoceptive trials makes this a short demonstration.")
        print( "      Do not treat its participant-level estimates as stable measurements.")
    if d["setup"] == "behavioral":
        print("  [i] Run check_device first and confirm a clean signal.")

describe(DESIGN)
""")

md(r"""
### Writing it as a script

For real data collection we would not use a notebook. We would copy one of the
scripts in [`wrappers/`](https://github.com/embodied-computation-group/Cardioception/tree/master/wrappers)
into the study directory, set the parameters, and run it from a terminal:

```python
from cardioception.HRD.parameters import getParameters
from cardioception.HRD import task

parameters = getParameters(
    participant='Subject_01', session='Test',
    serialPort='/dev/cu.usbserial-XXXX',    # recording port; see Part 1
    setup='behavioral', nTrials=120, screenNb=0,
    resultPath='/absolute/path/to/my_study/data',
)

task.run(parameters, confidenceRating=True, runTutorial=True)
parameters['win'].close()
```

> **Window creation.** `getParameters()` opens the PsychoPy window immediately because
> it builds the visual stimuli. Do not call it only to inspect settings; by the time it
> returns, the screen is already taken over. That is why the design cell above is
> plain Python.

`task.run()` takes two arguments of its own: `confidenceRating` (collect the 0 to 100
rating after each decision) and `runTutorial` (walk through the instructions and
practice trials first). Turn the tutorial off for a participant's *second* session.
""")

# ----------------------------------------------------------------- Part 3
md(r"""
---
## Part 3. Run a short session

We use two forms of the task in the workshop.

### Path A: software rehearsal with `setup="test"`

With `setup="test"` the task replays a **pre-recorded pulse signal**, so it runs on any
laptop without recording hardware. It uses the same tones, Psi staircase, trial
structure, and output format as the behavioural setup.

Run the task to learn the participant experience and confirm that the software works.
The resulting responses are not a measure of the user’s interoceptive performance
because the replayed cardiac reference is not their own. Notebook 2 will analyze the live
volunteer session or, if that session is unavailable, a bundled example.

Use headphones if the room is noisy.

### Path B: live collection with `setup="behavioral"`

The teaching machine runs the task with a pulse oximeter and a volunteer. Set
`setup="behavioral"` in the design cell and set `SERIAL_PORT` below.

Before that run:

- [ ] `check_device` gave **"clean physiological signal"**
- [ ] Sensor on the **non-dominant** hand, resting still and below heart level
- [ ] Volunteer can hear the tones clearly
- [ ] They know that Escape aborts the task
- [ ] Everyone else stays quiet

---

The next cell launches the task in a separate process so that the notebook kernel
remains available if PsychoPy exits unexpectedly.

> **Task window.** In behavioural mode the window opens full screen. Escape aborts at
> any point. If the task is aborted during the tutorial, no data is written; the task saves from the first
> real trial onward.
""")

co(r"""
from pathlib import Path
import subprocess, sys, textwrap, datetime

# Only used when setup="behavioral". Ignored entirely in test mode.
SERIAL_PORT  = "/dev/cu.usbserial-FT4TET5J"   # recording port from Part 1
RUN_TUTORIAL = True                           # False to skip straight to the trials

if DESIGN["setup"] == "test":
    print("Test mode: simulated pulse signal, no hardware used.\n")
else:
    print(f"Behavioral mode: recording from {SERIAL_PORT}\n")

workshop = Path.cwd()
result_dir = workshop / "data" / DESIGN["setup"]
log_path = workshop / f"run_{DESIGN['participant']}.log"

script = textwrap.dedent(f'''
    from cardioception.HRD.parameters import getParameters
    from cardioception.HRD import task

    parameters = getParameters(
        participant={DESIGN["participant"]!r},
        session={DESIGN["session"]!r},
        serialPort={SERIAL_PORT!r},
        setup={DESIGN["setup"]!r},
        stairType={DESIGN["stairType"]!r},
        exteroception={DESIGN["exteroception"]!r},
        catchTrials={DESIGN["catchTrials"]!r},
        nTrials={DESIGN["nTrials"]!r},
        device={DESIGN["device"]!r},
        language={DESIGN["language"]!r},
        screenNb=0,
        resultPath={str(result_dir)!r},
    )
    task.run(parameters, confidenceRating=True, runTutorial={RUN_TUTORIAL!r})
    parameters["win"].close()
    print("TASK COMPLETE")
''').strip()

script_path = workshop / "_run_task.py"
script_path.write_text(script)
result_dir.mkdir(parents=True, exist_ok=True)

print(f"Launching. Window opens on screen 0; escape aborts.")
print(f"Log:  {log_path}")
print(f"Data: {result_dir}\n")

with open(log_path, "w") as log:
    # No pipe: we want the real exit code, not a downstream command's.
    proc = subprocess.run([sys.executable, str(script_path)], stdout=log, stderr=log)

print(f"Exit code: {proc.returncode}  ({'clean' if proc.returncode == 0 else 'NON-ZERO - see log'})")
print("\nFiles written:")
for f in sorted(result_dir.rglob("*")):
    if f.is_file():
        print(f"  {f.relative_to(result_dir)}   {f.stat().st_size:,} bytes")
""")

md(r"""
### If no trial file was written

The task saves the trial table **after every single trial**, so an empty output
directory means it never completed trial 1.

| Symptom | Cause |
|---|---|
| Empty folder, exit code 0, no error | Aborted with escape during the tutorial |
| `SerialException` in the log | Wrong port, or the oximeter is unplugged |
| Hangs with no window | On macOS, grant your terminal Input Monitoring in System Settings, Privacy & Security |
| `Attempting to use a port that is not open` | `serialPort=None` with `setup='behavioral'`; see Part 1 |
| Window opens then closes instantly | Another PsychoPy window still holds the display; restart the kernel |

Read the final lines of `run_<participant>.log`. The `Font Helvetica
Bold was requested` and `No default speaker specified` warnings are cosmetic and appear
in every successful run too.

### Files produced by the task

One folder per participant/session, containing:

| File | Contents |
|---|---|
| `<participant><session>.txt` | Rolling trial table, rewritten after every trial |
| `<participant><session>_final.txt` | Completed trial table, one row per trial |
| `<participant>_signal.txt` | The full PPG trace |
| `Intero_posterior.npy` | The joint Psi posterior after every adaptive trial |
| `<participant>_ppg_*.txt` | Per-trial PPG segments |
| `*.pickle` | The complete parameter set, for reproducibility |

Take a first look at the trial table below, then move to notebook 2.
""")

co(r"""
import pandas as pd

# Self-contained: works whether or not you ran the launch cell above.
result_dir = globals().get("result_dir", Path.cwd() / "data")
def find_repo(start=None):
    '''Walk up until we find the repository root. Works wherever this notebook sits.'''
    here = (start or Path.cwd()).resolve()
    for cand in [here, *here.parents]:
        if (cand / "setup.py").exists() and (cand / "docs").is_dir():
            return cand
    return here

repo = find_repo()
EXAMPLE = repo / "docs/source/examples/templates/data/HRD/HRD_final.txt"

candidates = sorted(result_dir.rglob(f"{DESIGN['participant']}*.txt")) if result_dir.exists() else []
trial_files = [f for f in candidates if f.name.endswith("_final.txt")]
if not trial_files:
    trial_files = [f for f in candidates if "signal" not in f.name and "ppg" not in f.name]

if not trial_files:
    print("No workshop session found; using the bundled example.\n")
    trial_files = [EXAMPLE]

path = trial_files[0]
d = pd.read_csv(path)
print(f"{path.name}: {len(d)} trials, {d.shape[1]} columns\n")

cols = ["Modality", "Alpha", "Decision", "Confidence", "ResponseCorrect", "listenBPM"]
print(d[[c for c in cols if c in d.columns]].head(10).to_string(index=False))

print(f"\nStimulus intensity (Alpha) ranged {d['Alpha'].min():+.0f} to {d['Alpha'].max():+.0f} dBPM")
if "DecisionProvided" in d:
    missed = (~d["DecisionProvided"].astype(bool)).sum()
    print(f"Missed decisions: {missed} of {len(d)}")
""")

md(r"""
---
## Summary

- A demonstration design and the reasoning behind each parameter.
- Experience with the task interface and, when hardware was available, a live session.
- The vocabulary of threshold, slope, lapse, Psi, and ΔBPM used in notebook 2.

**Continue to `02_analysing_the_hrd.ipynb`** (switch to the **R (cardioception)**
kernel). It inspects this session properly, fits the psychometric model to it, and
then shows what the same model looks like across 512 participants.

### Why the analysis is in R

The psychometric and metacognition models in the Cardioception tutorials are `brms`
models built on the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception)
(Courtin et al., 2026). The published tutorial results use that R pipeline, and there
is no maintained Python equivalent. We therefore collect data in Python and fit the
models in R.

### References

- Legrand et al. (2022). *The heart rate discrimination task.* Biological Psychology. [doi:10.1016/j.biopsycho.2021.108239](https://doi.org/10.1016/j.biopsycho.2021.108239)
- Courtin et al. (2026). *Hierarchical Interoception toolbox.* Behavior Research Methods. [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
- Brener and Ring (2016). *Towards a psychophysics of interoceptive processes: the measurement of heartbeat detection.* Philosophical Transactions of the Royal Society B. [doi:10.1098/rstb.2016.0015](https://doi.org/10.1098/rstb.2016.0015)
- Desmedt et al. (2023). *The new measures of interoceptive accuracy: A systematic review and assessment.* Neuroscience & Biobehavioral Reviews. [doi:10.1016/j.neubiorev.2023.105388](https://doi.org/10.1016/j.neubiorev.2023.105388)
""")

nb["cells"] = c

# Deterministic cell ids, so rebuilding produces no spurious diff.
for i, cell in enumerate(nb["cells"]):
    cell["id"] = f"c{i:03d}"

nb.metadata = {
    "kernelspec": {"display_name": "Python (cardioception)", "language": "python",
                   "name": "cardioception"},
    "language_info": {"name": "python", "version": "3.10.11"},
}

out = Path(__file__).parent / "01_running_the_hrd.ipynb"
nbf.write(nb, str(out))
print(f"wrote {out}  ({len(c)} cells)")
