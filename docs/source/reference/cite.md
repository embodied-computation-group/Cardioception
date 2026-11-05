---
myst:
  html_meta:
    description: "How to cite Cardioception: the HRD paper, the software's Zenodo DOI, the other tasks, the analysis models, the Systole dependency, and publications using the HRD."
    keywords: "cite cardioception, heart rate discrimination citation, Legrand 2022, Systole, interoception"
---

# How to cite

If you use Cardioception, cite the paper that introduced it with the Heart Rate Discrimination task:

* Legrand, N., Nikolova, N., Correa, C., Brændholt, M., Stuckert, A., Kildahl, N., Vejlø, M., Fardo, F., & Allen, M. (2022). The heart rate discrimination task: A psychophysical method to estimate the accuracy and precision of interoceptive beliefs. Biological Psychology, 168, 108239. <https://doi.org/10.1016/j.biopsycho.2021.108239>

```text
@article{LEGRAND2022108239,
title = {The heart rate discrimination task: A psychophysical method to estimate the accuracy and precision of interoceptive beliefs},
journal = {Biological Psychology},
volume = {168},
pages = {108239},
year = {2022},
issn = {0301-0511},
doi = {10.1016/j.biopsycho.2021.108239},
url = {https://www.sciencedirect.com/science/article/pii/S0301051121002325},
author = {Nicolas Legrand and Niia Nikolova and Camile Correa and Malthe Brændholt and Anna Stuckert and Nanna Kildahl and Melina Vejlø and Francesca Fardo and Micah Allen},
keywords = {Heart rate discrimination, Heartbeat tracking, Interoception, Psychophysics, Metacognition},
abstract = {Interoception - the physiological sense of our inner bodies - has risen to the forefront of psychological and psychiatric research. Much of this research utilizes tasks that attempt to measure the ability to accurately detect cardiac signals. Unfortunately, these approaches are confounded by well-known issues limiting their validity and interpretation. At the core of this controversy is the role of subjective beliefs about the heart rate in confounding measures of interoceptive accuracy. Here, we recast these beliefs as an important part of the causal machinery of interoception, and offer a novel psychophysical “heart rate discrimination“ method to estimate their accuracy and precision. By applying this task in 223 healthy participants, we demonstrate that cardiac interoceptive beliefs are more biased, less precise, and are associated with poorer metacognitive insight relative to an exteroceptive control condition. Our task, provided as an open-source python package, offers a robust approach to quantifying cardiac beliefs.}
}
```

## The software

To refer to the software itself, or to a specific version, cite its Zenodo archive. The concept DOI, [10.5281/zenodo.22139105](https://doi.org/10.5281/zenodo.22139105), always resolves to the latest release; each release also has a DOI of its own, listed on the Zenodo page.

```text
@software{cardioception,
author = {Micah Allen and Nicolas Legrand and {Embodied Computation Group, Aarhus University}},
title = {Cardioception},
version = {1.0.0},
year = {2026},
doi = {10.5281/zenodo.22139105},
url = {https://github.com/embodied-computation-group/Cardioception}
}
```

## The other tasks

For a task other than the HRD, cite the method it implements as well:

| Task | Cite |
|---|---|
| Heartbeat Counting | {cite:t}`1981:schandry`; {cite:t}`1978:dale` |
| Phase Adjustment Task | {cite:t}`2021:plans`; {cite:t}`2026:hodgetts` for the ECG version; {cite:t}`2026:palmer` for the scoring |
| Heartbeat Synchrony Discrimination | {cite:t}`1993:brener` for the method it makes adaptive. The HSD itself has no paper yet; cite the software |

## The analysis models

If you analyze HRD data with the hierarchical models and priors of the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception), as the tutorials do, cite:

* Courtin, A. S., Ehmsen, J. F., Banellis, L., Fardo, F., & Allen, M. G. (2026). Hierarchical Bayesian modeling of interoceptive psychophysics. Behavior Research Methods, 58(9), 260. <https://doi.org/10.3758/s13428-026-03137-3>

## Systole

If you also use [Systole](https://embodied-computation-group.github.io/systole/index.html) to read the pulse oximeter (the default in Cardioception) or to analyze physiological recordings, cite:

* Legrand N., Allen, M., (2022). Systole: A python package for cardiac signal synchrony and analysis. Journal of Open Source Software, 7(69), 3832, <https://doi.org/10.21105/joss.03832>

```text
@article{Legrand2022,
doi = {10.21105/joss.03832},
url = {https://doi.org/10.21105/joss.03832},
year = {2022},
publisher = {The Open Journal},
volume = {7},
number = {69},
pages = {3832},
author = {Nicolas Legrand and Micah Allen},
title = {Systole: A python package for cardiac signal synchrony and analysis},
journal = {Journal of Open Source Software}
}
```

## Publications using the HRD

If your work is missing, open an issue or a pull request and we will add it.

- Banellis, L., Nikolova, N., Ehmsen, J. F., Courtin, A. S., Vejlø, M., Tyrer, A., Böhme, R. A., Bavato, F., Hoogervorst, K., Fardo, F., & Allen, M. G. (2026). Interoceptive performance is unrelated to mental health symptoms in a large multi-domain psychophysical investigation. *Nature Mental Health*, 1–15. <https://doi.org/10.1038/s44220-026-00688-4>
- Courtin, A. S., Ehmsen, J. F., Banellis, L., Fardo, F., & Allen, M. G. (2026). Hierarchical Bayesian modeling of interoceptive psychophysics. *Behavior Research Methods*, 58(9), 260. <https://doi.org/10.3758/s13428-026-03137-3>
- Desdentado, L., Allen, M. G., Schultze, J., Banellis, L., Navarro-Siurana, J., Nikolova, N., Baños, R. M., & Pollatos, O. (2026). Cardiac interoception in action: Modulation after a stress induction with a speech task. *Biological Psychology*, 205, 109228. <https://doi.org/10.1016/j.biopsycho.2026.109228>
- Jeganathan, J., Campbell, M. E. J., Legrand, N., Allen, M., & Breakspear, M. (2025). Aberrant cardiac interoception in psychosis. *Schizophrenia Bulletin*, 51(1), 208–216. <https://doi.org/10.1093/schbul/sbae078>
- Tyrer, A., Ehmsen, J. F., Hoogervorst, K., Nikolova, N., Pando-Naude, V., Steenkjær, C. H., Courtin, A. S., Fardo, F., Hauser, T., Bavato, F., & Allen, M. (2025). Peripheral beta-blockade differentially enhances cardiac and respiratory interoception. *bioRxiv*. <https://doi.org/10.1101/2025.02.28.640776>
- Leganes-Fonteneau, M. (2024). Alcohol effects on interoception shape expectancies and subjective effects: A registered report using the heart rate discrimination task. *Alcohol and Alcoholism*, 59(4), agae025. <https://doi.org/10.1093/alcalc/agae025>
