---
name: hrd-brms
description: Parameterize and fit hierarchical psychometric models to Heart Rate Discrimination Task (HRD) data using brms and the Hierarchical Interoception toolbox. Use when someone wants to analyse HRD or Cardioception output, test an effect on interoceptive threshold or slope, choose priors, set up a within- or between-subject design, or debug a psychometric model that will not converge.
---

# Fitting HRD data with brms

The Heart Rate Discrimination Task gives, per participant and condition, a psychometric
function over stimulus intensity. Fit it hierarchically. Do not compute per-subject
point estimates and run a t-test on them, and do not use the online Psi estimates
(`EstimatedThreshold`, `EstimatedSlope`) as your dependent variable: those are a
by-product of the staircase, not an analysis.

Reference implementation: <https://github.com/embodied-computation-group/Hierarchical-Interoception>
Paper: Courtin et al. (2026), *Behavior Research Methods*, <https://doi.org/10.3758/s13428-026-03137-3>

## The model

```r
library(brms)

inv_logit <- function(x) 1 / (1 + exp(-x))

bff <- bf(
  y | trials(n) ~ inv_logit(lambda) / 2 +
    (1 - inv_logit(lambda)) * (0.5 + 0.5 * erf(exp(beta) * (x - alpha) / sqrt(2))),
  alpha  ~ 1 + (1 | subj),
  beta   ~ 1 + (1 | subj),
  lambda ~ 1 + (1 | subj),
  nl = TRUE,
  family = binomial(link = "identity")
)
```

Three parameters, and they mean different things. Never put an effect only on `alpha`
because it is the one you have a hypothesis about; report both.

| Parameter | Scale | Interpretation |
|---|---|---|
| `alpha` | ΔBPM, unbounded | Threshold. Bias in what the participant believes their heart rate to be. Negative means they judge their heart as slower than it is. |
| `beta` | log | Slope. `exp(beta)` is the inverse of the psychometric sigma, so **larger `beta` is better discrimination**. Report on the log scale or transform consistently. |
| `lambda` | logit | Lapse rate. `inv_logit(lambda)` is the proportion of trials answered independently of the stimulus. |

## Data shape

The model wants aggregated binomial data: one row per subject × cell × intensity.

```r
model_df <- raw |>
  filter(Decision %in% c("More", "Less")) |>
  mutate(resp = as.integer(Decision == "More")) |>
  group_by(subj = Subject, condition = Modality, x = Alpha) |>
  summarise(y = sum(resp), n = n(), .groups = "drop")
```

With a Psi staircase most intensities are visited once, so `n` is usually 1. That is
fine and is not a reason to bin `x`; binning throws away stimulus placement.

## Choosing the formula for a design

This is where these models are most often specified wrongly. The rule: **a factor gets
a random slope only if it varies within a participant.**

| Design | Formula for `alpha` and `beta` |
|---|---|
| Single group | `~ 1 + (1 \| subj)` |
| Intero vs Extero, or pre vs post, or drug vs placebo | `~ condition + (condition \| subj)` |
| Patients vs controls, or gender | `~ group + (1 \| subj)` |
| Age, or any questionnaire score | `~ age_c + (1 \| subj)` |
| Age and gender together, within-subject condition too | `~ age_c + gender + condition + (condition \| subj)` |
| Interaction with a within-subject factor | `~ gender * condition + (condition \| subj)` |

Between-subject variables (gender, group, age) take `(1 | subj)`, never
`(gender | subj)`: a participant has one gender, so there is no within-subject
variance for the model to estimate and it will not identify.

Always centre continuous covariates, so the intercept stays interpretable as the
value at the sample mean rather than at age zero:

```r
model_df$age_c <- model_df$age - mean(model_df$age)
```

`lambda` normally stays `~ 1 + (1 | subj)`. Only give it predictors if lapse rate is
itself the hypothesis.

## Priors

Use the normative priors from the paper. They are the main reason to use this toolbox
rather than writing the model yourself, and they matter most for the slope, which the
staircase leaves poorly constrained.

```r
priors <- c(
  set_prior("normal(-8.67, 11.23)", class = "b", nlpar = "alpha", coef = "Intercept"),
  set_prior("normal(-2.3, 0.34)",   class = "b", nlpar = "beta",  coef = "Intercept"),
  set_prior("normal(-4.32, 1.96)",  class = "b", nlpar = "lambda"),

  set_prior("normal(11.23, 3.7)", class = "sd", nlpar = "alpha",  group = "subj", lb = 0),
  set_prior("normal(0.34, 0.2)",  class = "sd", nlpar = "beta",   group = "subj", lb = 0),
  set_prior("normal(1.96, 0.19)", class = "sd", nlpar = "lambda", group = "subj", lb = 0)
)
```

Every predictor you add needs its own prior, named by `coef`. Centre the effect on
zero, and scale it to the population SD of that parameter:

```r
set_prior("normal(0, 11.23)", class = "b", nlpar = "alpha", coef = "genderMale")
set_prior("normal(0, 0.34)",  class = "b", nlpar = "beta",  coef = "genderMale")
```

For a continuous covariate, scale by the population SD divided by the covariate's
plausible range, so the prior does not imply an implausibly large effect per unit.
Check what you have specified with `get_prior(bff, model_df)` and confirm nothing
silently fell back to a flat default.

## Fitting

```r
fit <- brm(
  bff, data = model_df,
  prior = priors,
  chains = 4, cores = 4,
  warmup = 2000, iter = 4000,
  control = list(adapt_delta = 0.9, max_treedepth = 10),
  backend = "cmdstanr", seed = 12345,
  file = "fit_hrd"   # cache: never refit by accident
)
```

**Runtime is hours, not minutes.** A few dozen subjects takes tens of minutes; several
hundred subjects with covariates runs overnight. Always set `file` so the fit is cached,
and develop the pipeline on a subset of subjects before launching the full model. Tell
the user the expected runtime before starting a fit rather than leaving them watching a
blank console.

## Checking the fit

In order:

1. Divergent transitions. Any at all means the posterior is not being explored properly.
   Raise `adapt_delta` to 0.95 or 0.99 before believing anything.
2. `rhat < 1.01` and bulk/tail ESS in the hundreds at least, via `summary(fit)`.
3. `pp_check(fit, type = "bars")` for the aggregated fit, and predicted curves against
   observed proportions per subject for a handful of participants.
4. Only then read the coefficients.

Report posterior means with credible intervals. For a directional claim, use the
posterior probability rather than a threshold on the interval:

```r
hypothesis(fit, "alpha_genderMale > 0")
mean(as_draws_df(fit)$b_alpha_genderMale > 0)
```

## Common problems

| Symptom | Cause |
|---|---|
| Divergences, or `sd` parameters pinned near zero | Random slope on a between-subject factor. Drop it to `(1 \| subj)`. |
| Slope estimates implausibly wide | Priors not set, or a predictor missing a prior. Run `get_prior()`. |
| Effect on threshold vanishes when slope gets the same predictor | The original effect was slope, misattributed. Keep both. |
| Fit takes forever, treedepth warnings | Data not aggregated, or `max_treedepth` too low. |
| Intercept is nonsense | Uncentred continuous covariate. |

## Confidence ratings

Confidence is a 0-100 slider with mass at both bounds, so it is not a job for this
model or for the m-ratio. Use ordered beta regression:

```r
library(ordbetareg)
data$Confidence <- data$Confidence / 100  # keep exact 0 and 1

fit_conf <- ordbetareg(
  bf(Confidence ~ ResponseCorrect * condition + (ResponseCorrect * condition | subj)),
  data = data, chains = 4, cores = 4
)
```

The coefficient on `ResponseCorrect` is metacognitive sensitivity: how much higher
confidence runs on correct trials. The m-ratio is a poor fit here because an adaptive
staircase pins type-1 sensitivity by design, so dividing by it is not meaningful.
