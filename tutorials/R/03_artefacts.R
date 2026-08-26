# Derive the small, tidy artefacts the documentation is built from.
#
#   Rscript R/03_artefacts.R
#
# The full fits are 190-320 MB each and go to a GitHub release, where the
# per-file limit is 2 GB. So this is not about making them fit anywhere. It
# exists because the documentation needs four things the fits cannot give it:
#
#   1. A docs build cannot load a 314 MB brmsfit to render a page. The pages
#      need numbers and figures already computed.
#   2. Some of what the figures show is not in a fit at all and has to be
#      computed here, over the whole posterior: the average of the participants'
#      curves, the pooled predictive intervals, the bound-mass check.
#   3. Someone who clones the repository should be able to redraw every figure
#      without brms, without CmdStan, and without a gigabyte of download.
#   4. A brmsfit is version-brittle. It depends on the brms, rstan and cmdstanr
#      it was written by; a CSV of draws will still open in ten years.
#
# So R/04_figures.R reads this bundle and nothing else. If it ever needs a
# brmsfit, the missing quantity belongs here instead.
#
# What is dropped: the per-draw subject-level parameters. psy_full carries 2,560
# `r_subj__*` against 15 population ones, so they are roughly 99% of the object,
# and the pages only ever show them summarised. Anything needing those draws has
# to go back to the full fit.

suppressPackageStartupMessages({
  library(brms)
  library(posterior)
  library(dplyr)
  library(tidyr)
})

source(Sys.getenv("HRD_MODELS", "R/models.R"))

out_dir   <- Sys.getenv("HRD_OUT", "results")
small_dir <- file.path(out_dir, "small")
data_path <- Sys.getenv("HRD_DATA", "data/model_data.rds")
dir.create(small_dir, showWarnings = FALSE, recursive = TRUE)

# 16,000 draws is far more than any interval in the tutorials needs; 4,000 still
# gives stable 2.5% and 97.5% quantiles at a quarter of the bytes.
THIN  <- as.integer(Sys.getenv("HRD_THIN", "4"))
# Draws used for the curve and predictive summaries. These run over grids of
# tens of thousands of rows, where the draw dimension is what costs memory.
NCURVE <- 2000L
NPPC   <- 400L
NMARG  <- 200L
# Nested credible bands, widest drawn first.
CIS <- c(0.5, 0.8, 0.95)

sizes <- list()
record <- function(path, note) {
  if (!file.exists(path)) return(invisible(NULL))
  sizes[[length(sizes) + 1]] <<- data.frame(
    file = basename(path), bytes = file.info(path)$size,
    mb = round(file.info(path)$size / 1024^2, 3), note = note
  )
  invisible(NULL)
}

write_gz <- function(df, path, note) {
  con <- gzfile(path, "w", compression = 9)
  write.csv(df, con, row.names = FALSE)
  close(con)
  record(path, note)
  message(sprintf("  %-42s %8.2f MB", basename(path),
                  file.info(path)$size / 1024^2))
}

seen <- character(0)
load_fit <- function(name) {
  p <- file.path(out_dir, paste0(name, ".rds"))
  if (!file.exists(p)) { message("missing fit, skipping: ", p); return(NULL) }
  if (!name %in% seen) { record(p, "full brmsfit, release asset"); seen <<- c(seen, name) }
  readRDS(p)
}

# The closed form, so per-subject curves can be drawn from summary parameters
# without materialising 512 subjects by 16,000 draws.
psy_curve <- function(x, alpha, beta, lambda) {
  lam <- inv_logit(lambda)
  lam / 2 + (1 - lam) * (0.5 + 0.5 * erf(exp(beta) * (x - alpha) / sqrt(2)))
}

# Nested quantile bands from a draws-by-rows epred matrix.
bands <- function(ep, grid) {
  do.call(rbind, lapply(CIS, function(ci) {
    g <- grid
    g$ci <- ci
    g$lo <- apply(ep, 2, quantile, (1 - ci) / 2)
    g$hi <- apply(ep, 2, quantile, 1 - (1 - ci) / 2)
    g$m  <- apply(ep, 2, median)
    g
  }))
}

# --- the two curves that are not the same curve ----------------------------
# A population curve (re_formula = NA) is the psychometric function OF THE
# AVERAGE SUBJECT: one draw's population alpha, beta and lambda pushed through
# the likelihood. Its band is uncertainty in the group parameters.
#
# The average OF the subjects' functions is a different quantity, and with
# SD(alpha) around 11 dBPM it is a visibly different curve: the mean of many
# sigmoids sitting at very different thresholds is much shallower than one
# sigmoid at their mean threshold. That is Jensen's inequality, not a fitting
# problem, and it is what pooled observed data actually estimate.
#
# Both are written out. The documentation shows them together, because "why do
# the data points miss the curve?" is the first question a reader has.
marginal_curve <- function(fit, subs, xs, extra = NULL) {
  nd <- tidyr::expand_grid(subs, x = xs)
  nd$n <- 1                       # n = 1 so epred returns a probability, not a count
  if (!is.null(extra)) nd <- tidyr::expand_grid(nd, extra)
  ep <- posterior_epred(fit, newdata = nd, ndraws = NMARG)   # re_formula = NULL: keep subjects
  key <- setdiff(names(nd), c("subj", "n"))
  g <- droplevels(interaction(nd[key], drop = TRUE, sep = "|"))
  m <- rowsum(t(ep), g) / as.vector(table(g))                # cells x draws
  out <- as.data.frame(do.call(rbind, strsplit(rownames(m), "|", fixed = TRUE)))
  names(out) <- key
  out$x  <- as.numeric(out$x)
  out$m  <- apply(m, 1, median)
  out$lo <- apply(m, 1, quantile, 0.025)
  out$hi <- apply(m, 1, quantile, 0.975)
  out
}

# --- pooled observed bins, with the model's prediction for them -------------
# posterior_predict, not posterior_epred. epred is the expected proportion, so
# its spread is uncertainty in the mean with no binomial sampling noise in it;
# used as a predictive interval it is far too narrow in thinly sampled bins and
# reports misfit that is nothing but noise. predict draws actual counts.
#
# Subject random effects stay in (re_formula default), so each row is predicted
# for the participant who actually produced it. This matters here more than
# usual: the HRD staircase concentrates trials near each participant's own
# threshold, so a bin at an extreme dBPM is a biased subset of people rather
# than a fair sample, and only a prediction over the real trials respects that.
pooled_ppc <- function(fit, by = character(0), binwidth = 5, min_n = 30) {
  md <- fit$data
  md$bin <- ifelse(abs(md$x) <= 40, round(md$x / binwidth) * binwidth, NA)
  keep <- !is.na(md$bin)
  ep <- posterior_predict(fit, ndraws = NPPC)[, keep, drop = FALSE]
  md <- md[keep, ]
  g <- droplevels(interaction(md[c(by, "bin")], drop = TRUE, sep = "|"))
  num <- rowsum(t(ep), g)
  den <- as.vector(rowsum(md$n, g))
  pp  <- num / den
  out <- as.data.frame(do.call(rbind, strsplit(rownames(num), "|", fixed = TRUE)))
  names(out) <- c(by, "x")
  out$x     <- as.numeric(out$x)
  out$p     <- as.vector(rowsum(md$y, g)) / den
  out$n     <- den
  out$pp_m  <- apply(pp, 1, median)
  out$pp_lo <- apply(pp, 1, quantile, 0.025)
  out$pp_hi <- apply(pp, 1, quantile, 0.975)
  out[out$n >= min_n, ]
}

# --- draws and subject summaries, every model ------------------------------
for (nm in names(MODELS)) {
  fit <- load_fit(nm)
  if (is.null(fit)) next
  message("=== ", nm)

  d <- as_draws_df(fit)
  keep <- grep("^r_", variables(d), value = TRUE, invert = TRUE)
  d <- subset_draws(d, variable = keep)
  if (THIN > 1) d <- thin_draws(d, thin = THIN)
  write_gz(as.data.frame(d), file.path(small_dir, paste0(nm, "_draws.csv.gz")),
           sprintf("%d draws x %d population variables", ndraws(d), length(keep)))

  # coef() is fixed plus random, so these are each participant's own threshold,
  # slope and lapse rather than a deviation from the group.
  cf <- coef(fit)$subj
  subj <- do.call(rbind, lapply(dimnames(cf)[[3]], function(p) data.frame(
    subj = dimnames(cf)[[1]], parameter = p,
    Estimate = cf[, "Estimate", p], Est.Error = cf[, "Est.Error", p],
    Q2.5 = cf[, "Q2.5", p], Q97.5 = cf[, "Q97.5", p], row.names = NULL
  )))
  write_gz(subj, file.path(small_dir, paste0(nm, "_subject.csv.gz")),
           sprintf("%d subjects x %d parameters", dim(cf)[1], dim(cf)[3]))

  rm(fit, d); gc(verbose = FALSE)
}

dat <- if (file.exists(data_path)) readRDS(data_path) else NULL

# --- what the z-scores mean ------------------------------------------------
# age and bmi enter the models z-scored over participants, so every coefficient
# on them is "per SD". A figure with a z-score on the axis is unreadable, and a
# reader cannot convert one back without these constants. The gender proportion
# is here too, because the age curves are marginalised over it rather than drawn
# at the reference level.
if (!is.null(dat) && !is.null(dat$subj_cov)) {
  sc <- dat$subj_cov
  write_gz(data.frame(
    variable = c("age", "bmi"),
    mean = c(mean(sc$age), mean(sc$bmi)),
    sd   = c(sd(sc$age), sd(sc$bmi)),
    min  = c(min(sc$age), min(sc$bmi)),
    max  = c(max(sc$age), max(sc$bmi)),
    n    = nrow(sc)
  ), file.path(small_dir, "scaling.csv.gz"),
  "centring and scaling constants for the z-scored covariates")

  # One row per participant. Small, and the data-inspection page needs it to
  # show who is in the sample before any model appears.
  cov_out <- sc[, intersect(c("subj", "age", "bmi", "age_z", "bmi_z"), names(sc))]
  if (!is.null(dat$trials)) {
    g <- dat$trials[!duplicated(dat$trials$subj), c("subj", "gender")]
    cov_out <- merge(cov_out, g, by = "subj", all.x = TRUE)
  }
  write_gz(cov_out, file.path(small_dir, "subject_covariates.csv.gz"),
           sprintf("%d participants: age, BMI, gender", nrow(cov_out)))
}

# --- psy_intero: the single-condition figures ------------------------------
fit <- load_fit("psy_intero")
if (!is.null(fit) && !is.null(dat)) {
  message("=== psy_intero curves")
  d0 <- dat$intero
  xs <- seq(-40, 40, by = 0.5)

  g <- data.frame(x = xs, n = 1)
  write_gz(bands(posterior_epred(fit, newdata = g, re_formula = NA, ndraws = NCURVE), g),
           file.path(small_dir, "psy_intero_curve_pop.csv.gz"),
           "average-subject psychometric curve, nested bands")

  write_gz(marginal_curve(fit, distinct(d0, subj), seq(-40, 40, by = 2)),
           file.path(small_dir, "psy_intero_curve_marginal.csv.gz"),
           "average of the subjects' curves")

  write_gz(pooled_ppc(fit), file.path(small_dir, "psy_intero_ppc_bins.csv.gz"),
           "pooled observed bins with 95% predictive intervals")

  # Every participant's curve at their posterior-mean parameters. A curve at the
  # mean parameter rather than the mean of the curve, which is the usual
  # convention for a spaghetti plot and is labelled as such in the docs.
  cf <- coef(fit)$subj
  xs_s <- seq(-40, 40, length.out = 61)
  write_gz(do.call(rbind, lapply(seq_len(dim(cf)[1]), function(i) data.frame(
             subj = dimnames(cf)[[1]][i], x = xs_s,
             p = psy_curve(xs_s, cf[i, "Estimate", "alpha_Intercept"],
                           cf[i, "Estimate", "beta_Intercept"],
                           cf[i, "Estimate", "lambda_Intercept"])))),
           file.path(small_dir, "psy_intero_curve_subjects.csv.gz"),
           sprintf("%d per-subject curves at posterior-mean parameters", dim(cf)[1]))

  # Three participants at full posterior width with their own trials, for the
  # single-subject figure: chosen by threshold rank so the page can show a
  # near-accurate, a typical, and a strongly biased participant.
  a <- cf[, "Estimate", "alpha_Intercept"]
  pick <- dimnames(cf)[[1]][order(a)[round(c(0.1, 0.5, 0.9) * length(a))]]
  ge <- expand.grid(x = seq(-40, 40, by = 1), subj = pick, n = 1,
                    stringsAsFactors = FALSE)
  write_gz(bands(posterior_epred(fit, newdata = ge, ndraws = NCURVE), ge),
           file.path(small_dir, "psy_intero_examples_curve.csv.gz"),
           "3 example subjects, nested bands")
  write_gz(d0[d0$subj %in% pick, c("subj", "x", "y", "n")],
           file.path(small_dir, "psy_intero_examples_data.csv.gz"),
           "observed trials for those 3 subjects")

  # A grid of participants, each curve against that participant's own data.
  # This is the fit check the Hierarchical Interoception toolbox recommends, and
  # it is the one that answers the question cleanly: a pooled plot mixes people
  # together, so a departure there can come from the pooling rather than from the
  # fit. Nothing is pooled here, so nothing is confounded.
  #
  # Curves come from coef() point estimates, as the toolbox does, rather than
  # from posterior_epred over a 16-subject grid: same line, far less to store.
  gpick <- dimnames(cf)[[1]][order(a)[round(seq(0.03, 0.97, length.out = 16) * length(a))]]
  xs_g <- seq(-40, 40, by = 1)
  write_gz(do.call(rbind, lapply(gpick, function(s) data.frame(
             subj = s, x = xs_g,
             p = psy_curve(xs_g, cf[s, "Estimate", "alpha_Intercept"],
                           cf[s, "Estimate", "beta_Intercept"],
                           cf[s, "Estimate", "lambda_Intercept"]),
             alpha = cf[s, "Estimate", "alpha_Intercept"]))),
           file.path(small_dir, "psy_intero_grid_curve.csv.gz"),
           "16 participants spanning the threshold range, fitted curves")
  write_gz(d0[d0$subj %in% gpick, c("subj", "x", "y", "n")],
           file.path(small_dir, "psy_intero_grid_data.csv.gz"),
           "observed trials for those 16 participants")
  rm(fit); gc(verbose = FALSE)
}

# --- psy_full: modality, gender, age ---------------------------------------
fit <- load_fit("psy_full")
if (!is.null(fit) && !is.null(dat)) {
  message("=== psy_full curves")
  d0 <- dat$both
  xs <- seq(-40, 40, by = 0.5)
  mods <- factor(c("Extero", "Intero"), levels = levels(d0$Modality))
  gens <- factor(c("Female", "Male"), levels = levels(d0$gender))

  g <- expand.grid(x = xs, Modality = mods, gender = gens,
                   age_z = 0, bmi_z = 0, n = 1)
  write_gz(bands(posterior_epred(fit, newdata = g, re_formula = NA, ndraws = NCURVE), g),
           file.path(small_dir, "psy_full_curve_gender.csv.gz"),
           "curves by modality and gender, nested bands")

  # age is z-scored, so -1.5 to +1.5 spans most of the sample.
  ga <- expand.grid(x = xs, Modality = mods, age_z = c(-1.5, 0, 1.5),
                    gender = factor("Female", levels = levels(d0$gender)),
                    bmi_z = 0, n = 1)
  write_gz(bands(posterior_epred(fit, newdata = ga, re_formula = NA, ndraws = NCURVE), ga),
           file.path(small_dir, "psy_full_curve_age.csv.gz"),
           "curves by modality across the age range")

  subs <- distinct(d0, subj, gender)
  write_gz(marginal_curve(fit, subs, seq(-40, 40, by = 2),
                          extra = data.frame(Modality = mods, age_z = 0, bmi_z = 0)),
           file.path(small_dir, "psy_full_curve_marginal.csv.gz"),
           "average of the subjects' curves, by modality and gender")

  write_gz(pooled_ppc(fit, by = c("Modality", "gender")),
           file.path(small_dir, "psy_full_ppc_bins.csv.gz"),
           "pooled observed bins by modality and gender, with predictive intervals")
  rm(fit); gc(verbose = FALSE)
}

# --- meta_full: confidence -------------------------------------------------
fit <- load_fit("meta_full")
if (!is.null(fit) && !is.null(dat)) {
  message("=== meta_full curves")
  d0 <- dat$trials
  g <- expand.grid(
    Accuracy = factor(c("incorrect", "correct"), levels = levels(d0$Accuracy)),
    Modality = factor(c("Extero", "Intero"), levels = levels(d0$Modality)),
    gender   = factor(c("Female", "Male"), levels = levels(d0$gender)),
    age_z = 0, bmi_z = 0)
  write_gz(bands(posterior_epred(fit, newdata = g, re_formula = NA, ndraws = NCURVE), g),
           file.path(small_dir, "meta_full_epred_accuracy.csv.gz"),
           "predicted confidence by accuracy, modality and gender")

  ga <- expand.grid(
    Accuracy = factor(c("incorrect", "correct"), levels = levels(d0$Accuracy)),
    Modality = factor(c("Extero", "Intero"), levels = levels(d0$Modality)),
    age_z = seq(-1.5, 1.5, by = 0.25),
    gender = factor("Female", levels = levels(d0$gender)), bmi_z = 0)
  write_gz(bands(posterior_epred(fit, newdata = ga, re_formula = NA, ndraws = NCURVE), ga),
           file.path(small_dir, "meta_full_epred_age.csv.gz"),
           "predicted confidence across the age range")

  # The observed distribution, binned. This is what justifies the model, so the
  # page needs to draw it without shipping 69,000 trials.
  br <- seq(0, 1, by = 0.02)
  write_gz(as.data.frame(table(
             Modality = d0$Modality, Accuracy = d0$Accuracy,
             bin = cut(d0$Confidence, breaks = br, include.lowest = TRUE))),
           file.path(small_dir, "meta_full_confidence_hist.csv.gz"),
           "observed confidence histogram, 50 bins")

  # Does the model reproduce the mass at exactly 0 and exactly 1? That is the
  # whole reason for using ordered beta rather than beta or Gaussian, so it is
  # the posterior predictive check that matters. A model that fits the interior
  # and misses the bounds has not done the job it was chosen for.
  yrep <- posterior_predict(fit, ndraws = NPPC)
  pb <- data.frame(
    bound = c("at 0", "at 1"),
    observed = c(mean(d0$Confidence == 0), mean(d0$Confidence == 1)),
    pred_m  = c(median(rowMeans(yrep == 0)), median(rowMeans(yrep == 1))),
    pred_lo = c(quantile(rowMeans(yrep == 0), 0.025), quantile(rowMeans(yrep == 1), 0.025)),
    pred_hi = c(quantile(rowMeans(yrep == 0), 0.975), quantile(rowMeans(yrep == 1), 0.975))
  )
  write_gz(pb, file.path(small_dir, "meta_full_ppc_bounds.csv.gz"),
           "observed vs predicted mass at each bound")

  write_gz(d0 %>% group_by(Modality, Accuracy) %>%
             summarise(at_zero = mean(Confidence == 0), at_one = mean(Confidence == 1),
                       mean_conf = mean(Confidence), n = n(), .groups = "drop"),
           file.path(small_dir, "meta_full_bound_mass.csv.gz"),
           "bound mass and mean confidence by cell")
  rm(fit); gc(verbose = FALSE)
}

# --- what it cost ----------------------------------------------------------
tab <- bind_rows(sizes)
write.csv(tab, file.path(small_dir, "sizes.csv"), row.names = FALSE)

is_full <- grepl("release asset", tab$note)
committed <- tab[!is_full, ]
message("\n--- committed bundle ---")
print(committed[, c("file", "mb", "note")], row.names = FALSE)
message(sprintf("\ncommitted total:      %8.2f MB across %d files",
                sum(committed$bytes) / 1024^2, nrow(committed)))
message(sprintf("full fits (release):  %8.1f MB across %d files",
                sum(tab$bytes[is_full]) / 1024^2, sum(is_full)))
message(sprintf("reduction:            %8.0fx",
                sum(tab$bytes[is_full]) / sum(committed$bytes)))
