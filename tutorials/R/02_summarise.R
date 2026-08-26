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
#
# Figures are not written here. See R/04_figures.R.

suppressPackageStartupMessages({
  library(brms)
  library(dplyr)
  library(posterior)
})

source(Sys.getenv("HRD_MODELS", "R/models.R"))

out_dir <- Sys.getenv("HRD_OUT", "results")


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

# Figures live in R/04_figures.R, which draws them from results/small/ rather
# than from a fitted model. Nothing here should call ggsave: this script and that
# one once both wrote fig_effects.png into the same directory, and whichever ran
# last silently won.

message("summaries complete")
