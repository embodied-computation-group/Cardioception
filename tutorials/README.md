# Tutorial analyses

The analysis behind the modelling tutorials in the documentation. Everything here
runs as ordinary R on an ordinary machine.

## What this is for

The tutorial pages in the docs do not fit models. Fitting these models takes hours,
which is no use in a page someone is reading. Instead the tutorials load the small
artefacts produced here: posterior summaries, contrast tables and figures.

This directory holds the code that produced them, so the numbers in the
documentation can be traced back to something you can run yourself.

## Layout

```
R/
  models.R        all four models defined once: formulas, priors, data each needs
  00_prepare.R    trials -> aggregated binomial cells, covariate coding, checks
  01_fit.R        fit one model by name, verify priors, write summary + diagnostics
  02_summarise.R  fitted models -> the tables and figures the docs read
slurm/            how we ran these on a cluster. Not needed to follow the tutorials.
data/             input trial data
results/          posterior summaries, diagnostics and figures
```

## Running it

Assumes R with brms and a working Stan backend (cmdstanr recommended), plus
tidyverse and ordbetareg. The tutorials assume basic familiarity with brms formula
syntax; if that is new, start with the
[brms vignettes](https://paul-buerkner.github.io/brms/articles/) before this.

```bash
Rscript R/00_prepare.R data/hrd_tutorial.csv data/model_data.rds
Rscript R/01_fit.R psy_intero      # the minimal example
Rscript R/01_fit.R psy_full        # the full model
Rscript R/02_summarise.R
```

`01_fit.R` skips any model whose summary already exists, so it is safe to rerun.

**Expect hours, not minutes.** `psy_intero` on a few hundred subjects is the
quickest; `psy_full` and `meta_full` are considerably slower. Sampling settings are
controlled by environment variables (`HRD_CHAINS`, `HRD_THREADS`, `HRD_ITER`,
`HRD_WARMUP`) so you can fit a cut-down version first:

```bash
HRD_CHAINS=2 HRD_THREADS=2 HRD_ITER=800 HRD_WARMUP=400 Rscript R/01_fit.R psy_intero
```

Use that to check the pipeline runs end to end. Do not report anything from it.

## The models

| Name | What it is for |
|---|---|
| `psy_intero` | One condition, no predictors. The simplest useful fit. |
| `psy_main` | Modality, gender, age and BMI as main effects. |
| `psy_full` | Modality interacting with gender and age, BMI controlled. |
| `meta_full` | Confidence, ordered beta regression, same covariates. |

`psy_main` exists to be compared against `psy_full`: an effect can look like a main
effect until the interaction is in the model.

The psychometric form and the normative priors come from the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception),
described in [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3).
Cite that paper for the models, and Cardioception for the data collection.

## A note on the cluster scripts

`slurm/` is how we produced the committed results on GenomeDK, because 512 subjects
with covariates is an overnight job. It is included for transparency, not because
you need it. The R scripts are identical either way; SLURM only supplies the
machine.
