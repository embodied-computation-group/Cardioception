"""Build the optional power-analysis notebook (part 7)."""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: c.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# Optional — How many participants, and how many trials?

**An optional module. Nothing else depends on it.** Do it if you are planning a study;
skip it if you came to learn the task.

By the end you will be able to answer, with numbers rather than convention, the question
that decides your budget: *how many people do I need, and how long should each session be?*

---

**Kernel:** `R (cardioception)`.

This module uses the power-analysis suite from the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception)
(Courtin et al., 2026) — the same toolbox the models in notebook 2 come from. It ships
both a Shiny app and the underlying simulation results. We use the results directly here,
and show you how to launch the app at the end.
""")

md(r"""
## Why this is not a G*Power question

For a simple two-group comparison of a measured quantity, power depends on the effect
size and the number of participants. Standard tools handle it.

The HRD breaks that in three ways.

**1. Your dependent variable is estimated, not measured.** Threshold and slope are
*parameters of a model fitted to each participant's responses*. They arrive with
uncertainty attached, and that uncertainty depends on how many trials the participant did.
A threshold from 30 trials is a noisier measurement than one from 90.

**2. You have two design knobs, not one.** More participants, or more trials each? They
cost differently — trials are cheap within a session, participants are expensive — and, as
you are about to see, they do not buy the same thing for the same parameter.

**3. The analysis strategy itself changes your power.** Fitting everyone in one
hierarchical model extracts more from the same data than fitting each participant
separately and testing the results. The simulations below quantify it for both threshold
and slope, against both a simple *t*-test and one that propagates each participant's
uncertainty.

So the question is not "how many participants" but **"which combination of participants,
trials, and analysis gets me adequate power for the parameter I care about"**.
""")

md(r"""
## What was simulated

The toolbox ran a full grid: for each combination below, data were generated from a known
ground truth, analysed, and it was recorded whether the effect was detected. 100
simulations per cell.

| Factor | Values |
|---|---|
| Participants | 15, 30, 60, 120 |
| Trials per participant | 30, 60, 90 |
| True effect size (Cohen's *d*) | 0, 0.2, 0.5, 0.8 |
| Parameter | Threshold, Slope |
| Analysis | Hierarchical model, a simple *t*-test, or a *t*-test propagating per-participant uncertainty |

The **`d = 0`** cells are the control: with no true effect, the detection rate should equal
the false-positive rate you are willing to accept. We check that before trusting anything else.

The next cell downloads the results — three small files totalling under 40 KB, so no need
to clone the 365 MB toolbox.
""")

co(r"""
suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readr); library(ggplot2); library(patchwork)
})

options(repr.plot.width = 11, repr.plot.height = 5)
theme_set(theme_minimal(base_size = 12) +
          theme(panel.grid.minor = element_blank(),
                plot.title = element_text(face = "bold", size = 11)))

ORANGE <- "#D55E00"; BLUE <- "#0072B2"; GREY <- "#a4acb8"; NAVY <- "#1F3352"

BASE <- paste0("https://raw.githubusercontent.com/embodied-computation-group/",
               "Hierarchical-Interoception/main/results/power%20analysis/Extracted/")

# Three separate result files, one per analysis strategy, exactly as the
# toolbox's own Figure 6 script combines them. There is also a merged
# all_data.csv in the repository, but its analysis labels are ambiguous, so we
# read the per-method files instead.
SOURCES <- list(
  list(dir = "Hierarchical", method = "Hierarchical model"),
  list(dir = "Psi",          method = "Simple t-test"),
  list(dir = "Psi_un",       method = "t-test, uncertainty propagated")
)

power <- bind_rows(lapply(SOURCES, function(src) {
  cache <- file.path(getwd(), paste0("power_", src$dir, ".csv"))
  if (!file.exists(cache)) {
    message("Downloading ", src$dir, " results ...")
    try(download.file(paste0(BASE, src$dir, "/df.csv"), cache, quiet = TRUE),
        silent = TRUE)
  }
  if (!file.exists(cache) || file.size(cache) < 1000)
    stop("Could not download ", src$dir, "/df.csv - check your connection.")
  read_csv(cache, show_col_types = FALSE) |> mutate(method = src$method)
}))

power <- power |> rename(power = mean, n_sims = n)

wide <- power |>
  select(parameter, subjects, trials, effect_size, method, power) |>
  pivot_wider(names_from = method, values_from = power) |>
  rename(h = `Hierarchical model`, s = `Simple t-test`,
         u = `t-test, uncertainty propagated`)

cat("Loaded", nrow(power), "cells across", n_distinct(power$method), "analysis strategies.\n")

cat("\nGrid:\n")
cat("  participants  ", paste(sort(unique(power$subjects)), collapse = ", "), "\n")
cat("  trials        ", paste(sort(unique(power$trials)),   collapse = ", "), "\n")
cat("  effect sizes  ", paste(sort(unique(power$effect_size)), collapse = ", "), "\n")
cat("  analyses      ", paste(sort(unique(power$method)), collapse = " | "), "\n")
cat("  simulations per cell:", unique(power$n_sims), "\n")
""")

md(r"""
## First: does the null behave?

Before reading any power number, check the `d = 0` cells. If a procedure claims an effect
more than 5% of the time when there is none, its "power" elsewhere is not power — it is
just a higher rate of claiming things.

With only 100 simulations per cell the Monte Carlo error is substantial: the standard error
on a proportion near 0.05 is about 0.022, so individual cells scattering between roughly
0.01 and 0.09 is expected. Read the **median**, not the extremes.

This check earns its place here. The three strategies do *not* all sit at nominal, and that
changes how you should read their power.
""")

co(r"""
null_rates <- power |>
  filter(effect_size == 0) |>
  group_by(parameter, method) |>
  summarise(min = min(power), median = median(power), max = max(power),
            cells = n(), .groups = "drop")

print(as.data.frame(null_rates), row.names = FALSE)

mc_se <- sqrt(0.05 * 0.95 / 100)
cat(sprintf("\nMonte Carlo SE at a true rate of 0.05, with 100 sims: %.3f\n", mc_se))
cat(sprintf("So single cells anywhere in roughly %.2f to %.2f are consistent with nominal.\n",
            max(0, 0.05 - 2 * mc_se), 0.05 + 2 * mc_se))
hi <- null_rates |> filter(median > 0.05 + 2 * mc_se)
lo <- null_rates |> filter(median < 0.05 - 2 * mc_se)

if (nrow(hi)) {
  cat("\n[!] Above nominal - these claim effects more often than 5% when there are none:\n")
  for (i in seq_len(nrow(hi)))
    cat(sprintf("      %s, %s: %.3f\n", hi$parameter[i], hi$method[i], hi$median[i]))
}
if (nrow(lo)) {
  cat("\n[i] Below nominal - conservative, which costs power elsewhere:\n")
  for (i in seq_len(nrow(lo)))
    cat(sprintf("      %s, %s: %.3f\n", lo$parameter[i], lo$method[i], lo$median[i]))
}
cat("\nThe hierarchical model sits at nominal for both parameters. Read the power\n")
cat("numbers below with these rates in mind: a method that over-rejects under the\n")
cat("null is not purely 'more powerful', and one that under-rejects pays for it.\n")
""")

md(r"""
Worth pausing on that output. The hierarchical model sits at the nominal rate. The simple
*t*-test runs low (medians around 0.01–0.02, though within Monte Carlo error of nominal),
which is consistent with it also detecting less when there *is* an effect. The
uncertainty-propagating *t*-test runs **above** nominal for threshold, so some of its
apparent power there is bought by a higher false-positive rate rather than by better
estimation.

This is exactly why a power comparison is only meaningful alongside the null behaviour.
Comparing detection rates between methods calibrated differently would flatter whichever
one rejects most readily.

## The power grid

Now the substance. Each panel is one parameter; each line is a number of trials; colour is
the analysis strategy. The dashed line is 80% power.
""")

co(r"""
D <- 0.5   # <-- change this to 0.2 or 0.8 and re-run

grid_plot <- power |>
  filter(effect_size == D) |>
  ggplot(aes(subjects, power, colour = method)) +
  geom_hline(yintercept = 0.8, linetype = "dashed", colour = GREY) +
  geom_line(linewidth = 0.9) +
  geom_point(size = 1.7) +
  facet_grid(trials ~ parameter,
             labeller = labeller(trials = \(x) paste(x, "trials"))) +
  scale_colour_manual(values = c("Hierarchical model" = ORANGE,
                                 "Simple t-test" = "#CC79A7",
                                 "t-test, uncertainty propagated" = BLUE),
                      name = "Analysis") +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.25)) +
  labs(title = paste0("Power to detect a true effect of d = ", D),
       subtitle = "Dashed line = 80% power",
       x = "Participants", y = "Power")

options(repr.plot.width = 10, repr.plot.height = 7)
grid_plot
""")

md(r"""
## The two findings that should change your design

Read them off the plot, then confirm with the table below.
""")

co(r"""
tbl <- wide |>
  filter(effect_size == D) |>
  select(parameter, subjects, trials, h) |>
  pivot_wider(names_from = trials, values_from = h, names_prefix = "trials_")

cat(sprintf("Power at d = %.1f, hierarchical model:\n\n", D))
print(as.data.frame(tbl), row.names = FALSE)

gain_trials_thr <- wide |> filter(effect_size == D, parameter == "Threshold",
                                  subjects == 30) |> arrange(trials) |> pull(h)
gain_trials_slp <- wide |> filter(effect_size == D, parameter == "Slope",
                                  subjects == 30) |> arrange(trials) |> pull(h)

cat(sprintf("\nAt 30 participants, going from 30 to 90 trials each:\n"))
cat(sprintf("  Threshold:  %.2f -> %.2f   (gain %+.2f)\n",
            gain_trials_thr[1], gain_trials_thr[3],
            gain_trials_thr[3] - gain_trials_thr[1]))
cat(sprintf("  Slope:      %.2f -> %.2f   (gain %+.2f)\n",
            gain_trials_slp[1], gain_trials_slp[3],
            gain_trials_slp[3] - gain_trials_slp[1]))
""")

md(r"""
### 1. Threshold and slope have completely different economics

**Threshold is cheap, and buying more trials barely helps it.** Tripling the session
length at a fixed sample moves threshold power very little. What moves it is
participants.

The reason is structural: the threshold is the *location* of the psychometric function,
and Psi spends its trials right around that location. You pin the 50% point down quickly,
and after that extra trials are refining something already well estimated.

**Slope is expensive, and it needs the trials.** Power for the slope is far lower
everywhere, and unlike threshold it improves substantially with session length. The slope
is the *width* of the function, which is only constrained by responses spread across the
transition — and those accumulate slowly.

The design consequence is direct. **If your hypothesis is about discrimination precision
rather than bias, a short session will not save you by adding participants.** You need both.
And you should decide which parameter your hypothesis is actually about before you collect
anything, because the cheapest design for one is not the cheapest for the other.

### 2. The hierarchical advantage is real — but only where you look

Notebook 2 argued structurally that pooling participants beats analysing them one at a
time. The simulations let us put a number on that, and the number is **not the same for
both parameters**. Read the next cell before believing either direction.
""")

co(r"""
# Compare against each two-stage alternative separately. Floor and ceiling cells
# compress any difference, so the informative range is where the comparator has
# room to move: power between 0.2 and 0.95.
cmp <- wide |>
  filter(effect_size > 0) |>
  mutate(vs_simple = h - s, vs_uncert = h - u)

informative <- cmp |> filter(s >= 0.2, s <= 0.95)

summary_tbl <- informative |>
  group_by(parameter) |>
  summarise(cells = n(),
            median_vs_simple = round(median(vs_simple), 3),
            better_vs_simple = sum(vs_simple > 0),
            median_vs_uncert = round(median(vs_uncert), 3),
            largest_gain     = round(max(vs_simple), 2),
            .groups = "drop")

cat("Hierarchical advantage, informative cells only (simple t-test power 0.2-0.95):\n\n")
print(as.data.frame(summary_tbl), row.names = FALSE)

cat("\nSlope, d = 0.5, power by design and analysis:\n\n")
print(as.data.frame(
  wide |> filter(parameter == "Slope", effect_size == 0.5) |>
    select(subjects, trials, hierarchical = h, simple_t = s, uncert_t = u)
), row.names = FALSE)
""")

md(r"""
**The hierarchical model wins for both parameters, and it wins nearly everywhere.**

For **threshold** the gain is large: a median of about **+0.19** over the simple *t*-test in
the informative range, and it is ahead in *every* such cell. At 30 participants with
d = 0.5 that is roughly 0.90 against 0.71; at d = 0.2 with 120 participants, 0.84 against 0.57.

For **slope** the gain is smaller but consistently in the same direction — a median of about
**+0.04**, ahead in 19 of 21 informative cells, reaching **+0.14** at its largest. The clearest
single case is 60 participants at 30 trials with d = 0.5: **0.87 hierarchical against 0.73**
for the simple *t*-test. Recovering 14 points of power without collecting another participant
is not a rounding error — reaching 0.87 the two-stage way would cost you real recruitment.

The size difference between the two parameters is worth understanding rather than
generalising from. Partial pooling buys most where per-participant estimates are noisy
relative to the between-participant spread. That describes threshold sharply; slope is
noisy for everyone, so there is proportionally less to redistribute. **Less does not mean
none** — the direction is consistent across the grid, which is what you would want before
committing to a method.

> Caveats that apply throughout. 100 simulations per cell gives a Monte Carlo SE near 0.05
> on any single power estimate, so read the pattern across cells rather than any one number.
> These simulations also assume the toolbox's generative model and normative priors.
""")

md(r"""
## Answering your own design question

Set the parameter you care about, the effect you consider worth detecting, and the power
you want. The cell reports the cheapest cells that clear it.
""")

co(r"""
# ---- your study --------------------------------------------------
MY_PARAMETER <- "Slope"      # "Threshold" or "Slope"
MY_EFFECT    <- 0.5          # smallest effect worth detecting (Cohen's d)
MY_POWER     <- 0.80
# -------------------------------------------------------------------

feasible <- wide |>
  filter(parameter == MY_PARAMETER, effect_size == MY_EFFECT, h >= MY_POWER) |>
  arrange(subjects, trials) |>
  select(subjects, trials, power = h)

cat(sprintf("%s, d = %.1f, target power %.0f%%, hierarchical model\n\n",
            MY_PARAMETER, MY_EFFECT, 100 * MY_POWER))

if (nrow(feasible) == 0) {
  cat("No cell in the simulated grid reaches that power.\n")
  best <- wide |>
    filter(parameter == MY_PARAMETER, effect_size == MY_EFFECT) |>
    arrange(desc(h)) |> head(3)
  cat("The best available were:\n\n")
  print(as.data.frame(best |> select(subjects, trials, power = h)), row.names = FALSE)
  cat("\nThe grid stops at 120 participants and 90 trials. Needing more than that\n")
  cat("is itself the finding: reconsider the effect size, or the parameter.\n")
} else {
  print(as.data.frame(feasible), row.names = FALSE)
  cheapest <- feasible |> slice(1)
  cat(sprintf("\nCheapest adequate design: %d participants x %d trials  (power %.2f)\n",
              cheapest$subjects, cheapest$trials, cheapest$power))
  cat("\nThat estimate carries a Monte Carlo SE of about 0.05, from 100 simulations.\n")
  cat("Treat a cell at 0.81 as 'about 80%', not 'above 80%', and prefer the next\n")
  cat("design up if the decision is close.\n")
}
""")

md(r"""
### Choosing an effect size honestly

This is where power analyses usually go wrong, and no amount of simulation fixes it.

**Do not** pick *d* by taking the effect from a small previous study. Published effects from
underpowered work are biased upward — that is the winner's curse, and designing to detect
an inflated effect is how you plan an underpowered study while believing otherwise.

Better options, in order:

1. **The smallest effect you would care about.** If a group difference of 2 ΔBPM in threshold
   would not change what you think, do not power for it.
2. **An effect from a large study**, ideally the normative datasets in the toolbox itself.
3. **A meta-analytic estimate**, if one exists for your contrast.

Then report it as a design decision: *"we powered to detect d = 0.5, the smallest difference
we considered theoretically meaningful"*, not *"we powered on the effect observed by X"*.
""")

md(r"""
## The interactive app

Everything above uses the simulation results directly. The toolbox also ships a **Shiny
app** over the same simulations, with smooth interpolated power contours rather than the
four discrete sample sizes we have here, plus a continuous effect-size axis.

It needs the full toolbox, which is a **365 MB** clone — worth it if you are actively
planning a study, not worth it during the workshop.

```bash
git clone https://github.com/embodied-computation-group/Hierarchical-Interoception.git
cd Hierarchical-Interoception
```

```r
install.packages(c("shiny", "tidyverse", "flextable", "posterior", "here"))

# Note the spaces in both the directory and the filename - the quotes are required
shiny::runApp("Ressources (app, tutorial, and updated thresholding scripts)/sample_size_exploration_app/shiny app.R")
```

> **Run it from the repository root.** The app resolves its data with `here::here()`, so
> starting R anywhere else makes it fail to find the simulation results.

Three tabs:

| Tab | What it gives you |
|---|---|
| **Power Grid** | Power contours over trials × participants, one line per analysis strategy |
| **Effect Size vs. Power** | Power against a continuous effect-size axis at a fixed design |
| **Manual Input** | A single design in, a formatted power estimate out |

The app's contours come from a model fitted to the simulations, which is why it can
interpolate between the grid points we plotted. The underlying evidence is the same.
""")

md(r"""
## What to take away

- **Decide which parameter your hypothesis is about before designing.** Threshold and slope
  have different economics, and the cheapest design for one is not the cheapest for the other.
- **Threshold: buy participants.** Extra trials add little once Psi has located the 50% point.
- **Slope: buy both.** Short sessions cannot be rescued by adding people.
- **Fit hierarchically.** It is more powerful than either two-stage alternative for both
  threshold and slope — substantially so for threshold, and by a consistent margin for
  slope that is worth several participants' worth of recruitment.
- **Choose the effect size as a judgement about meaning**, not by copying a previous estimate.

### References

- Courtin et al. (2026). *Hierarchical Interoception toolbox.* Behavior Research Methods. [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
- [The toolbox repository](https://github.com/embodied-computation-group/Hierarchical-Interoception) — models, priors, power suite
- Legrand et al. (2022). *The heart rate discrimination task.* Biological Psychology. [doi:10.1016/j.biopsycho.2021.108239](https://doi.org/10.1016/j.biopsycho.2021.108239)
""")

nb["cells"] = c
nb.metadata = {
    "kernelspec": {"display_name": "R (cardioception)", "language": "R",
                   "name": "ir-cardioception"},
    "language_info": {"name": "R"},
}

out = Path(__file__).parent / "03_power_analysis.ipynb"
nbf.write(nb, str(out))
print(f"wrote {out}  ({len(c)} cells)")
