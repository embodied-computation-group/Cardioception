# Cardioception

[![GitHub license](https://img.shields.io/github/license/embodied-computation-group/Cardioception)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![GitHub release](https://img.shields.io/github/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit) [![pip](https://badge.fury.io/py/cardioception-toolbox.svg)](https://pypi.org/project/cardioception-toolbox/) [![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/) [![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

---

# Official repository notice

This is the original, officially maintained version of the Cardioception software package, co-created by Micah Allen and the Embodied Computation Group at Aarhus University (2019-2022). Development of this package was funded by a Lundbeckfonden Fellowship to Micah Allen.

This is the version cited in peer-reviewed publications, and the Embodied Computation Group maintains it. We cannot guarantee the accuracy, validity, or scientific reproducibility of unofficial forks or versions of this software, so please use this repository for scientific work, installation, and citation.

---

Cardioception is a Python package for measuring interoception with Psychopy. It implements two measures of cardiac interoception:

1. The Heartbeat Counting task (HBC), also known as the Heartbeat tracking task, developed by Rainer Schandry {cite:p}`1978:dale,1981:schandry`. Participants count their heartbeats for a given period of time, and an accuracy score comes from comparing the reported number of heartbeats with the true number.
2. The Heart Rate Discrimination task {cite:p}`2022:legrand`, an adaptive psychophysical measure in which participants estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. Staircase procedures manipulate the difference between the true heart rate and the presented tone, which gives the bias (threshold) and precision (slope) of the psychometric function, along with metacognitive efficiency. These can be estimated online or offline (see the data analysis section below).

The tasks run with minimal equipment: a computer and a recording device to monitor the participant's heart rate. The default version uses the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). This sensor plugs directly into the stim PC over USB and works with Cardioception without any additional code. The tasks can also be used with other recording devices and experimental settings (ECG, M/EEG, fMRI...).

## Installation

```{important}
Install the package as **`cardioception-toolbox`**:

    pip install cardioception-toolbox

This is the official package, maintained by the Embodied Computation Group at Aarhus University. It is the version described in this documentation and used in our publications. Make sure the package name you install is exactly `cardioception-toolbox`.
```

The import name is still `cardioception`, so existing scripts do not need to be edited:

```python
from cardioception.HRD import task
```

See the [user guide](user_guide.md) for conda environments, dependencies and the development version.

## Data analysis

### R analysis

We recommend the R scripts in the `R_analysis/` directory. They cover single-subject analysis with reaction time plots and signal detection theory metrics, group-level hierarchical analysis, Bayesian analysis with Stan models, and plotting of the results.

Example scripts:

- `R_analysis/Example scripts/Example_analysis_simple.Rmd` for a single subject
- `R_analysis/Example scripts/Example_analysis_Hierarchical.Rmd` for group-level analysis
- `R_analysis/Example scripts/Example_analysis_bayesian.Rmd` for Bayesian analysis

The [R analysis README](../R_analysis/README.md) has the full documentation and further examples.

### Python analysis (outdated)

The Python analysis examples are outdated and may not be maintained. They are kept mainly for reference and include basic preprocessing and reporting functions, template notebooks for data visualization, and older Bayesian modelling examples. If you want to fit hierarchical Bayesian models, use the R code above instead.

## Looking for help?

If you have questions regarding the tasks or want to discuss data analysis, please contact Micah Allen directly.

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
