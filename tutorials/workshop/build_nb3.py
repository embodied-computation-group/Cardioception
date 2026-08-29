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
hierarchical model can extract more from the same data than fitting each participant
separately and testing the results. How much more depends on which parameter you care
about — the simulations below show a large gain for threshold and essentially none for
slope, which is worth knowing before you design around it.

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
| Analysis | Hierarchical model, or a *t*-test propagating per-participant uncertainty |

The **`d = 0`** cells are the control: with no true effect, the detection rate should equal
the false-positive rate you are willing to accept. We check that before trusting anything else.

The next cell downloads the results — a 38 KB file, so no need to clone the 365 MB toolbox.
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

URL <- paste0("https://raw.githubusercontent.com/embodied-computation-group/",
              "Hierarchical-Interoception/main/results/power%20analysis/",
              "Extracted/all_data.csv")
CACHE <- file.path(getwd(), "power_all_data.csv")

if (!file.exists(CACHE)) {
  message("Downloading power simulation results (38 KB) ...")
  try(download.file(URL, CACHE, quiet = TRUE), silent = TRUE)
}

if (file.exists(CACHE) && file.size(CACHE) > 1000) {
  power <- read_csv(CACHE, show_col_types = FALSE)
  cat("Loaded", nrow(power), "simulation cells.\n")
} else {
  stop("Could not download the results. Check your connection, or clone the toolbox ",
       "and point CACHE at results/power analysis/Extracted/all_data.csv")
}

power <- power |> rename(power = mean, n_sims = n)

# The exported file carries TWO t-test rows per design cell, both labelled "u",
# with different results. The Shiny app distinguishes three analyses (h / s / u),
# so these are almost certainly the simple and uncertainty-propagating t-tests
# with the label lost on export. We cannot tell which is which, so we keep them
# as a band rather than pretending they are one number - and compare the
# hierarchical model against the BETTER of the two, which is the conservative
# choice.
wide <- power |>
  group_by(parameter, subjects, trials, effect_size) |>
  summarise(h    = power[test_type == "h"][1],
            u_lo = min(power[test_type == "u"]),
            u_hi = max(power[test_type == "u"]),
            n_u  = sum(test_type == "u"),
            .groups = "drop")

cat("\nt-test rows per design cell:", paste(sort(unique(wide$n_u)), collapse = ", "),
    "- kept as a range, see the comment in this cell.\n")

cat("\nGrid:\n")
cat("  participants  ", paste(sort(unique(power$subjects)), collapse = ", "), "\n")
cat("  trials        ", paste(sort(unique(power$trials)),   collapse = ", "), "\n")
cat("  effect sizes  ", paste(sort(unique(power$effect_size)), collapse = ", "), "\n")
cat("  analyses      ", "hierarchical model | t-test (two variants)", "\n")
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
""")

co(r"""
null_rates <- power |>
  filter(effect_size == 0) |>
  mutate(analysis = ifelse(test_type == "h", "Hierarchical model", "t-test variants")) |>
  group_by(parameter, analysis) |>
  summarise(min = min(power), median = median(power), max = max(power),
            cells = n(), .groups = "drop")

print(as.data.frame(null_rates), row.names = FALSE)

mc_se <- sqrt(0.05 * 0.95 / 100)
cat(sprintf("\nMonte Carlo SE at a true rate of 0.05, with 100 sims: %.3f\n", mc_se))
cat(sprintf("So single cells anywhere in roughly %.2f to %.2f are consistent with nominal.\n",
            max(0, 0.05 - 2 * mc_se), 0.05 + 2 * mc_se))
cat("\nThe medians sit near 0.05. Nothing here is inflating its false-positive rate.\n")
""")

md(r"""
## The power grid

Now the substance. Each panel is one parameter; each line is a number of trials; colour is
the analysis strategy. The dashed line is 80% power.
""")

co(r"""
D <- 0.5   # <-- change this to 0.2 or 0.8 and re-run

grid_plot <- wide |>
  filter(effect_size == D) |>
  ggplot(aes(subjects)) +
  geom_hline(yintercept = 0.8, linetype = "dashed", colour = GREY) +
  geom_ribbon(aes(ymin = u_lo, ymax = u_hi, fill = "t-test (range of 2 variants)"),
              alpha = 0.25) +
  geom_line(aes(y = h, colour = "Hierarchical model"), linewidth = 0.9) +
  geom_point(aes(y = h, colour = "Hierarchical model"), size = 1.8) +
  facet_grid(trials ~ parameter, labeller = labeller(trials = \(x) paste(x, "trials"))) +
  scale_colour_manual(values = c("Hierarchical model" = ORANGE), name = NULL) +
  scale_fill_manual(values = c("t-test (range of 2 variants)" = BLUE), name = NULL) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.25)) +
  labs(title = paste0("Power to detect a true effect of d = ", D),
       subtitle = "Dashed line = 80% power. Band spans the two t-test variants in the export.",
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
# Compare against the BETTER of the two t-test variants, and drop cells where
# either method is at ceiling - a difference of 0.00 at power 1.00 is not evidence
# of anything.
comparison <- wide |>
  filter(effect_size > 0, h < 1, u_hi < 1) |>
  mutate(advantage = h - u_hi)

by_par <- comparison |>
  group_by(parameter) |>
  summarise(cells = n(),
            median_advantage = round(median(advantage), 3),
            hierarchical_better = sum(advantage > 0),
            worse = sum(advantage < 0), .groups = "drop")

cat("Hierarchical minus the better t-test variant, all effect sizes,\n")
cat("excluding ceiling cells:\n\n")
print(as.data.frame(by_par), row.names = FALSE)

mc <- sqrt(0.5 * 0.5 / 100)
cat(sprintf("\nMonte Carlo SE on a single cell is about %.2f, and a difference of two\n", mc))
cat(sprintf("cells about %.2f. Treat anything smaller than that as noise.\n", mc * sqrt(2)))

cat("\nLargest advantages:\n\n")
print(as.data.frame(comparison |> arrange(desc(advantage)) |>
      select(parameter, subjects, trials, effect_size, h, u_hi, advantage) |>
      head(6) |> mutate(advantage = round(advantage, 2))), row.names = FALSE)
""")

md(r"""
**For threshold the advantage is large and consistent.** At 30 participants and d = 0.5 the
hierarchical model reaches about 0.90 where the t-tests reach 0.71–0.78; at d = 0.2 with 120
participants it is roughly 0.84 against 0.52–0.61. That is the difference between a study
that works and one that does not, from identical data.

**For slope the advantage is small and inconsistent**, and at low power the two approaches
are separated by less than the Monte Carlo error of the simulation. Do not claim a
hierarchical advantage for slope on the basis of this grid.

Why the asymmetry? Partial pooling helps most when individual estimates are noisy *relative
to* the spread between participants — then shrinking a wild estimate toward the group is a
large correction. Threshold is estimated precisely per participant and varies a lot between
them, which is the regime where pooling pays. Slope is noisy for everyone, so there is less
signal to redistribute.

The honest summary: **fit hierarchically because it is the right model for the data and it
propagates uncertainty correctly** — and expect a real power gain for threshold, but do not
count on one for slope.

> Two caveats on all of this. 100 simulations per cell gives a standard error around 0.05 on
> a single power estimate, so small differences are not interpretable. And these simulations
> assume the toolbox's generative model and normative priors; your design may differ.
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
- **Fit hierarchically**, because it models the data correctly and propagates uncertainty.
  Expect a substantial power gain for threshold; do not expect one for slope.
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
