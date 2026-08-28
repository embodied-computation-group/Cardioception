---
# The page opens with badge images, whose alt text is what sphinxext-opengraph
# would otherwise scrape into the preview description. These two keys override
# it. The released version is deliberately not repeated here: it is in the
# <title>, which reads it from the package and so cannot go stale.
og:title: "Cardioception Toolbox - Cardiac Interoception in PsychoPy"
og:description: "Official documentation for Cardioception, the Aarhus University toolbox that measures cardiac interoception in PsychoPy with the Heart Rate Discrimination task."
myst:
  html_meta:
    description: "Official documentation for Cardioception, the Aarhus University toolbox that measures cardiac interoception in PsychoPy with the Heart Rate Discrimination task."
    keywords: "cardioception, interoception, cardiac interoception, heart rate discrimination, HRD, heartbeat counting, psychophysics, metacognition, PsychoPy"
---

# Cardioception Toolbox

Cardioception measures cardiac interoception in [Psychopy](https://www.psychopy.org/). The package is built around the Heart Rate Discrimination task (HRD), a psychophysical method that estimates how accurately and how precisely people judge their own heart rate. It also ships the classic Heartbeat Counting task.

[![GitHub release](https://img.shields.io/github/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pip](https://img.shields.io/pypi/v/cardioception-toolbox)](https://pypi.org/project/cardioception-toolbox/) [![GitHub license](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22139105.svg)](https://doi.org/10.5281/zenodo.22139105)

The tasks run with minimal equipment: a computer and a device that reads the participant's pulse. They also work with richer setups (ECG, M/EEG, fMRI) when you have them.

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

## The tasks

### Heart Rate Discrimination task

The HRD {cite:p}`2022:legrand` is an adaptive psychophysical measure. Participants attend to their heartbeat sensations, then hear tones played faster or slower than their true heart rate and judge which. Staircase procedures adjust that difference from trial to trial, which gives the bias (threshold) and the precision (slope) of the psychometric function. Both can be estimated online during the task or offline afterwards.

### Heartbeat Counting task

The HBC {cite:p}`1978:dale,1981:schandry`, also known as the heartbeat tracking task, asks participants to count their heartbeats over a fixed period. An accuracy score compares the reported count against the true number of beats.

The package keeps this task because much of the literature rests on it. For new studies we would point you to the HRD, which separates interoceptive bias from precision and is less confounded by beliefs about heart rate. The [theory page](measuring.md) sets out that argument in full.

## Recording devices

The default setup uses the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/), which plugs into the stimulus PC over USB and needs no extra code. Remote Data Access through BrainVision Recorder is also supported, and you can add other devices by writing a recording class. The [user guide](user_guide.md) has the details.

## Analysing your data

For HRD data we recommend the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception), described in [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3). The [tutorials](tutorials/index.md) walk through the workflow, from checking your data to fitting hierarchical models with covariates.

## Where to go next

- [User guide](user_guide.md) for installation, dependencies and running a task
- [Theory](measuring.md) for what the two tasks measure and why
- [Tutorials](tutorials/index.md) for inspecting your data, then modelling it
- [API](api.rst) for the parameters and task functions
- [Cite](cite.md) for the references to use in a publication

## Getting help

For questions about the tasks or about data analysis, contact Micah Allen directly. To report a bug, open an issue on the [GitHub page](https://github.com/embodied-computation-group/Cardioception/issues).

```{note}
This is the original Cardioception, created by Micah Allen and the Embodied Computation Group at Aarhus University between 2019 and 2022, funded by a Lundbeckfonden Fellowship to Micah Allen. It is the version cited in the peer-reviewed publications listed on the [cite page](cite.md). We cannot vouch for unofficial forks, so we recommend working from this repository for research, installation and citation.
```

## Development

Written and maintained by Micah Allen and the Embodied Computation Group, Aarhus University. Contact: micah@cfin.au.dk

<img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/LabLogo.png" height ="100"><img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/AU.png" height ="100">

```{toctree}
---
hidden:
---
Installation <installation.md>
Guide <user_guide.md>
Theory <measuring.md>
Tutorials <tutorials/index.md>
API <api.rst>
Cite <cite.md>
References <references.md>
```
