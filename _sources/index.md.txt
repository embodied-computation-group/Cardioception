[![GitHub license](https://img.shields.io/github/license/embodied-computation-group/Cardioception)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![GitHub release](https://img.shields.io/github/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit) [![pip](https://badge.fury.io/py/cardioception.svg)](https://badge.fury.io/py/cardioception) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/) [![Gitter](https://badges.gitter.im/Cardioception/community.svg)](https://gitter.im/Cardioception/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

***

# Cardioception

<img src="https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/logo.png" align="left" alt="cardioception" height="230" HSPACE=30>

The Cardioception Python Package - Measuring Interoception with Psychopy - implements two measures of cardiac interoception (cardioception):
1. The **Heartbeat counting task** developed by Rainer Schandry<sup>1,2</sup>. This task cardiac measures interoception by asking participants to count their heartbeats for a given period of time. An accuracy score is then derived by comparing the reported number of heartbeats and the true number of heartbeats.
2. The **Heart Rate Discrimination Task** <sup>3</sup> implementing an adaptive psychophysical measure of cardiac interoception where participants have to estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. By manipulating the difference between the true heart rate and the presented tone using different staircase procedures, the bias (threshold) and precision (slope) of the psychometric function can be estimated either online or offline (see *Analyses* below), together with metacognitive efficiency.

These tasks can run using minimal experimental settings: a computer and a recording device to monitor the heart rate of the participant. The default version of the task use the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). This sensor can be plugged directly into the stim PC via USB and will work with Cardioception without any additional coding required. 

The tasks can also integrate easily with other recording devices and experimental settings (ECG, M/EEG, fMRI...). See *Sending triggers* below for details.

# Analyses

## Task reports

The results are saved in the `'resultPath'` folder defined in the parameters dictionary. For each task, we provide a comprehensive notebook detailing the main results, quality checks, and basic preprocessing steps. You can automatically generate the HTML reports using the following code snippet:

```python
from cardioception.reports import report

resultPath = "./"  # the folder containing the result files
reportPath = "./"  # the folder where you want to save the HTML report

report(resultPath, reportPath, task='HRD')
```

This code will generate the HTML reports for the Heart Rate Discrimination task in the `reportPath` folder using the results files located in `resultPath`. This will require [papermill](https://papermill.readthedocs.io/en/latest/).

You can also analyze the results in [Google Colab](https://colab.research.google.com/) using one of the following link and upload the content of your result folder.

| Notebook | Colab | nbViewer |
| --- | ---| --- |
| Heartbeat Counting task report | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartBeatCounting.ipynb) | [![View the notebook](https://img.shields.io/badge/render-nbviewer-orange.svg)](https://nbviewer.jupyter.org/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartBeatCounting.ipynb)
| Heart Rate Discrimination task report | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartRateDiscrimination.ipynb) | [![View the notebook](https://img.shields.io/badge/render-nbviewer-orange.svg)](https://nbviewer.jupyter.org/github/embodied-computation-group/Cardioception/blob/master/cardioception/notebooks/HeartRateDiscrimination.ipynb)

# References

1. Dale, A., & Anderson, D. (1978). Information Variables in Voluntary Control and Classical Conditioning of Heart Rate: Field Dependence and Heart-Rate Perception. Perceptual and Motor Skills, 47(1), 79–85. https://doi.org/10.2466/pms.1978.47.1.79
2. Schandry, R. (1981). Heart Beat Perception and Emotional Experience. Psychophysiology, 18(4), 483–488. https://doi.org/10.1111/j.1469-8986.1981.tb02486.x
3. Legrand, N., Nikolova, N., Correa, C., Brændholt, M., Stuckert, A., Kildahl, N., Vejlø, M., Fardo, F., & Allen, M. (2021). The heart rate discrimination task: a psychophysical method to estimate the accuracy and precision of interoceptive beliefs. bioRxiv 2021.02.18.431871. https://doi.org/10.1101/2021.02.18.431871
4. Leganes-Fonteneau, M., Cheang, Y., Lam, Y., Garfinkel, S., & Duka, T. (2019). Interoceptive awareness is associated with acute alcohol-induced changes in subjective effects. Pharmacology Biochemistry and Behavior, 181, 69–76. https://doi.org/10.1016/j.pbb.2019.03.007
5. Hart, N., McGowan, J., Minati, L., & Critchley, H. D. (2013). Emotional Regulation and Bodily Sensation: Interoceptive Awareness Is Intact in Borderline Personality Disorder. Journal of Personality Disorders, 27(4), 506–518. https://doi.org/10.1521/pedi_2012_26_049

# Development
This package was created and is maintained by [Nicolas Legrand](https://legrandnico.github.io/) and [Micah Allen](https://micahallen.org/) from the [ECG group](https://the-ecg.org/).

<img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/LabLogo.png" height ="100"><img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/AU.png" height ="100">

# Credit
Some icons used in the Figures or presented during the tasks were downloaded from [www.flaticon.com](www.flaticon.com).


```{toctree}
---
hidden:
maxdepth: 3
---
User guide <user_guide.md>
API <api.rst>
Statistical analysis <examples/README.md>
Cite <cite.md>
```