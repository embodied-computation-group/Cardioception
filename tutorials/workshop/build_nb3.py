"""Build the optional power-analysis notebook - how to use the toolbox widget."""

import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
c = []
md = lambda s: c.append(nbf.v4.new_markdown_cell(s.strip()))
co = lambda s: c.append(nbf.v4.new_code_cell(s.strip()))

md(r"""
# Optional module: planning an HRD study

The Hierarchical Interoception toolbox includes a Shiny application for examining power
across participant numbers, trial numbers, effect sizes, and analysis strategies. This
notebook introduces the simulation design, shows how to run the application, and reads
the underlying results directly in R.

**Kernel:** `R (cardioception)`.
""")

md(r"""
## Match the simulation to the planned design

Study planning requires decisions about both:

- **How many participants**
- **How many trials per condition**

Recruitment and additional trials have different practical costs and contribute
differently to estimation.

The simulations represent a within-participant comparison between two interoceptive HRD
conditions. They use 15, 30, 60, or 120 participants; 30, 60, or 90 trials per
condition; standardized effects of 0, 0.2, 0.5, or 0.8; and 100 simulated datasets per
cell. The results do not directly provide power for a between-group design or a
different task structure.

We must also specify whether the hypothesis concerns threshold or slope. Under matched
designs, slope effects generally require more data.
""")

md(r"""
## Launching the widget

The application is part of the toolbox repository. The clone is about 365 MB.

```bash
git clone https://github.com/embodied-computation-group/Hierarchical-Interoception.git
cd Hierarchical-Interoception
```

Then run the following in R from the repository root. The app finds its data with
`here::here()`, so
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
| **Effect Size vs. Power** | Fix a design and examine how power varies with effect size |
| **Manual Input** | Type in one specific design, get a single power estimate back |

Each tab compares analysis strategies: the hierarchical model against a simple *t*-test on
per-participant estimates, and against a *t*-test that propagates their uncertainty.
""")

md(r"""
## Read the simulation grid directly

The following cell downloads and caches the extracted simulation results. It therefore
requires an internet connection on its first run.
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
### Examine a proposed design
""")

co(r"""
# ---- proposed study ----------------------------------------------
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
  cat("\nThese designs meet the target in the simulated grid. Choosing among them\n")
  cat("requires the relative cost of recruitment and additional trials.\n")
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
## Interpret the plot

**Threshold effects are easier to detect than slope effects under matched designs.**
Compare the two columns before selecting a trial count.

**Additional trials contribute more strongly to slope estimation.** Compare rows within
a column. Threshold power approaches its upper range sooner, whereas slope power
continues to improve as the number of trials increases.

**The planned analysis is part of the design.** The hierarchical and two-stage analyses
do not have identical power. Plan for the analysis that will be used, and preregister
that analysis rather than selecting it after observing the results.

## Choosing the effect size

Use the smallest effect that would support the intended scientific conclusion. An
estimate from a small earlier study is often too uncertain to serve as a single design
value. We can examine several plausible effects and report the assumptions used for the
chosen design.

---

- [The toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception): models, priors, and power analysis
- Courtin et al. (2026). [doi:10.3758/s13428-026-03137-3](https://doi.org/10.3758/s13428-026-03137-3)
""")

nb["cells"] = c

# Deterministic cell ids, so rebuilding produces no spurious diff.
for i, cell in enumerate(nb["cells"]):
    cell["id"] = f"c{i:03d}"

nb.metadata = {
    "kernelspec": {"display_name": "R (cardioception)", "language": "R",
                   "name": "ir-cardioception"},
    "language_info": {"name": "R"},
}

out = Path(__file__).parent / "03_power_analysis.ipynb"
nbf.write(nb, str(out))
print(f"wrote {out}  ({len(c)} cells)")
