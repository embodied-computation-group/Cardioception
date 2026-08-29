"""Build the optional power-analysis notebook - how to use the toolbox widget."""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: c.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# Optional — Planning your own study

**Optional module. Nothing else depends on it.**

The Hierarchical Interoception toolbox ships a **sample size widget**: a Shiny app that
tells you what power a given design has. This notebook shows you how to use it, and gives
you a quick offline lookup so you can get an answer right now.

**Kernel:** `R (cardioception)`.
""")

md(r"""
## The design question

You have two knobs, not one:

- **How many participants**
- **How many trials each**

They cost differently, and they do not buy the same thing. The widget lets you try
combinations and read the power off, so you can pick a design before committing to it.

Decide one thing first: **are you testing an effect on threshold or on slope?** They
behave differently, and the widget shows you that immediately.
""")

md(r"""
## Launching the widget

It lives in the toolbox repository, so you need that first. The clone is about 365 MB.

```bash
git clone https://github.com/embodied-computation-group/Hierarchical-Interoception.git
cd Hierarchical-Interoception
```

Then in R, **from the repository root** — the app finds its data with `here::here()`, so
starting anywhere else fails:

```r
install.packages(c("shiny", "tidyverse", "flextable", "posterior", "here"))

shiny::runApp("Ressources (app, tutorial, and updated thresholding scripts)/sample_size_exploration_app/shiny app.R")
```

> The path has spaces in both the folder name and the file name. Keep the quotes.

### The three tabs

| Tab | Use it to |
|---|---|
| **Power Grid** | See power contours over trials × participants. Set parameter, effect size and target power, then read off which combinations clear the line |
| **Effect Size vs. Power** | Fix a design and see how power varies with effect size — useful when you are unsure what to expect |
| **Manual Input** | Type in one specific design, get a single power estimate back |

Each tab compares analysis strategies: the hierarchical model against a simple *t*-test on
per-participant estimates, and against a *t*-test that propagates their uncertainty.
""")

md(r"""
## A quick lookup, without the clone

If you just want an answer now, the underlying simulation results are small enough to pull
directly.
""")

co(r"""
suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readr); library(ggplot2)
})

theme_set(theme_minimal(base_size = 12) +
          theme(panel.grid.minor = element_blank(),
                plot.title = element_text(face = "bold", size = 11)))
ORANGE <- "#D55E00"; PINK <- "#CC79A7"; BLUE <- "#0072B2"; GREY <- "#a4acb8"

BASE <- paste0("https://raw.githubusercontent.com/embodied-computation-group/",
               "Hierarchical-Interoception/main/results/power%20analysis/Extracted/")

SOURCES <- list(
  list(dir = "Hierarchical", method = "Hierarchical model"),
  list(dir = "Psi",          method = "Simple t-test"),
  list(dir = "Psi_un",       method = "t-test, uncertainty propagated")
)

power <- bind_rows(lapply(SOURCES, function(src) {
  cache <- file.path(getwd(), paste0("power_", src$dir, ".csv"))
  if (!file.exists(cache))
    try(download.file(paste0(BASE, src$dir, "/df.csv"), cache, quiet = TRUE), silent = TRUE)
  if (!file.exists(cache) || file.size(cache) < 1000)
    stop("Could not download ", src$dir, "/df.csv - check your connection.")
  read_csv(cache, show_col_types = FALSE) |> mutate(method = src$method)
})) |> rename(power = mean)

cat("Simulated grid:\n")
cat("  participants ", paste(sort(unique(power$subjects)), collapse = ", "), "\n")
cat("  trials each  ", paste(sort(unique(power$trials)), collapse = ", "), "\n")
cat("  effect sizes ", paste(sort(unique(power$effect_size)), collapse = ", "), "\n")
cat("  100 simulations per cell, so read any single number as +/- about 0.05\n")
""")

md(r"""
### Look up your design
""")

co(r"""
# ---- your study --------------------------------------------------
MY_PARAMETER <- "Threshold"   # "Threshold" or "Slope"
MY_EFFECT    <- 0.5           # smallest effect worth detecting (Cohen's d)
MY_POWER     <- 0.80
# -------------------------------------------------------------------

hier <- power |> filter(method == "Hierarchical model")

feasible <- hier |>
  filter(parameter == MY_PARAMETER, effect_size == MY_EFFECT, power >= MY_POWER) |>
  arrange(subjects, trials) |>
  select(subjects, trials, power)

cat(sprintf("%s, d = %.1f, target power %.0f%%\n\n",
            MY_PARAMETER, MY_EFFECT, 100 * MY_POWER))

if (nrow(feasible) == 0) {
  cat("Nothing in the simulated grid reaches that. Closest available:\n\n")
  print(as.data.frame(hier |>
    filter(parameter == MY_PARAMETER, effect_size == MY_EFFECT) |>
    arrange(desc(power)) |> head(3) |> select(subjects, trials, power)), row.names = FALSE)
} else {
  print(as.data.frame(feasible), row.names = FALSE)
  ch <- feasible |> slice(1)
  cat(sprintf("\nCheapest option here: %d participants x %d trials (power %.2f)\n",
              ch$subjects, ch$trials, ch$power))
}
""")

md(r"""
### The whole picture at a glance
""")

co(r"""
D <- 0.5   # change and re-run

power |>
  filter(effect_size == D) |>
  ggplot(aes(subjects, power, colour = method)) +
  geom_hline(yintercept = 0.8, linetype = "dashed", colour = GREY) +
  geom_line(linewidth = 0.9) + geom_point(size = 1.6) +
  facet_grid(trials ~ parameter,
             labeller = labeller(trials = \(x) paste(x, "trials"))) +
  scale_colour_manual(values = c("Hierarchical model" = ORANGE,
                                 "Simple t-test" = PINK,
                                 "t-test, uncertainty propagated" = BLUE),
                      name = "Analysis") +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.25)) +
  labs(title = paste0("Power at d = ", D), subtitle = "Dashed line = 80% power",
       x = "Participants", y = "Power")
""")

md(r"""
## Three things to take from the plot

**Threshold is cheaper than slope.** Compare the two columns. If your hypothesis is about
discrimination precision rather than bias, budget for more of everything.

**Trials matter far more for slope than for threshold.** Compare rows within a column. At
30 participants, going from 30 to 90 trials moves threshold power by about +0.02 and slope
power by about +0.25. A short session cannot be rescued by recruiting more people if slope
is your outcome.

**Your analysis choice is part of the design.** The orange line sits above the others, so
plan your sample size for the analysis you intend to run. Notebook 2, Part 6 covers why the
hierarchical model behaves this way.

## Choosing the effect size

Do not take *d* from a small previous study — published effects from underpowered work are
biased upward, and designing around one plans an underpowered study. Use the smallest
effect you would actually care about, and report it that way.

---

- [The toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception) — models, priors, power suite
- Courtin et al. (2026). [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
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
