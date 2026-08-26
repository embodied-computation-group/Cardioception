# Tutorials

Working with Heart Rate Discrimination data, from opening the files the task
wrote through to a hierarchical model with covariates.

Read them in order if the whole workflow is new to you. They build on each other:
each one assumes the data preparation from the one before.

| Tutorial | What it covers |
|---|---|
| [Inspecting and plotting data](inspecting-data.md) | Loading sessions, checking what is missing, the staircase, the confidence distribution. In Python and R. |
| [The psychophysical model](psychophysics.md) | What threshold, slope and lapse rate are, and fitting one participant. |
| [Hierarchical modelling](hierarchical.md) | Fitting everyone at once, and testing covariates and between-group effects. |
| [Metacognition](metacognition.md) | Modelling confidence ratings, and whether confidence tracks accuracy. |

## What you need

Data inspection works in either Python or R. **Model fitting is done in R**, with
[brms](https://paul-buerkner.github.io/brms/) and a Stan backend, using the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception).

The modelling tutorials assume you have met brms before: that a formula like
`y ~ x + (x | subject)` means something to you, and that you know roughly what a
posterior is. If that is new, the
[brms vignettes](https://paul-buerkner.github.io/brms/articles/) and
[Bürkner (2017)](https://doi.org/10.18637/jss.v080.i01) are the place to start,
and you will get much more out of these pages afterwards.

Nothing here assumes you know psychophysics.

## These pages do not fit models

The models take hours to sample. A page you are reading cannot wait for that, so
the tutorials show the code and then load results that were fitted in advance.

The scripts that produced those results live in
[`tutorials/`](https://github.com/embodied-computation-group/Cardioception/tree/master/tutorials)
in the repository, and they run on an ordinary machine. If you want to reproduce
a fit rather than read about it, start there. Every number quoted in these pages
came out of those scripts.

## The example data

The figures come from a study of 512 participants, each completing the HRD in two
conditions, with age, gender and BMI recorded. That is a larger sample than most
studies will have, which is deliberate: it makes the group-level structure visible.
The methods apply unchanged to a sample of thirty.

## Citing

Cite [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3) for the
models and the priors, and Cardioception for the data collection. See the
[cite page](../cite.md) for the full references.

```{toctree}
---
hidden:
---
Inspecting data <inspecting-data.md>
Psychophysical model <psychophysics.md>
Hierarchical modelling <hierarchical.md>
Metacognition <metacognition.md>
```
