# Cardioception

[![GitHub license](https://img.shields.io/github/license/embodied-computation-group/Cardioception)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![GitHub release](https://img.shields.io/github/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit) [![pip](https://badge.fury.io/py/cardioception.svg)](https://badge.fury.io/py/cardioception) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

---

# 🧠 Official Repository Notice

This is the **original and officially maintained version** of the Cardioception software package, co-created by Micah Allen and the Embodied Computation Group at Aarhus University (2019–2022). Development of this package was funded by a Lundbeckfonden Fellowship to Micah Allen.

This repository reflects the version cited in peer-reviewed publications and is actively maintained by the Embodied Computation Group.

⚠️ We cannot guarantee the accuracy, validity, or scientific reproducibility of any unofficial forks or versions of this software. Please use this repository for all scientific work, installations, and citation.

---

<img src="https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/logo.png" align="left" alt="cardioception" height="230" HSPACE=30>

The Cardioception Python Package - Measuring Interoception with Psychopy - implements two measures of cardiac interoception (cardioception):

1. The **Heartbeat counting task (HBC)**, also known as the **Heartbeat tracking task**, developed by Rainer Schandry {cite:p}`1978:dale,1981:schandry`. This task measures cardiac interoception by asking participants to count their heartbeats for a given period of time. An accuracy score is then derived by comparing the reported number of heartbeats and the true number of heartbeats.
2. The **Heart Rate Discrimination task** {cite:p}`2022:legrand` implementing an adaptive psychophysical measure of cardiac interoception where participants have to estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. By manipulating the difference between the true heart rate and the presented tone using different staircase procedures, the bias (threshold) and precision (slope) of the psychometric function can be estimated either online or offline (see *Analyses* below), together with metacognitive efficiency.

These tasks can run using minimal experimental settings: a computer and a recording device to monitor the heart rate of the participant. The default version of the task uses the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). This sensor can be plugged directly into the stim PC via USB and will work with Cardioception without any additional coding required. The tasks can also integrate easily with other recording devices and experimental settings (ECG, M/EEG, fMRI...).

## 📊 Data Analysis

### 🎯 Recommended: R Analysis

**For comprehensive data analysis, we recommend using our R analysis scripts located in the `R_analysis/` directory.**

The R analysis provides:
- **Individual subject analysis** with reaction time plots and signal detection theory metrics
- **Group-level hierarchical analysis** 
- **Bayesian analysis** using Stan models
- **Comprehensive visualization** of results

**🚀 Quick Start:**
- **Individual subject analysis**: See `R_analysis/Example scripts/Example_analysis_simple.Rmd`
- **Group-level analysis**: See `R_analysis/Example scripts/Example_analysis_Hierarchical.Rmd`
- **Bayesian analysis**: See `R_analysis/Example scripts/Example_analysis_bayesian.Rmd`

For complete documentation and examples, see the [R Analysis README](../R_analysis/README.md).

### 📈 Python Analysis (Outdated)

*Python analysis examples are available but are outdated and may not be maintained. For hierarchical Bayesian modeling, we strongly recommend using the R analysis approach above.*

Python users can find examples in the documentation, but these are primarily for reference. The Python analysis includes:
- Basic preprocessing and reporting functions
- Template notebooks for data visualization
- Outdated Bayesian modeling examples

**⚠️ Important**: Users interested in hierarchical Bayesian modeling should refer to the R analysis code, which provides more comprehensive and up-to-date implementations.

## Looking for help?

If you have questions regarding the tasks or want discuss data analysis, please contact Micah Allen directly.

If you want to report a bug, you can open an issue on the [GitHub page](https://github.com/embodied-computation-group/Cardioception).

## Development

Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
Maintained by the Embodied Computation Group, Aarhus University.

<img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/LabLogo.png" height ="100"><img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/AU.png" height ="100">

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
