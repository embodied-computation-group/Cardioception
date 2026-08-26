# Model definitions for the HRD tutorial fits.
#
# Sourced by 01_fit.R and 02_summarise.R so that a formula is written once and
# the summary step cannot drift from what was fitted.
#
# The psychometric form and the normative priors come from the Hierarchical
# Interoception toolbox (Courtin et al., 2026, Behavior Research Methods,
# doi:10.3758/s13428-026-03137-3).

suppressPackageStartupMessages({
  library(brms)
})

inv_logit <- function(x) 1 / (1 + exp(-x))

# Stan provides erf(); R does not. brms compiles the non-linear formula for
# sampling, so fitting works without this, but posterior_epred() evaluates the
# same expression in R and fails at post-processing time without it.
erf <- function(x) 2 * pnorm(x * sqrt(2)) - 1

# Population values from the normative refit (Fit population.R in the toolbox).
# SD_* are the between-subject SDs; SE_* are the standard errors of the
# population estimates, which the toolbox widens tenfold for the group-level SD
# priors. Kept as expressions rather than products so the intent stays visible.
SD_ALPHA <- 11.23   # threshold, dBPM
SD_BETA <- 0.34     # log slope
SE_ALPHA <- 0.37
SE_BETA <- 0.02

# How wide a prior an effect gets depends on what kind of effect it is.
#
#   binary contrast   the toolbox's own choice: a group difference could
#                     plausibly be as large as the between-subject SD
#   continuous (z)    a *per SD of the covariate* effect that large would be
#                     implausible, so halve it. age and bmi are z-scored in
#                     00_prepare.R, so these are per-SD effects
#   interaction       a difference of differences, tighter again
PRIOR_SCALE <- function(coef, sd_pop) {
  if (grepl(":", coef, fixed = TRUE)) return(sd_pop / 4)   # interaction
  if (grepl("_z$", coef)) return(sd_pop / 2)               # continuous covariate
  sd_pop                                                    # binary contrast
}

# --- psychometric function -------------------------------------------------
# y successes out of n trials at intensity x.
#   alpha  threshold in dBPM (negative = judges own heart as slower than it is)
#   beta   log slope; exp(beta) is 1/sigma, so larger beta = better discrimination
#   lambda lapse rate on the logit scale
psychometric_rhs <- paste(
  "y | trials(n) ~ inv_logit(lambda) / 2 +",
  "(1 - inv_logit(lambda)) * (0.5 + 0.5 * erf(exp(beta) * (x - alpha) / sqrt(2)))"
)

make_psychometric_bf <- function(predictors, group_terms) {
  bf(
    as.formula(psychometric_rhs),
    as.formula(paste("alpha ~", predictors, "+", group_terms)),
    as.formula(paste("beta ~", predictors, "+", group_terms)),
    lambda ~ 1 + (1 | subj),
    nl = TRUE,
    family = binomial(link = "identity")
  )
}

# Priors: intercepts from the normative values, every effect centred on zero and
# scaled to the population SD of that parameter. Continuous covariates are
# z-scored in 00_prepare.R, so their priors are per SD of the covariate.
psychometric_priors <- function(effect_coefs) {
  p <- c(
    set_prior("normal(-8.67, 11.23)", class = "b", nlpar = "alpha", coef = "Intercept"),
    set_prior("normal(-2.3, 0.34)", class = "b", nlpar = "beta", coef = "Intercept"),
    set_prior("normal(-4.32, 1.96)", class = "b", nlpar = "lambda"),
    set_prior(sprintf("normal(%s, %s)", SD_ALPHA, SE_ALPHA * 10),
              class = "sd", nlpar = "alpha", group = "subj", lb = 0),
    set_prior(sprintf("normal(%s, %s)", SD_BETA, SE_BETA * 10),
              class = "sd", nlpar = "beta", group = "subj", lb = 0),
    set_prior("normal(1.96, 0.19)", class = "sd", nlpar = "lambda", group = "subj", lb = 0)
  )
  for (co in effect_coefs) {
    p <- c(
      p,
      set_prior(sprintf("normal(0, %s)", PRIOR_SCALE(co, SD_ALPHA)),
                class = "b", nlpar = "alpha", coef = co),
      set_prior(sprintf("normal(0, %s)", PRIOR_SCALE(co, SD_BETA)),
                class = "b", nlpar = "beta", coef = co)
    )
  }
  p
}

# --- the models ------------------------------------------------------------
# Each entry: what to fit, and which data frame it needs. `effect_coefs` must
# match the coefficient names brms generates; 01_fit.R verifies this against
# get_prior() before sampling and fails loudly on a mismatch.
MODELS <- list(

  # 1. The simplest useful case: one condition, one group. Tutorial section 1.
  psy_intero = list(
    kind = "psychometric",
    data = "intero",
    formula = make_psychometric_bf("1", "(1 | subj)"),
    effect_coefs = character(0),
    description = "Intero only, no predictors"
  ),

  # 2. Main effects only. Shown against psy_full so the tutorial can make the
  #    point that an interaction changes what the main effect means.
  psy_main = list(
    kind = "psychometric",
    data = "both",
    formula = make_psychometric_bf(
      "1 + Modality + gender + age_z + bmi_z", "(Modality | subj)"
    ),
    effect_coefs = c("ModalityIntero", "genderMale", "age_z", "bmi_z"),
    description = "Modality, gender, age and BMI as main effects"
  ),

  # 3. The full model. Modality interacts with gender and age, so the tutorial
  #    can ask whether an effect is specific to interoception or also present
  #    in the auditory control condition. BMI stays a main-effect control.
  psy_full = list(
    kind = "psychometric",
    data = "both",
    formula = make_psychometric_bf(
      "1 + Modality * (gender + age_z) + bmi_z", "(Modality | subj)"
    ),
    effect_coefs = c(
      "ModalityIntero", "genderMale", "age_z", "bmi_z",
      "ModalityIntero:genderMale", "ModalityIntero:age_z"
    ),
    description = "Modality by gender and age, BMI controlled"
  ),

  # 4. Confidence. Ordered beta regression: the rating is bounded at 0 and 1
  #    with real mass at both ends, so neither Gaussian nor beta will do.
  meta_full = list(
    kind = "ordbeta",
    data = "trials",
    formula = bf(
      Confidence ~ Accuracy * (Modality + gender + age_z) + bmi_z +
        (Accuracy * Modality | subj)
    ),
    effect_coefs = character(0),
    description = "Confidence by accuracy, modality, gender and age"
  )
)
