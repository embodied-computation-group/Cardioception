---
name: hrd-metacognition
description: Model confidence ratings from the Heart Rate Discrimination Task (HRD) using ordered beta regression in brms via ordbetareg. Use when analysing HRD confidence data, testing whether confidence tracks accuracy (metacognitive calibration), comparing confidence or metacognition between groups or conditions, or deciding how to handle a 0-100 confidence slider with responses piled up at both ends.
---

# HRD metacognition

Modelling the confidence ratings collected on every HRD trial, and the relationship
between confidence and accuracy.

This skill supplies mechanics. Which contrast, which exclusions, and how to report are
the user's decisions.

## What the data look like

Cardioception records confidence on a continuous slider, 0 to 100. Participants use both
ends heavily: "completely unsure" and "completely certain" are real answers, not
rounding. In a reference sample of 512 participants and 68,932 trials, 15.0% sit
exactly on a bound: 3.9% at zero and 11.1% at one. Measure this in your own data
before fitting, because it is what justifies the model.

That shape rules out the obvious options:

- **Gaussian** puts probability mass outside 0 and 100, and its predictions at the
  bounds are wrong in a way that gets worse as more responses pile up there.
- **Beta** is undefined at exactly 0 and 1, so it forces you either to nudge the bounds
  inward by an arbitrary epsilon or to drop those trials. Both distort the quantity of
  interest, and the second throws away the most confident and least confident responses.
- **Binning into a Likert scale** discards information and makes the answer depend on
  where you put the cut points.

## Why not the m-ratio

The m-ratio, meta-d′ divided by d′, is the usual summary of metacognitive
efficiency. It fits the HRD badly, for a reason specific to the staircase.

**The HRD does not hold accuracy constant.** Psi converges on the participant's
point of subjective equality, the Δ-BPM where they are equally likely to answer
"faster" or "slower". It tracks their bias, which is the quantity of interest, not
a target percentage correct.

**Accuracy is scored against the true heart rate**: "faster" is correct only when
Δ-BPM > 0, "slower" only when Δ-BPM < 0.

So for a biased participant the two come apart. A threshold of −15 Δ-BPM means the
staircase presents tones around 15 BPM below the true rate all session, and
"slower" is objectively correct on nearly every trial. One stimulus class is
nearly absent, and the hit and false-alarm rates behind d′ and meta-d′ rest on very
few trials. The more biased the participant, the more degenerate the type-1 table,
so the measure fails hardest on the participants the task has most to say about.

Two further problems: d′ under this design mixes bias with precision, which is the
confound the psychometric function exists to separate; and meta-d′ needs discrete
confidence bins, so a continuous slider must be cut, which discards information and
makes the answer depend on the cut points.

If a meta-d′ analysis is specifically required, for instance to match a published
protocol, it is a separate job with its own machinery and its own failure modes.
Do not improvise it inside this skill.

## The model

Ordered beta regression models the interior of the scale with a beta likelihood and the
two bounds as separate outcomes in a single generative model. Nothing is nudged, nothing
is dropped. See Kubinec (2023), *Political Analysis* 31(4), 519-536,
<https://doi.org/10.1017/pan.2022.20>.

```r
library(ordbetareg)

data$Confidence <- data$Confidence / 100   # keep exact 0 and 1

fit <- ordbetareg(
  formula = bf(Confidence ~ Accuracy + (Accuracy | Subject)),
  data = data,
  chains = 4, cores = 4,
  seed = 12345,
  file = "fit_confidence"
)
```

`ordbetareg` wraps brms, so all brms syntax, priors, and post-processing apply.

## Preparing the data

```r
data <- raw |>
  filter(Decision %in% c("More", "Less"), !is.na(Confidence), !is.na(ResponseCorrect)) |>
  mutate(
    Accuracy   = factor(ResponseCorrect, levels = c(0, 1), labels = c("incorrect", "correct")),
    Confidence = Confidence / 100
  )
```

Check these before fitting:

- **Range.** `range(data$Confidence)` must be within [0, 1] inclusive. Values outside
  mean the scale was not 0-100.
- **Bound mass.** `mean(data$Confidence %in% c(0, 1))`. This is what justifies the
  model; report it.
- **Per-subject scale usage.** A participant who left the slider at one value all
  session contributes no metacognitive information. Find them with
  `data |> group_by(Subject) |> summarise(sd = sd(Confidence))` and decide explicitly
  whether to exclude, rather than letting the model absorb them.
- **Trials without a response** have no accuracy and must be dropped, not recoded.

## Choosing the formula

The core question is whether confidence tracks accuracy. That is the coefficient on
`Accuracy`, and it is metacognitive calibration stated directly rather than as a ratio.

| Question | Formula |
|---|---|
| Does confidence track accuracy | `Confidence ~ Accuracy + (Accuracy \| Subject)` |
| Does it differ between Intero and Extero | `Confidence ~ Accuracy * Modality + (Accuracy * Modality \| Subject)` |
| Does it differ between groups | `Confidence ~ Accuracy * group + (Accuracy \| Subject)` |
| Relation to a covariate such as age | `Confidence ~ Accuracy * age_c + (Accuracy \| Subject)` |

Same random effect rule as the psychophysics model: **a term gets a random slope only if
it varies within a participant.** `Accuracy` and `Modality` do. `group`, `age` and
`gender` do not, so they take `(Accuracy | Subject)`, never `(group | Subject)`.

Centre continuous covariates. Sum-code a two-level between-subject contrast (-0.5/+0.5)
if you want the intercept to mean the grand mean rather than one group.

## Reading the output

- The **coefficient on `Accuracy`** is metacognitive calibration: how much higher
  confidence runs on correct trials than incorrect ones.
- The **intercept** is overall confidence, so bias and calibration stay separate. This is
  the practical advantage over a ratio measure: you do not have to choose between them.
- An **interaction with group or condition** is the difference in calibration, which is
  usually the actual hypothesis.

Coefficients are on the latent scale and are not directly interpretable as slider
points. For anything reported to a reader, compute marginal predictions on the response
scale:

```r
library(marginaleffects)
avg_predictions(fit, by = "Accuracy")           # mean confidence per level
avg_comparisons(fit, variables = "Accuracy")    # the difference, on the 0-1 scale
```

For a directional claim, give the posterior probability:

```r
hypothesis(fit, "Accuracycorrect > 0")
```

## Checking

1. Divergent transitions: any at all, raise `adapt_delta` to 0.95 or 0.99, and suspect a
   random slope on a between-subject term.
2. `rhat < 1.01`, bulk and tail ESS in the hundreds.
3. `pp_check(fit)` — specifically check that the model reproduces the **mass at 0 and
   1**, not just the interior. That is what the model is for; if it misses there, the
   model is not doing its job.

## Common problems

| Symptom | Likely cause |
|---|---|
| Error about values outside the interval | Confidence not divided by 100, or negative values from missing-data codes |
| Model fits but bound mass is badly predicted | Bound trials were dropped or nudged before fitting |
| Divergences, `sd` near zero | Random slope on a between-subject factor |
| Sensitivity near zero for everyone | `Accuracy` coded backwards, or trials without a response coded as incorrect |
| Coefficients look tiny | They are on the latent scale; use marginal predictions |

## Related

Perception is modelled separately: see the `hrd-psychophysics` skill for threshold,
slope and lapse rate. An effect can appear in perception with metacognition unchanged,
or the reverse, so do not treat one as a proxy for the other.
