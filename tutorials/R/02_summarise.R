# Turn fitted models into the small artefacts the tutorial pages read.
#
#   Rscript 02_summarise.R
#
# The tutorials do not fit anything: fitting takes hours. They load what this
# script writes. Everything here is small enough to commit.
#
# Outputs, into results/:
#   <model>_fixef.csv          fixed effects with credible intervals
#   <model>_diagnostics.txt    written by 01_fit.R, copied through unchanged
#   contrasts.csv              the effects the tutorial actually discusses
#   fig_*.png                  figures for the documentation

suppressPackageStartupMessages({
  library(brms)
  library(dplyr)
  library(ggplot2)
  library(posterior)
})

source(Sys.getenv("HRD_MODELS", "R/models.R"))

out_dir <- Sys.getenv("HRD_OUT", "results")
fig_dir <- Sys.getenv("HRD_FIGS", file.path(out_dir, "figures"))
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

NAVY <- "#1f3352"; MID <- "#2f4b73"; GREY <- "#8a94a3"
PAPER <- "#f7f6f2"; ROSE <- "#a8586b"

theme_hrd <- function() {
  theme_classic(base_size = 11) +
    theme(
      plot.background = element_rect(fill = PAPER, colour = NA),
      panel.background = element_rect(fill = PAPER, colour = NA),
      legend.background = element_rect(fill = PAPER, colour = NA),
      plot.title = element_text(colour = NAVY, size = 11),
      axis.text = element_text(colour = NAVY, size = 9)
    )
}

load_fit <- function(name) {
  p <- file.path(out_dir, paste0(name, ".rds"))
  if (!file.exists(p)) {
    message("missing fit, skipping: ", p)
    return(NULL)
  }
  readRDS(p)
}

# --- fixed effects tables --------------------------------------------------
all_fixef <- list()
for (nm in names(MODELS)) {
  fit <- load_fit(nm)
  if (is.null(fit)) next
  fx <- as.data.frame(fixef(fit))
  fx$term <- rownames(fx)
  fx$model <- nm
  rownames(fx) <- NULL
  write.csv(fx, file.path(out_dir, paste0(nm, "_fixef.csv")), row.names = FALSE)
  all_fixef[[nm]] <- fx
  message("wrote fixef for ", nm)
}

# --- the contrasts the tutorial discusses ----------------------------------
# Reported as posterior means with intervals and the posterior probability of
# being above zero, rather than as a threshold on whether an interval excludes
# zero.
contrast_table <- function(fit, model_name, terms) {
  draws <- as_draws_df(fit)
  rows <- lapply(terms, function(tm) {
    col <- paste0("b_", tm)
    if (!col %in% names(draws)) return(NULL)
    v <- draws[[col]]
    data.frame(
      model = model_name,
      term = tm,
      mean = mean(v),
      lower = quantile(v, 0.025, names = FALSE),
      upper = quantile(v, 0.975, names = FALSE),
      p_gt0 = mean(v > 0)
    )
  })
  bind_rows(rows)
}

contrasts <- list()
fit_full <- load_fit("psy_full")
if (!is.null(fit_full)) {
  contrasts$psy_full <- contrast_table(fit_full, "psy_full", c(
    "alpha_Intercept", "alpha_ModalityIntero",
    "alpha_genderMale", "alpha_age_z", "alpha_bmi_z",
    "alpha_ModalityIntero:genderMale", "alpha_ModalityIntero:age_z",
    "beta_Intercept", "beta_ModalityIntero",
    "beta_genderMale", "beta_age_z", "beta_bmi_z",
    "beta_ModalityIntero:genderMale", "beta_ModalityIntero:age_z"
  ))
}
fit_meta <- load_fit("meta_full")
if (!is.null(fit_meta)) {
  nms <- grep("^b_", names(as_draws_df(fit_meta)), value = TRUE)
  contrasts$meta_full <- contrast_table(
    fit_meta, "meta_full", sub("^b_", "", nms)
  )
}
if (length(contrasts)) {
  write.csv(bind_rows(contrasts), file.path(out_dir, "contrasts.csv"), row.names = FALSE)
  message("wrote contrasts.csv")
}

# --- figure: psychometric curves by gender ---------------------------------
# Posterior mean curves for the two genders in each modality, at the sample mean
# of age and BMI, which is what centring the covariates makes the intercept mean.
if (!is.null(fit_full)) {
  d <- readRDS(Sys.getenv("HRD_DATA", "data/model_data.rds"))$both
  grid <- expand.grid(
    x = seq(-40, 40, length.out = 120),
    Modality = factor(c("Extero", "Intero"), levels = levels(d$Modality)),
    gender = factor(c("Female", "Male"), levels = levels(d$gender)),
    age_z = 0, bmi_z = 0, n = 1
  )
  ep <- posterior_epred(fit_full, newdata = grid, re_formula = NA)
  grid$p <- colMeans(ep)
  grid$lo <- apply(ep, 2, quantile, 0.025)
  grid$hi <- apply(ep, 2, quantile, 0.975)

  p <- ggplot(grid, aes(x, p, colour = gender, fill = gender)) +
    geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.18, colour = NA) +
    geom_line(linewidth = 1) +
    geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY) +
    geom_vline(xintercept = 0, linetype = "dotted", colour = GREY) +
    facet_wrap(~Modality) +
    scale_colour_manual(values = c(Female = ROSE, Male = MID)) +
    scale_fill_manual(values = c(Female = ROSE, Male = MID)) +
    labs(x = "Intensity (dBPM)", y = "P(\"faster\")",
         title = "Posterior psychometric functions at mean age and BMI") +
    theme_hrd()
  ggsave(file.path(fig_dir, "fig_psychometric_gender.png"), p,
         width = 7.5, height = 3.4, dpi = 200)
  message("wrote fig_psychometric_gender.png")

  # --- figure: where the effects are ---------------------------------------
  fx <- all_fixef[["psy_full"]]
  eff <- fx %>%
    filter(grepl("^(alpha|beta)_", term), !grepl("Intercept", term)) %>%
    mutate(
      parameter = ifelse(grepl("^alpha", term), "alpha (threshold)", "beta (log slope)"),
      label = sub("^(alpha|beta)_", "", term)
    )
  p2 <- ggplot(eff, aes(Estimate, label)) +
    geom_vline(xintercept = 0, linetype = "dotted", colour = GREY) +
    geom_errorbarh(aes(xmin = Q2.5, xmax = Q97.5), height = 0.18, colour = MID) +
    geom_point(colour = NAVY, size = 2) +
    facet_wrap(~parameter, scales = "free_x") +
    labs(x = "Posterior estimate", y = NULL,
         title = "Effects on threshold and slope, with 95% credible intervals") +
    theme_hrd()
  ggsave(file.path(fig_dir, "fig_effects.png"), p2,
         width = 8, height = 3.2, dpi = 200)
  message("wrote fig_effects.png")
}

# --- figure: confidence by accuracy ----------------------------------------
if (!is.null(fit_meta)) {
  grid <- expand.grid(
    Accuracy = factor(c("incorrect", "correct"), levels = c("incorrect", "correct")),
    Modality = factor(c("Extero", "Intero")),
    gender = factor(c("Female", "Male")),
    age_z = 0, bmi_z = 0
  )
  ep <- posterior_epred(fit_meta, newdata = grid, re_formula = NA)
  grid$p <- colMeans(ep)
  grid$lo <- apply(ep, 2, quantile, 0.025)
  grid$hi <- apply(ep, 2, quantile, 0.975)

  p3 <- ggplot(grid, aes(Accuracy, p, colour = gender, group = gender)) +
    geom_errorbar(aes(ymin = lo, ymax = hi), width = 0.08,
                  position = position_dodge(0.2)) +
    geom_line(position = position_dodge(0.2)) +
    geom_point(size = 2, position = position_dodge(0.2)) +
    facet_wrap(~Modality) +
    scale_colour_manual(values = c(Female = ROSE, Male = MID)) +
    labs(x = NULL, y = "Predicted confidence",
         title = "Confidence by accuracy, on the response scale") +
    theme_hrd()
  ggsave(file.path(fig_dir, "fig_confidence.png"), p3,
         width = 7.5, height = 3.4, dpi = 200)
  message("wrote fig_confidence.png")
}

message("summaries complete")
