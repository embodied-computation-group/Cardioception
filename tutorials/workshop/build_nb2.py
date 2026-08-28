"""Build the hands-on R analysis notebook (parts 4-6)."""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: c.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# The Heart Rate Discrimination task — 2. Inspecting, fitting, and modelling

**Continues from `01_running_the_hrd.ipynb`.** You should have a session of your own in
`workshop/data/`. If you do not, every cell below falls back to a bundled example
session, so you can still follow along.

By the end you will have:

1. **inspected** a session properly, and know which checks would make you exclude it;
2. **fitted the psychometric model** to your volunteer, with priors, diagnostics and posterior uncertainty;
3. seen the **hierarchical group model** across 512 participants, and what it says that a single fit cannot.

---

**Kernel:** `R (cardioception)`. Change it in the top right if it is not selected.

### Why R for this half

The models in the Cardioception tutorials are `brms` models, built on the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception)
(Courtin et al., 2026). Every number in the published tutorials came out of that R
pipeline, and there is no maintained Python equivalent for these models. Data
collection is Python; modelling is R.
""")

co(r"""
suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readr); library(ggplot2)
  library(brms);  library(posterior); library(patchwork)
})

options(repr.plot.width = 10, repr.plot.height = 4.5, mc.cores = 4)
theme_set(theme_minimal(base_size = 12) +
          theme(panel.grid.minor = element_blank(),
                plot.title = element_text(face = "bold", size = 11)))

NAVY <- "#1F3352"; RED <- "#A8455F"; BLUE <- "#2F6F8F"; GREY <- "#a4acb8"; GOLD <- "#D49A45"
MODALITY_COLOURS <- c(Intero = RED, Extero = BLUE)

# Paths. Walk up to the repository root so this works wherever the notebook sits.
find_repo <- function(start = getwd()) {
  p <- normalizePath(start, mustWork = FALSE)
  repeat {
    if (file.exists(file.path(p, "setup.py")) && dir.exists(file.path(p, "docs"))) return(p)
    parent <- dirname(p)
    if (parent == p) return(normalizePath(start))
    p <- parent
  }
}
REPO      <- find_repo()
DATA_DIR  <- file.path(getwd(), "data")
EXAMPLE   <- file.path(REPO, "docs/source/examples/templates/data/HRD/HRD_final.txt")
SMALL     <- file.path(REPO, "tutorials/results/small")

cat("brms", as.character(packageVersion("brms")),
    "| cmdstan", tryCatch(as.character(cmdstanr::cmdstan_version()), error = function(e) "NOT FOUND"), "\n")
cat("artefacts:", ifelse(dir.exists(SMALL), "found", "MISSING"), "\n")
""")

# ----------------------------------------------------------------- Part 4
md(r"""
---
## Part 4 — Inspect the session before you model it

Fitting a model to a session you have not looked at is how bad data becomes a
published number. The checks below take two minutes and are the difference between
an exclusion you can defend and one you cannot.

### What the task wrote

| File | Contents |
|---|---|
| `<participant><session>.txt` | **The trial table.** One row per trial |
| `<participant>_signal.txt` | Full PPG trace |
| `Intero_posterior.npy` | Joint Psi posterior after each adaptive trial |
| `*.pickle` | The complete parameter set used |

### The columns that matter

| Column | Meaning |
|---|---|
| `Modality` | `Intero` (cardiac) or `Extero` (auditory control) |
| `Alpha` | **The stimulus, in ΔBPM.** This is $x$ in the model |
| `Decision` | `More` (faster) or `Less` (slower). This is $y$ |
| `Confidence` | 0–100 visual analogue rating |
| `ResponseCorrect` | Whether the decision matched the sign of `Alpha` |
| `DecisionProvided` | `FALSE` if they ran out of time — **check this** |
| `listenBPM` | Measured heart rate during the listening window |
| `TrialType` | `psi` (adaptive) or a catch trial |
| `EstimatedThreshold` / `EstimatedSlope` | Psi's running online estimates |
""")

co(r"""
# Load your volunteer's session if it exists; otherwise the bundled example.
own <- list.files(DATA_DIR, pattern = "\\.txt$", full.names = TRUE, recursive = TRUE)
own <- own[!grepl("signal|ppg", basename(own))]

if (length(own) > 0) {
  session_path <- own[1]
  SOURCE <- "your volunteer"
} else {
  session_path <- EXAMPLE
  SOURCE <- "the bundled example (no session of your own found)"
}

trials <- read_csv(session_path, show_col_types = FALSE)

cat("Reading", SOURCE, "\n ", session_path, "\n\n")
cat(nrow(trials), "trials,", ncol(trials), "columns\n")
cat("Modalities:", paste(unique(trials$Modality), collapse = ", "), "\n\n")

trials |>
  select(any_of(c("Modality","TrialType","Alpha","Decision","Confidence",
                  "ResponseCorrect","listenBPM"))) |>
  head(8) |>
  as.data.frame() |>
  print(row.names = FALSE)
""")

md(r"""
### Did the session actually complete?

Three questions, in order of how often they matter:

1. **Missing responses.** A participant who timed out on many trials was not doing the
   task. A handful is normal; a run of them is not.
2. **Heart rate plausibility.** `listenBPM` outside roughly 40–120 usually means the
   sensor slipped, not that the heart did something interesting.
3. **Did Psi converge?** If the online threshold estimate is still wandering at the end,
   the session was too short or the responses too noisy.
""")

co(r"""
qc <- trials |>
  group_by(Modality) |>
  summarise(
    n            = n(),
    missed       = sum(!DecisionProvided, na.rm = TRUE),
    no_rating    = if ("RatingProvided" %in% names(trials)) sum(!RatingProvided, na.rm = TRUE) else NA_integer_,
    accuracy     = mean(ResponseCorrect, na.rm = TRUE),
    median_bpm   = median(listenBPM, na.rm = TRUE),
    bpm_range    = sprintf("%.0f - %.0f", min(listenBPM, na.rm = TRUE), max(listenBPM, na.rm = TRUE)),
    median_rt    = round(median(DecisionRT, na.rm = TRUE), 2),
    .groups = "drop"
  )
print(as.data.frame(qc), row.names = FALSE)

cat("\n--- flags ---\n")
miss_rate <- sum(!trials$DecisionProvided, na.rm = TRUE) / nrow(trials)
if (miss_rate > 0.10) cat(sprintf("[!] %.0f%% of trials had no decision. Investigate before modelling.\n", 100 * miss_rate))
if (any(trials$listenBPM < 40 | trials$listenBPM > 120, na.rm = TRUE))
  cat("[!] Heart rate outside 40-120 BPM on some trials - check the sensor trace.\n")
if (miss_rate <= 0.10 && !any(trials$listenBPM < 40 | trials$listenBPM > 120, na.rm = TRUE))
  cat("No flags raised.\n")

cat("\nNote: accuracy is reported here only as a data-quality signal.\n")
cat("It is NOT the quantity we model - see notebook 1, Part 0.\n")
""")

md(r"""
### The stimulus trace: watch Psi work

This is the single most informative plot for a session. Each point is one trial's
stimulus intensity, in the order presented. The line is Psi's running threshold
estimate.

A healthy session **funnels**: wide swings early while Psi is uncertain, converging to a
narrow band around the participant's threshold. A session that never settles, or that
pins to the ±50 edge of the grid, is telling you something went wrong.
""")

co(r"""
p_trace <- trials |>
  mutate(trial = row_number()) |>
  ggplot(aes(trial, Alpha, colour = Modality)) +
  geom_hline(yintercept = 0, colour = GREY, linetype = "dotted") +
  geom_line(aes(y = EstimatedThreshold, group = Modality), linewidth = 0.9, alpha = 0.85) +
  geom_point(aes(shape = Decision), size = 2.2, alpha = 0.85) +
  scale_colour_manual(values = MODALITY_COLOURS) +
  labs(title = "Stimulus intensity by trial, with Psi's running threshold estimate",
       x = "Trial", y = expression(Delta*"BPM"),
       subtitle = "Points = the stimulus played. Line = Psi's belief about the threshold.")

p_hist <- trials |>
  ggplot(aes(Alpha, fill = Modality)) +
  geom_histogram(bins = 20, alpha = 0.8, position = "identity") +
  scale_fill_manual(values = MODALITY_COLOURS) +
  geom_vline(xintercept = 0, colour = GREY, linetype = "dotted") +
  labs(title = "Where the trials were spent", x = expression(Delta*"BPM"), y = "Trials")

options(repr.plot.width = 12, repr.plot.height = 4)
p_trace + p_hist + plot_layout(widths = c(2, 1), guides = "collect")
""")

md(r"""
### Choices against stimulus intensity

Now the quantity the model actually fits: the proportion of "faster" responses as a
function of ΔBPM. Bin the trials and plot the proportions with point size showing how
many trials fell in each bin.

This is the raw material of the psychometric function. You should be able to see the
sigmoid by eye — and roughly where it crosses 50%, which is the threshold the model
will estimate formally.
""")

co(r"""
binned <- trials |>
  filter(Decision %in% c("More", "Less"), !is.na(Alpha)) |>
  mutate(resp = as.integer(Decision == "More"),
         bin  = cut(Alpha, breaks = seq(-52, 52, by = 8), include.lowest = TRUE)) |>
  group_by(Modality, bin) |>
  summarise(x = mean(Alpha), p = mean(resp), n = n(), .groups = "drop")

ggplot(binned, aes(x, p, colour = Modality, size = n)) +
  geom_hline(yintercept = 0.5, colour = GREY, linetype = "dotted") +
  geom_vline(xintercept = 0, colour = GREY, linetype = "dotted") +
  geom_point(alpha = 0.8) +
  scale_colour_manual(values = MODALITY_COLOURS) +
  scale_size_continuous(range = c(2, 8)) +
  coord_cartesian(ylim = c(0, 1)) +
  labs(title = 'Proportion of "faster" responses by stimulus intensity',
       subtitle = "The sigmoid the model will fit. Where it crosses 0.5 is the threshold.",
       x = expression(Delta*"BPM"), y = 'P("faster")', size = "trials")
""")

md(r"""
### Confidence and response times

Two more checks worth making before modelling.

**Confidence** should use a reasonable spread of the 0–100 scale. A participant who
answered 50 on every trial, or who used only the top of the scale, is not giving you a
usable metacognitive signal. Note also that the HRD records confidence as a *continuous*
VAS, which matters later: models like `hmetad` need discrete bins, and how you cut a
continuous scale determines what the type-2 criteria can express.

**Response times** flag disengagement. A cluster of very fast responses usually means
button-mashing rather than judging.
""")

co(r"""
p_conf <- trials |>
  filter(!is.na(Confidence)) |>
  ggplot(aes(Confidence, fill = Modality)) +
  geom_histogram(bins = 20, alpha = 0.8, position = "identity") +
  scale_fill_manual(values = MODALITY_COLOURS) +
  labs(title = "Confidence ratings", x = "Confidence (0-100 VAS)", y = "Trials")

p_conf_acc <- trials |>
  filter(!is.na(Confidence), !is.na(ResponseCorrect)) |>
  mutate(Accuracy = ifelse(ResponseCorrect == 1, "correct", "incorrect")) |>
  ggplot(aes(Accuracy, Confidence, fill = Accuracy)) +
  geom_boxplot(alpha = 0.75, outlier.alpha = 0.4, width = 0.55) +
  scale_fill_manual(values = c(correct = BLUE, incorrect = RED), guide = "none") +
  labs(title = "Confidence by accuracy",
       subtitle = "Higher confidence when correct = some metacognitive sensitivity",
       x = NULL, y = "Confidence")

p_rt <- trials |>
  filter(!is.na(DecisionRT)) |>
  ggplot(aes(DecisionRT, fill = Modality)) +
  geom_histogram(bins = 20, alpha = 0.8, position = "identity") +
  scale_fill_manual(values = MODALITY_COLOURS) +
  labs(title = "Decision response times", x = "Seconds", y = "Trials")

options(repr.plot.width = 13, repr.plot.height = 3.8)
p_conf + p_conf_acc + p_rt + plot_layout(guides = "collect")
""")

md(r"""
### A collection checklist

Before a session enters your analysis:

- [ ] Fewer than ~10% missing decisions
- [ ] `listenBPM` plausible throughout, no sensor dropout
- [ ] Stimulus trace funnels rather than wandering or pinning to the grid edge
- [ ] Confidence uses a real range of the scale
- [ ] No long run of near-instant responses
- [ ] Enough trials per condition — below ~30 the slope will not be identified

Write your exclusion rules down **before** you look at the effect. Deciding what counts
as a bad session after seeing which way it pushes your result is how a defensible
pipeline stops being one.
""")

# ----------------------------------------------------------------- Part 5
md(r"""
---
## Part 5 — Fit the psychometric model to your volunteer

Two Bayesian procedures run in this workflow, and they have different jobs:

- **Psi**, during the task, picks informative stimuli. It fixes the lapse rate at 0.02
  and is optimised for choosing the *next* trial.
- **`brms`**, afterwards, estimates the response model properly: lapse rate free,
  cleaned trials, and full posterior uncertainty retained.

The model is the same cumulative Gaussian from notebook 1, now written as a non-linear
`brms` formula:

$$p_i = \frac{\ell}{2} + (1-\ell)\,\Phi\!\left[e^{\beta}(x_i-\alpha)\right], \qquad y_i \sim \text{Bernoulli}(p_i)$$

with $\alpha$ the threshold in ΔBPM, $\beta = -\log\sigma$ the log slope, and $\ell$ the
lapse rate on the logit scale.

> ⚠️ Remember the sign convention: **larger $\beta$ = better** discrimination, while
> larger Psi $\sigma$ = **worse**. They run in opposite directions.

### Aggregate to binomial cells

Trials at the same intensity are exchangeable, so we collapse them into
successes-out-of-trials. This is algebraically identical to the Bernoulli likelihood and
samples faster. Catch trials are kept — they did not update Psi, but they are valid
observations and they sample the tails, where the lapse rate is identified.
""")

co(r"""
model_df <- trials |>
  filter(Modality == "Intero", Decision %in% c("More", "Less"), !is.na(Alpha)) |>
  mutate(x = Alpha, resp = as.integer(Decision == "More")) |>
  group_by(x) |>
  summarise(y = sum(resp), n = n(), .groups = "drop")

cat(sprintf("%d interoceptive trials at %d unique intensities\n",
            sum(model_df$n), nrow(model_df)))
print(head(as.data.frame(model_df), 10), row.names = FALSE)

if (sum(model_df$n) < 30) {
  cat("\n[!] Under 30 trials. The fit will run, but expect a very wide slope posterior.\n")
  cat("    Treat the numbers below as a demonstration of the machinery, not an estimate.\n")
}
""")

md(r"""
### The formula and the priors

`brms` compiles the non-linear formula to Stan. Two helper functions are needed in R
itself: Stan provides `erf()` but R does not, and `posterior_epred()` evaluates the same
expression in R at post-processing time — so without them, fitting succeeds and
post-processing fails.

The priors come from the normative refit in the Hierarchical Interoception toolbox:

| Prior | Centre | Meaning |
|---|---|---|
| `alpha ~ normal(-8.67, 11.23)` | −8.67 ΔBPM | Most people underestimate their heart rate |
| `beta ~ normal(-2.3, 0.34)` | $\sigma \approx 10$ ΔBPM | Typical discrimination precision |
| `lambda ~ normal(-4.32, 1.96)` | ≈1.3% lapse | Lapses are rare but possible |

These are *weakly informative and empirically grounded*, not flat. With 20–60 trials from
one person, flat priors would let the sampler wander into absurd regions.
""")

co(r"""
inv_logit <- function(x) 1 / (1 + exp(-x))
erf <- function(x) 2 * pnorm(x * sqrt(2)) - 1   # Stan has erf(); R does not

bff <- bf(
  y | trials(n) ~ inv_logit(lambda) / 2 +
    (1 - inv_logit(lambda)) *
      (0.5 + 0.5 * erf(exp(beta) * (x - alpha) / sqrt(2))),
  alpha ~ 1, beta ~ 1, lambda ~ 1,
  nl = TRUE, family = binomial(link = "identity")
)

priors <- c(
  set_prior("normal(-8.67, 11.23)", class = "b", nlpar = "alpha",  coef = "Intercept"),
  set_prior("normal(-2.3, 0.34)",   class = "b", nlpar = "beta",   coef = "Intercept"),
  set_prior("normal(-4.32, 1.96)",  class = "b", nlpar = "lambda", coef = "Intercept")
)

# Always check the coefficient names your formula actually generates. A typo in a
# non-linear nlpar leaves an unintended FLAT prior and brms will not warn you.
print(as.data.frame(get_prior(bff, data = model_df))[, c("prior","class","coef","nlpar")],
      row.names = FALSE)
""")

md(r"""
### Check the priors before seeing the data

Sampling from the prior alone and drawing the *implied psychometric curves* is far more
informative than inspecting three prior densities separately. It answers the question
that matters: does this combination of priors put probability on response curves that
could plausibly happen over the intensities the participant will meet?
""")

co(r"""
prior_fit <- brm(
  bff, data = model_df, prior = priors, sample_prior = "only",
  chains = 2, iter = 1000, refresh = 0, backend = "cmdstanr", seed = 5101
)

grid <- data.frame(x = seq(-50.5, 50.5, length.out = 150), n = 1)
prior_curves <- posterior_epred(prior_fit, newdata = grid)

prior_long <- as.data.frame(t(prior_curves[1:120, ])) |>
  mutate(x = grid$x) |>
  pivot_longer(-x, names_to = "draw", values_to = "p")

options(repr.plot.width = 7, repr.plot.height = 4)
ggplot(prior_long, aes(x, p, group = draw)) +
  geom_line(alpha = 0.1, colour = NAVY) +
  geom_hline(yintercept = 0.5, colour = GREY, linetype = "dotted") +
  labs(title = "120 psychometric functions drawn from the priors alone",
       subtitle = "Plausible curves, not yet informed by any response",
       x = expression(Delta*"BPM"), y = 'P("faster")')
""")

md(r"""
### Sample the posterior

Four chains, 3000 iterations with 1000 warmup. `sample_prior = "yes"` keeps prior draws
alongside the posterior so we can show directly how much the data moved each parameter.

This takes **one to three minutes**. The first run also compiles the Stan model.
""")

co(r"""
fit <- brm(
  bff, data = model_df, prior = priors, sample_prior = "yes",
  chains = 4, cores = 4, warmup = 1000, iter = 3000,
  control = list(adapt_delta = 0.95, max_treedepth = 12),
  backend = "cmdstanr", seed = 5102, refresh = 0,
  file = file.path(getwd(), "fit_single_subject"), file_refit = "on_change"
)
cat("done\n")
""")

md(r"""
### Read the diagnostics before the estimates

Non-negotiable, and in this order. A beautiful posterior plot from a broken sampler is
worse than no plot at all.

| Check | Requirement |
|---|---|
| Divergent transitions | **0** |
| $\widehat{R}$ | < 1.01 |
| Bulk / tail ESS | at least in the hundreds |
| E-BFMI | > 0.3 |
""")

co(r"""
np <- nuts_params(fit)
ds <- summarise_draws(as_draws_array(fit))
energy <- np |> filter(Parameter == "energy__") |> group_by(Chain) |>
  summarise(ebfmi = mean(diff(Value)^2) / var(Value), .groups = "drop")

diagnostics <- data.frame(
  divergences  = sum(np$Value[np$Parameter == "divergent__"]),
  max_treedepth = max(np$Value[np$Parameter == "treedepth__"]),
  max_rhat     = round(max(ds$rhat, na.rm = TRUE), 4),
  min_ess_bulk = round(min(ds$ess_bulk, na.rm = TRUE)),
  min_ess_tail = round(min(ds$ess_tail, na.rm = TRUE)),
  min_ebfmi    = round(min(energy$ebfmi), 3)
)
print(diagnostics, row.names = FALSE)

verdict <- with(diagnostics,
  divergences == 0 && max_rhat < 1.01 && min_ess_bulk > 400 && min_ebfmi > 0.3)
cat("\n", ifelse(verdict, "No indication of a sampling problem.",
                 "[!] Something is off - do not interpret these estimates yet."), "\n")
""")

md(r"""
### From priors to posterior

The upper row compares prior and posterior draws for each parameter. The lower row shows
post-warmup draws in sampling order — a *computational* diagnostic, not a record of how
the participant learned. All four chains should explore the same region without trends
or long sticky periods.
""")

co(r"""
draws <- as_draws_df(fit) |> as.data.frame()

comp <- bind_rows(
  data.frame(parameter = "threshold (dBPM)", source = "prior",     value = draws$prior_b_alpha_Intercept),
  data.frame(parameter = "threshold (dBPM)", source = "posterior", value = draws$b_alpha_Intercept),
  data.frame(parameter = "sigma (dBPM)",     source = "prior",     value = exp(-draws$prior_b_beta_Intercept)),
  data.frame(parameter = "sigma (dBPM)",     source = "posterior", value = exp(-draws$b_beta_Intercept)),
  data.frame(parameter = "lapse",            source = "prior",     value = plogis(draws$prior_b_lambda_Intercept)),
  data.frame(parameter = "lapse",            source = "posterior", value = plogis(draws$b_lambda_Intercept))
)

p_dens <- ggplot(comp, aes(value, fill = source, colour = source)) +
  geom_density(alpha = 0.45, linewidth = 0.4) +
  facet_wrap(~parameter, scales = "free", nrow = 1) +
  scale_fill_manual(values = c(prior = GREY, posterior = RED)) +
  scale_colour_manual(values = c(prior = GREY, posterior = RED)) +
  labs(title = "The data moved the parameters", x = NULL, y = NULL)

p_trace2 <- draws |>
  select(.chain, .iteration, alpha = b_alpha_Intercept, beta = b_beta_Intercept) |>
  pivot_longer(c(alpha, beta)) |>
  ggplot(aes(.iteration, value, colour = factor(.chain))) +
  geom_line(alpha = 0.55, linewidth = 0.3) +
  facet_wrap(~name, scales = "free_y", nrow = 1) +
  scale_colour_brewer(palette = "Set2", name = "chain") +
  labs(title = "Chains in sampling order", x = "Iteration", y = NULL)

options(repr.plot.width = 12, repr.plot.height = 7)
p_dens / p_trace2
""")

md(r"""
### The fitted psychometric function

Carrying every posterior draw through the psychometric function gives a *distribution*
of response probabilities at each intensity — hence the credible bands. This is what a
Bayesian fit buys you over the single point estimate Psi reports online.
""")

co(r"""
grid  <- data.frame(x = seq(-50.5, 50.5, by = 0.5), n = 1)
pd    <- posterior_epred(fit, newdata = grid)

curve <- data.frame(
  x      = grid$x,
  median = apply(pd, 2, median),
  lo95   = apply(pd, 2, quantile, 0.025), hi95 = apply(pd, 2, quantile, 0.975),
  lo80   = apply(pd, 2, quantile, 0.100), hi80 = apply(pd, 2, quantile, 0.900),
  lo50   = apply(pd, 2, quantile, 0.250), hi50 = apply(pd, 2, quantile, 0.750)
)
thr <- median(draws$b_alpha_Intercept)

options(repr.plot.width = 8, repr.plot.height = 5)
ggplot(curve, aes(x)) +
  geom_ribbon(aes(ymin = lo95, ymax = hi95), fill = RED, alpha = 0.15) +
  geom_ribbon(aes(ymin = lo80, ymax = hi80), fill = RED, alpha = 0.20) +
  geom_ribbon(aes(ymin = lo50, ymax = hi50), fill = RED, alpha = 0.25) +
  geom_line(aes(y = median), colour = RED, linewidth = 1.1) +
  geom_point(data = mutate(model_df, p = y / n),
             aes(x = x, y = p, size = n), colour = NAVY, alpha = 0.7,
             inherit.aes = FALSE) +
  geom_vline(xintercept = thr, linetype = "dashed", colour = NAVY) +
  geom_hline(yintercept = 0.5, colour = GREY, linetype = "dotted") +
  scale_size_continuous(range = c(1.5, 6), name = "trials") +
  coord_cartesian(ylim = c(0, 1)) +
  labs(title = "Observed responses and the posterior psychometric function",
       subtitle = "Bands contain 50%, 80% and 95% of posterior probability",
       x = expression(Delta*"BPM"), y = 'P("faster")')
""")

md(r"""
### Report on scientific scales

Always transform before reporting. $\beta$ is a log inverse-σ and $\lambda$ is on the
logit scale; neither is interpretable raw.
""")

co(r"""
summary_tbl <- data.frame(
  threshold_dBPM    = draws$b_alpha_Intercept,
  log_slope_beta    = draws$b_beta_Intercept,
  sigma_dBPM        = exp(-draws$b_beta_Intercept),
  lapse_probability = plogis(draws$b_lambda_Intercept)
) |>
  pivot_longer(everything(), names_to = "parameter", values_to = "value") |>
  group_by(parameter) |>
  summarise(median = median(value), q2.5 = quantile(value, 0.025),
            q97.5 = quantile(value, 0.975), .groups = "drop") |>
  mutate(across(where(is.numeric), \(v) round(v, 3)))

print(as.data.frame(summary_tbl), row.names = FALSE)

a  <- median(draws$b_alpha_Intercept)
ci <- quantile(draws$b_alpha_Intercept, c(0.025, 0.975))
cat(sprintf(
  "\nThreshold %+.1f dBPM [%.1f, %.1f].\nTones had to be about %.0f BPM %s than the measured rate\nbefore 'faster' and 'slower' were equally likely: %s.\n",
  a, ci[1], ci[2], abs(a), ifelse(a > 0, "faster", "slower"),
  ifelse(a > 0, "overestimation of their own heart rate",
                "underestimation of their own heart rate")))
""")

md(r"""
### Where a single-participant fit stops

This fit is genuinely useful: it describes one session, shows whether the response
function is identified at all, and makes the remaining uncertainty visible.

It is **not** a route to a group analysis. Fitting every participant separately and then
running a test on their posterior means throws away exactly the information that
distinguishes a well-estimated participant from a barely-estimated one. That is what
Part 6 is for.
""")

# ----------------------------------------------------------------- Part 6
md(r"""
---
## Part 6 — The hierarchical group model

The tutorial models were fitted to **512 participants**, each completing both the cardiac
and auditory conditions, with age, gender and BMI recorded.

### These fits take hours, so we load the results

Nothing below refits anything. The `tutorials/results/small/` artefacts are the compact
posterior output of the pipeline in `tutorials/R/`. To reproduce them:

```bash
Rscript tutorials/R/00_prepare.R data/hrd_tutorial.csv data/model_data.rds
Rscript tutorials/R/01_fit.R psy_intero      # the minimal model
Rscript tutorials/R/01_fit.R psy_full        # the full model
Rscript tutorials/R/02_summarise.R
```

**Expect hours, not minutes.** Cut it down first to check the pipeline runs end to end —
but do not report anything from a cut-down fit:

```bash
HRD_CHAINS=2 HRD_ITER=800 HRD_WARMUP=400 Rscript tutorials/R/01_fit.R psy_intero
```

### The four models

| Name | What it is for |
|---|---|
| `psy_intero` | One condition, no predictors. The simplest useful fit |
| `psy_main` | Modality, gender, age, BMI as main effects |
| `psy_full` | Modality **interacting** with gender and age, BMI controlled |
| `meta_full` | Confidence, ordered beta regression, same covariates |

`psy_main` exists to be compared against `psy_full`: an effect can look like a main
effect right up until the interaction is in the model.
""")

co(r"""
read_small <- function(name) read_csv(file.path(SMALL, name), show_col_types = FALSE)

psy_full_draws <- read_small("psy_full_draws.csv.gz")
psy_subj       <- read_small("psy_intero_subject.csv.gz")
cat("psy_full draws:", nrow(psy_full_draws), "x", ncol(psy_full_draws), "\n")
cat("subject-level estimates:", nrow(psy_subj), "rows,",
    length(unique(psy_subj$subj)), "participants\n")
""")

md(r"""
### Why hierarchical, concretely

Every participant is estimated *with* the group rather than in isolation. Someone with 60
clean trials contributes a sharp estimate; someone with 25 noisy ones contributes a vague
estimate and is pulled further toward the group mean. That pooling is not a nuisance — it
is the model correctly refusing to take a noisy participant at face value.

The plot below shows the spread of individual threshold and slope estimates behind the
population parameters.
""")

co(r"""
subj_wide <- psy_subj |>
  filter(parameter %in% c("alpha_Intercept", "beta_Intercept")) |>
  select(subj, parameter, Estimate, Est.Error) |>
  pivot_wider(names_from = parameter, values_from = c(Estimate, Est.Error))

p1 <- ggplot(subj_wide, aes(Estimate_alpha_Intercept)) +
  geom_histogram(bins = 40, fill = RED, alpha = 0.8) +
  geom_vline(xintercept = 0, colour = NAVY, linetype = "dashed") +
  labs(title = "Threshold across 512 participants",
       subtitle = "Dashed line = no bias. Most of the mass is left of it.",
       x = expression("Threshold ("*Delta*"BPM)"), y = "Participants")

p2 <- ggplot(subj_wide, aes(Estimate_alpha_Intercept, Est.Error_alpha_Intercept)) +
  geom_point(alpha = 0.35, colour = NAVY, size = 1.3) +
  labs(title = "Uncertainty varies a lot between participants",
       subtitle = "Each point is one person. Higher = less certain estimate.",
       x = expression("Threshold ("*Delta*"BPM)"), y = "Posterior SD")

options(repr.plot.width = 12, repr.plot.height = 4.2)
p1 + p2

cat(sprintf("\nMedian threshold %.1f dBPM; %.0f%% of participants estimated below zero.\n",
            median(subj_wide$Estimate_alpha_Intercept),
            100 * mean(subj_wide$Estimate_alpha_Intercept < 0)))
cat(sprintf("Posterior SD ranges %.1f to %.1f - a %.0fx difference in how much\n",
            min(subj_wide$Est.Error_alpha_Intercept),
            max(subj_wide$Est.Error_alpha_Intercept),
            max(subj_wide$Est.Error_alpha_Intercept) / min(subj_wide$Est.Error_alpha_Intercept)))
cat("each participant should be trusted. A two-stage analysis would ignore this.\n")
""")

md(r"""
### What the full model found

The formula, from `tutorials/R/models.R`:

```r
alpha ~ 1 + Modality * (gender + age_z) + bmi_z + (Modality | subj)
beta  ~ 1 + Modality * (gender + age_z) + bmi_z + (Modality | subj)
lambda ~ 1 + (1 | subj)
```

Age and BMI are z-scored, so their coefficients are **per SD of the covariate**. The
auditory condition and women are the reference levels.
""")

co(r"""
terms_of_interest <- c(
  "b_alpha_Intercept", "b_alpha_ModalityIntero", "b_alpha_genderMale",
  "b_alpha_age_z", "b_alpha_bmi_z",
  "b_beta_ModalityIntero", "b_beta_ModalityIntero:genderMale", "b_beta_ModalityIntero:age_z"
)

coef_tbl <- psy_full_draws |>
  select(any_of(terms_of_interest)) |>
  pivot_longer(everything(), names_to = "term", values_to = "value") |>
  group_by(term) |>
  summarise(mean = mean(value), q2.5 = quantile(value, 0.025),
            q97.5 = quantile(value, 0.975),
            p_neg = mean(value < 0), .groups = "drop") |>
  mutate(across(where(is.numeric), \(v) round(v, 3))) |>
  arrange(match(term, terms_of_interest))

print(as.data.frame(coef_tbl), row.names = FALSE)

d <- psy_full_draws
cat("\n--- on interpretable scales ---\n")
cat(sprintf("Auditory threshold  %+.2f dBPM\n", mean(d$b_alpha_Intercept)))
cat(sprintf("Cardiac threshold   %+.2f dBPM   (intercept + modality)\n",
            mean(d$b_alpha_Intercept + d$b_alpha_ModalityIntero)))
cat(sprintf("Auditory sigma      %.2f dBPM\n", mean(exp(-d$b_beta_Intercept))))
cat(sprintf("Cardiac sigma       %.2f dBPM   (larger = poorer discrimination)\n",
            mean(exp(-(d$b_beta_Intercept + d$b_beta_ModalityIntero)))))
""")

md(r"""
Two findings worth pausing on.

**The cardiac threshold sits about 9–10 ΔBPM below the auditory one.** People judge tones
roughly 9 BPM *slower* than their measured heart rate as equally likely to be faster or
slower — a systematic underestimation of their own heart rate. The auditory condition,
where the reference is an external tone sequence, shows almost no such bias. That
contrast is the argument that this is about cardiac belief and not a general
tone-comparison artefact.

**Discrimination is also poorer for the cardiac condition** (larger σ). Threshold and
slope are separate claims: this population is both *biased* and *less precise* about
their heart, and either could have moved without the other.

### Reading interactions correctly

Once an interaction is in the model, a main-effect coefficient describes **the reference
condition only**. `b_beta_genderMale` is the gender contrast in the *auditory* condition.
The cardiac contrast is the sum of the main effect and the interaction — which you should
compute from the draws, so the uncertainty comes along with it.
""")

co(r"""
simple_effects <- data.frame(
  auditory = d$b_beta_genderMale,
  cardiac  = d$b_beta_genderMale + d$`b_beta_ModalityIntero:genderMale`
) |>
  pivot_longer(everything(), names_to = "condition", values_to = "value") |>
  group_by(condition) |>
  summarise(mean = round(mean(value), 3),
            q2.5 = round(quantile(value, 0.025), 3),
            q97.5 = round(quantile(value, 0.975), 3),
            `P(<0)` = round(mean(value < 0), 3), .groups = "drop")

cat("Gender contrast on log-slope (beta), by condition:\n\n")
print(as.data.frame(simple_effects), row.names = FALSE)
cat("\nThe cardiac contrast is NOT the main effect. Reporting only the main effect\n")
cat("would describe the auditory control condition while sounding like a claim\n")
cat("about interoception.\n")
""")

md(r"""
### Population psychometric functions

The clearest way to show a group result: push the population parameters back through the
psychometric function and plot the curves the model implies.
""")

co(r"""
curve_gender <- read_small("psy_full_curve_gender.csv.gz")
cat("columns:", paste(names(curve_gender), collapse = ", "), "\n\n")

ycol  <- intersect(c("m", "median", "Estimate", "p"), names(curve_gender))[1]
locol <- intersect(c("lo", "lower", "Q2.5", "q2.5"), names(curve_gender))[1]
hicol <- intersect(c("hi", "upper", "Q97.5", "q97.5"), names(curve_gender))[1]
grpcols <- intersect(c("Modality", "gender"), names(curve_gender))

p <- ggplot(curve_gender, aes(x = x, y = .data[[ycol]], colour = .data[[grpcols[1]]]))
if (!is.na(locol))
  p <- p + geom_ribbon(aes(ymin = .data[[locol]], ymax = .data[[hicol]],
                           fill = .data[[grpcols[1]]]), alpha = 0.18, colour = NA)
p <- p + geom_line(linewidth = 1.1) +
  scale_colour_manual(values = MODALITY_COLOURS) +
  scale_fill_manual(values = MODALITY_COLOURS) +
  geom_hline(yintercept = 0.5, colour = GREY, linetype = "dotted") +
  geom_vline(xintercept = 0, colour = GREY, linetype = "dotted") +
  labs(title = "Population psychometric functions",
       subtitle = "At the sample mean of age and BMI",
       x = expression(Delta*"BPM"), y = 'P("faster")')

if (length(grpcols) > 1) p <- p + facet_wrap(as.formula(paste("~", grpcols[2])))

options(repr.plot.width = 10, repr.plot.height = 4.5)
p
""")

md(r"""
### The confidence model

Confidence gets its own model, and it is **not** a psychometric function. The HRD records
a continuous 0–100 VAS with real mass piled at both ends — participants use the extremes.
Neither a Gaussian nor a plain beta likelihood can represent that, so the tutorials use
**ordered beta regression**:

```r
Confidence ~ Accuracy * (Modality + gender + age_z) + bmi_z +
             (Accuracy * Modality | subj)
```

The `Accuracy × Modality` interaction is the interesting term: it asks whether the
*confidence gap between correct and incorrect trials* — a calibration signal — differs
between cardiac and auditory judgements.

> **Why not M-ratio / meta-d′ here?** The tutorials deliberately do not use it for HRD
> data. It needs discrete confidence bins, and `hmetad` puts a log link on
> M = meta-d′/d′, so any cell with d′ ≤ 0 or meta-d′ ≤ 0 is *unrepresentable* and piles
> against a boundary. Excluding those cells selects on the dependent variable, which
> biases the very contrast you are estimating toward zero. The ordered beta model on raw
> confidence avoids both problems.
""")

co(r"""
meta_draws <- read_small("meta_full_draws.csv.gz")

meta_terms <- c("b_Accuracycorrect", "b_ModalityIntero",
                "b_Accuracycorrect:ModalityIntero", "b_age_z", "b_Accuracycorrect:age_z")

meta_tbl <- meta_draws |>
  select(any_of(meta_terms)) |>
  pivot_longer(everything(), names_to = "term", values_to = "value") |>
  group_by(term) |>
  summarise(mean = round(mean(value), 3),
            q2.5 = round(quantile(value, 0.025), 3),
            q97.5 = round(quantile(value, 0.975), 3), .groups = "drop") |>
  arrange(match(term, meta_terms))

cat("Ordered beta model of confidence (latent scale):\n\n")
print(as.data.frame(meta_tbl), row.names = FALSE)

cat("\nb_Accuracycorrect > 0 means higher confidence on correct trials:\n")
cat("the participants had some insight into their own accuracy.\n")
cat("The Accuracy:Modality interaction asks whether that insight differs\n")
cat("between cardiac and auditory judgements.\n")
""")

md(r"""
---
## What you have done

1. Built intuition for threshold, slope and lapse on simulated data you could steer.
2. Installed Cardioception and verified the oximeter was producing a real signal.
3. Designed a task and collected a live session.
4. Inspected that session against a quality checklist.
5. Fitted the psychometric model with grounded priors, checked the sampler, and reported on interpretable scales.
6. Read a 512-participant hierarchical model, including how to read an interaction without misdescribing it.

### Where to go next

| If you want to | Go to |
|---|---|
| Run a real study | `wrappers/` in the repository |
| Reproduce the group fits | `tutorials/R/`, and expect hours |
| Understand the models properly | The [tutorial pages](https://www.the-ecg.org/Cardioception/) |
| Adapt the models to your design | [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception) |

### Three things to carry away

- **Model responses, not accuracy.** Accuracy throws away the sign of the bias, which is the main thing the HRD recovers.
- **Threshold and slope are separate claims.** An effect on one is not evidence for the other.
- **Fit participants together, not one at a time.** A two-stage analysis discards how much each participant should be trusted.

### References

- Legrand et al. (2022). *The heart rate discrimination task.* Biological Psychology. [doi:10.1016/j.biopsycho.2021.108239](https://doi.org/10.1016/j.biopsycho.2021.108239)
- Courtin et al. (2026). *Hierarchical Interoception toolbox.* Behavior Research Methods. [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
- Bürkner (2017). *brms.* Journal of Statistical Software. [doi:10.18637/jss.v080.i01](https://doi.org/10.18637/jss.v080.i01)
""")

nb["cells"] = c
nb.metadata = {
    "kernelspec": {"display_name": "R (cardioception)", "language": "R",
                   "name": "ir-cardioception"},
    "language_info": {"name": "R"},
}

out = Path(__file__).parent / "02_analysing_the_hrd.ipynb"
nbf.write(nb, str(out))
print(f"wrote {out}  ({len(c)} cells)")
