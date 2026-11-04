---
myst:
  html_meta:
    description: "Design of the Heartbeat Synchrony Discrimination task: an adaptive Bayesian version of the method of constant stimuli that estimates where in the cardiac cycle a person feels the heartbeat, and how sharply."
    keywords: "heartbeat detection, heartbeat synchrony, method of constant stimuli, Psi-marginal, adaptive psychophysics, cardiac interoception"
---

# Heartbeat Synchrony Discrimination task

The Heartbeat Synchrony Discrimination task (HSD) is an adaptive Bayesian
version of the heartbeat detection task of Brener, Liu and Ring
{cite:p}`1993:brener`. A train of tones is played, each tone a chosen delay
after a detected R-wave, and the participant judges whether the tones were
synchronous with their heartbeat. After each judgement the next delay is
chosen to be as informative as possible about where in the cardiac cycle the
sensation lies and how sharp it is.

```{note}
This is a design document for an experimental task. The estimation engine,
`cardioception.HSD.psi`, exists and is tested, and its
[simulation study](#simulation-study) has run. The task runner
(`cardioception.HSD.parameters` and `cardioception.HSD.task`), its English
instructions and `wrappers/hsd_lsl.py` exist and run headlessly against a
virtual heart and against a synthetic ECG over LSL. One
[hardware dry run](#hardware-dry-run) has been done, a single 60-trial session
on a real ECG. The task has not been validated in a study; see
[what comes next](#what-comes-next).
```

## Why a new task

The two-interval task of Whitehead and colleagues {cite:p}`1977:whitehead`
presents stimuli (light flashes in the original) at two fixed delays after the
R-wave, usually about 128 and 384 ms, and asks which train is simultaneous
with the heartbeat. The design
assumes that everyone feels the heartbeat at about the same delay. They do
not. In common versions of the task only about one person in four meets the
detector criterion {cite:p}`2016:brener`, and a person whose sensation falls
between the two delays has no correct answer to give.

Multi-interval tasks remove that assumption. Tones are presented at several
delays across the cardiac cycle, and each person's data show where their
sensation lies. The cost is time: the standard method of constant stimuli
(MCS) takes about 35 minutes. The HSD keeps the multi-interval logic and
spends the trials where they are informative.

## What the classical task established

The [theory page](measuring.md) already covers
[what fixed-delay synchrony tasks can establish](measuring.md#what-fixed-delay-synchrony-tasks-can-establish)
and why the MCS is
[a stronger measure of heartbeat timing](measuring.md#a-stronger-measure-of-heartbeat-timing).
This section adds the findings that shaped the HSD design. It follows the
review by Brener and Ring {cite:p}`2016:brener`.

| Study | Procedure | Finding |
|---|---|---|
| Yates et al. {cite:p}`1985:yates` | Six delays, 0 to 500 ms, one light flash per trial | Only 25 percent met detector criteria, later attributed to a single stimulus per trial giving too little data |
| Brener and Kluvitse {cite:p}`1988:brener` | Participants switched freely among tones at the six delays | Preferred intervals from 100 to 400 ms; standard deviations of the preferred interval from 43 to 167 ms |
| Brener, Liu and Ring {cite:p}`1993:brener` | MCS: ten tones per trial at each of the six delays | 54 percent classified as detectors, against 50 percent (Brener-Kluvitse method) and 33 percent (Whitehead variant). Tones at 100 to 300 ms most often judged simultaneous. Median preferred intervals 152 to 373 ms; interquartile ranges 118 to 362 ms |
| Brener, Ring and Liu {cite:p}`1994:brener` | MCS with fewer tones per trial | Five tones per trial did not impair reliability |
| Ring and Brener {cite:p}`2018:ring` | MCS at six fixed delays, 48 participants, alongside heartbeat counting | Each task gave reliable scores; heartbeat detection was unrelated to heartbeat counting |

The standard MCS is 20 trials at each of six delays, 120 trials in all. With
a 30-trial exteroceptive familiarization it takes about 35 minutes. It yields
two measures: the median of the delays judged simultaneous (the location of
the sensation in the cardiac cycle) and their interquartile range (its
precision).

Three points carry into the HSD. Location varies between people by hundreds of
milliseconds, so it must be estimated rather than assumed. Width varies too,
and is a separate quantity from location. And each trial should carry several
tones, because one stimulus per trial is too little data.

```{admonition} Two claims we could not verify
:class: warning

Two figures that circulate in summaries of this literature are not used on
this page, because we could not open the papers to check them.

- Detector rates of 13, 43 and 47 percent for one, five and ten tones per
  trial, attributed to Brener, Ring and Liu {cite:p}`1994:brener`. The review
  confirms only that five tones per trial did not impair reliability relative
  to ten.
- A study by Schneider, Ring and Katkin {cite:p}`1998:schneider` said to have
  shifted the delay range from 0 to 500 ms to 100 to 600 ms and found that
  preferred delays did not move. We cite the paper only as a validity test of
  the MCS, which is what its title describes.

The design does not depend on either claim.
```

## Relation to the phase adjustment task

The ECG-based phase adjustment task (PAT-ECG) of Hodgetts and colleagues
{cite:p}`2026:hodgetts` is the closest current method. It descends from the
smartphone phase adjustment task {cite:p}`2021:plans`. In the PAT-ECG,
91 participants completed 28 trials in about 30 minutes, turning a dial until
tones felt synchronous with their heartbeat. Consistency of the chosen delays
was scored as the mean resultant length and tested against a Monte Carlo null;
16.7 percent were classified as interoceptive. Confidence was rated from 1 to
10 after each trial. The task has an absolute-delay and a relative-delay
version, and an exteroceptive control in which a tactor vibrates on the hand.

The two tasks share the trigger (the R-wave), the stimulus (a tone at a
delay), the two possible timing axes (milliseconds or cardiac phase), a
confidence rating and an exteroceptive control. They differ in the
psychophysical method.

| | PAT-ECG | HSD |
|---|---|---|
| Method | Adjustment: the participant turns a dial until the tones feel synchronous, then presses space | Constant stimuli made adaptive: the procedure sets the delay, the participant answers yes or no |
| Who samples the delays | The participant, freely, for as long as they like (about 1 minute per trial, 28 trials in 30 minutes) | The algorithm, by expected information gain; a trial is five beats plus a response |
| Measure | Circular consistency of the chosen delays across trials (mean resultant length), tested against a Monte Carlo null | Posterior over the location, width, floor and peak of a response envelope; credible intervals; posterior evidence that the envelope rises at all |
| Width of the sensation | Not separable from consistency | An explicit parameter, `sigma` |
| Lapses and bias | Not modelled; confidence weighting offered instead | Floor and peak parameters absorb lapses, and are marginalized out |
| Stopping | Fixed 28 trials, justified by simulation (15 to 20 enough for classification) | Credible-interval width on `mu`, with a maximum |

The phase adjustment task was built for smartphone photoplethysmography,
where the participant's own exploration replaces a controlled stimulus
schedule and a consistency score needs no psychometric model. That choice has
costs. Adjustment mixes perception with search strategy: a participant can be
consistent by always stopping after a similar turn of the dial. It gives no
control over which delays are presented. And it cannot separate where the
sensation lies from how precise it is. A yes or no judgement at a delay the
experimenter chooses is the classical remedy, and Bayesian placement is what
makes it short enough to use.

Two ideas from the PAT carry over:

- **Cardiac phase as an alternative stimulus axis.** A delay can be fixed in
  milliseconds or as a fraction of the interbeat interval. Palmer and
  colleagues report both delay-based and phase-based responders
  {cite:p}`2025:palmer`. The HSD engine works on any real-valued stimulus, so a
  phase axis needs only a different candidate set and grid.
- **An exteroceptive version with a known delay.** The same procedure applied
  to a stimulus whose true delay is known validates the whole pipeline, from
  timing to estimation.

## The model

The probability of a "synchronous" answer at delay $d$ (ms after the R-wave)
is a Gaussian bump on a floor:

$$
P(\text{yes} \mid d) = \text{floor} + (\text{peak} - \text{floor})
\exp\left(-\frac{1}{2}\left(\frac{d - \mu}{\sigma}\right)^2\right)
$$

| Parameter | Meaning | Default grid |
|---|---|---|
| `mu` | Where in the cardiac cycle the sensation is felt, in ms after the R-wave | 0 to 600 ms in 10 ms steps (61 values) |
| `sigma` | Width of the sensation, in ms | 20 to 300 ms, log-spaced (20 values) |
| `floor` | Rate of "yes" far from the sensation: lapses towards "yes", and the whole response profile of a non-detector | 0, 0.05, 0.1, 0.2, 0.3, 0.4 |
| `peak` | Rate of "yes" at the sensation: one minus the lapse rate towards "no" | 0.5, 0.6, 0.7, 0.8, 0.9, 0.97 |

The grids cover the published range of observers with room to spare
{cite:p}`1988:brener,2016:brener`, because the point of estimating the
location is not to assume it. The simulations offer candidate delays from 0
to 600 ms in 20 ms steps and the task runner from 80 to 600 ms, of which the
current hardware can realize those from 130 ms (see
[delay limits](#realized-delays-and-per-trial-constraints)). The posterior is discrete on the outer product of the four grids,
about 44,000 points; one stimulus selection takes about 13 ms.

**Prior.** Uniform over `mu` by default, or any non-negative weights over the
`mu` grid. Uniform over the `sigma` grid points, which is log-uniform because
the grid is log-spaced. Uniform over `floor` and `peak`, with zero mass where
the peak would lie below the floor (an inverted envelope).

**A non-detector** answers "yes" at a rate that does not depend on delay. In
the model that is a flat envelope, with the peak close to the floor. The
detection evidence is the posterior mass on `peak - floor` above 0.2. On the
default grids 33 of the 36 floor and peak pairs rise by more than 0.2, so the
prior on this event is about 0.92, and the design reports the evidence
alongside its prior as a Bayes factor (posterior odds over prior odds). A flat
response profile can also be absorbed by a very wide `sigma` or by a `mu` at
the edge of the grid, so the number is a sanity check. It is reported, never
used to classify people as detectors.

## Choosing the next delay

**Objective.** Each trial presents the candidate delay that minimizes the
expected entropy of the marginal posterior over the target parameters, the
Psi-marginal method {cite:p}`2013:prins`. The default target is `mu` alone;
`sigma`, `floor` and `peak` stay in the posterior as nuisance parameters but
do not steer placement. Naming all four as targets reproduces the joint
objective of the original Psi method {cite:p}`1999:kontsevich`, which also
spends trials on the nuisance parameters.

**Why not PsychoPy's `PsiHandler`.** It assumes a monotonic, cumulative
Gaussian psychometric function, as in the HRD. A synchrony judgement rises
towards the sensation and falls after it, so the function is not monotonic.
The HSD has its own grid posterior for that reason.

**The clustering concern.** García-Pérez {cite:p}`2014:garciaperez` names
binary synchrony judgements as a case of a non-monotonic psychometric
function. He proposes inward-outward staircases for them and warns that
Bayesian placement concentrates trials in too narrow a range for a later fit.
The HSD answers that in four ways:

1. Targeting `mu` alone samples the two flanks of the bump, where a change in
   `mu` changes the response probability most, rather than one narrow band.
2. An `explore` fraction of trials ignores the objective and draws a delay
   uniformly from the allowed candidates, so the tails stay sampled. The
   engine default is 0; the planned task default is 0.1, and the simulations
   vary it.
3. The raw trial history is saved, so any later refit is possible, including
   one with a different model.
4. The simulation study measures the distribution of sampled delays directly.

## Realized delays and per-trial constraints

**Realized delays.** The posterior is updated with the delay the participant
actually heard (the mean over the five tones of a trial, measured online
against the stamped R-wave and corrected by the latency bias below), not the
delay requested. The likelihood is recomputed from the envelope, so
any real-valued delay can be used. This is a correction the HRD, built on
PsychoPy's `PsiHandler`, could not make.

**Delay limits.** Each trial can restrict the candidates:

| Limit | Set by | Why |
|---|---|---|
| `min_delay` | The system's R-to-tone latency | No tone can be scheduled before the system knows about the R-wave. 130 ms of physical delay on current hardware (below); the simulations used 80 ms |
| `max_delay` | 0.75 of the anticipated interbeat interval | Keeps the last tone clear of the next beat. The envelope is periodic in the cardiac cycle and the model ignores that, so delays near the next beat would be misread |

If no candidate lies between the two limits, the engine raises an error
rather than presenting a delay outside them.

**The latency floor on current hardware.** These figures come from
measurements on the pat-ecg branch, 2026-11-03, with a PLUX ECG streamed over
Lab Streaming Layer to the stimulus PC. They are bench measurements, not a
published result.

| Stage | Measured |
|---|---|
| Online R detector (`OnlineRDetector`) commits a beat | 14 ms median, 18 ms maximum after the R peak |
| Whole chain knows about a beat | 20 ms median, 31 ms at the 95th percentile, after the R-wave |
| Tone scheduled with psychtoolbox audio, latency class 1, 50 ms lead | Lands within 1 ms of the scheduled time (latency class 3 was unusable on that laptop) |
| Dry run, tones anchored on the real R-wave | Within 17 ms of the intended phase at the 95th percentile |

**The latency bias.** Two delays do not appear in any recording. The PLUX
Bluetooth transport delivers each sample 20 to 40 ms after the hub took it,
and LSL stamps it on arrival, so the stamped R-wave is late. The sound leaves
the speaker some milliseconds after the onset the audio driver reports.
Together these come to a roughly constant 30 to 70 ms, which the PAT dry run
measured. As the PAT task does, the runner subtracts a latency bias,
`TaskConfig.latencyBias` (50 ms by default), from every tone's target, so
that the tone reaches the participant at the requested delay after the true
R-wave. A delay measured against the stamped R-wave is then 50 ms short of
the physical one, and the runner adds the bias back before it updates the
posterior. Both values are saved: `RealizedDelay` as measured,
`RealizedCorrected` as the engine saw it. The phase axis applies the same
subtraction to the target and the same addition to the realized fraction.

**The latency floor.** A tone for a physical delay `d` is due at the stamped
R-wave plus `d` less the 50 ms bias. It can be scheduled only if that is at
least the 50 ms audio lead after the beat is known, which is up to 31 ms after
the stamped R-wave. So

```{math}
d \geq 31 + 50 + 50 = 131 \text{ ms},
```

and the runner's floor, `TaskConfig.minDelay`, is 130 ms. The candidates
still start at 80 ms; the per-trial bounds leave out those under the floor.
Shorter delays are possible only by scheduling predictively from the
anticipated interbeat interval (the mean of the last three RR intervals).
That adds the beat-to-beat variability of the heart period to the delay as
jitter, and is not implemented. A sensation earlier than 130 ms can still be
located, but only from the falling side of the envelope.

The main simulation study used an 80 ms floor, the reactive floor before the
latency bias was accounted for. A rerun at the 130 ms floor is reported under
[results at the 130 ms floor](#results-at-the-130-ms-floor): the higher floor
costs accuracy for sensations at 250 ms and earlier, most of all at 150 to
200 ms.

The latency bias is an estimate. The LabRecorder file remains the ground
truth for checking it: with the ECG and the tone markers on one clock, the
offline R-waves and the reported onsets show the delay actually delivered,
less the speaker.

**Stopping rule candidates.** Stop when the 95 percent credible interval on
`mu` is at most a target width, with a minimum and a maximum number of trials.
The [simulations](#results-at-the-80-ms-floor), run with the 80 ms floor, show
that the width an observer can reach depends
mostly on how noisy their answers are. The table gives the trial at which the
median credible-interval width under Psi-marginal on `mu` first reaches each
value, over 150 runs per class.

| Median 95% CI width on `mu` | Clean observers (floor 0.05, peak 0.95) | Noisy observers (floor 0.2, peak 0.8) |
|---|---|---|
| 150 ms | 26 trials | 62 trials |
| 100 ms | 42 trials | 81 trials |
| 80 ms | 53 trials | 106 trials |
| 60 ms | 69 trials | Not reached by 120 |
| 40 ms | 105 trials | Not reached by 120 |

At fixed trial counts the median widths are 150, 110, 70 and 40 ms for clean
observers at 30, 40, 60 and 120 trials, and 260, 220, 160 and 80 ms for noisy
ones. Width also grows with `sigma`: at 60 trials the clean medians are 30, 75
and 120 ms for `sigma` of 50, 100 and 150 ms.

| Setting | Candidate | Status |
|---|---|---|
| Credible-interval width on `mu` | 60 ms, the original candidate, is reached in median only by clean observers, at about 70 trials; 100 ms is reached at about 40 (clean) or 80 (noisy) trials | Open |
| Minimum trials | 15 | So that the floor and peak have data |
| Maximum trials | 60 | Open. At 60 trials, 45 percent of clean and 17 percent of noisy runs reach 60 ms; 71 and 33 percent reach 100 ms |

A stopping rule on width alone would therefore run most noisy observers to the
maximum. Whether the target should be a width, a fixed trial count, or a width
with a per-person cap is a choice for the task, and is left open here.

## Trial structure and saved data

This section describes the task as `cardioception.HSD.task` runs it. The
[user guide](user_guide.md#heartbeat-synchrony-discrimination) lists the
files a session writes.

1. Five tones, each at the chosen delay after a detected R-wave.
2. A "synchronous" or "not synchronous" judgement on the keyboard.
3. A confidence rating on the existing confidence scale, reusing the HRD's
   keyboard rating and `cardioception.scales.ConfidenceScale`.

Confidence is recorded alongside the judgement. It is not part of the
likelihood and does not affect stimulus placement.

Saved for every trial:

| Column group | Contents |
|---|---|
| Stimulus | Requested delay; realized delay of each tone; interbeat intervals during the train; trial type (adaptive or explore) |
| Response | Decision; response time; confidence |
| Online estimates | Posterior mean, median and credible interval for `mu`, `sigma`, `floor` and `peak`; detection evidence |

As with the HRD, the online estimates are a monitoring aid. They are not an
analysis, and the trial history is what a later model should be fitted to.

## Simulation study

The study asks how many five-beat trials the adaptive procedure needs to
recover `mu` to within about 20 to 30 ms across realistic observers,
compared with the 120-trial MCS, and whether Bayesian placement biases
anything.

**Observers.**

| Group | Parameters | Count |
|---|---|---|
| Detectors | `mu` in {150, 200, 250, 300, 350} ms; `sigma` in {50, 100, 150} ms; (`floor`, `peak`) in {(0.05, 0.95), (0.2, 0.8)} | 30 |
| Non-detectors | Flat "yes" rate of 0.3 or 0.5 | 2 |
| Misspecified | Asymmetric envelope, right tail twice as wide as the left, `mu` at 200 or 300 ms, `sigma` 100 ms, (`floor`, `peak`) = (0.05, 0.95) | 2 |

**Methods.**

| Label | Method |
|---|---|
| MCS | Six delays from 0 to 500 ms, 20 trials each, random order. Analyzed on the same grid posterior, and with the classical median interval and interquartile range |
| Psi-marginal, `mu` | Target `mu`; `sigma`, `floor` and `peak` as nuisances |
| Psi-marginal, `mu` and `sigma` | Target `mu` and `sigma` |
| Psi joint | All four parameters as targets |

Each adaptive method runs with `explore` at 0 and at 0.1. Every run lasts 120
trials so that estimates can be compared at every trial count. An
inward-outward staircase arm after García-Pérez was optional and was not run.
The adaptive methods use a `min_delay` of 80 ms, the reactive floor measured
above before the latency bias was accounted for, so their candidates run from
80 to 600 ms. The runner's floor is now 130 ms, and four of the methods were
rerun with it (see [results at the 130 ms floor](#results-at-the-130-ms-floor)).
The MCS keeps its published
levels from 0 to 500 ms as the classical benchmark, although 0 ms cannot be
realized on current hardware.

**Replications.** Ten seeds per observer and method, seeded through the
package's random number generator so every run can be reproduced: 34
observers, 7 methods (MCS and three adaptive objectives, each adaptive one
with and without exploration), 10 repetitions and 120 trials, 2,380 runs in
all. With seed 2026 and 28 worker processes the study took 38 minutes on a
32-core machine:

    python -m cardioception.HSD.simulate --out <dir> --reps 10 --processes 28 --trials 120 --seed 2026

**Metrics.** Absolute error and root mean squared error of the posterior mean
of `mu` at each trial count; credible-interval width; coverage of the 95
percent interval; error in `sigma`; detection evidence for the non-detectors;
the distribution of sampled delays, which is the check on clustering.

**Outputs.** A CSV of per-trial estimates, a figure of RMSE and
credible-interval width against trial count by method, and a table at 20, 30,
40, 60 and 120 trials. The simulation script regenerates all three.

### Results at the 80 ms floor

These are the results of the main study, in which the adaptive methods could
present any candidate delay from 80 ms. Error and interval width are over the
30 detectors (300 runs per method) unless stated otherwise. In the method labels, `psi_mu` targets `mu`, `psi_mu_sigma`
targets `mu` and `sigma`, `psi_joint` targets all four parameters, and `_x10`
marks an `explore` fraction of 0.1.

```{figure} images/hsd_simulation.png
:alt: Two panels against trial number, 1 to 120. Left, RMSE of the posterior mean of mu falls from about 85 ms for all methods; MCS stays highest until about trial 75, and all methods end between 16 and 23 ms. Right, mean 95 percent credible-interval width falls from about 570 ms to between 70 and 86 ms, with MCS widest throughout.

RMSE of the posterior mean of `mu` (left) and mean width of its 95 percent
credible interval (right) against trial count, by method, for the 30 detectors,
with the 80 ms floor.
```

| `mu` RMSE (ms) at trial | 20 | 30 | 40 | 60 | 120 |
|---|---|---|---|---|---|
| MCS | 58.8 | 54.8 | 45.4 | 35.5 | 20.7 |
| `psi_mu` | 46.8 | 38.5 | 33.3 | 25.1 | 17.1 |
| `psi_mu_x10` | 46.0 | 37.3 | 32.6 | 23.2 | 15.7 |
| `psi_mu_sigma` | 39.8 | 34.7 | 31.6 | 27.4 | 19.8 |
| `psi_mu_sigma_x10` | 42.0 | 36.7 | 32.4 | 27.8 | 21.1 |
| `psi_joint` | 47.0 | 37.7 | 34.2 | 30.6 | 22.4 |
| `psi_joint_x10` | 46.6 | 39.5 | 33.6 | 28.7 | 22.2 |
| Median absolute error, `psi_mu` | 22.8 | 18.1 | 14.8 | 11.7 | 6.8 |
| Mean CI width, MCS | 351 | 274 | 224 | 164 | 86 |
| Mean CI width, `psi_mu` | 288 | 214 | 172 | 120 | 70 |

**Accuracy of `mu`.** Every adaptive method has a lower RMSE than MCS within
the first few trials, and a narrower interval from about trial 12. The joint
objectives and `psi_mu_sigma_x10` lose that advantage from about trial 75 to
90 and end slightly worse than MCS at 120 trials (21.1 to 22.4 ms against
20.7 ms); `psi_mu`, `psi_mu_x10` and `psi_mu_sigma` stay ahead throughout.
`psi_mu_sigma` has the lowest RMSE up to about trial 45, by up to 7 ms; from
about trial 50, `psi_mu` (with or without exploration) is lowest. `psi_mu`
reaches the 60-trial MCS error of 35.5 ms at trial 37 (`psi_mu_sigma` at
trial 29), and the 120-trial MCS error of 20.7 ms at trial 81. Its median
absolute error is 18 ms at 30 trials and 15 ms at 40, so the plan's 20 to
30 ms target is met in median by about 30 trials. The mean credible interval
at those counts (214 and 172 ms) is far wider, mostly because of the noisy
observers; the [stopping-rule candidates](#realized-delays-and-per-trial-constraints)
give the widths by observer class. Exploration at 0.1 changes RMSE by at most
about 2 ms in either direction. On the same MCS data, the classical median
interval has an RMSE of 37.7 ms at 120 trials against 20.7 ms for the grid
posterior, so part of the gain over the classical analysis comes from the
model, not the placement.

**Calibration and bias.** Coverage of the 95 percent interval lies between 0.96
and 1.00 for every method at every trial count from 20, so the intervals are
honest, if conservative. MCS is biased upward early (+10.9 ms at 20 trials,
+3.7 ms at 60, -0.2 ms at 120); the adaptive methods stay within about -6 to
+2 ms throughout. Error in `sigma` improves little for any method, from about
36 ms at 20 trials to 23 to 28 ms at 120, including the methods that target
`sigma`. The two asymmetric observers (20 runs per method) have a `mu` RMSE of
45 to 71 ms for every method, with little improvement over trials (`psi_mu`
50 to 45 ms, MCS 71 to 54 ms). That is the cost of the Gaussian assumption
when the envelope is skewed, and a reason to keep the raw trial history for
refitting.

**Detection evidence.** For detectors the median log10 Bayes factor passes +1
between trials 30 and 41 depending on method (33 for `psi_mu`, 41 for MCS)
and reaches +2.9 to +4.8 by trial 120, highest for the joint objectives, which
target `floor` and `peak` directly. For the two flat non-detectors it is
negative throughout, from about -0.3 to -0.5 at 20 trials to -0.6 to -1.2 at
120, and their posterior detection evidence is still 0.47 to 0.65 at 120
trials against a prior of 0.92. The evidence moves in the right direction for
both groups, but slowly, which is why it is reported as a sanity check and
not used as a classifier.

| Sampled delays, detectors, all trials | MCS | `psi_mu` | `psi_mu_x10` |
|---|---|---|---|
| Candidate delays | 6, from 0 to 500 ms | 27, from 80 to 600 ms | 27, from 80 to 600 ms |
| Delays receiving at least 2 percent of trials | 6 | 18 | 19 |
| Largest share at any one delay | 16.7 percent (every level) | 13.8 percent (80 ms) | 13.2 percent (80 ms) |
| Share at 80 to 160 ms | 16.7 percent (the 100 ms level) | 26.6 percent | 26.8 percent |
| Share at 520 to 600 ms | None (no level above 500 ms) | 3.3 percent | 5.0 percent |

**Clustering.** Bayesian placement did not concentrate trials in a narrow
band. Under `psi_mu`, 18 of the 27 candidate delays each receive at least
2 percent of trials, with 5 to 7 percent per delay between 180 and 320 ms,
against six levels at 16.7 percent each under MCS. The one concentration is at
the 80 ms floor: 32 percent of trials for observers with a `mu` of 150 ms and
3 percent for a `mu` of 350 ms. For early sensations the hardware floor cuts
off the rising side of the envelope, so the lowest allowed delay is the most
informative one left. The longest delays, 520 to 600 ms, receive 3 percent of
trials without exploration and 5 percent with it.

### Results at the 130 ms floor

The rerun used the runner's 130 ms floor, with the same 34 observers, the same
10 repetitions and the same seed (2026) as the main study, for four methods:
MCS, `psi_mu`, `psi_mu_x10` and `psi_mu_sigma`, 1,360 runs in all. The
adaptive candidates now start at 140 ms. MCS keeps its published levels from
0 to 500 ms, which the floor does not touch, so its figures are those of the
main study.

| `mu` RMSE (ms) at trial, 130 ms floor | 20 | 30 | 40 | 60 | 120 |
|---|---|---|---|---|---|
| MCS (levels 0 to 500 ms, unaffected) | 58.8 | 54.8 | 45.4 | 35.5 | 20.7 |
| `psi_mu` | 39.0 | 33.0 | 31.6 | 29.4 | 25.8 |
| `psi_mu_x10` | 40.6 | 34.7 | 33.3 | 30.3 | 26.9 |
| `psi_mu_sigma` | 40.4 | 35.9 | 34.2 | 29.6 | 24.6 |
| Bias of `mu`, `psi_mu` | -8.5 | -9.2 | -11.1 | -10.7 | -10.0 |
| Mean CI width, `psi_mu` | 283 | 219 | 185 | 135 | 85 |

Against the 80 ms floor, `psi_mu` is no worse early on: its RMSE is lower up to
about trial 40 (39.0 against 46.8 ms at 20 trials). From about trial 45 it is
higher, by 4 ms at 60 trials and by 9 ms at 120, where it rises from 17.1 to
25.8 ms. A bias of about -10 ms appears from the first trials and stays,
against -2.6 ms at 120 trials with the 80 ms floor. The adaptive methods still
beat MCS up to about trial 75, but at 120 trials all three are worse than MCS
(24.6 to 26.9 ms against 20.7 ms), because the MCS levels are not held to the
floor.

The loss sits in the observers whose sensation is early. Split by the true
`mu`, at trial 120 (60 runs per cell):

| `psi_mu` at trial 120, true `mu` | 150 ms | 200 ms | 250 ms | 300 ms | 350 ms |
|---|---|---|---|---|---|
| RMSE (ms), 80 ms floor | 24.0 | 15.6 | 12.6 | 12.8 | 17.8 |
| RMSE (ms), 130 ms floor | 34.3 | 38.3 | 17.7 | 12.2 | 14.6 |
| Bias (ms), 80 ms floor | -13.0 | -1.6 | +1.0 | +1.4 | -1.0 |
| Bias (ms), 130 ms floor | -24.1 | -20.5 | -5.7 | -1.1 | +1.6 |

At `mu` of 300 and 350 ms the two floors agree within a few milliseconds. At
150 and 200 ms the RMSE rises by 10 and 23 ms and the bias reaches about
-20 ms. Within those observers it is the wide sensations that suffer: at a
`mu` of 200 ms the bias is -4 ms for a `sigma` of 50 ms, and -25 and -33 ms for
100 and 150 ms. A wide envelope centred at 150 or 200 ms has much of its rising
flank below 130 ms, so the falling flank carries most of what the data say
about it, and the falling flank alone is consistent with an earlier `mu`,
which pulls the posterior mean down.

Lowering the floor is therefore worth real accuracy, for the observers whose
sensation comes early in the cycle. That is the case for roadmap items C1 to
C3 under [what comes next](#what-comes-next): C1 brings the floor to about
100 ms on the current hardware and C3 to about 60 ms with a wired ECG, and C2
removes the transport jitter that the [hardware dry run](#hardware-dry-run)
found.

## Hardware dry run

On 2026-11-03 the runner was run for one full session on the test desktop: a
PLUX ECG streamed over Bluetooth into LSL by the PLUX bridge, the wrapper's
settings (absolute axis, at most 60 trials), and LabRecorder recording the ECG
and the `HSD` marker stream. The participant wore a tight finger pulse
oximeter throughout, as a positive control, so that there was a clear pulse
sensation to locate. One session on one person checks the pipeline. It says
nothing yet about heartbeat perception.

| Check | Measured |
|---|---|
| Session | 60 trials in 7 minutes |
| Tones | 305 scheduled and 305 played, the practice trials included; onsets within 1 ms of the schedule |
| Online R detector | Commits a beat 13 ms (median) and 14 ms (95th percentile) after the stamped R-wave |
| ECG stream | No dropped samples |
| Online beats against offline R-waves from the recording | Sensitivity 0.996, positive predictive value 1.0 |
| Realized delay against the stamped R-wave | 50 ms below the request on every trial, by design (the latency bias) |
| Tone onsets against the offline R-wave | Interquartile range of 23 ms on the raw LSL timestamps, 44 ms on the dejittered ones |
| Bluetooth arrival jitter of the ECG samples | SD 26 ms on the test desktop, against 6 ms on the stimulus PC |

The scheduling itself was exact: every tone landed within 1 ms of the time it
was given. The scatter against the offline R-wave comes from before the
scheduler. The online detector times each R-wave from the timestamps its
samples carry when they arrive, and on that desktop the Bluetooth arrival
times jittered with an SD of 26 ms, against 6 ms on the stimulus PC. Against
the recording's dejittered timestamps, which are closer to when the hub took
each sample, the tones therefore scattered more widely (44 ms) than against
its raw ones (23 ms). Jitter of this size widens the measured `sigma`, which is
what roadmap items C2 and C3 address.

```{figure} images/hsd_dryrun_session.png
:alt: Three panels from the 60-trial dry run. Left, each answer (1 synchronous, 0 not) against the realized delay from 140 to 540 ms, coloured by confidence, with the proportion of synchronous answers per 50 ms bin as squares and the posterior-mean envelope, which rises from a floor of about 0.32 to a peak of about 0.75 near 270 ms. Middle, the posterior mean of mu settles near 270 ms over trials while its 95 percent credible interval narrows from 0 to 600 ms to 150 to 400 ms. Right, the log10 Bayes factor for detection wanders between -0.6 and +0.3 and ends near 0.

The dry run session. Left: each answer against the realized delay, coloured by
confidence, with the proportion of "synchronous" answers in each 50 ms bin
(squares, sized by the number of trials) and the posterior-mean envelope.
Middle: posterior mean of `mu` and its 95 percent credible interval after each
trial. Right: log10 Bayes factor for detection after each trial.
```

After 60 trials, the session's maximum, the posterior put `mu` at 272 ms with
a 95 percent credible interval of 150 to 400 ms, `sigma` at 98 ms, the floor
at 0.32 and the peak at 0.75. The log10 Bayes factor for detection was about 0.
The interval never came down to the 100 ms stopping width, so the session ran
to its maximum.

| Realized delay (ms) | 100 to 150 | 150 to 200 | 200 to 250 | 250 to 300 | 300 to 350 | 350 to 400 | 400 to 450 | 450 to 500 | 500 to 550 |
|---|---|---|---|---|---|---|---|---|---|
| P(synchronous) | 0.33 | none | 0.62 | 0.84 | 0.57 | 0.20 | 0.00 | 0.33 | 0.62 |
| Trials | 9 | 0 | 8 | 19 | 7 | 5 | 1 | 3 | 8 |

The answers rise to a clear peak at 250 to 300 ms and fall away by 350 to
400 ms. But the participant also answered "synchronous" on 5 of the 8 trials
at 500 to 550 ms. The model has one bump, so it absorbed those long-delay
answers as a high floor, 0.32, rather than as a second rise. A floor that high
leaves the envelope a rise of only 0.43 from floor to peak, and the posterior
mass on a rise of more than 0.2 stayed at 0.92, the same as its prior. That is
why the Bayes factor stayed near 1 even though `mu` was located. Whether the
long-delay answers were heard against the next beat, the periodicity the model
ignores, cannot be told from one session.

## What comes next

| Phase | Status | Content |
|---|---|---|
| B. Task runner | Implemented | The task, its parameters and configuration, English instructions, an autopilot observer, the train scheduler with both stimulus axes, a headless test on a virtual heart, an LSL test on a synthetic ECG through `LSLRecorder` and the shared `LSLBeatSource`, the wrapper and a user guide section. `setup="behavioral"` uses the shared `LSLBeatSource` and `TonePlayer` in `cardioception.devices` |
| B. Hardware dry run | Done, 2026-11-03 | The Plux-to-LSL bridge installed on the test desktop and 60 trials run on a real ECG in 7 minutes, recorded with LabRecorder. All 305 tones were scheduled and played, onsets matched their schedule within 1 ms, the detector committed 13 ms after each R, no samples were dropped, and the realized delay sat 50 ms below the request by design. Against the offline R-wave the tones scattered with an interquartile range of 23 to 44 ms, because the Bluetooth arrival stamps of the ECG samples jitter (SD 26 ms on that desktop, 6 ms on the stimulus PC). The session put the sensation of a participant wearing a tight finger pulse oximeter at 272 ms, interval 150 to 400 ms. See [hardware dry run](#hardware-dry-run) |
| C1. Audio lead and output calibration | Planned, software only | Cut the audio scheduling lead from 50 to 20 ms (the bench showed 20 ms still lands within 1 ms) and measure the output offset of the speaker or headphones with the microphone loopback in `bench/audio_onset.py`, so the latency bias becomes a measured constant per setup. Lowers the physical floor from 130 to about 100 ms and makes `mu` comparable across laboratories |
| C2. Re-time Plux samples from the hub's counter | Planned, bridge change shared with PAT | The hub samples at exactly 1000 Hz, so a running fit of its sample counter to the clock in the bridge removes the Bluetooth arrival jitter down to the chunk period, about 10 ms, without touching the constant lag. Jitter is the error that inflates `sigma`: 26 ms of it turns a true width of 40 ms into a measured 48 ms |
| C3. Wired ECG into LSL | Recommended configuration | Biopac, ADInstruments and Brain Products all have LSL paths. Jitter falls to a millisecond or two, the transport lag to a few milliseconds, and with the shorter lead the floor to about 60 ms. The simulations put the gain of a lower floor at 26 to 17 ms RMSE on `mu` at 120 trials and remove a 10 ms bias, because sensations at 150 to 200 ms regain their rising flank |
| D. Exteroceptive validation | Not started | The same adaptive procedure on a tone and vibration (or light) stimulus with a known delay, as a screening condition and as a ground-truth check of the engine |

## References

Full entries for the citations on this page are on the
[references page](references.md).
