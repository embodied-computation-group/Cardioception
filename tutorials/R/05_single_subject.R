# Fit the single-participant example used at the end of the psychophysics tutorial.
#
# Run from the repository root:
#
#   Rscript tutorials/R/05_single_subject.R
#
# The full brmsfit is cached under tutorials/results/ and ignored by git. Only the
# compact draws, curve summaries, observations, and diagnostics under
# tutorials/results/small/ are intended for version control.

suppressPackageStartupMessages({
  library(brms)
  library(cmdstanr)
  library(dplyr)
  library(posterior)
  library(readr)
})

cmd <- commandArgs(trailingOnly = FALSE)
script_arg <- sub("^--file=", "", grep("^--file=", cmd, value = TRUE))
if (length(script_arg) != 1) stop("could not determine the script path")
repo_root <- normalizePath(file.path(dirname(script_arg), "..", ".."))

data_path <- file.path(
  repo_root, "docs", "source", "examples", "templates", "data", "HRD",
  "HRD_final.txt"
)
out_dir <- file.path(repo_root, "tutorials", "results")
small_dir <- file.path(out_dir, "small")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(small_dir, showWarnings = FALSE, recursive = TRUE)

raw <- read_csv(data_path, show_col_types = FALSE)

# Catch trials did not update Psi, but they are valid observations and are useful
# for the offline fit because they sample the tails of the response function.
trials <- raw |>
  filter(
    Modality == "Intero",
    Decision %in% c("More", "Less"),
    !is.na(Alpha)
  ) |>
  mutate(
    x = Alpha,
    resp = as.integer(Decision == "More")
  )

model_df <- trials |>
  group_by(x) |>
  summarise(y = sum(resp), n = dplyr::n(), .groups = "drop")

message(sprintf(
  "single participant: %d trials at %d unique intensities",
  nrow(trials), nrow(model_df)
))

inv_logit <- function(x) 1 / (1 + exp(-x))
erf <- function(x) 2 * pnorm(x * sqrt(2)) - 1

bff <- bf(
  y | trials(n) ~ inv_logit(lambda) / 2 +
    (1 - inv_logit(lambda)) *
      (0.5 + 0.5 * erf(exp(beta) * (x - alpha) / sqrt(2))),
  alpha ~ 1,
  beta ~ 1,
  lambda ~ 1,
  nl = TRUE,
  family = binomial(link = "identity")
)

priors <- c(
  set_prior(
    "normal(-8.67, 11.23)",
    class = "b", nlpar = "alpha", coef = "Intercept"
  ),
  set_prior(
    "normal(-2.3, 0.34)",
    class = "b", nlpar = "beta", coef = "Intercept"
  ),
  set_prior(
    "normal(-4.32, 1.96)",
    class = "b", nlpar = "lambda", coef = "Intercept"
  )
)

expected <- get_prior(bff, data = model_df)
expected_b <- expected |>
  filter(class == "b", coef == "Intercept") |>
  select(nlpar, coef)
specified_b <- data.frame(
  nlpar = c("alpha", "beta", "lambda"),
  coef = "Intercept"
)
stopifnot(nrow(anti_join(specified_b, expected_b, by = c("nlpar", "coef"))) == 0)

fit_path <- file.path(out_dir, "psy_single_subject")
fit <- brm(
  bff,
  data = model_df,
  prior = priors,
  sample_prior = "yes",
  chains = 4,
  cores = 4,
  warmup = 1000,
  iter = 3000,
  control = list(adapt_delta = 0.95, max_treedepth = 12),
  backend = "cmdstanr",
  seed = 5102,
  file = fit_path,
  file_refit = "on_change",
  refresh = 250
)

draws <- as_draws_df(fit)
required <- c(
  "b_alpha_Intercept", "b_beta_Intercept", "b_lambda_Intercept",
  "prior_b_alpha_Intercept", "prior_b_beta_Intercept",
  "prior_b_lambda_Intercept", ".chain", ".iteration", ".draw"
)
missing <- setdiff(required, colnames(draws))
if (length(missing)) {
  stop("fit is missing expected draws: ", paste(missing, collapse = ", "))
}

compact <- as.data.frame(draws[, required]) |>
  transmute(
    chain = .chain,
    iteration = .iteration,
    draw = .draw,
    alpha = b_alpha_Intercept,
    beta = b_beta_Intercept,
    sigma = exp(-b_beta_Intercept),
    lapse = plogis(b_lambda_Intercept),
    prior_alpha = prior_b_alpha_Intercept,
    prior_beta = prior_b_beta_Intercept,
    prior_sigma = exp(-prior_b_beta_Intercept),
    prior_lapse = plogis(prior_b_lambda_Intercept)
  )

write_csv(
  compact,
  file.path(small_dir, "psy_single_subject_draws.csv.gz")
)

curve_x <- seq(-50.5, 50.5, by = 0.25)
curve_matrix <- vapply(curve_x, function(x) {
  compact$lapse / 2 +
    (1 - compact$lapse) * pnorm((x - compact$alpha) / compact$sigma)
}, numeric(nrow(compact)))
curve <- data.frame(
  x = curve_x,
  q2.5 = apply(curve_matrix, 2, quantile, 0.025),
  q10 = apply(curve_matrix, 2, quantile, 0.10),
  q25 = apply(curve_matrix, 2, quantile, 0.25),
  median = apply(curve_matrix, 2, median),
  q75 = apply(curve_matrix, 2, quantile, 0.75),
  q90 = apply(curve_matrix, 2, quantile, 0.90),
  q97.5 = apply(curve_matrix, 2, quantile, 0.975)
)
write_csv(curve, file.path(small_dir, "psy_single_subject_curve.csv.gz"))

observed <- model_df |>
  mutate(proportion = y / n)
write_csv(observed, file.path(small_dir, "psy_single_subject_data.csv.gz"))

parameter_summary <- compact |>
  select(alpha, beta, sigma, lapse) |>
  tidyr::pivot_longer(everything(), names_to = "parameter", values_to = "value") |>
  group_by(parameter) |>
  summarise(
    mean = mean(value),
    sd = sd(value),
    q2.5 = quantile(value, 0.025),
    median = median(value),
    q97.5 = quantile(value, 0.975),
    .groups = "drop"
  )
write_csv(
  parameter_summary,
  file.path(small_dir, "psy_single_subject_summary.csv")
)

np <- nuts_params(fit)
draw_summary <- summarise_draws(as_draws_array(fit))
energy <- np |>
  filter(Parameter == "energy__") |>
  group_by(Chain) |>
  summarise(ebfmi = mean(diff(Value)^2) / var(Value), .groups = "drop")
diagnostics <- data.frame(
  trials = nrow(trials),
  unique_intensities = nrow(model_df),
  divergences = sum(np$Value[np$Parameter == "divergent__"]),
  max_treedepth = max(np$Value[np$Parameter == "treedepth__"]),
  max_rhat = max(draw_summary$rhat, na.rm = TRUE),
  min_ess_bulk = min(draw_summary$ess_bulk, na.rm = TRUE),
  min_ess_tail = min(draw_summary$ess_tail, na.rm = TRUE),
  min_ebfmi = min(energy$ebfmi)
)
write_csv(
  diagnostics,
  file.path(small_dir, "psy_single_subject_diagnostics.csv")
)

print(parameter_summary)
print(diagnostics)
message("wrote compact single-subject artefacts to ", small_dir)
