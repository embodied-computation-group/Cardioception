---
myst:
  html_meta:
    description: "The legacy HTML reports in Cardioception: a notebook of main results, quality checks and preprocessing, run with papermill."
    keywords: "cardioception reports, HTML report, papermill, heart rate discrimination, heartbeat counting"
---

# HTML reports (legacy)

The HRD and the HBC each come with a notebook of main results, quality checks and basic preprocessing. `report` runs it with papermill and writes it out as HTML:

```python
from cardioception.reports import report

resultPath = "./"  # the folder holding one participant's result files
reportPath = "./"  # where to write the HTML report

report(resultPath, reportPath, task="HRD")
```

```{warning}
The notebooks look for the file names that version 0.7 and earlier wrote, so they do not read a 1.0 run directory. The HRD notebook looks for `*Intero_posterior.npy`, where 1.0 writes `*_posterior-Intero.npy`, and the HBC notebook for one `.npy` recording per trial, where 1.0 writes `*_ppg-<n>.txt`.
```

papermill, matplotlib, seaborn and pingouin install with the package. The reports also need three things that do not:

* [Jupyter nbconvert](https://nbconvert.readthedocs.io/), which `report` calls to convert the notebook to HTML.
* [metadpy](https://github.com/embodied-computation-group/metadpy) (>=0.1.0), which the HRD notebook imports.
* [PyMC](https://www.pymc.io/welcome.html) (>=5.0), which `preprocessing` uses with metadpy.
