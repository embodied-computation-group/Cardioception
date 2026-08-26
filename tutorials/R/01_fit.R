# Fit one model from MODELS and write its posterior.
#
#   Rscript 01_fit.R <model_name>
#
# Designed to be driven by a SLURM array: each task fits one model. A task whose
# output already exists exits immediately, so a partially completed array can be
# resubmitted unchanged and will only fill the gaps.
#
# Environment:
#   HRD_DATA     path to model_data.rds        (default data/model_data.rds)
#   HRD_OUT      output directory              (default results)
#   HRD_CHAINS   chains                        (default 8)
#   HRD_THREADS  threads per chain             (default 16)
#   HRD_ITER     total iterations per chain    (default 4000)
#   HRD_WARMUP   warmup per chain              (default 2000)

suppressPackageStartupMessages({
  library(brms)
  library(cmdstanr)
  library(dplyr)
})

# The SLURM script sets the working directory to the project root.
source(Sys.getenv("HRD_MODELS", "R/models.R"))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("usage: Rscript 01_fit.R <model_name>")
model_name <- args[1]
if (!model_name %in% names(MODELS)) {
  stop("unknown model '", model_name, "'. Known: ", paste(names(MODELS), collapse = ", "))
}

data_path <- Sys.getenv("HRD_DATA", "data/model_data.rds")
out_dir <- Sys.getenv("HRD_OUT", "results")
chains <- as.integer(Sys.getenv("HRD_CHAINS", "8"))
threads_n <- as.integer(Sys.getenv("HRD_THREADS", "16"))
iter <- as.integer(Sys.getenv("HRD_ITER", "4000"))
warmup <- as.integer(Sys.getenv("HRD_WARMUP", "2000"))

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
fit_path <- file.path(out_dir, paste0(model_name, ".rds"))
done_path <- file.path(out_dir, paste0(model_name, "_summary.csv"))

# Idempotence: judge by the summary, which is only written after sampling ends.
# The .rds alone is not proof, because brms writes it before post-processing.
if (file.exists(done_path)) {
  message("already complete: ", done_path, " -- nothing to do")
  quit(save = "no", status = 0)
}

spec <- MODELS[[model_name]]
message("=== ", model_name, ": ", spec$description, " ===")

d <- readRDS(data_path)
dat <- switch(spec$data,
  trials = d$trials,
  both = d$both,
  intero = d$intero,
  stop("unknown data key: ", spec$data)
)
message(sprintf("data: %d rows, %d subjects", nrow(dat), dplyr::n_distinct(dat$subj)))

# HRD_MAX_SUBJ cuts the data down to a handful of participants. This exists for
# rehearsing the pipeline end to end before committing a node for a day. Results
# from a subset are not reportable, so the run is labelled loudly.
max_subj <- suppressWarnings(as.integer(Sys.getenv("HRD_MAX_SUBJ", "")))
if (!is.na(max_subj) && max_subj > 0) {
  keep <- head(levels(droplevels(dat$subj)), max_subj)
  dat <- dat[dat$subj %in% keep, , drop = FALSE]
  dat$subj <- droplevels(dat$subj)
  message(sprintf("SMOKE TEST: cut to %d subjects, %d rows -- not reportable",
                  dplyr::n_distinct(dat$subj), nrow(dat)))
}

# --- priors ----------------------------------------------------------------
# Verify the coefficient names before sampling. A prior naming a coefficient
# that brms does not generate is silently ignored, and the effect then samples
# under a flat default. That is the failure this check exists to catch, and it
# is far cheaper to catch here than after a day of sampling.
if (spec$kind == "psychometric") {
  priors <- psychometric_priors(spec$effect_coefs)
  expected <- get_prior(spec$formula, data = dat)
  known <- unique(expected$coef[expected$coef != ""])
  missing <- setdiff(spec$effect_coefs, known)
  if (length(missing)) {
    stop("priors name coefficients brms does not generate: ",
         paste(missing, collapse = ", "),
         "\nbrms generates: ", paste(known, collapse = ", "))
  }
  flat <- expected %>%
    filter(class == "b", coef != "", prior == "") %>%
    pull(coef) %>%
    setdiff(c(spec$effect_coefs, "Intercept"))
  if (length(flat)) {
    stop("these coefficients would sample under a flat prior: ",
         paste(flat, collapse = ", "))
  }
  message("priors verified against get_prior(): ",
          length(spec$effect_coefs), " effect coefficients")
}

# --- fit -------------------------------------------------------------------
started <- Sys.time()
message(sprintf("sampling: %d chains x %d threads, %d iter (%d warmup)",
                chains, threads_n, iter, warmup))

common <- list(
  data = dat,
  chains = chains,
  cores = chains,
  threads = threading(threads_n),
  iter = iter,
  warmup = warmup,
  seed = 12345,
  backend = "cmdstanr",
  control = list(adapt_delta = 0.95, max_treedepth = 12),
  file = tools::file_path_sans_ext(fit_path),
  file_refit = "never"
)

fit <- if (spec$kind == "psychometric") {
  do.call(brm, c(list(formula = spec$formula, prior = priors), common))
} else if (spec$kind == "ordbeta") {
  suppressPackageStartupMessages(library(ordbetareg))
  do.call(ordbetareg, c(list(formula = spec$formula), common))
} else {
  stop("unknown model kind: ", spec$kind)
}

elapsed <- difftime(Sys.time(), started, units = "hours")
message(sprintf("sampling finished in %.2f hours", as.numeric(elapsed)))

# --- diagnostics and summary ----------------------------------------------
np <- brms::nuts_params(fit)
divergent <- sum(np$Value[np$Parameter == "divergent__"])
s <- posterior::summarise_draws(posterior::as_draws_df(fit))
max_rhat <- max(s$rhat, na.rm = TRUE)
min_ess <- min(s$ess_bulk, na.rm = TRUE)

message(sprintf("divergent transitions: %d", divergent))
message(sprintf("max rhat: %.4f | min bulk ESS: %.0f", max_rhat, min_ess))
if (divergent > 0) message("WARNING: divergences present, do not trust this fit as is")
if (max_rhat > 1.01) message("WARNING: rhat above 1.01, chains have not converged")

fixed <- as.data.frame(brms::fixef(fit))
fixed$term <- rownames(fixed)
fixed$model <- model_name
write.csv(fixed, done_path, row.names = FALSE)

writeLines(
  c(
    sprintf("model=%s", model_name),
    sprintf("description=%s", spec$description),
    sprintf("rows=%d", nrow(dat)),
    sprintf("subjects=%d", dplyr::n_distinct(dat$subj)),
    sprintf("chains=%d threads=%d iter=%d warmup=%d", chains, threads_n, iter, warmup),
    sprintf("hours=%.2f", as.numeric(elapsed)),
    sprintf("divergent=%d", divergent),
    sprintf("max_rhat=%.4f", max_rhat),
    sprintf("min_ess_bulk=%.0f", min_ess)
  ),
  file.path(out_dir, paste0(model_name, "_diagnostics.txt"))
)

message("wrote ", done_path)
