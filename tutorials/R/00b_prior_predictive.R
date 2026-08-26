# Prior predictive check.
#
#   Rscript 00b_prior_predictive.R [model_name]
#
# Samples from the priors with the likelihood switched off, and reports what
# they imply before any data is involved. A prior is a claim about what is
# plausible; this is how that claim gets checked rather than asserted.
#
# What to look for:
#   - implied thresholds should cover the plausible range of human bias in
#     judging one's own heart rate, roughly +/- 40 dBPM, without piling up at
#     the edges of the stimulus range
#   - implied psychometric curves should be monotonic and mostly resolvable,
#     not a bundle of near-flat or near-step functions
#   - effect priors should not imply group differences larger than the entire
#     between-subject spread

suppressPackageStartupMessages({
  library(brms)
  library(dplyr)
  library(ggplot2)
})

source(Sys.getenv("HRD_MODELS", "R/models.R"))

args <- commandArgs(trailingOnly = TRUE)
model_name <- if (length(args) >= 1) args[1] else "psy_full"
spec <- MODELS[[model_name]]
if (is.null(spec)) stop("unknown model: ", model_name)
if (spec$kind != "psychometric") stop("prior predictive is set up for the psychometric models")

out_dir <- Sys.getenv("HRD_OUT", "results")
fig_dir <- Sys.getenv("HRD_FIGS", file.path(out_dir, "figures"))
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

d <- readRDS(Sys.getenv("HRD_DATA", "data/model_data.rds"))
dat <- switch(spec$data, both = d$both, intero = d$intero, trials = d$trials)

# A small slice is plenty: nothing here depends on the data beyond its structure.
keep <- head(levels(droplevels(dat$subj)), 30)
dat <- dat[dat$subj %in% keep, , drop = FALSE]
dat$subj <- droplevels(dat$subj)

message("sampling from the prior only for ", model_name)
fit <- brm(
  spec$formula,
  data = dat,
  prior = psychometric_priors(spec$effect_coefs),
  sample_prior = "only",
  chains = 2, cores = 2, iter = 1000, warmup = 500,
  backend = "cmdstanr", seed = 12345, refresh = 0
)

draws <- as.data.frame(fit)

# --- what the priors imply about the threshold -----------------------------
a_col <- "b_alpha_Intercept"
q <- quantile(draws[[a_col]], c(0.025, 0.25, 0.5, 0.75, 0.975))
message(sprintf(
  "implied threshold: median %.1f dBPM, 95%% interval [%.1f, %.1f]",
  q[3], q[1], q[5]
))

# --- what they imply about each effect -------------------------------------
eff_cols <- grep("^b_(alpha|beta)_", names(draws), value = TRUE)
eff_cols <- eff_cols[!grepl("Intercept", eff_cols)]
if (length(eff_cols)) {
  tbl <- lapply(eff_cols, function(cl) {
    v <- draws[[cl]]
    data.frame(term = sub("^b_", "", cl),
               sd_prior = sd(v),
               q2.5 = quantile(v, 0.025, names = FALSE),
               q97.5 = quantile(v, 0.975, names = FALSE))
  }) %>% bind_rows()
  print(tbl, row.names = FALSE)
  write.csv(tbl, file.path(out_dir, paste0(model_name, "_prior_predictive.csv")),
            row.names = FALSE)
}

# --- implied psychometric curves -------------------------------------------
grid <- seq(-40, 40, length.out = 120)
n_draw <- 100
idx <- sample(nrow(draws), n_draw)
curves <- lapply(idx, function(i) {
  a <- draws[[a_col]][i]
  b <- draws[["b_beta_Intercept"]][i]
  l <- draws[["b_lambda_Intercept"]][i]
  lam <- 1 / (1 + exp(-l))
  p <- lam / 2 + (1 - lam) * pnorm((grid - a) * exp(b))
  data.frame(draw = i, x = grid, p = p)
}) %>% bind_rows()

pl <- ggplot(curves, aes(x, p, group = draw)) +
  geom_line(alpha = 0.15, colour = "#2f4b73") +
  geom_hline(yintercept = 0.5, linetype = "dotted", colour = "#8a94a3") +
  labs(x = "Intensity (dBPM)", y = "P(\"faster\")",
       title = paste0("Prior predictive psychometric functions: ", model_name)) +
  theme_classic(base_size = 11)
ggsave(file.path(fig_dir, paste0("fig_prior_predictive_", model_name, ".png")),
       pl, width = 6.5, height = 3.4, dpi = 200)
message("wrote prior predictive figure")

# --- a blunt sanity check --------------------------------------------------
# If most of the prior mass puts the threshold outside the range of stimuli the
# task can present, the prior is claiming something the experiment cannot show.
outside <- mean(abs(draws[[a_col]]) > 40)
message(sprintf("prior mass with |threshold| > 40 dBPM: %.1f%%", 100 * outside))
if (outside > 0.10) {
  message("WARNING: prior puts substantial mass outside the presentable range")
}
