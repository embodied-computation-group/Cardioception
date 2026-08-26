# Draw every figure in the documentation.
#
#   Rscript R/04_figures.R
#
# Reads only results/small/, never a fitted model. That is deliberate: the fits
# are 190-320 MB each and live in a GitHub release, but the figures should be
# reproducible by anyone who clones the repository. If this script ever needs a
# brmsfit, the missing quantity belongs in 03_compress.R instead.
#
# House style, borrowed from the lab's psychophysics figures: theme_classic with
# the grid off, gender in colour and modality in panels, nested credible bands
# rather than a single ribbon, no legend box (the legend is two coloured words),
# and millimetre sizing at 600 dpi so the same file works in the docs and in a
# manuscript.

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(ggdist)
  library(patchwork)
})

# Run from tutorials/. The default output is the documentation's own image
# directory, so regenerating a figure locally updates the page that shows it
# rather than leaving a second copy somewhere to go stale.
small_dir <- Sys.getenv("HRD_SMALL", "results/small")
fig_dir   <- Sys.getenv("HRD_FIGS", "../docs/source/images/tutorials")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

PAL    <- c(Female = "#E8735A", Male = "#3FA6A0")
MODPAL <- c(Intero = "#A8455F", Extero = "#2F6F8F")
NAVY   <- "#1f3352"
GREY   <- "grey70"

theme_set(theme_classic(base_size = 9))
th <- theme(
  axis.text       = element_text(size = 7.5, colour = "grey35"),
  axis.title      = element_text(size = 8.5, colour = "grey20"),
  axis.line       = element_line(linewidth = 0.3, colour = "grey40"),
  axis.ticks      = element_line(linewidth = 0.3, colour = "grey40"),
  panel.grid      = element_blank(),
  legend.position = "none",
  plot.title      = element_text(size = 9, colour = "grey20", hjust = 0.5),
  plot.subtitle   = element_text(size = 7.5, colour = "grey45", hjust = 0.5),
  strip.background = element_blank(),
  strip.text      = element_text(size = 8.5, colour = "grey20"),
  plot.margin     = margin(6, 6, 4, 4)
)

have <- function(f) file.exists(file.path(small_dir, f))
rd <- function(f) {
  d <- read.csv(gzfile(file.path(small_dir, f)), stringsAsFactors = FALSE)
  if ("Modality" %in% names(d)) d$Modality <- factor(d$Modality, c("Intero", "Extero"))
  if ("gender"   %in% names(d)) d$gender   <- factor(d$gender,   c("Female", "Male"))
  if ("Accuracy" %in% names(d)) d$Accuracy <- factor(d$Accuracy, c("incorrect", "correct"))
  if ("ci"       %in% names(d)) d$ci       <- factor(d$ci, sort(unique(d$ci), decreasing = TRUE))
  d
}
save_fig <- function(name, plot, w, h) {
  ggsave(file.path(fig_dir, paste0(name, ".png")), plot, width = w, height = h,
         units = "mm", dpi = 600, bg = "white")
  message("wrote ", name, ".png  (", w, " x ", h, " mm)")
}

# Two coloured words instead of a legend box.
word_legend <- function(pal, labels = names(pal)) {
  ggplot() +
    annotate("text", x = -0.06, y = 0, label = labels[1], colour = pal[[1]],
             size = 2.9, hjust = 1) +
    annotate("text", x = 0, y = 0, label = "/", colour = "grey60", size = 2.9) +
    annotate("text", x = 0.06, y = 0, label = labels[2], colour = pal[[2]],
             size = 2.9, hjust = 0) +
    scale_x_continuous(limits = c(-0.7, 0.7)) + theme_void()
}

inv_logit <- function(x) 1 / (1 + exp(-x))

# ===========================================================================
# 1. What the three parameters mean.
# A schematic, drawn from chosen values rather than from a fit, so the page can
# introduce alpha, beta and lambda before any data appears.
# ===========================================================================
{
  pf <- function(x, a, b, l) inv_logit(l) / 2 +
    (1 - inv_logit(l)) * pnorm(exp(b) * (x - a))
  x <- seq(-40, 40, by = 0.25)
  A <- -10; B <- log(1 / 8); L <- qlogis(0.04)
  base <- data.frame(x = x, p = pf(x, A, B, L))

  shift <- rbind(
    data.frame(x = x, p = pf(x, -22, B, L), what = "alpha = -22"),
    data.frame(x = x, p = pf(x, 2, B, L),  what = "alpha =  +2"))
  slope <- rbind(
    data.frame(x = x, p = pf(x, A, log(1 / 3), L), what = "steeper"),
    data.frame(x = x, p = pf(x, A, log(1 / 18), L), what = "shallower"))
  lapse <- rbind(
    data.frame(x = x, p = pf(x, A, B, qlogis(0.20)), what = "lambda = 0.20"),
    data.frame(x = x, p = pf(x, A, B, qlogis(0.001)), what = "lambda = 0"))

  panel <- function(extra, title, sub) {
    ggplot(base, aes(x, p)) +
      geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.3) +
      geom_vline(xintercept = 0, linetype = "dotted", colour = GREY, linewidth = 0.3) +
      geom_line(data = extra, aes(group = what), colour = "grey65", linewidth = 0.45) +
      geom_line(colour = NAVY, linewidth = 0.85) +
      scale_y_continuous(breaks = c(0, 0.5, 1), limits = c(0, 1)) +
      labs(title = title, subtitle = sub, x = NULL, y = NULL) + th
  }

  p1 <- panel(shift, "alpha  threshold", "where the curve sits") +
    annotate("segment", x = A, xend = A, y = 0, yend = 0.5,
             linetype = "dashed", colour = NAVY, linewidth = 0.35) +
    annotate("text", x = A - 1.5, y = 0.13, label = "alpha", colour = NAVY,
             size = 2.5, hjust = 1) +
    labs(y = "P(respond \"faster\")")
  p2 <- panel(slope, "beta  slope", "how sharply it rises") +
    labs(x = expression(Delta*"BPM (tone - true heart rate)"))
  p3 <- panel(lapse, "lambda  lapse rate", "how flat the asymptotes are")

  fig <- (p1 | p2 | p3)
  save_fig("fig_parameters", fig, 180, 62)
}

# ===========================================================================
# 2. Three participants, with their own trials.
# The point of the page: the same three-parameter curve describes people who
# behave very differently.
# ===========================================================================
if (have("psy_intero_examples_curve.csv.gz")) {
  cur <- rd("psy_intero_examples_curve.csv.gz")
  obs <- rd("psy_intero_examples_data.csv.gz")

  # The staircase revisits a handful of intensities many times, so pool by
  # intensity and size the point by how often it was actually presented.
  obs <- obs %>% group_by(subj, x) %>%
    summarise(p = sum(y) / sum(n), n = sum(n), .groups = "drop") %>%
    filter(n >= 3)

  ord <- cur %>% filter(ci == max(as.numeric(as.character(cur$ci)))) %>%
    group_by(subj) %>%
    summarise(a = x[which.min(abs(m - 0.5))], .groups = "drop") %>%
    arrange(a)
  lab <- setNames(sprintf("threshold %+.0f dBPM", ord$a), ord$subj)
  cur$subj <- factor(cur$subj, ord$subj, lab[ord$subj])
  obs$subj <- factor(obs$subj, ord$subj, lab[ord$subj])

  fig <- ggplot(cur, aes(x)) +
    geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.3) +
    geom_vline(xintercept = 0, linetype = "dotted", colour = GREY, linewidth = 0.3) +
    geom_ribbon(aes(ymin = lo, ymax = hi, group = ci), fill = MODPAL[["Intero"]],
                alpha = 0.22) +
    geom_line(aes(y = m), colour = MODPAL[["Intero"]], linewidth = 0.7) +
    geom_point(data = obs, aes(y = p, size = n), colour = NAVY, alpha = 0.55,
               stroke = 0) +
    scale_size_area(max_size = 2.4) +
    scale_y_continuous(breaks = c(0, 0.5, 1)) +
    coord_cartesian(ylim = c(0, 1)) +
    facet_wrap(~subj) +
    labs(x = expression(Delta*"BPM (tone - true heart rate)"),
         y = "P(respond \"faster\")",
         title = "Three participants, ordered by threshold",
         subtitle = paste("Points are observed proportions, sized by trials.",
                          "Bands are 50, 80 and 95% credible intervals.")) +
    th
  save_fig("fig_single_subjects", fig, 180, 68)
}

# ===========================================================================
# 3. Everyone at once: every participant's curve, with the group curve over it.
#
# Two figures rather than one panel pair, deliberately. This one is the plain
# picture of the sample and belongs in the main flow. The comparison between the
# two kinds of group average is a genuine subtlety, but it derails a first
# reading, so it gets its own figure and its own aside at the end of a page.
# ===========================================================================
if (have("psy_intero_curve_subjects.csv.gz")) {
  spag <- rd("psy_intero_curve_subjects.csv.gz")
  pop  <- rd("psy_intero_curve_pop.csv.gz")
  pop1 <- pop[pop$ci == levels(pop$ci)[1], ]

  fig <- ggplot(spag, aes(x, p, group = subj)) +
    geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.3) +
    geom_vline(xintercept = 0, linetype = "dotted", colour = GREY, linewidth = 0.3) +
    geom_line(colour = MODPAL[["Intero"]], alpha = 0.07, linewidth = 0.25) +
    geom_line(data = pop1, aes(y = m, group = 1), colour = NAVY, linewidth = 1) +
    scale_y_continuous(breaks = c(0, 0.5, 1)) +
    coord_cartesian(ylim = c(0, 1)) +
    labs(x = expression(Delta*"BPM (tone - true heart rate)"),
         y = "P(respond \"faster\")",
         title = paste0("All ", length(unique(spag$subj)), " participants, and the group"),
         subtitle = paste("each faint line is one participant at their",
                          "posterior-mean parameters")) + th
  save_fig("fig_all_participants", fig, 180, 76)

  # The figure that motivates pooling: the sample and the group above, then
  # individual participants with their posterior uncertainty below, each with
  # the group curve behind them. Two things should be visible at once. The
  # group curve is estimated from everybody, and how tightly any one person is
  # pinned down varies enormously, which is the quantity a two-stage analysis
  # silently discards.
  if (have("psy_intero_pooling_curve.csv.gz")) {
    pc <- rd("psy_intero_pooling_curve.csv.gz")
    pd <- rd("psy_intero_pooling_data.csv.gz") %>%
      group_by(subj, x) %>%
      summarise(p = sum(y) / sum(n), n = sum(n), .groups = "drop")

    ord <- pc %>% distinct(subj, sd_alpha) %>% arrange(sd_alpha)
    lab <- setNames(sprintf("threshold SD %.1f dBPM", ord$sd_alpha), ord$subj)
    pc$subj <- factor(pc$subj, ord$subj, lab[ord$subj])
    pd$subj <- factor(pd$subj, ord$subj, lab[ord$subj])

    top <- fig + labs(title = NULL, subtitle = NULL) +
      annotate("text", x = -39, y = 0.96, hjust = 0, size = 2.5, colour = NAVY,
               label = paste0("all ", length(unique(spag$subj)),
                              " participants, and the group curve"))

    bot <- ggplot(pc, aes(x)) +
      geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.25) +
      geom_line(data = pop1, aes(x, m), colour = "grey60", linewidth = 0.5,
                linetype = "dashed", inherit.aes = FALSE) +
      geom_ribbon(aes(ymin = lo, ymax = hi, group = ci), fill = MODPAL[["Intero"]],
                  alpha = 0.22) +
      geom_line(aes(y = m), colour = MODPAL[["Intero"]], linewidth = 0.6) +
      geom_point(data = pd, aes(x, p, size = n), colour = NAVY, alpha = 0.5,
                 stroke = 0, inherit.aes = FALSE) +
      scale_size_area(max_size = 1.8) +
      scale_y_continuous(breaks = c(0, 0.5, 1)) +
      coord_cartesian(ylim = c(0, 1)) +
      facet_wrap(~subj, nrow = 1) +
      labs(x = expression(Delta*"BPM (tone - true heart rate)"),
           y = "P(\"faster\")",
           subtitle = paste("four participants with their 50, 80 and 95%",
                            "intervals. Grey dashed is the group curve.")) +
      th + theme(strip.text = element_text(size = 7, colour = "grey35"),
                 axis.text = element_text(size = 6.5))

    save_fig("fig_pooling", top / bot + plot_layout(heights = c(1, 0.85)), 180, 120)
  }

  # The aside figure. Kept out of the main flow, and referenced from one place.
  if (have("psy_intero_curve_marginal.csv.gz") && have("psy_intero_ppc_bins.csv.gz")) {
    marg <- rd("psy_intero_curve_marginal.csv.gz")
    ppc  <- rd("psy_intero_ppc_bins.csv.gz")
    two <- ggplot(pop, aes(x)) +
      geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.3) +
      geom_vline(xintercept = 0, linetype = "dotted", colour = GREY, linewidth = 0.3) +
      geom_line(aes(y = m, group = ci), colour = NAVY, linewidth = 0.7,
                linetype = "dashed") +
      geom_line(data = marg, aes(x, m), colour = MODPAL[["Intero"]], linewidth = 1,
                inherit.aes = FALSE) +
      geom_point(data = ppc, aes(x, p, size = n), colour = "grey35", alpha = 0.7,
                 stroke = 0, inherit.aes = FALSE) +
      scale_size_area(max_size = 2.4) +
      scale_y_continuous(breaks = c(0, 0.5, 1)) +
      coord_cartesian(ylim = c(0, 1)) +
      labs(x = expression(Delta*"BPM"), y = "P(respond \"faster\")",
           title = "Two group averages that are not the same",
           subtitle = paste("dashed: the average participant's curve.",
                            "solid: the average of the participants' curves.",
                            "points: observed")) + th
    save_fig("fig_two_averages", two, 180, 76)
  }
}

# ===========================================================================
# 3b. The fit check that is not confounded by pooling.
#
# Sixteen participants spanning the threshold range, each fitted curve against
# that participant's own trials. This is what the Hierarchical Interoception
# toolbox does, and it is the right primary check: nothing is pooled, so a
# departure here is misfit rather than an artefact of mixing people together.
# ===========================================================================
if (have("psy_intero_grid_curve.csv.gz") && have("psy_intero_grid_data.csv.gz")) {
  gc_ <- rd("psy_intero_grid_curve.csv.gz")
  gd  <- rd("psy_intero_grid_data.csv.gz")

  gd <- gd %>% group_by(subj, x) %>%
    summarise(p = sum(y) / sum(n), n = sum(n), .groups = "drop")

  ord <- gc_ %>% distinct(subj, alpha) %>% arrange(alpha)
  lab <- setNames(sprintf("%+.0f", ord$alpha), ord$subj)
  gc_$subj <- factor(gc_$subj, ord$subj, lab[ord$subj])
  gd$subj  <- factor(gd$subj,  ord$subj, lab[ord$subj])

  fig <- ggplot(gc_, aes(x, p)) +
    geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.25) +
    geom_vline(xintercept = 0, linetype = "dotted", colour = GREY, linewidth = 0.25) +
    geom_line(colour = MODPAL[["Intero"]], linewidth = 0.6) +
    geom_point(data = gd, aes(x, p, size = n), colour = NAVY, alpha = 0.5, stroke = 0) +
    scale_size_area(max_size = 1.6) +
    scale_y_continuous(breaks = c(0, 0.5, 1)) +
    # Match the curve's own range, or the line stops dead at 40 while a handful
    # of trials carry on to 50 and it reads as the model giving up.
    coord_cartesian(ylim = c(0, 1), xlim = c(-40, 40)) +
    facet_wrap(~subj, ncol = 4) +
    labs(x = expression(Delta*"BPM"), y = "P(respond \"faster\")",
         title = "Sixteen participants, each against their own data",
         subtitle = "panel labels are that participant's threshold in dBPM") +
    th + theme(strip.text = element_text(size = 7, colour = "grey35"),
               axis.text = element_text(size = 6))
  save_fig("fig_subject_fits", fig, 180, 150)
}

# ===========================================================================
# 4. Modality and gender.
# Modality in panels, gender in colour. The interoceptive shift is large enough
# that it has to be seen next to the auditory control to be read properly.
# ===========================================================================
if (have("psy_full_curve_gender.csv.gz")) {
  cur <- rd("psy_full_curve_gender.csv.gz")
  ppc <- if (have("psy_full_ppc_bins.csv.gz")) rd("psy_full_ppc_bins.csv.gz") else NULL

  main <- ggplot(cur, aes(x)) +
    geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.3) +
    geom_vline(xintercept = 0, linetype = "dotted", colour = GREY, linewidth = 0.3) +
    geom_ribbon(aes(ymin = lo, ymax = hi, fill = gender,
                    group = interaction(gender, ci)), alpha = 0.20) +
    geom_line(aes(y = m, colour = gender, group = interaction(gender, ci)),
              linewidth = 0.7) +
    scale_colour_manual(values = PAL) + scale_fill_manual(values = PAL) +
    scale_y_continuous(breaks = c(0, 0.5, 1)) +
    coord_cartesian(ylim = c(0, 1)) +
    facet_wrap(~Modality) +
    labs(x = expression(Delta*"BPM (tone - reference)"), y = "P(respond \"faster\")",
         title = "Psychometric functions by modality and gender",
         subtitle = "at the sample mean of age and BMI") + th

  fig <- main / word_legend(PAL) + plot_layout(heights = c(1, 0.08))
  save_fig("fig_modality_gender", fig, 180, 76)

  if (!is.null(ppc)) {
    # Predictions against data, and nothing else. The curve of the average
    # participant is a different quantity, and it belongs beside the effects
    # table it describes rather than on a check of fit: pooled data do not
    # estimate it, so drawing it here only invites the reader to measure the
    # points against the wrong line. Both lines together live on fig_two_averages,
    # where the distinction between them is the actual subject.
    #
    # What is left is all model prediction of the pooled quantity: the bars
    # discretely, per bin, and the line continuously.
    marg <- if (have("psy_full_curve_marginal.csv.gz"))
      rd("psy_full_curve_marginal.csv.gz") else NULL

    chk <- ggplot(ppc, aes(x)) +
      geom_hline(yintercept = 0.5, linetype = "dotted", colour = GREY, linewidth = 0.3) +
      geom_linerange(aes(ymin = pp_lo, ymax = pp_hi, colour = gender),
                     alpha = 0.35, linewidth = 1.1) +
      { if (!is.null(marg))
          geom_line(data = marg, aes(x, m, colour = gender, group = gender),
                    linewidth = 0.8, alpha = 0.9, inherit.aes = FALSE) } +
      geom_point(aes(y = p, colour = gender, size = n), alpha = 0.8, stroke = 0) +
      scale_colour_manual(values = PAL) + scale_size_area(max_size = 2.2) +
      scale_y_continuous(breaks = c(0, 0.5, 1)) +
      coord_cartesian(ylim = c(0, 1)) +
      facet_wrap(~Modality) +
      labs(x = expression(Delta*"BPM"), y = "P(respond \"faster\")",
           title = "Posterior predictive check",
           subtitle = paste("points are observed, sized by trials.",
                            "Line and bars are what the model predicts for them.")) + th
    save_fig("fig_ppc_modality_gender", chk / word_legend(PAL) +
               plot_layout(heights = c(1, 0.08)), 180, 76)
  }
}

# ===========================================================================
# 5. Where the effects are.
# Threshold and slope terms on one axis, standardised within draw by the
# between-subject SD of the same parameter. The six terms do not share a unit
# otherwise: alpha is in dBPM, beta is a log slope. Dividing within the draw
# rather than by the posterior mean SD carries the uncertainty in that SD into
# the interval, which is the point of doing it at all. Native units are printed
# in the margin, because they are what anyone will report.
# ===========================================================================
if (have("psy_full_draws.csv.gz")) {
  dr <- rd("psy_full_draws.csv.gz")
  terms <- c("ModalityIntero", "genderMale", "age_z", "bmi_z",
             "ModalityIntero.genderMale", "ModalityIntero.age_z")
  pretty <- c("Intero vs Extero", "male vs female", "age (per SD)", "BMI (per SD)",
              "Intero x male", "Intero x age")

  con <- bind_rows(lapply(c("alpha", "beta"), function(par) {
    den <- dr[[paste0("sd_subj__", par, "_Intercept")]]
    bind_rows(lapply(seq_along(terms), function(i) {
      col <- paste0("b_", par, "_", terms[i])
      if (!col %in% names(dr)) return(NULL)
      data.frame(parameter = par, term = pretty[i],
                 raw = dr[[col]], std = dr[[col]] / den)
    }))
  }))
  con$parameter <- factor(con$parameter, c("alpha", "beta"),
                          c("alpha  threshold", "beta  log slope"))
  con$term <- factor(con$term, rev(pretty))

  lab <- con %>% group_by(parameter, term) %>%
    summarise(native = sprintf("%+.2f [%+.2f, %+.2f]", median(raw),
                               quantile(raw, 0.025), quantile(raw, 0.975)),
              .groups = "drop")

  rng <- quantile(con$std, c(0.002, 0.998))
  rng <- rng + c(-1, 1) * diff(rng) * 0.04

  fig <- ggplot(con, aes(std, term)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey55", linewidth = 0.35) +
    stat_pointinterval(.width = c(0.66, 0.95), point_size = 1.4,
                       interval_size_range = c(0.4, 1.1), colour = NAVY) +
    geom_text(data = lab, aes(x = rng[2] + diff(rng) * 0.03, y = term, label = native),
              hjust = 0, size = 2.2, colour = "grey30", inherit.aes = FALSE) +
    facet_wrap(~parameter, scales = "free_x") +
    coord_cartesian(xlim = rng, clip = "off") +
    labs(x = "effect, in between-subject SDs", y = NULL,
         title = "Effects on threshold and slope") +
    th + theme(axis.text.y = element_text(size = 8, colour = "grey20"),
               axis.line.y = element_blank(), axis.ticks.y = element_blank(),
               panel.spacing.x = unit(24, "mm"),
               plot.margin = margin(3, 26, 3, 3, unit = "mm"))
  save_fig("fig_effects", fig, 180, 68)
}

# ===========================================================================
# 5b. The age effect, on the parameters themselves.
#
# Drawing three psychometric curves at three ages is a weak way to show a
# continuous predictor: the reader has to infer the trend from overlapping
# sigmoids. Plotting the parameter against age says it directly, and shows a
# flat line honestly when there is nothing there.
#
# Computed from the population draws rather than from a prediction grid, so it
# is exact and needs nothing but this bundle. Marginalised over gender at the
# sample proportion rather than drawn at the reference level, because "women
# only" is not what a reader assumes an age panel means.
# ===========================================================================
if (have("psy_full_draws.csv.gz") && have("scaling.csv.gz")) {
  dr <- rd("psy_full_draws.csv.gz")
  sc <- rd("scaling.csv.gz")
  age <- sc[sc$variable == "age", ]

  p_male <- 0.5
  if (have("subject_covariates.csv.gz")) {
    cv <- rd("subject_covariates.csv.gz")
    if ("gender" %in% names(cv)) p_male <- mean(cv$gender == "Male", na.rm = TRUE)
  }

  # Span where the participants actually are. Age here is strongly right-skewed,
  # so mean +/- 2 SD stops around 35 and leaves the line hanging in mid-air
  # under a third of the sample. Percentiles of the observed ages do not.
  age_rng <- c(age$min, age$max)
  if (have("subject_covariates.csv.gz")) {
    cv0 <- rd("subject_covariates.csv.gz")
    age_rng <- as.numeric(quantile(cv0$age, c(0.01, 0.99), na.rm = TRUE))
  }
  yrs <- seq(age_rng[1], age_rng[2], length.out = 80)
  z <- (yrs - age$mean) / age$sd

  # For each modality, the parameter as a linear function of age_z, averaged
  # over gender. Intero adds its own main effect and its own age slope.
  curve_for <- function(par, intero) {
    b   <- function(nm) if (nm %in% names(dr)) dr[[nm]] else 0
    a0  <- b(paste0("b_", par, "_Intercept")) + p_male * b(paste0("b_", par, "_genderMale"))
    if (intero) a0 <- a0 + b(paste0("b_", par, "_ModalityIntero")) +
        p_male * b(paste0("b_", par, "_ModalityIntero.genderMale"))
    slope <- b(paste0("b_", par, "_age_z"))
    if (intero) slope <- slope + b(paste0("b_", par, "_ModalityIntero.age_z"))
    # draws x ages
    v <- outer(a0, rep(1, length(z))) + outer(slope, z)
    if (par == "beta") v <- 1 / exp(v)          # report sigma in BPM, not log slope
    data.frame(
      age = yrs, Modality = if (intero) "Intero" else "Extero",
      parameter = if (par == "alpha") "threshold (dBPM)" else "slope sigma (BPM)",
      m  = apply(v, 2, median),
      lo = apply(v, 2, quantile, 0.025),
      hi = apply(v, 2, quantile, 0.975)
    )
  }

  ag <- bind_rows(lapply(c("alpha", "beta"), function(p)
    bind_rows(curve_for(p, FALSE), curve_for(p, TRUE))))
  ag$Modality <- factor(ag$Modality, c("Intero", "Extero"))
  ag$parameter <- factor(ag$parameter, c("threshold (dBPM)", "slope sigma (BPM)"))

  # No per-participant points here. Individual thresholds span roughly -50 to
  # +50 dBPM, so plotting them forces an axis on which a 0.6 dBPM-per-SD trend is
  # a flat line indistinguishable from no trend at all. The spread has its own
  # figure; this one is about the trend, and the axis should serve it.
  fig <- ggplot(ag, aes(age, m, colour = Modality, fill = Modality)) +
    geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.20, colour = NA) +
    geom_line(linewidth = 0.8) +
    scale_colour_manual(values = MODPAL) + scale_fill_manual(values = MODPAL) +
    facet_wrap(~parameter, scales = "free_y") +
    labs(x = "age (years)", y = NULL,
         title = "Age, on the parameters themselves",
         subtitle = paste("population means with 95% intervals, marginalised over",
                          "gender. Note the narrow axes: individuals vary far more.")) +
    th
  save_fig("fig_age", fig / word_legend(MODPAL, c("Intero", "Extero")) +
             plot_layout(heights = c(1, 0.09)), 180, 74)
}

# ===========================================================================
# 6. How the participants are spread out.
# The between-subject SDs the effects above are standardised against, shown as
# the distributions they summarise.
# ===========================================================================
if (have("psy_intero_subject.csv.gz")) {
  s <- rd("psy_intero_subject.csv.gz")
  s <- s %>% filter(parameter %in% c("alpha_Intercept", "beta_Intercept")) %>%
    mutate(value = ifelse(parameter == "beta_Intercept", 1 / exp(Estimate), Estimate),
           parameter = factor(parameter, c("alpha_Intercept", "beta_Intercept"),
                              c("threshold (dBPM)", "slope sigma (BPM)")))

  fig <- ggplot(s, aes(value)) +
    geom_histogram(bins = 42, fill = MODPAL[["Intero"]], colour = NA, alpha = 0.8) +
    geom_vline(data = s %>% group_by(parameter) %>%
                 summarise(m = median(value), .groups = "drop"),
               aes(xintercept = m), colour = NAVY, linetype = "dashed",
               linewidth = 0.4) +
    facet_wrap(~parameter, scales = "free") +
    labs(x = NULL, y = "participants",
         title = "How much participants differ",
         subtitle = "posterior means, one per participant; dashed line is the median") +
    th
  save_fig("fig_subject_spread", fig, 180, 62)
}

# ===========================================================================
# 7. Why confidence needs an ordered beta model.
# A quarter of the ratings sit exactly on a bound. Gaussian puts mass outside
# the scale, beta is undefined at the ends, and binning throws the ends away.
# ===========================================================================
if (have("meta_full_confidence_hist.csv.gz")) {
  h <- rd("meta_full_confidence_hist.csv.gz")
  h$mid <- as.numeric(sub("^[\\(\\[]([-0-9.e]+),.*$", "\\1", h$bin)) + 0.01

  left <- ggplot(h, aes(mid, Freq, fill = Modality)) +
    geom_col(width = 0.019, alpha = 0.85, position = "identity") +
    scale_fill_manual(values = MODPAL) +
    scale_x_continuous(breaks = c(0, 0.5, 1)) +   # 0.25 steps collide across facets
    facet_wrap(~Modality) +
    labs(x = "confidence", y = "trials",
         title = "The ratings pile up at both ends",
         subtitle = "which is what rules out a Gaussian or a plain beta") +
    th + theme(panel.spacing.x = unit(6, "mm"))

  fig <- left
  if (have("meta_full_ppc_bounds.csv.gz")) {
    pb <- rd("meta_full_ppc_bounds.csv.gz")
    # The predictive interval is narrower than the plotting symbol, so print the
    # numbers as well: an interval you cannot see reads as a missing interval
    # rather than as a tight one.
    pb$lab <- sprintf("%.3f\n[%.3f, %.3f]", pb$observed, pb$pred_lo, pb$pred_hi)
    right <- ggplot(pb, aes(bound)) +
      geom_linerange(aes(ymin = pred_lo, ymax = pred_hi), colour = "grey55",
                     linewidth = 3, alpha = 0.7) +
      geom_point(aes(y = observed), colour = MODPAL[["Intero"]], size = 2.4,
                 shape = 18) +
      geom_text(aes(y = observed, label = lab), hjust = -0.22, size = 2.1,
                colour = "grey30", lineheight = 0.95) +
      scale_x_discrete(expand = expansion(add = c(0.5, 1.5))) +
      expand_limits(y = 0) +
      labs(x = NULL, y = "proportion of trials",
           title = "Are they reproduced?",
           subtitle = "observed, with 95% predicted") + th
    fig <- (left | right) + plot_layout(widths = c(2.1, 1))
  }
  save_fig("fig_confidence_distribution", fig, 180, 66)
}

# ===========================================================================
# 8. Metacognitive sensitivity, stated directly.
# The gap between correct and incorrect is the quantity the m-ratio is usually
# used for, on the response scale, without a ratio and without binning.
# ===========================================================================
if (have("meta_full_epred_accuracy.csv.gz")) {
  e <- rd("meta_full_epred_accuracy.csv.gz")
  wide <- e %>% filter(ci == 0.95)

  fig <- ggplot(wide, aes(Accuracy, m, colour = gender, group = gender)) +
    geom_line(position = position_dodge(0.16), linewidth = 0.6) +
    geom_linerange(aes(ymin = lo, ymax = hi), position = position_dodge(0.16),
                   linewidth = 0.9, alpha = 0.55) +
    geom_point(size = 2, position = position_dodge(0.16)) +
    scale_colour_manual(values = PAL) +
    facet_wrap(~Modality) +
    labs(x = NULL, y = "predicted confidence",
         title = "Confidence tracks accuracy",
         subtitle = "the gap is metacognitive sensitivity, on the response scale") +
    th
  save_fig("fig_confidence_accuracy",
           fig / word_legend(PAL) + plot_layout(heights = c(1, 0.09)), 180, 70)
}

# ===========================================================================
# 8b. Does metacognition change with age?
# The gap between the two lines is metacognitive sensitivity. If it stays the
# same width across the axis, sensitivity does not change with age, whatever
# overall confidence does. Two questions that a single ratio would confound.
# ===========================================================================
if (have("meta_full_epred_age.csv.gz") && have("scaling.csv.gz")) {
  e <- rd("meta_full_epred_age.csv.gz")
  sc <- rd("scaling.csv.gz")
  age <- sc[sc$variable == "age", ]
  e <- e %>% filter(ci == 0.95) %>% mutate(age = age_z * age$sd + age$mean)

  fig <- ggplot(e, aes(age, m, colour = Accuracy, fill = Accuracy)) +
    geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.18, colour = NA) +
    geom_line(linewidth = 0.8) +
    scale_colour_manual(values = c(incorrect = "#8a94a3", correct = MODPAL[["Intero"]])) +
    scale_fill_manual(values = c(incorrect = "#8a94a3", correct = MODPAL[["Intero"]])) +
    facet_wrap(~Modality) +
    labs(x = "age (years)", y = "predicted confidence",
         title = "Confidence and metacognitive sensitivity across age",
         subtitle = "the gap between the lines is sensitivity; its width is the question") +
    th
  save_fig("fig_confidence_age",
           fig / word_legend(c(correct = MODPAL[["Intero"]], incorrect = "#8a94a3"),
                             c("correct", "incorrect")) +
             plot_layout(heights = c(1, 0.09)), 180, 70)
}

message("\nfigures written to ", fig_dir)
