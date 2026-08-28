"""Build the hands-on Python notebook (parts 0-3)."""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: c.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# The Heart Rate Discrimination task — 1. Understanding, installing, and running it

**A hands-on workshop notebook.** For PhD students who know what interoception is,
but have not necessarily run a psychophysics task or fitted a psychometric function.

By the end of this notebook you will have:

1. a working mental model of **what the HRD actually measures**, and why it is not a heartbeat-counting score;
2. Cardioception **installed and verified** on your own machine;
3. a **task design of your own**, with the parameters chosen deliberately rather than copied;
4. **real data**, collected live from a volunteer in the room.

Notebook 2 (`02_analysing_the_hrd.ipynb`, R kernel) then takes that data through
inspection, a psychometric model fit, and the group-level hierarchical models.

---

**Kernel:** `Python (cardioception)`. If that is not selected in the top right, change it now.
""")

# ----------------------------------------------------------------- Part 0
md(r"""
## Part 0 — What the task actually measures

### The trial

On each trial the participant:

1. **listens to their own heart for 5 seconds** and forms an estimate of its rate;
2. hears **five tones** played at some frequency;
3. judges whether the tones were **faster or slower** than their heart;
4. rates their **confidence** in that judgement on a 0–100 visual analogue scale.

The tone rate is not arbitrary. It is set relative to the participant's *measured*
heart rate on that trial:

$$x_i = \text{tone rate} - \text{reference rate} \quad (\Delta\text{BPM})$$

For an interoceptive trial the reference is the heart rate measured by the pulse
oximeter during the listening window. For an exteroceptive (auditory control)
trial it is the rate of a first tone sequence. Negative $x$ means the tones were
slower than the reference.

The response is coded

$$y_i = \begin{cases} 1 & \text{"faster"} \\ 0 & \text{"slower"} \end{cases}$$

### The one idea that matters most

**We model $P(y=1)$ — the probability of a "faster" response — not accuracy.**

This trips up almost everyone at first, so it is worth being concrete about why.

Imagine a participant who believes their heart is beating 10 BPM slower than it
actually is. When the tones are played at exactly their true heart rate, those tones
sound *fast* to them, and they will say "faster". Their responses will only split
50/50 when the tones are around **−10 ΔBPM**. That 50/50 point is their **subjective
match** — the quantity we want.

Now score those same responses for correctness. Accuracy is *lowest* near their
subjective threshold and rises in both directions, so it is a **V-shape, not a
sigmoid**. Fitting accuracy would throw away the sign of the bias, which is the
main thing the HRD was designed to recover.

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

print("Note where accuracy bottoms out: at the participant's subjective threshold,")
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
| $\lambda$ | probability | **Lapse rate.** Stimulus-independent responding — inattention, button errors. Pulls both asymptotes toward 0.5. |

This separation is the reason the HRD improves on heartbeat counting. A counting
score confounds *how biased* someone's cardiac belief is with *how precisely* they
can discriminate. Here they are two numbers, and an experimental effect can move
one without the other.

> **A caution worth stating early.** Threshold and slope describe *judgements about
> heart rate*. They are not pure measures of ascending cardiac afferent signal.
> Participants can draw on somatic cues, prior beliefs about what a normal resting
> pulse feels like, time estimation, and memory of the listening interval. The
> exteroceptive condition helps identify general temporal-comparison biases, but it
> does not make the interoceptive estimate process-pure.

### A simulated participant you can steer

The widget below is a complete simulated experiment. You set the participant's true
parameters and how many trials you run; it generates actual trial-by-trial responses,
bins them, and fits the psychometric function back.

**Things worth doing with it — each takes ten seconds and teaches something:**

1. **Move $\alpha$ alone.** The curve slides sideways without changing shape. This is
   *bias*, and it is what heartbeat-counting scores cannot separate out.
2. **Move $\sigma$ alone.** The curve stretches around a fixed 50% point. This is
   *precision*, and it is a completely different claim about a participant.
3. **Drop the trial count to 20.** Watch the recovered estimates jump around every time
   you change the seed. This is exactly your live volunteer session in Part 3, and it is
   why we quote credible intervals rather than point estimates.
4. **Push lapse to 0.3.** The asymptotes collapse toward 0.5. Now try to recover
   $\sigma$ — a high lapse rate looks a lot like a shallow slope, which is precisely why
   the offline model estimates lapse rather than fixing it.
5. **Switch stimulus placement to `uniform`.** With the same trial count the estimates
   get noticeably worse, because most trials land where the answer was never in doubt.
   That gap is what Psi buys you.
""")

co(r"""
import ipywidgets as widgets
from scipy.optimize import minimize

def simulate_experiment(alpha=-9.0, sigma=8.0, lapse=0.02, n_trials=60,
                        placement="adaptive (Psi-like)", seed=1):
    rng = np.random.default_rng(seed)

    # Where the trials are placed.
    if placement.startswith("adaptive"):
        # Psi converges to sampling near the threshold it is homing in on.
        xs = rng.normal(alpha, max(sigma, 1.0) * 1.2, n_trials)
    else:
        xs = rng.uniform(-40, 40, n_trials)
    xs = np.clip(np.round(xs), -50, 50)

    # The participant responds.
    ys = rng.random(n_trials) < p_faster(xs, alpha, sigma, lapse)

    # Fit alpha and sigma back from the responses (lapse fixed at truth here).
    def nll(theta):
        a, log_s = theta
        pr = np.clip(p_faster(xs, a, np.exp(log_s), lapse), 1e-9, 1 - 1e-9)
        return -np.sum(np.where(ys, np.log(pr), np.log(1 - pr)))

    fit = minimize(nll, x0=[np.median(xs), np.log(8.0)], method="Nelder-Mead")
    a_hat, s_hat = fit.x[0], np.exp(fit.x[1])

    # Bin the simulated responses for display.
    edges = np.arange(-50, 55, 5.0)
    idx = np.digitize(xs, edges) - 1
    bx, by, bn = [], [], []
    for b in np.unique(idx):
        m = idx == b
        if m.sum():
            bx.append(xs[m].mean()); by.append(ys[m].mean()); bn.append(m.sum())

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2),
                             gridspec_kw={"width_ratios": [2, 1]})
    ax = axes[0]
    ax.plot(x, p_faster(x, alpha, sigma, lapse), color="#1f3352", lw=2.5,
            label=f"true:      a={alpha:+.1f}, s={sigma:.1f}")
    ax.plot(x, p_faster(x, a_hat, s_hat, lapse), color="#A8455F", lw=2, ls="--",
            label=f"recovered: a={a_hat:+.1f}, s={s_hat:.1f}")
    ax.scatter(bx, by, s=np.array(bn) * 14, color="#A8455F", alpha=0.55,
               edgecolor="white", zorder=3, label="simulated data")
    ax.axvline(alpha, ls=":", color="#1f3352", lw=1)
    ax.axhline(0.5, ls=":", color="#a4acb8", lw=1)
    ax.set(xlabel="Stimulus intensity (dBPM)", ylabel='P("faster")',
           ylim=(-0.04, 1.04), xlim=(-45, 45))
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", fontsize=8, frameon=False)

    # Where the trials actually went.
    axes[1].hist(xs, bins=np.arange(-50, 55, 5), color="#2F6F8F", alpha=0.75)
    axes[1].axvline(alpha, ls="--", color="#1f3352", lw=1.2)
    axes[1].set(xlabel="Stimulus intensity (dBPM)", ylabel="Trials",
                title="Where the trials were spent", xlim=(-45, 45))
    axes[1].spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.show()

    err_a, err_s = a_hat - alpha, s_hat - sigma
    print(f"threshold  true {alpha:+6.1f}   recovered {a_hat:+6.1f}   error {err_a:+.1f} dBPM")
    print(f"sigma      true {sigma:6.1f}   recovered {s_hat:6.1f}   error {err_s:+.1f} dBPM")
    print(f"\n{n_trials} trials. Change the seed to resample the same participant.")

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
    placement=widgets.Dropdown(options=["adaptive (Psi-like)", "uniform"],
                               value="adaptive (Psi-like)", description="placement"),
    seed=widgets.IntSlider(min=1, max=50, step=1, value=1,
                           description="seed", continuous_update=False),
);
""")

md(r"""
### How the task chooses what to play: the Psi staircase

We could present a fixed grid of intensities, but most of those trials would be
wasted — a tone 45 BPM faster than your heart is trivially easy and tells us almost
nothing about where your threshold lies.

Instead Cardioception runs **Psi**, an adaptive Bayesian procedure. It maintains a
joint posterior over threshold and slope, and on each trial picks the intensity
expected to be *most informative* — the one that will shrink that posterior most.

| Quantity | Range | Resolution |
|---|---:|---:|
| stimulus $x$ | −50.5 to 50.5 ΔBPM | 1 ΔBPM |
| threshold $\alpha$ | −50.5 to 50.5 ΔBPM | 1 ΔBPM |
| Psi slope $\sigma$ | 0.1 to 25 ΔBPM | 0.1 ΔBPM |

The online lapse rate is fixed at 0.02.

Two practical consequences you will meet again in notebook 2:

- **Psi concentrates trials near the threshold.** Your stimulus histogram will look
  clustered, not uniform. That is the procedure working, not a bug.
- **The online estimate is not the final answer.** Psi is optimised for choosing the
  *next* stimulus, and it fixes the lapse rate. We refit offline with `brms`, where
  lapse is free and we keep full posterior uncertainty.

> ⚠️ **A parameterisation trap that has bitten published analyses.** PsychoPy's online
> Psi reports $\sigma$, where **larger = worse** discrimination. The offline `brms`
> model estimates $\beta = -\log\sigma$, where **larger = better**. They point in
> opposite directions. Legrand et al. (2022) use the Psi convention. Always state which
> one you are reporting.
""")

md(r"""
Go back to the widget above and switch **placement** to `uniform`, keeping everything
else fixed. The recovered threshold gets worse for the same number of trials — most of
those trials landed where the answer was never in doubt. That difference is the whole
argument for adaptive sampling.
""")

# ----------------------------------------------------------------- Part 1
md(r"""
---
## Part 1 — Installing Cardioception

Skip to Part 2 if it is already working. Otherwise, the whole install is four commands.

### Requirements

**Python 3.10 or 3.11.** The ceiling is not PsychoPy (which allows 3.12) but
`pywinhook`, which publishes wheels only up to 3.11 and otherwise needs a C toolchain
on Windows.

```bash
python -m venv cardioception-env
source cardioception-env/bin/activate      # macOS / Linux
cardioception-env\Scripts\activate         # Windows
pip install cardioception-toolbox
python -c "from cardioception.HRD import task; print('ok')"
```

The package name is `cardioception-toolbox`; the *import* name stays `cardioception`,
so older scripts keep working. If you already use conda, `conda env create -f
environment.yml` is an alternative to all four lines — it pins 3.10 and gets
`pywinhook` prebuilt from conda-forge.

The install pulls down about **140 MB of media**, most of it the 370 pre-generated
tone files the task plays. This is normal.

### Four things that actually go wrong

These are the ones worth knowing in advance — the first two cost real time.

1. **A shell alias shadows the venv Python.** If your `.zshrc`/`.bashrc` aliases
   `python` (lazy conda initialisers do this), then after activating the venv, `python`
   still resolves to the alias and you get a confusing `command not found`. The venv is
   *fine*; the alias is intercepting. Call `./cardioception-env/bin/python` by absolute
   path, or use `command python`.

2. **`serialPort=None` fails with `setup='behavioral'`.** The README's script example
   passes `None`, which reaches `serial.Serial(None)`. pyserial accepts that but leaves
   the port *unopened*, so the setup read immediately after it raises. That example only
   works under `setup='test'`. Pass the real port.

3. **`resultPath` defaults relative to the current working directory** —
   `os.getcwd() + "/data/" + participant + session`. Launch the same script from two
   different folders and your data quietly scatters. Set it explicitly.

4. **Piping the task through another command hides its exit code.** `python task.py |
   tail` reports *tail's* status, so a crash looks like success. Redirect instead:
   `python task.py > run.log 2>&1`.

Run the cell below to check your own environment.
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
Anything else needs a small recording class of your own — the task only requires a
reliable estimate of cardiac frequency.

Before collecting any data, verify the oximeter is producing a *real* signal:

```bash
python -m cardioception.check_device                 # lists serial ports
python -m cardioception.check_device --port <PORT>   # records 20 s and judges it
```

This check exists because **the obvious check does not work**. On an empty sensor the
peak detector still reports beats at an entirely plausible rate — a session can look
fine and contain nothing at all. What separates the cases is *signal amplitude*: a
finger gives a swing of a couple of hundred ADC units, an empty sensor gives one or two.

Here is real output from an empty sensor. Note that it reports a perfectly believable
67 BPM and is still, correctly, rejected:

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

If you get "signal present but detection unreliable" in between these, reseat the
clip so the emitter sits flat on the fingerpad, keep the hand still and below heart
level, and re-run. It usually takes one adjustment.
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
## Part 2 — Designing your own experiment

A task splits into two submodules:

- **`parameters`** — the experimental settings (`getParameters()`)
- **`task`** — the PsychoPy script that runs them (`task.run()`)

Almost everything you would want to change is an argument to `getParameters`.
The ones that matter scientifically:

| Argument | Default | What it controls |
|---|---|---|
| `nTrials` | 120 | **Total** trials, *including* both modalities |
| `exteroception` | `True` | Adds the auditory control condition, splitting `nTrials` in half |
| `stairType` | `'psi'` | `'psi'` (adaptive Bayesian) or `'updown'` |
| `catchTrials` | 0.0 | Fraction placed at ±20 BPM extremes. Use `0.2` if you want the tails sampled |
| `device` | `'mouse'` | `'mouse'` or `'keyboard'` |
| `setup` | `'behavioral'` | `'behavioral'` = real oximeter; `'test'` = **pre-recorded signal, no hardware** |
| `nBreaking` | 20 | Trials between rest breaks |
| `language` | `'english'` | also `'danish'`, `'danish_children'`, `'french'` |
| `resultPath` | `None` | Where data goes. **Set this.** |
| `screenNb` / `fullscr` | 0 / `True` | Which monitor, and whether to take it over |

### Three design decisions worth thinking about

**How many trials?** `nTrials` is the *total*. With `exteroception=True`, `nTrials=120`
gives you **60 interoceptive and 60 exteroceptive** trials, not 120 of each. The Psi
posterior is usually usable by around 40–60 trials per condition; below ~30 the slope
in particular stays poorly identified. Note also that an odd `nTrials` with
`exteroception=True` cannot split evenly — recent versions warn and round rather than
crash, but pick an even number.

**Do you need the auditory control?** It costs half your trials. It buys the ability to
say an effect is *specific to interoception* rather than a general bias in comparing
tone sequences to a remembered rate. For most between-group questions this is worth it.
For a first pilot on one person, drop it and spend everything on the cardiac condition.

**`setup='test'` is your friend.** It replays a pre-recorded pulse signal, so the whole
task runs with no oximeter attached. Use it to debug your design, time your session,
and let students rehearse the procedure — then switch to `'behavioral'` for real data.

Set your design below. This cell only *describes* it — it does not open a window.
""")

co(r"""
# ---- Your design -------------------------------------------------------
DESIGN = dict(
    participant   = "Volunteer_01",
    session       = "Workshop",
    nTrials       = 20,          # total, across both modalities
    exteroception = False,       # False = all trials cardiac
    stairType     = "psi",
    catchTrials   = 0.0,
    device        = "mouse",
    language      = "english",
    setup         = "behavioral",
)
# ------------------------------------------------------------------------

def describe(d):
    n = d["nTrials"]
    if d["exteroception"]:
        intero, extero = n // 2 + n % 2, n // 2
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
        print(f"  catch trials      {catch} at +/-20 BPM extremes")
    print(f"  staircase         {d['stairType']}")
    print(f"  responses via     {d['device']}")
    print(f"  recording         {d['setup']}"
          + ("   (pre-recorded signal, no hardware needed)" if d["setup"] == "test" else ""))
    print(f"  rough duration    ~{secs // 60} min, excluding the tutorial")
    print()
    if intero and intero < 30:
        print(f"  [!] {intero} interoceptive trials is below ~30. Expect a wide, poorly")
        print( "      identified slope. Fine for a demo; not enough for a real estimate.")
    if d["setup"] == "behavioral":
        print("  [i] Run check_device first and confirm a clean signal.")

describe(DESIGN)
""")

md(r"""
### Writing it as a script

For real data collection you would not use a notebook — you would copy one of the
scripts in [`wrappers/`](https://github.com/embodied-computation-group/Cardioception/tree/master/wrappers)
into your own study folder and run it from a terminal. The whole thing is five lines:

```python
from cardioception.HRD.parameters import getParameters
from cardioception.HRD import task

parameters = getParameters(
    participant='Subject_01', session='Test',
    serialPort='/dev/cu.usbserial-XXXX',    # your port; see Part 1
    setup='behavioral', nTrials=120, screenNb=0,
    resultPath='/absolute/path/to/my_study/data',
)

task.run(parameters, confidenceRating=True, runTutorial=True)
parameters['win'].close()
```

> ⚠️ **`getParameters()` opens the PsychoPy window immediately** (it builds all the
> visual stimuli). You cannot call it just to inspect settings — by the time it
> returns, the screen is already taken over. That is why the design cell above is
> plain Python.

`task.run()` takes two arguments of its own: `confidenceRating` (collect the 0–100
rating after each decision) and `runTutorial` (walk through the instructions and
practice trials first). Turn the tutorial off for a participant's *second* session.
""")

# ----------------------------------------------------------------- Part 3
md(r"""
---
## Part 3 — Run it on a volunteer

**You need a volunteer at the keyboard with the oximeter on a finger.**

Before you start:

- [ ] `check_device` gave **"clean physiological signal"**
- [ ] Sensor on the **non-dominant** hand, hand resting still and below heart level
- [ ] Volunteer can hear the tones clearly (**headphones** if the room is noisy)
- [ ] They know **escape aborts** the task
- [ ] Everyone else stays quiet — this is a listening task

Set the serial port, then run the next cell. It launches the task in a **separate
process**, which matters: PsychoPy takes over the display, and if it crashed inside
the notebook kernel it would take the kernel with it.
""")

co(r"""
from pathlib import Path
import subprocess, sys, textwrap, datetime

SERIAL_PORT = "/dev/cu.usbserial-FT4TET5J"   # <-- set to your port from Part 1
RUN_TUTORIAL = True                          # False to skip straight to trials

workshop = Path.cwd()
result_dir = workshop / "data"
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
### If nothing was written

The task saves the trial table **after every single trial**, so an empty output
directory means it never completed trial 1. In order of likelihood:

| Symptom | Cause |
|---|---|
| Empty folder, exit code 0, no error | Aborted with escape during the tutorial |
| `SerialException` in the log | Wrong port, or the oximeter is unplugged |
| Hangs with no window | On macOS, grant your terminal **Input Monitoring** in System Settings → Privacy & Security |
| `Attempting to use a port that is not open` | `serialPort=None` with `setup='behavioral'` — see Part 1 |
| Window opens then closes instantly | Another PsychoPy window still holds the display; restart the kernel |

Read `run_<participant>.log` — the real error is at the bottom. The `Font Helvetica
Bold was requested` and `No default speaker specified` warnings are cosmetic and appear
in every successful run too.

### What you just collected

One folder per participant/session, containing:

| File | Contents |
|---|---|
| `<participant><session>.txt` | **The trial table.** One row per trial — this is your data |
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
trial_files = [f for f in candidates if "signal" not in f.name and "ppg" not in f.name]

if not trial_files:
    print("No session of your own found - falling back to the bundled example")
    print("so you can continue to notebook 2 regardless.\n")
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
## What you have now

- A design you chose, and the reasoning behind each parameter.
- A real session from a real person, in a folder you can point at.
- The vocabulary — threshold, slope, lapse, Psi, ΔBPM — that the next notebook assumes.

**Continue to `02_analysing_the_hrd.ipynb`** (switch to the **R (cardioception)**
kernel). It inspects this session properly, fits the psychometric model to it, and
then shows what the same model looks like across 512 participants.

### Why the analysis is in R

Not arbitrary. The psychometric and metacognition models in the Cardioception
tutorials are `brms` models, built on the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception)
(Courtin et al., 2026). Every number in the published tutorials came out of that R
pipeline, and there is no maintained Python equivalent. Collecting data is Python;
modelling it is R.

### References

- Legrand et al. (2022). *The heart rate discrimination task.* Biological Psychology. [doi:10.1016/j.biopsycho.2021.108239](https://doi.org/10.1016/j.biopsycho.2021.108239)
- Courtin et al. (2026). *Hierarchical Interoception toolbox.* Behavior Research Methods. [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
""")

nb["cells"] = c
nb.metadata = {
    "kernelspec": {"display_name": "Python (cardioception)", "language": "python",
                   "name": "cardioception"},
    "language_info": {"name": "python", "version": "3.10.11"},
}

out = Path(__file__).parent / "01_running_the_hrd.ipynb"
nbf.write(nb, str(out))
print(f"wrote {out}  ({len(c)} cells)")
