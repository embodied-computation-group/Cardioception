---
myst:
  html_meta:
    description: "The rationale and psychometric model behind HSD, including adaptive delay selection, detection evidence, stopping and hardware timing limits."
    keywords: "heartbeat synchrony discrimination, HSD, psychometric model, Psi-marginal, cardiac interoception"
---

# HSD method and rationale

The Heartbeat Synchrony Discrimination task (HSD) asks when, relative to the
ECG R-wave, a participant experiences their heartbeat. Participants judge
whether a sequence of tones feels synchronous with it. By varying the delay,
the task estimates where synchronous responses are most likely and how
broadly they are distributed across the cardiac cycle.

This page explains the measurement logic, the adaptive procedure, and the
timing constraints. For session setup, use the [HSD task page](index.md).
The companion [validation page](validation.md) presents the simulations,
hardware demonstration, and remaining validation work.

```{important}
HSD is in beta. Simulations and a hardware demonstration have been completed,
but the task has not been validated in a participant study. The reported
simulation results use marginal estimates of heartbeat timing; the current
stopping rule uses conditional estimates. Their implications are distinguished
on the [validation page](validation.md#simulation-study).
```

## Why a new task

Heartbeat sensations do not occur at the same delay after the R-wave in every
person. A task that compares only two fixed delays can therefore miss a clearly
perceived heartbeat whose timing falls between them. Across heartbeat
discrimination tasks with two fixed delays, Brener and Ring estimate that only
about one in three or four people reliably discriminate {cite:p}`2016:brener`.
Whitehead and colleagues, who introduced the procedure, set no detector
criterion {cite:p}`1977:whitehead`.

The original procedure flashed a light 128 or 384 ms after each R-wave; later
versions mostly use tones, and the delays vary between laboratories.

The method of constant stimuli addresses this problem by sampling several
delays across the cardiac cycle {cite:p}`1993:brener`. Each participant's
responses reveal a preferred delay and a spread of delays judged synchronous.
A standard session takes about 35 minutes, including familiarization. HSD
retains this multi-interval approach and uses adaptive sampling to obtain
information about the preferred delay in fewer trials.

The [theory page](../theory.md#what-fixed-delay-synchrony-tasks-can-establish)
explains the measurement problem in more detail. The literature and the
relationship to the Phase Adjustment Task are reviewed under
[background evidence](#background-evidence).

## The model

The model links the probability of a synchronous response to the tone delay
$d$ through a Gaussian response envelope:

```{math}
P(\text{synchronous} \mid d)
= \mathrm{floor} + (\mathrm{peak} - \mathrm{floor})
\exp\left[-\frac{1}{2}\left(\frac{d-\mu}{\sigma}\right)^2\right].
```

The centre, $\mu$, is the delay at which synchronous responses are most
likely. The width, $\sigma$, describes how quickly that probability falls as
tones move away from the centre. The `floor` and `peak` set the baseline and
maximum response probabilities. They allow the model to represent occasional
inconsistent responses and a general tendency to answer yes or no.

These are properties of the response pattern. In particular, $\sigma$ can
reflect variability in both perception and stimulus timing. A narrow
envelope is consistent with precise judgements only to the extent that the
recording and audio system deliver the intended delays reliably.

The task can express delays in milliseconds after the R-wave or as fractions
of the cardiac period. In either case it updates a discrete posterior over
the four parameters after each valid response. The absolute-axis parameter
grids and priors are given below.

::::{dropdown} Parameter grids and priors

| Parameter | Meaning | Default grid |
|---|---|---|
| `mu` | Where in the cardiac cycle the sensation is felt, in ms after the R-wave | 0 to 600 ms in 10 ms steps (61 values) |
| `sigma` | Width of the sensation, in ms | 20 to 300 ms, log-spaced (20 values) |
| `floor` | Rate of "yes" far from the sensation: lapses towards "yes" | 0.03, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.97 |
| `peak` | Rate of "yes" at the sensation: one minus the lapse rate towards "no". Equal to `floor` for a flat responder | The same grid as `floor`, at or above it |

The parameter grids extend beyond the published range of heartbeat timing
estimates {cite:p}`1988:brener,2016:brener`, allowing the model to represent
a wide range of response patterns. The simulations offer candidate delays from 0
to 600 ms in 20 ms steps and the task runner from 80 to 600 ms. With the
130 ms floor of the current hardware the shortest delay presented is 140 ms,
the first candidate above it, and the ceiling of about 0.68 of the heart
period allows 600 ms only at periods over 0.89 s (see
[delay limits](#realized-delays-and-per-trial-constraints)). The posterior is discrete on the outer product of the four grids,
98,820 points, of which the 54,900 with the peak at or above the floor carry
prior mass; one stimulus selection takes about 20 ms.

**Prior.** Uniform over `mu` by default, or any non-negative weights over the
`mu` grid. Uniform over the `sigma` grid points, which is log-uniform because
the grid is log-spaced. Uniform over the 45 pairs of `floor` and `peak` with
the peak at or above the floor, and zero mass where it would lie below (an
inverted envelope). The 9 pairs with the peak equal to the floor, the flat
responders, carry 0.2 of the prior.
::::

## Choosing the next delay

After each response, the task evaluates the information expected from each
available delay. By default, it chooses the delay expected to reduce
uncertainty about $\mu$ most. This is the Psi-marginal approach
{cite:p}`2013:prins`: $\sigma$, `floor`, and `peak` remain in the model, but
the objective averages over their uncertainty rather than targeting them
directly. Targeting all four parameters instead gives the joint objective of
the original Psi method {cite:p}`1999:kontsevich`.

The task also selects a delay at random on 10 percent of trials. This
exploration helps sample parts of the response pattern that the adaptive
objective might otherwise visit rarely. The underlying engine defaults to
no exploration; the task configuration sets `explore=0.1`.

Adaptive sampling can concentrate observations within a limited stimulus
range, a concern raised for non-monotonic psychometric functions by
García-Pérez {cite:p}`2014:garciaperez`. HSD addresses this through the
location objective, random exploration, and retention of the full trial
history for later fitting. The validation study also checks
[which delays were actually sampled](validation.md#sampling-across-delays).

PsychoPy's `PsiHandler` assumes a monotonic cumulative Gaussian function,
as used in HRD. Synchrony responses instead rise towards a preferred delay
and fall beyond it. HSD therefore uses its own grid-based estimation engine,
`cardioception.HSD.psi`.

## Evidence for a timing-dependent response

A participant may answer synchronous at roughly the same rate at every
delay. The model represents this with `peak` equal to `floor`. Such a flat
response pattern provides no information about a preferred timing, whether
the participant answers yes frequently, rarely, or about half the time.

The task consequently reports both a timing estimate and evidence that
responses vary with delay. Detection evidence is the posterior probability
that the model's largest and smallest response probabilities differ by more
than 0.2 **over the range of delays presented**. This is distinct from
`peak - floor`: a peak outside the sampled range, or an extremely broad
envelope, may produce little variation within that range. Before two distinct
delays have been presented, the candidate range is used.

The prior probability of this event is about 0.47 over 140 to 500 ms and
0.55 over 80 to 600 ms. The task also reports a Bayes factor, calculated as
posterior odds divided by prior odds, to express how the observations change
the evidence. This is a monitoring measure. The
[simulation results](validation.md#detection-evidence) do not establish it
as a classifier of individual participants.

## Timing estimates and the stopping rule

A flat envelope leaves $\mu$ unidentified. If it retains posterior
probability, the marginal posterior for $\mu$ includes a diffuse component,
even when the location of a possible rise is fairly well constrained.

The current task reports $\mu$ and $\sigma$ conditional on a rise greater
than 0.2 over the presented range. These estimates answer: where and how broad
is the response pattern, given that such a rise exists? The estimates of
`floor` and `peak` remain marginal. Detection evidence must be read alongside
the conditional estimates to assess support for their premise.

If the posterior probability of a rise falls below 0.01, the task falls back
to marginal estimates and sets `MuConditional` to False. Delay selection
always uses the marginal posterior of $\mu$, so trials continue to inform
both location and the evidence for a rise.

The session may stop after at least 15 valid updates when the 95 percent
interval for $\mu$ is no wider than 100 ms, or 0.17 of a cardiac period on
the phase axis. Otherwise it ends at the maximum of 60 trials. These defaults
are provisional. The [session-length results](validation.md#session-length)
were calculated from marginal intervals and do not establish the stopping
behaviour of the current conditional rule.

## Realized delays and per-trial constraints

The recording and audio system restrict which delays can be presented. At the
short end, the task must detect an R-wave and schedule a tone before its
target time. At the long end, the tone must remain sufficiently far from the
next heartbeat to avoid ambiguity about which beat it accompanies.

The default minimum delay is 130 ms, making 140 ms the first available
candidate. On the absolute axis, the upper limit is 0.675 of the anticipated
heart period: a 0.75 limit with a 10 percent margin. Thus, a 600 ms candidate
requires a period longer than about 0.89 s. If no candidate falls within the
limits, the engine raises an error.

The minimum must be checked on the actual recording setup. The hardware
demonstration recorded some beats too late to deliver a 140 ms tone. Delays
below the minimum are not sampled; an earlier preferred timing can only be
inferred from the accessible portion of the response envelope. This is a
major source of error for early sensations in the simulations.

The model updates from the mean reported delay of the tones delivered on a
trial, with `latencyBias` added back, rather than simply using the requested
delay. This accommodates real-valued delays. However, driver-reported onset
is not a direct measurement of sound reaching the participant. Constant
latency and timing variability must be assessed separately. The
[timing measurements](validation.md#timing-measurements) explain these
quantities and the default 50 ms correction.

## Trial structure and saved data

This section describes the task as `cardioception.HSD.task` runs it. The
[HSD page](index.md#what-it-saves) lists the
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
| Stimulus | Requested delay; realized delay, the trial's mean (each tone's is in `*_tones.txt`); interbeat intervals during the train; trial type (adaptive or explore) |
| Response | Decision; response time; confidence |
| Online estimates | Posterior mean, median and credible interval for `mu` and `sigma`; posterior mean of `floor` and `peak`; detection evidence and Bayes factor |

As with the HRD, the online estimates are a monitoring aid. They are not an
analysis, and the trial history is what a later model should be fitted to.

## Background evidence

The following sections retain the literature supporting the task's design
and its relationship to adjustment methods.

### What the classical task established

::::{dropdown} Multi-interval studies and their implications

[Measuring cardiac interoception](../theory.md) already covers
[what fixed-delay synchrony tasks can establish](../theory.md#what-fixed-delay-synchrony-tasks-can-establish)
and why the MCS is
[a stronger measure of heartbeat timing](../theory.md#a-stronger-measure-of-heartbeat-timing).
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

These findings motivate three features of the HSD. The location of the sensation
must be estimated because it varies between people by hundreds of milliseconds.
Its width also varies and requires a separate parameter. Finally, each trial
presents several tones to support a more reliable judgement.
::::

### Relation to the Phase Adjustment Task

::::{dropdown} Shared features and differences in measurement

The ECG-based Phase Adjustment Task (PAT-ECG) of Hodgetts and colleagues
{cite:p}`2026:hodgetts` is the closest current method. It descends from the
smartphone Phase Adjustment Task {cite:p}`2021:plans`. In the PAT-ECG,
91 participants completed 28 trials in about 30 minutes, turning a dial until
tones felt synchronous with their heartbeat. Consistency of the chosen delays
was scored as the mean resultant length and tested against a Monte Carlo null;
16.7 percent were classified as interoceptive. Confidence was rated from 1 to
10 after each trial. The task has an absolute-delay and a relative-delay
version, and an exteroceptive control in which a tactor vibrates on the hand.

The two tasks share the trigger (the R-wave), the stimulus (a tone at a
delay), the two possible timing axes (milliseconds or cardiac phase) and a
confidence rating. An exteroceptive control like the PAT's is planned for the
HSD ([roadmap item D](validation.md#what-comes-next)). They differ in the psychophysical method.

The [tasks overview](../index.md#the-pat-and-the-hsd) sets the two side by
side.

The Phase Adjustment Task was developed for smartphone photoplethysmography.
Participants explore delays themselves, and their consistency can be scored
without fitting a psychometric function. However, adjustment also involves a
search strategy: consistent choices may reflect a habitual way of moving the
dial. The experimenter does not control which delays are sampled, and the
consistency score does not separately estimate the location and width of the
response pattern.

The HSD uses yes or no judgements at delays selected by the procedure. This
allows the model to estimate location and width separately. Bayesian selection
aims to reduce the number of trials needed for those estimates.

Two ideas from the PAT carry over:

- **Cardiac phase as an alternative stimulus axis.** A delay can be fixed in
  milliseconds or as a fraction of the interbeat interval. Palmer and
  colleagues report both delay-based and phase-based responders
  {cite:p}`2026:palmer_phase`. The HSD engine works on any real-valued stimulus, so a
  phase axis needs only a different candidate set and grid.
- **An exteroceptive version with a known delay.** The same procedure applied
  to a stimulus whose true delay is known validates the whole pipeline, from
  timing to estimation.
::::

## Validation and further reading

The [validation and technical details](validation.md) page presents the
simulation results, hardware demonstration, and implementation history.

### Simulation study

See the [simulation design and results](validation.md#simulation-study),
including accuracy, detection evidence, and session length.

### Hardware dry run

See the [hardware demonstration](validation.md#hardware-dry-run) for timing
measurements and the recorded session figure.

### What comes next

See the [remaining validation work](validation.md#what-comes-next) for the
hardware improvements and planned exteroceptive validation.

## References

Full citation details are on the [references page](../../reference/references.md).
