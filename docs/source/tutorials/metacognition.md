# Metacognition

Modelling the confidence rating collected on every trial, and asking whether
confidence tracks accuracy.

Perception and metacognition are different questions. A participant can
discriminate their heart rate well while having no idea when they are right, and
the reverse happens too. An effect can appear in one with the other unchanged, so
neither is a proxy for the other.

## What the ratings look like

Confidence is a slider from 0 to 100, and people use both ends in earnest. In the
example data, 15% of trials sit exactly on a bound.

![Distribution of confidence ratings](../images/confidence_distribution.png)

That shape rules out the obvious models. A Gaussian puts probability outside the
scale. A beta likelihood is undefined at exactly 0 and 1, so it forces you to
nudge the bounds inward by some epsilon or drop those trials, and the trials you
would drop are the most and least confident ones. Binning into a Likert scale
throws away information and makes the answer depend on where you cut.

## Why not the m-ratio

The m-ratio, meta-d′ divided by d′, is the usual summary of metacognitive
efficiency. We no longer recommend it for the HRD, for reasons that compound.

The staircase holds performance near a target accuracy **by construction**. That
means type-1 sensitivity is set largely by the procedure rather than by the
participant, and between-subject variance in d′ is compressed. Dividing by a
quantity the design has pinned down is hard to interpret, and the ratio becomes
unstable for anyone performing near chance.

Meta-d′ also assumes a stationary type-1 process, whereas an adaptive staircase
changes the stimulus from trial to trial deliberately. And the estimator wants
confidence in a handful of discrete bins, while the HRD records a continuous
rating.

None of this makes meta-d′ a bad measure in general. It makes it a poor fit for
this task.

## Ordered beta regression

Ordered beta regression models the interior of the scale with a beta likelihood
and the two bounds as separate outcomes, in one generative model. Nothing is
nudged and nothing is dropped
([Kubinec, 2023](https://doi.org/10.1017/pan.2022.20)).

```r
library(ordbetareg)

data <- data |>
  filter(Decision %in% c("More", "Less"), !is.na(Confidence), !is.na(ResponseCorrect)) |>
  mutate(
    Accuracy   = factor(ResponseCorrect, levels = c(0, 1),
                        labels = c("incorrect", "correct")),
    Confidence = Confidence / 100          # keep exact 0 and 1
  )

fit <- ordbetareg(
  formula = bf(Confidence ~ Accuracy + (Accuracy | Subject)),
  data = data,
  chains = 4, cores = 4,
  file = "fit_confidence"
)
```

`ordbetareg` wraps brms, so the formula syntax, priors and post-processing are all
the usual ones.

## The quantity of interest

The coefficient on `Accuracy` is how much higher confidence runs on correct trials
than incorrect ones. That is metacognitive sensitivity, stated directly rather
than as a ratio, and it needs no division by a staircase-determined d′.

Because the intercept absorbs overall confidence, sensitivity and bias stay
separate. You do not have to choose between "how confident are they" and "does
confidence track accuracy": the model gives both.

In the example data the raw gap is large and near-universal: mean confidence is
about 25 points higher on correct trials, and 99% of participants show a gap in
that direction.

## Testing a hypothesis about it

| Question | Formula |
|---|---|
| Does confidence track accuracy | `Confidence ~ Accuracy + (Accuracy \| Subject)` |
| Does that differ between conditions | `Confidence ~ Accuracy * Modality + (Accuracy * Modality \| Subject)` |
| Does it differ between groups | `Confidence ~ Accuracy * gender + (Accuracy \| Subject)` |
| Does it change with age | `Confidence ~ Accuracy * age_z + (Accuracy \| Subject)` |

The interaction is usually the actual hypothesis. "Group A had lower metacognitive
sensitivity" is a claim about `Accuracy × group`, not about `group`.

The random effects rule is the same as in the [hierarchical
model](hierarchical.md): a term gets a random slope only if it varies within a
participant. `Accuracy` and `Modality` do. `gender` and `age` do not.

## Reading the output

Coefficients are on the latent scale and are not slider points. For anything you
report, compute predictions on the response scale:

```r
library(marginaleffects)
avg_predictions(fit, by = "Accuracy")
avg_comparisons(fit, variables = "Accuracy")
```

## Checking

The usual diagnostics apply: no divergent transitions, `rhat < 1.01`, healthy ESS.

One check is specific to this model. The posterior predictive must reproduce the
**mass at 0 and 1**, not just the interior. Handling those bounds properly is the
entire reason for using ordered beta, so if `pp_check()` misses them, the model is
not doing the job you chose it for.

## Before you fit

Look at scale usage per participant. Someone who left the slider at one value all
session contributes nothing about metacognition, and the model will quietly absorb
them:

```r
data |> group_by(Subject) |> summarise(sd = sd(Confidence))
```

Decide explicitly whether to exclude them. Trials with no response have no
accuracy and must be dropped, never recoded as incorrect.
