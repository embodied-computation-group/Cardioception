---
name: hrd-psychophysics
description: Fit hierarchical Bayesian psychometric functions to Heart Rate Discrimination Task (HRD) data with brms, estimating interoceptive threshold (alpha), slope (beta) and lapse rate (lambda). Use when analysing HRD or Cardioception trial data, testing whether a group, condition, or covariate such as age affects interoceptive bias or precision, choosing priors, setting up a within- or between-subject design, or debugging a psychometric model that will not converge.
---

# HRD psychophysics

Fitting the psychometric function for the Heart Rate Discrimination Task, hierarchically,
in brms.

Reference implementation: <https://github.com/embodied-computation-group/Hierarchical-Interoception>
Paper: Courtin et al. (2026), *Behavior Research Methods*, <https://doi.org/10.3758/s13428-026-03137-3>

This skill supplies mechanics. Which conditions to compare, which participants to
exclude, and how to report are the user's decisions.

## Two things not to do

**Do not analyse `EstimatedThreshold` or `EstimatedSlope`.** Those columns are the Psi
staircase's own running estimates, a by-product of stimulus placement. They are a useful
sanity check on a session and nothing more. Feeding them into a t-test or a regression
discards the trial-level information and the uncertainty.

**Do not fit each subject separately and test the point estimates.** The staircase
concentrates trials near each participant's threshold, so individual slopes are poorly
constrained. Two-stage analysis treats those noisy estimates as if they were known.

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

| Parameter | Scale | Meaning |
|---|---|---|
| `alpha` | ΔBPM | Threshold: bias in the participant's belief about their own heart rate. Negative means they judge it slower than it is, which is the typical finding. |
| `beta` | log | Slope. `exp(beta)` is the inverse of the psychometric sigma, so **larger `beta` means better discrimination**. Watch the sign when interpreting. |
| `lambda` | logit | Lapse rate. `inv_logit(lambda)` is the proportion of trials answered independently of the stimulus. |

Report threshold and slope together. They answer different questions, and an effect on
one is not evidence about the other.

## Data shape

One row per subject × cell × intensity, aggregated binomially.

```r
model_df <- raw |>
  filter(Decision %in% c("More", "Less")) |>
  mutate(resp = as.integer(Decision == "More")) |>
  group_by(subj = Subject, condition = Modality, x = Alpha) |>
  summarise(y = sum(resp), n = dplyr::n(), .groups = "drop")
```

Verify the response coding rather than assuming it. `y` must count responses in the
direction that increases with `x`. If the psychometric curve comes out inverted, this is
why.

With a Psi staircase most intensities are visited once, so `n` is mostly 1. That is
expected. Do not bin `x` to make `n` larger: binning discards the stimulus placement the
staircase worked to achieve.

## Choosing the formula

The rule that matters: **a factor gets a random slope only if it varies within a
participant.**

| Design | `alpha` and `beta` formula |
|---|---|
| Single group | `~ 1 + (1 \| subj)` |
| Intero vs Extero, pre vs post, drug vs placebo | `~ condition + (condition \| subj)` |
| Patients vs controls, gender | `~ group + (1 \| subj)` |
| Age or a questionnaire score | `~ age_c + (1 \| subj)` |
| Covariate and group and a within-subject factor | `~ age_c + gender + condition + (condition \| subj)` |
| Group by condition interaction | `~ gender * condition + (condition \| subj)` |

`(gender | subj)` is a specification error: a participant has one gender, so there is no
within-subject variance to estimate. It shows up as divergences and `sd` parameters
pinned near zero, not as an error message.

Centre continuous covariates so the intercept means something:

```r
model_df$age_c <- model_df$age - mean(model_df$age, na.rm = TRUE)
```

Leave `lambda ~ 1 + (1 | subj)` unless lapse rate is itself the hypothesis.

## Priors

Use the normative priors. They are the main reason to use this toolbox rather than
rolling your own, and they matter most for the slope.

```r
priors <- c(
  set_prior("normal(-8.67, 11.23)", class = "b", nlpar = "alpha",  coef = "Intercept"),
  set_prior("normal(-2.3, 0.34)",   class = "b", nlpar = "beta",   coef = "Intercept"),
  set_prior("normal(-4.32, 1.96)",  class = "b", nlpar = "lambda"),
  set_prior("normal(11.23, 3.7)",   class = "sd", nlpar = "alpha",  group = "subj", lb = 0),
  set_prior("normal(0.34, 0.2)",    class = "sd", nlpar = "beta",   group = "subj", lb = 0),
  set_prior("normal(1.96, 0.19)",   class = "sd", nlpar = "lambda", group = "subj", lb = 0)
)
```

Every predictor needs its own prior, named by `coef`, centred on zero and scaled to the
population SD of that parameter:

```r
set_prior("normal(0, 11.23)", class = "b", nlpar = "alpha", coef = "genderMale"),
set_prior("normal(0, 0.34)",  class = "b", nlpar = "beta",  coef = "genderMale")
```

For a continuous covariate, scale by the population SD over the covariate's plausible
range, so the prior does not imply an enormous effect per year of age.

Always run `get_prior(bff, model_df)` and confirm nothing fell back to a flat default.

## Fitting

```r
fit <- brm(
  bff, data = model_df, prior = priors,
  chains = 4, cores = 4,
  warmup = 2000, iter = 4000,
  control = list(adapt_delta = 0.9, max_treedepth = 10),
  backend = "cmdstanr", seed = 12345,
  file = "fit_hrd"
)
```

**These fits take hours.** Tens of subjects is tens of minutes; several hundred with
covariates runs overnight. Always set `file` so a fit is cached and never repeated by
accident. Develop on a subset of subjects first, and tell the user the expected runtime
before starting rather than leaving them watching a blank console. On a cluster, submit
it; do not run it on a login node.

## Checking, in order

1. **Divergent transitions.** Any at all means the posterior is not being explored.
   Raise `adapt_delta` to 0.95 or 0.99. If divergences persist, suspect the formula
   before the sampler, and check for a random slope on a between-subject factor.
2. **`rhat < 1.01`**, bulk and tail ESS in the hundreds at minimum.
3. **`pp_check(fit, type = "bars")`**, plus predicted curves against observed
   proportions for a handful of individual subjects.
4. Only then read coefficients.

Report posterior means with credible intervals. For a directional claim, give the
posterior probability rather than whether an interval excludes zero:

```r
hypothesis(fit, "alpha_genderMale > 0")
mean(brms::as_draws_df(fit)$b_alpha_genderMale > 0)
```

## Common problems

| Symptom | Likely cause |
|---|---|
| Divergences, `sd` near zero | Random slope on a between-subject factor |
| Slopes implausibly wide | A predictor with no prior; check `get_prior()` |
| Threshold effect disappears when the slope gets the same predictor | It was a slope effect all along |
| Curve runs backwards | Response coding inverted in the aggregation step |
| Treedepth warnings, very slow | Data not aggregated, or `max_treedepth` too low |
| Intercept nonsensical | Uncentred continuous covariate |

## Confidence ratings

Out of scope here. Confidence is modelled separately: see the `hrd-metacognition`
skill.
