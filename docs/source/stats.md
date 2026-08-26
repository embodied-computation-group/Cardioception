# Statistical analysis

An HRD session gives you two things per participant: a psychometric function for each condition, summarised by a threshold (bias) and a slope (precision), and a confidence rating on every trial. This page is a short orientation to how we recommend modelling both. The worked tutorials live in the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception), and we link to them rather than repeat them here.

## Hierarchical modelling of the psychometric function

Fitting each participant separately wastes information. The staircase concentrates trials near each person's threshold, so you end up with few trials far from it and correspondingly poor constraint on the slope. Fitting all participants at once, with subject-level parameters drawn from a group distribution, lets the group inform each individual estimate and propagates the uncertainty into whatever you test at the group level.

That is what the toolbox does. It is described in [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3), which covers the models, the parameter and model recovery work, the normative priors and a power analysis.

To get started:

```r
source(here::here("setup.R"))          # install and load dependencies
```

Then open `app & demo/BRMS demo.Rmd`, which walks through a complete analysis in BRMS from raw HRD output to interpreted parameters. That demo is the reference implementation, and is the right starting point for adapting to your own study.

### Parameterizing for common designs

The models put predictors on the threshold and on the slope separately, because a manipulation can shift what someone believes their heart rate to be without changing how finely they can discriminate it, and vice versa. Predicting only accuracy, or only one parameter, throws that distinction away.

The shapes below are the ones most studies need. They are sketches of the structure to specify, not runnable code: the demo shows the exact BRMS syntax and priors.

| Design | What to specify |
|---|---|
| One group, interoception only | Intercepts for threshold and slope, each with a subject-level random effect |
| Intero versus Extero | `Modality` as a within-subject predictor on both threshold and slope, with a subject-level random slope for it |
| Patients versus controls | `Group` as a between-subject predictor on both parameters; the random effects stay at subject level |
| Pre versus post, or drug versus placebo | `Session` as a within-subject predictor, with a subject-level random slope so each person can respond differently |
| Relating to a questionnaire | The centred score as a continuous subject-level predictor on threshold, on slope, or on both |

Two practical points. Keep the random effect structure as rich as the design allows, since dropping random slopes for a within-subject factor inflates the group-level effect. And put the predictor on the slope as well as the threshold even when your hypothesis is only about one of them: an effect that appears on the threshold in a threshold-only model can turn out to be a slope effect once both are free.

### Priors and sample size

The toolbox ships normative priors derived from a large reference dataset, which is the main practical reason to use it rather than rolling your own model with flat priors. It also includes a Shiny app for exploring the power analysis:

```r
shiny::runApp(here::here("app & demo", "shiny app.R"))
```

Use it to work out how many participants and how many trials per condition you need for the effect size you care about, and report that reasoning in your preregistration.

The figure below shows a single participant's responses against staircase intensity, from the example data shipped with this package. Note how few trials land far from threshold. That is by design, and it is why the slope is the harder parameter to estimate and benefits most from hierarchical fitting.

![Responses against stimulus intensity for one participant](images/psychometric_example.png)

## Modelling confidence

### Why not the m-ratio

The m-ratio, meta-d' divided by d' {cite:p}`2014:fleming`, is the usual summary of metacognitive efficiency, and it is a poor fit for the HRD for several reasons at once.

The staircase holds performance near a target accuracy by construction, so type-1 sensitivity is largely set by the procedure rather than by the participant, and between-subject variance in d' is compressed. Dividing by a quantity that the design has pinned down makes the ratio hard to interpret, and it becomes unstable for anyone performing near chance. Meta-d' also assumes a stationary type-1 process, whereas the whole point of an adaptive staircase is that stimulus intensity changes from trial to trial. Finally, the estimator expects confidence in a handful of discrete bins, while the HRD collects a continuous rating; binning it is arbitrary, and the answer moves with the bin edges.

### Ordered beta regression

The confidence rating is a slider bounded at 0 and 100 with real mass piled up at both ends, as participants frequently answer "completely unsure" or "completely sure". In the example data, 28 of 118 trials sit exactly on a bound.

![Distribution of confidence ratings](images/confidence_distribution.png)

Neither a Gaussian nor a plain beta model handles that. A Gaussian puts probability outside the bounds, and a beta likelihood is undefined at exactly 0 and 1. Ordered beta regression is built for this case: it models the interior with a beta likelihood and the two bounds as separate outcomes in one generative model, with no arbitrary rescaling or dropped trials {cite:p}`2023:kubinec`. It is available in R through the [ordbetareg](https://cran.r-project.org/package=ordbetareg) package, which wraps BRMS.

Scale the rating into the unit interval, keeping the endpoints, and model confidence as a function of whether the response was correct:

```r
library(ordbetareg)

data$Confidence <- data$Confidence / 100  # keep exact 0 and 1

fit <- ordbetareg(
  formula = bf(Confidence ~ ResponseCorrect * Modality +
                            (ResponseCorrect * Modality | Subject)),
  data = data,
  chains = 4, cores = 4
)
```

The coefficient for `ResponseCorrect` is the quantity of interest: how much higher confidence is on correct trials than on incorrect ones, which is metacognitive sensitivity expressed directly rather than as a ratio. The intercept captures overall confidence, so bias and sensitivity stay separate. Interactions extend it to your design in the usual way, and the same random effect advice applies as above.

## Preparing your data

Each participant folder holds a `final.txt` written by the task, one row per trial. The columns you need for the models above are:

| Column | Meaning |
|---|---|
| `Modality` | `Intero` or `Extero` |
| `Alpha` | Staircase intensity for the trial, the BPM difference between the tone and the estimated heart rate |
| `Decision` | The participant's response |
| `ResponseCorrect` | 1 for a correct response, 0 otherwise |
| `Confidence` | Confidence rating |
| `listenBPM`, `responseBPM` | Estimated heart rate and the frequency of the tones played |
| `EstimatedThreshold`, `EstimatedSlope` | Online Psi estimates, useful as a sanity check rather than as your analysis |

Add a subject identifier when you concatenate folders. Trials where the participant did not respond in time have an empty `ResponseCorrect` and should be dropped before modelling.

## Quality checks in Python

```{note}
The `preprocessing` and `report` functions are the original Python helpers. They still
work, but they are due to be rebuilt, so treat them as a convenience for checking data
quality rather than as the basis of an analysis pipeline.
```

The package includes two functions that summarise a result folder and build an HTML report per participant. The reports are worth generating for every session, mainly to check the quality of the PPG recording.

The [preprocessing function](cardioception.reports.preprocessing) takes the `final.txt` data frame, or a path to it, and returns a summary data frame with response times, the psychometric parameters estimated online by the Psi algorithm, and signal detection measures.

The [report function](cardioception.reports.report) runs the notebook templates below and writes HTML. It needs more than `final.txt`, because it analyses the PPG signal as well. The script assumes a `data` folder containing one sub-folder per participant:

```python
from pathlib import Path
from cardioception.reports import report

data_folder = Path(Path().cwd(), "data")  # path to the data folder

# for each folder, create the HTML report from the files it contains
for f in data_folder.iterdir():

    # this command runs the notebook and converts it into HTML
    results_df = report(result_path=f, report_path=Path(data_folder, "reports"))
```

### Report templates

The report function runs one notebook per task. They live in the package at
`cardioception/notebooks/` and are kept for data quality checks rather than as tutorials.
You can open them in [Google Colab](https://colab.research.google.com/) and upload your own data:

| Task | Colab |
| --- | --- |
| Heartbeat Counting | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartBeatCounting.ipynb) |
| Heart Rate Discrimination | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartRateDiscrimination.ipynb) |

## Archived material

```{warning}
The material below is kept for reference and is no longer maintained. Use the hierarchical toolbox for modelling, and the R scripts for the older workflow.
```

The R scripts in `R_analysis/` are still maintained for existing pipelines and cover single-subject analysis, group-level models and Bayesian fits in Stan. See the [R analysis directory](https://github.com/embodied-computation-group/Cardioception/tree/master/R_analysis).

The PyMC notebooks that used to fit the psychometric function offline have been removed. Model fitting is done in R with the toolbox, and the [data inspection page](inspecting_data.md) covers what Python is still used for.
