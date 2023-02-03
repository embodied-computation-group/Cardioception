# Statistical analysis

## Using the preprocessing function

The {py:mod}`cardioception.reports` module includes a function {py:fun}`cardioception.reports.preprocessing` that automates the analysis and extraction of behavioural variables from the main outputs saved by the task. The function only requires the `final.txt` data frame (either the Pandas data frame or simply a path to the file) that is saved in each subject folder and will return a summary data frame containing the response time, the psychometric parameter estimated by the Psi algorithm and Bayesian inference as well as SDT measures and metacognitive efficiency (meta-d prime). This approach is the most straightforward to extract relevant parameters using default settings that will fit most users' needs.

This script exemplifies how this function can be used to extract summary statistics from a result folder. It is assumed that the script is in a folder that contains the `data` folder in which the main outputs of the task are saved. You may addapt the following script to fit your needs:

```python
import pandas as pd
from pathlib import Path
from cardioception.reports import preprocessing

data_folder = Path(Path().cwd(), "data")  # path to the data folder
summary_df = pd.DataFrame([])  # creat an empty summary data frame

# for each file found in the result folder, do the preprocessing 
# and save in the summary dataframe
for f in data_folder.glob(f"*{session}*"):

    # all the preprocessing happens here
    # the input is a file name at it returns a summary dataframe
    results_df = preprocessing(f)
    
    # log additional info about the participant
    # considering that the first 3 digits are the participant ID
    results_df["participant_id"] = f.name[:3]

    # concatenate everything in a result data frame
    summary_df = pd.concat([summary_df, results_df])

# save in the current working directory
summary_df.to_csv("results.tsv", sep="\t", index=False)
```

## Report templates

Here, you will find the report templates used to produce the HTML reports when calling the {py:fun}`cardioception.reports.report` function. We provide one for the Heart Rate Discrimination task and one for the Heart Beat Counting task. You can navigate the notebooks by clicking on the links or run it interactively in [Google Colab](https://colab.research.google.com/) using the badges, and upload your own data. Visualizing the data this way is recommended to assess the quality of the PPG recording or the general performance of the participant during the tasks.

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
