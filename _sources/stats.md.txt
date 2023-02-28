# Statistical analysis

## Using R

If you want to use R to analyse your data, you can find R/Stan scripts with example notebooks in [this folder](https://github.com/embodied-computation-group/Cardioception/tree/master/docs/source/examples/R).

## Using Python

If you want to use Python to analyse your data, the package include two functions ([preprocessing](cardioception.reports.preprocessing) and [report](cardioception.reports.report)) that can help automate the analyse of large datasets obtained with the Heart Rate Discrimination task. We also provide notebooks detailling specific parts of the data analysis and Bayesian modelling of psychophysics (see below).

### Behavioural summary using the preprocessing function

The reports module includes a [preprocessing function](cardioception.reports.preprocessing) that automates the analysis and extraction of behavioural variables from the main outputs saved by the task. The function only requires the `final.txt` data frame (either the Pandas data frame or simply a path to the file) that is saved in each subject folder and will return a summary data frame containing the response time, the psychometric parameter estimated by the Psi algorithm and Bayesian inference as well as SDT measures and metacognitive efficiency (meta-d prime). This approach is the most straightforward to extract relevant parameters using default settings that will fit most users' needs.

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

Using a similar approach, the [report function](cardioception.reports.report) that automates the production of HTML reports that are generated using the templates below. The function will require more files than the previous one, especially as this time the PPG signal is being anaysed. Using the HTML reports is an important step of the data quality checks, especially for the quality of the PPG recording. Here, we will assume that the following script is in a folder that contains the `data` folder in which the main outputs of the tasks (either the Heart Rate Discrimination task or the Heartbeats Detection task) are stored.

```python
from pathlib import Path
from cardioception.reports import report

data_folder = Path(Path().cwd(), "data")  # path to the data folder

# for each folder, create the HTML report from the files it contains
for f in data_folder.iterdir():

    # this command runs the notebook and convert it into HTML
    results_df = report(result_path=f, report_path=Path(data_folder, "reports"))
```

## Report templates

Here, you will find the report templates used to produce the HTML reports when calling the [report function](cardioception.reports.report) function. We provide one for the Heart Rate Discrimination task and one for the Heart Beat Counting task. You can navigate the notebooks by clicking on the links or run it interactively in [Google Colab](https://colab.research.google.com/) using the badges, and upload your own data. Visualizing the data this way is recommended to assess the quality of the PPG recording or the general performance of the participant during the tasks.

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

## Bayesian modelling of psychophysics

These notebooks provide a more detailled introduction to the Bayesian modelling of the psychometric functions to estimate threshold and slope offline (as opposed to the online estimation performed by the Psi staircase). The models are implemented in PyMC, the code can easily be adapted to fit different modelling needs (e.g. group comparison, repeated measure...).

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
