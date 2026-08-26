# Hierarchical modelling

Fitting every participant in one model, and testing whether a covariate or a group
membership moves interoceptive bias or precision.

This is the tutorial most studies need. It assumes the
[psychophysical model](psychophysics.md) and the data preparation from
[inspecting and plotting data](inspecting-data.md).

## Why one model rather than many

The staircase gives each participant few trials far from their threshold, so
individual slopes are poorly constrained. Fitting separately and then testing the
point estimates treats a barely identified slope as if it were known exactly.

A hierarchical model draws each participant's parameters from a group
distribution. Participants with sparse data are pulled toward the group, those
with plenty are left alone, and the uncertainty travels through to the group-level
effects instead of being discarded halfway.

```r
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

## Adding your design

Predictors go on `alpha` and on `beta`, separately. Put them on both even when your
hypothesis concerns only one: an effect that looks like a threshold shift in a
threshold-only model can turn out to be a slope effect once both are free to move.

The rule that governs the random effects: **a term gets a random slope only if it
varies within a participant.**

| What you are testing | Formula for `alpha` and `beta` |
|---|---|
| Nothing, just the population | `~ 1 + (1 \| subj)` |
| Intero vs Extero, pre vs post, drug vs placebo | `~ condition + (condition \| subj)` |
| Patients vs controls, or gender | `~ group + (1 \| subj)` |
| Age, BMI, a questionnaire score | `~ age_z + (1 \| subj)` |
| A covariate and a group and a within-subject condition | `~ Modality + gender + age_z + bmi_z + (Modality \| subj)` |
| Whether an effect is specific to interoception | `~ Modality * gender + (Modality \| subj)` |

`(gender | subj)` is a specification error. A participant has one gender, so there
is no within-subject variance for the model to find. It does not raise an error: it
produces divergent transitions and group SDs pinned near zero, which is a much
worse way to discover the problem.

Centre continuous covariates, or the intercept becomes the threshold of a
participant aged zero:

```r
model_df$age_z <- as.numeric(scale(model_df$age))
model_df$bmi_z <- as.numeric(scale(model_df$bmi))
```

Scale them over participants, not over trials, or people with more trials pull the
mean.

## The worked model

The example study has both conditions, gender as a between-subject factor, and age
and BMI as subject-level covariates. All of it goes in one model, because covariates
only control for each other when they are fitted together:

```r
alpha ~ Modality * (gender + age_z) + bmi_z + (Modality | subj)
beta  ~ Modality * (gender + age_z) + bmi_z + (Modality | subj)
lambda ~ 1 + (1 | subj)
```

Reading that formula: `Modality` is within-subject and gets a random slope. `gender`
is between-subject and does not. `age_z` and `bmi_z` are subject-level covariates.
The `Modality` interactions ask the question that matters for an interoception
claim: does the effect appear specifically when judging one's own heart, or does it
show up in the auditory control condition too? An effect present in both is telling
you something about the task, not about interoception.

BMI enters as a main effect only. It is there as a control, not as a hypothesis.

## Priors

Every predictor needs its own prior. A prior naming a coefficient brms does not
generate is **silently ignored**, and that coefficient then samples under a flat
default. Check what you actually specified:

```r
get_prior(bff, model_df)
```

The intercept priors come from the population refit in
[Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3). Effect priors
are centred on zero and scaled to the between-subject SD of the parameter, with
narrower scales where a wide one would be implausible:

```r
set_prior("normal(0, 11.23)", class = "b", nlpar = "alpha", coef = "genderMale")
set_prior("normal(0, 5.62)",  class = "b", nlpar = "alpha", coef = "age_z")
set_prior("normal(0, 2.81)",  class = "b", nlpar = "alpha", coef = "ModalityIntero:genderMale")
```

The logic: a difference between two groups could plausibly be about as large as the
spread between individuals, so a binary contrast gets the full SD. A *per standard
deviation of age* effect that large would not be plausible, so it gets half. An
interaction is a difference of differences, so it gets less again.

Check the choice rather than trusting it. Sampling with the likelihood switched off
shows what the priors alone imply:

```r
fit_prior <- brm(bff, data = model_df, prior = priors, sample_prior = "only", ...)
```

If most of the prior mass puts thresholds outside the range of intensities the task
can present, the prior is asserting something the experiment could never show.

## Fitting

```r
fit <- brm(
  bff, data = model_df, prior = priors,
  chains = 4, cores = 4,
  warmup = 2000, iter = 4000,
  control = list(adapt_delta = 0.95, max_treedepth = 12),
  backend = "cmdstanr",
  file = "fit_hrd"
)
```

Set `file`. It caches the fit, so an accidental rerun does not resample for hours.

**Expect hours.** A few dozen participants is tens of minutes; several hundred with
covariates is an overnight job. Develop the pipeline on a handful of participants
with short chains first, confirm it runs end to end, and only then start the real
fit.

## Checking, in this order

1. **Divergent transitions.** Any at all means the sampler is not exploring the
   posterior properly. Raise `adapt_delta` to 0.99. If they persist, look at the
   formula before the sampler, and check for a random slope on a between-subject
   term.
2. **`rhat < 1.01`**, with bulk and tail ESS in the hundreds at least.
3. **Posterior predictive checks**, and predicted curves against observed
   proportions for a few individual participants.
4. Only then read the coefficients.

## Reporting

Give posterior means with credible intervals. For a directional claim, the
posterior probability is more informative than whether an interval excludes zero:

```r
hypothesis(fit, "alpha_genderMale > 0")
mean(as_draws_df(fit)$b_alpha_genderMale > 0)
```

Report threshold and slope together, and say which condition an effect appeared in.
"Gender affected interoceptive bias" means something quite different depending on
whether the same difference showed up in the auditory control.
