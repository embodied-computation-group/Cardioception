# Cardioception

[![GitHub license](https://img.shields.io/github/license/LegrandNico/Cardioception)](https://github.com/LegrandNico/Cardioception/blob/master/LICENSE) [![GitHub release](https://img.shields.io/github/release/LegrandNico/Cardioception)](https://GitHub.com/LegrandNico/Cardioception/releases/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit) [![pip](https://badge.fury.io/py/cardioception.svg)](https://badge.fury.io/py/cardioception) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/) [![Gitter](https://badges.gitter.im/Cardioception/community.svg)](https://gitter.im/Cardioception/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

---

<img src="https://raw.githubusercontent.com/LegrandNico/Cardioception/master/docs/source/images/logo.png" align="left" alt="cardioception" height="230" HSPACE=30>

The Cardioception Python Package - Measuring Interoception with Psychopy - implements two measures of cardiac interoception (cardioception):

1. The **Heartbeat counting task (HBC)**, also known as the **Heartbeat tracking task**, developed by Rainer Schandry {cite:p}`1978:dale,1981:schandry`. This task cardiac measures interoception by asking participants to count their heartbeats for a given period of time. An accuracy score is then derived by comparing the reported number of heartbeats and the true number of heartbeats.
2. The **Heart Rate Discrimination task** {cite:p}`2022:legrand` implementing an adaptive psychophysical measure of cardiac interoception where participants have to estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. By manipulating the difference between the true heart rate and the presented tone using different staircase procedures, the bias (threshold) and precision (slope) of the psychometric function can be estimated either online or offline (see *Analyses* below), together with metacognitive efficiency.

```{note}
While having slightly similar names, the **Heartbeat counting task (HBC)** and the **Heart Rate Discrimination task** are different in term of implementation and the measures they provided and should not be conflated. We developped the cardioception package first to provide an open sourced version of the *HBC*, which was lacking, with easy support to record heart rate via cheap pulse oximetry via [Systole](https://github.com/LegrandNico/systole). In addition to that, we developped the **HRD** task as a new measure of cardiac interoception {cite:p}`2022:legrand`, grounding on a different reasonning and trying to control for the confounds other interoception tasks migh have.

```

These tasks can run using minimal experimental settings: a computer and a recording device to monitor the heart rate of the participant. The default version of the task use the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). This sensor can be plugged directly into the stim PC via USB and will work with Cardioception without any additional coding required. The tasks can also integrate easily with other recording devices and experimental settings (ECG, M/EEG, fMRI...).

## Looking for help?

If you have questions regarding the tasks or want discuss data analysis, please ask on our public [![Gitter](https://badges.gitter.im/Cardioception/community.svg)](https://gitter.im/Cardioception/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge).

If you want to report a bug, you can open an issue on the [GitHub page](https://github.com/LegrandNico/Cardioception).

## Development

This package was created and is maintained by [Nicolas Legrand](https://legrandnico.github.io/) and [Micah Allen](https://micahallen.org/) from the [ECG group](https://the-ecg.org/).

<img src = "https://raw.githubusercontent.com/LegrandNico/Cardioception/master/docs/source/images/LabLogo.png" height ="100"><img src = "https://raw.githubusercontent.com/LegrandNico/Cardioception/master/docs/source/images/AU.png" height ="100">

```{toctree}
---
hidden:
---
Theory <measuring.md>
Guide <user_guide.md>
API <api.rst>
Statistical analysis <stats.md>
Cite <cite.md>
References <references.md>
```
