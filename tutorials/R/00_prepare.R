# Prepare HRD trial data for the tutorial fits.
#
# Reads the tutorial CSV, applies the coding the models expect, and writes three
# data frames as one RDS:
#
#   trials  one row per trial, for the confidence model
#   both    aggregated binomial data, both modalities, for the psychometric models
#   intero  the same, Intero only, for the minimal example
#
# Run this once before submitting the fits. It is cheap and can run on a login
# node, unlike everything downstream.

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})

args <- commandArgs(trailingOnly = TRUE)
in_csv <- if (length(args) >= 1) args[1] else "data/hrd_tutorial.csv"
out_rds <- if (length(args) >= 2) args[2] else "data/model_data.rds"

raw <- read_csv(in_csv, show_col_types = FALSE)
message(sprintf("read %d rows, %d subjects", nrow(raw), n_distinct(raw$Subject)))

# --- trial level -----------------------------------------------------------
# Drop trials with no decision: the participant ran out of time, so there is no
# response to model. These must be dropped, not recoded as incorrect.
trials <- raw %>%
  filter(Decision %in% c("More", "Less")) %>%
  mutate(
    subj = factor(Subject),
    Modality = factor(Modality, levels = c("Extero", "Intero")),
    gender = factor(gender, levels = c("Female", "Male")),
    resp = as.integer(Decision == "More"),
    x = Alpha
  )

# Covariates are subject level, so z-score them over subjects rather than over
# trials: otherwise participants with more trials pull the mean.
subj_cov <- trials %>%
  group_by(subj) %>%
  summarise(age = first(age), bmi = first(bmi), .groups = "drop") %>%
  mutate(
    age_z = as.numeric(scale(age)),
    bmi_z = as.numeric(scale(bmi))
  )

message(sprintf(
  "age mean %.1f sd %.1f | bmi mean %.1f sd %.1f | over %d subjects",
  mean(subj_cov$age), sd(subj_cov$age),
  mean(subj_cov$bmi), sd(subj_cov$bmi), nrow(subj_cov)
))

trials <- trials %>% left_join(subj_cov[, c("subj", "age_z", "bmi_z")], by = "subj")

# Confidence for the ordered beta model: onto [0, 1] keeping the exact bounds.
# Nudging them inward or dropping them would defeat the point of the model.
trials <- trials %>%
  mutate(
    Confidence = Confidence_raw / 100,
    Accuracy = factor(Accuracy, levels = c(0, 1), labels = c("incorrect", "correct"))
  )

stopifnot(all(trials$Confidence >= 0 & trials$Confidence <= 1, na.rm = TRUE))
message(sprintf(
  "confidence: %.1f%% of ratings sit exactly on a bound",
  100 * mean(trials$Confidence %in% c(0, 1), na.rm = TRUE)
))

# --- aggregate for the psychometric models ---------------------------------
# One row per subject x modality x intensity. With a Psi staircase most
# intensities are visited once, so n is usually 1. That is expected; binning x
# would throw away the stimulus placement the staircase worked to achieve.
aggregate_cells <- function(d) {
  d %>%
    filter(!is.na(x)) %>%
    group_by(subj, Modality, gender, age_z, bmi_z, x) %>%
    summarise(y = sum(resp), n = dplyr::n(), .groups = "drop")
}

both <- aggregate_cells(trials)
intero <- aggregate_cells(filter(trials, Modality == "Intero"))

message(sprintf("aggregated: both %d cells, intero %d cells", nrow(both), nrow(intero)))
message("cells with n > 1: ", sum(both$n > 1), " of ", nrow(both))

# Sanity check the direction of the response coding. Averaged over subjects,
# the proportion of "More" responses must increase with intensity. If this
# fails the psychometric curve will come out inverted.
trend <- both %>%
  mutate(bin = ntile(x, 5)) %>%
  group_by(bin) %>%
  summarise(p = sum(y) / sum(n), .groups = "drop")
message("proportion 'More' by intensity quintile: ",
        paste(sprintf("%.2f", trend$p), collapse = " "))
if (trend$p[1] > trend$p[nrow(trend)]) {
  stop("response coding looks inverted: p('More') falls as intensity rises")
}

dir.create(dirname(out_rds), showWarnings = FALSE, recursive = TRUE)
saveRDS(
  list(trials = trials, both = both, intero = intero, subj_cov = subj_cov),
  out_rds
)
message("wrote ", out_rds)
