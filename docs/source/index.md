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
    keywords: "cardioception, interoception, cardiac interoception, heart rate discrimination, HRD, heartbeat counting, heartbeat synchrony, psychophysics, metacognition, PsychoPy"
---

# Cardioception Toolbox

Cardioception measures cardiac interoception in [Psychopy](https://www.psychopy.org/). The package is built around the Heart Rate Discrimination task (HRD), a psychophysical method that estimates how accurately and how precisely people judge their own heart rate. It also ships the classic Heartbeat Counting task and two experimental tasks, the Heartbeat Synchrony Discrimination task and the Phase Adjustment Task. [The tasks](tasks/index.md) compares all four.

[![GitHub release](https://img.shields.io/github/v/release/embodied-computation-group/Cardioception)](https://GitHub.com/embodied-computation-group/Cardioception/releases/) [![pip](https://img.shields.io/pypi/v/cardioception-toolbox)](https://pypi.org/project/cardioception-toolbox/) [![GitHub license](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/embodied-computation-group/Cardioception/blob/master/LICENSE) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22139105.svg)](https://doi.org/10.5281/zenodo.22139105)

The tasks run with minimal equipment: a computer and a device that reads the participant's pulse. They also work with richer setups (ECG, M/EEG, fMRI) when you have them.

```{important}
Install the package as **`cardioception-toolbox`**:

    pip install cardioception-toolbox

This is the official package, maintained by the Embodied Computation Group at Aarhus University, and the one used in our publications. Make sure the package name you install is exactly `cardioception-toolbox`. Until the next release, PyPI has the 0.7 line; [Installation](getting-started/installation.md#3-install-cardioception) says how to install the version this documentation describes.
```

The import name is still `cardioception`, so existing scripts do not need to be edited:

```python
from cardioception.HRD import task
```

See [Installation](getting-started/installation.md) for conda environments, dependencies and the development version.

## The tasks

### Heart Rate Discrimination task

The HRD {cite:p}`2022:legrand` is an adaptive psychophysical measure. Participants attend to their heartbeat sensations, then hear tones played faster or slower than their true heart rate and judge which. Staircase procedures adjust that difference from trial to trial, which gives the bias (threshold) and the precision (slope) of the psychometric function. Both can be estimated online during the task or offline afterwards.

### Heartbeat Counting task

The HBC {cite:p}`1978:dale,1981:schandry`, also known as the heartbeat tracking task, asks participants to count their heartbeats over a fixed period. An accuracy score compares the reported count against the true number of beats.

The package keeps this task because much of the literature rests on it. Counting scores can reflect beliefs about heart rate as well as heartbeat sensations; the [theory page](tasks/index.md#what-heartbeat-counting-can-establish) sets out the evidence.

### Heartbeat Synchrony Discrimination task

**Experimental.** The HSD is an adaptive Bayesian version of the heartbeat detection task {cite:p}`1993:brener`. Participants hear tones a chosen delay after each R-wave and judge whether they were synchronous with their heartbeat, and the delays are placed to estimate where in the cardiac cycle the heartbeat is felt and how sharply. It needs an ECG over Lab Streaming Layer and has so far been run on hardware once. The [design page](tasks/hsd/design.md) describes the method and the evidence, and [Running the HSD](tasks/hsd/running.md) explains how to run it.

### Phase Adjustment Task

**Experimental.** The PAT {cite:p}`2021:plans` follows the ECG version of {cite:t}`2026:hodgetts`. Participants turn a dial that moves a tone earlier or later after each R-wave until tone and heartbeat feel simultaneous, and the score is how consistently their choices fall at one phase of the cardiac cycle, tested against chance. It needs an ECG over Lab Streaming Layer. The [PAT page](tasks/pat.md) explains how to run and score it.

## Recording devices

The default setup uses the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/), which plugs into the stimulus PC over USB and needs no extra code. Any ECG or PPG device that streams over [Lab Streaming Layer](https://labstreaminglayer.org/) also works, through `cardioception.devices.LSLRecorder`, and other devices can be added by supplying a recorder object to `getParameters`. [Recording devices](getting-started/recording-devices.md) has the details.

## Analysing your data

For HRD data we recommend the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception), described in [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3). The [tutorials](tasks/hrd/tutorials/index.md) walk through the workflow, from checking your data to fitting hierarchical models with covariates.

## Where to go next

- [Running a session](getting-started/running-a-session.md) for running a task
- [The tasks](tasks/index.md) for the four tasks side by side, and which to choose
- [Theory](tasks/hrd/theory.md) for what the HRD and the HBC measure and why
- [HSD design](tasks/hsd/design.md) for the experimental Heartbeat Synchrony Discrimination task
- [PAT](tasks/pat.md) for the experimental Phase Adjustment Task
- [Tutorials](tasks/hrd/tutorials/index.md) for inspecting your data, then modelling it
- [API](reference/api.rst) for the parameters and task functions
- [Cite](reference/cite.md) for the references to use in a publication

## Getting help

For questions about the tasks or about data analysis, contact Micah Allen directly. To report a bug, open an issue on the [GitHub page](https://github.com/embodied-computation-group/Cardioception/issues).

```{note}
This is the original Cardioception, created by Micah Allen and the Embodied Computation Group at Aarhus University between 2019 and 2022, funded by a Lundbeckfonden Fellowship to Micah Allen. It is the version cited in the peer-reviewed publications listed on the [cite page](reference/cite.md). We cannot vouch for unofficial forks, so we recommend working from this repository for research, installation and citation.
```

## Development

Written and maintained by Micah Allen and the Embodied Computation Group, Aarhus University. Contact: micah@cfin.au.dk

<img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/LabLogo.png" height ="100"><img src = "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/images/AU.png" height ="100">

```{toctree}
---
caption: Getting started
hidden:
---
Installation <getting-started/installation.md>
Recording devices <getting-started/recording-devices.md>
Running a session <getting-started/running-a-session.md>
```

```{toctree}
---
caption: Tasks
hidden:
---
The tasks <tasks/index.md>
```

```{toctree}
---
caption: Reference
hidden:
---
API <reference/api.rst>
Cite <reference/cite.md>
References <reference/references.md>
Changelog <reference/changelog.md>
```
