# Statistical analysis

```{warning}
The Python analysis tutorials on this page are deprecated and may not be maintained. For analyzing Cardioception data we recommend the R scripts described below.
```

## Analysis in R

The scripts in the `R_analysis/` directory are the ones we maintain. They cover analysis at the level of individual subjects, with reaction time plots and signal detection theory metrics, hierarchical analysis at the group level, and Bayesian models fitted with Stan, together with the figures that go with each.

The example scripts are a good place to start:

- `R_analysis/Example scripts/Example_analysis_simple.Rmd` for a single subject
- `R_analysis/Example scripts/Example_analysis_Hierarchical.Rmd` for group-level analysis
- `R_analysis/Example scripts/Example_analysis_bayesian.Rmd` for the Bayesian models

The [R analysis README](https://github.com/embodied-computation-group/Cardioception/tree/master/R_analysis) has the full documentation and further examples.

## Python analysis (deprecated)

Everything below is deprecated and may not be maintained. Use the R scripts above instead.

If you still want to analyze your data in Python, the package includes two functions ([preprocessing](cardioception.reports.preprocessing) and [report](cardioception.reports.report)) that can help automate the analysis of large datasets obtained with the Heart Rate Discrimination task. We also provide notebooks detailing specific parts of the data analysis and Bayesian modelling of psychophysics (see below).

### Behavioural summary using the preprocessing function

The reports module includes a [preprocessing function](cardioception.reports.preprocessing) that automates the analysis and extraction of behavioural variables from the main outputs saved by the task. The function only requires the `final.txt` data frame (either the Pandas data frame or simply a path to the file) that is saved in each subject folder and will return a summary data frame containing the response time, the psychometric parameter estimated by the Psi algorithm and Bayesian inference as well as SDT measures and metacognitive efficiency (meta-d prime). This is the most straightforward way to extract the relevant parameters, using default settings that will fit most users' needs.

This script exemplifies how this function can be used to extract summary statistics from a result folder. It is assumed that the following script is in a folder that contains the `data` folder with sub-folders `sub-01`, `sub-02` for each participant in which the main outputs of the task are stored. The HTML reports will be saved in the `reports` folder.

```python
from pathlib import Path
from cardioception.reports import report

data_folder = Path(Path().cwd(), "data")  # path to the data folder

# for each file found in the result folder, create the HTML report
for f in data_folder.iterdir():

    # all the preprocessing happens here
    # the input is a file name at it returns a summary dataframe
    results_df = report(result_path=f, report_path=Path(data_folder, "reports"))
```

### HTML reports using the report function

Using a similar approach, the [report function](cardioception.reports.report) automates the production of HTML reports that are generated using the templates below. The function will require more files than the previous one, especially as this time the PPG signal is being analyzed. Using the HTML reports is an important step in the data quality checks, especially for the quality of the PPG recording. Here, we will assume that the following script is in a folder that contains the `data` folder in which the main outputs of the tasks (either the Heart Rate Discrimination task or the Heartbeats Detection task) are stored.

```python
from pathlib import Path
from cardioception.reports import report

data_folder = Path(Path().cwd(), "data")  # path to the data folder

# for each folder, create the HTML report from the files it contains
for f in data_folder.iterdir():

    # this command runs the notebook and converts it into HTML
    results_df = report(result_path=f, report_path=Path(data_folder, "reports"))
```

## Report templates (deprecated)

Here, you will find the report templates used to produce the HTML reports when calling the [report function](cardioception.reports.report) function. We provide one for the Heart Rate Discrimination task and one for the Heartbeat Counting task. You can navigate the notebooks by clicking on the links or run them interactively in [Google Colab](https://colab.research.google.com/) using the badges, and upload your data. Visualizing the data this way is recommended to assess the quality of the PPG recording or the general performance of the participant during the tasks.

```{toctree}
---
hidden:
glob:
---

examples/templates/*

```

| Notebook | Colab |
| --- | ---|
| {ref}`hbc_template` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/docs/source/examples/templates/HeartBeatCounting.ipynb)
| {ref}`hrd_template` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/docs/source/examples/templates/HeartRateDiscrimination.ipynb)

## Bayesian modelling of psychophysics (deprecated)

These notebooks give a more detailed introduction to the Bayesian modelling of the psychometric functions, estimating threshold and slope offline rather than online as the Psi staircase does. The models are implemented in PyMC, and the code can easily be adapted to fit different modelling needs (e.g. group comparison, repeated measure...).

```{toctree}
---
hidden:
glob:
---

examples/psychophysics/*

```

| Notebook | Colab |
| --- | ---|
| {ref}`psychophysics_subject_level` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/docs/source/examples/psychophysics/1-psychophysics_subject_level.ipynb)
| {ref}`psychophysics_group_level` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/docs/source/examples/psychophysics/2-psychophysics_group_level.ipynb)
