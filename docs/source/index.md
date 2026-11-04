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
```

## The tasks

| Task | What participants do | Main measures | Reference | Status |
|---|---|---|---|---|
| [Heart Rate Discrimination (HRD)](tasks/hrd/index.md) | Judge whether a sequence of tones is faster or slower than their own heart rate | Bias and precision of heart rate judgements, with optional confidence ratings | [Legrand et al., 2022](https://doi.org/10.1016/j.biopsycho.2021.108239) | Established |
| [Heartbeat Counting (HBC)](tasks/hbc.md) | Count their heartbeats during intervals of different lengths | Reported heartbeat counts relative to recorded counts | [Schandry, 1981](https://doi.org/10.1111/j.1469-8986.1981.tb02486.x) | Established |
| [Phase Adjustment Task (PAT)](tasks/pat.md) | Adjust the delay of tones until they match their perceived heartbeat | The delay chosen, and its consistency across trials | [Plans et al., 2021](https://doi.org/10.1016/j.biopsycho.2021.108171); ECG version after [Hodgetts et al., 2026](https://doi.org/10.1111/psyp.70415) | Beta |
| [Heartbeat Synchrony Discrimination (HSD)](tasks/hsd/index.md) | Judge whether tones played at different delays after each heartbeat are synchronous with it | Perceived timing of the heartbeat, and its temporal precision | New in Cardioception; see the [design page](tasks/hsd/design.md) | Beta |
| [Whitehead method](tasks/whitehead.md) | Judge which of two tone sequences, one at a short and one at a longer delay after each heartbeat, is simultaneous with it | Discrimination of synchronous from delayed tones | [Whitehead et al., 1977](https://doi.org/10.1007/BF00998623) | Coming soon |
| [Method of constant stimuli (Brener)](tasks/constant-stimuli.md) | Judge whether tones at one of several fixed delays, from 0 to 500 ms after each heartbeat, are simultaneous with it | Proportion of tones judged simultaneous at each delay | [Brener, Liu & Ring, 1993](https://doi.org/10.1111/j.1469-8986.1993.tb02091.x) | Coming soon |

## Analysing your data

For HRD data we recommend the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception), described in [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3). The [tutorials](tasks/hrd/tutorials/index.md) walk through the workflow, from checking your data to fitting hierarchical models with covariates.

## Where to go next

- [Installation](getting-started/installation.md), [Recording devices](getting-started/recording-devices.md) and [Running a session](getting-started/running-a-session.md) for setting up and running a task
- [The tasks](tasks/index.md) for the tasks side by side, and what each can establish
- [Heart Rate Discrimination](tasks/hrd/index.md) for running the HRD, its theory, the tutorials and the legacy reports
- [Heartbeat Counting](tasks/hbc.md), [Phase Adjustment Task](tasks/pat.md) and [Heartbeat Synchrony Discrimination](tasks/hsd/index.md) for the other tasks
- [API](reference/api.rst) for the parameters and task functions
- [Cite](reference/cite.md) for the references to use in a publication
- [Changelog](reference/changelog.md) for what changed in 1.0

## Getting help

For questions about the tasks or about data analysis, contact Micah Allen directly. To report a bug, open an issue on the [GitHub page](https://github.com/embodied-computation-group/Cardioception/issues).

```{note}
This is the original Cardioception, created by Micah Allen and the Embodied Computation Group at Aarhus University between 2019 and 2022, funded by a Lundbeckfonden Fellowship to Micah Allen. It is the version cited in the peer-reviewed publications listed on the [cite page](reference/cite.md).
```

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
