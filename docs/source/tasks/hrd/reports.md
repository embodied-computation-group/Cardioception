---
myst:
  html_meta:
    description: "The legacy HTML reports in Cardioception: a notebook of main results, quality checks and preprocessing, run with papermill."
    keywords: "cardioception reports, HTML report, papermill, heart rate discrimination, heartbeat counting"
---

# HTML reports (legacy)

Results are saved in the `'resultPath'` folder defined in the parameters dictionary. The HRD and the HBC each come with a notebook covering the main results, quality checks, and basic preprocessing steps. To generate the HTML report:

```python
from cardioception.reports import report

resultPath = "./"  # the folder containing the result files
reportPath = "./"  # the folder where you want to save the HTML report

report(resultPath, reportPath, task='HRD')
```

This writes the HTML report for the Heart Rate Discrimination task into `reportPath`, using the result files found in `resultPath`. It requires [papermill](https://papermill.readthedocs.io/en/latest/).

The functions that build the HTML reports also require:

* [papermill](https://papermill.readthedocs.io/en/latest/) (>=2.3.1)
* [matplotlib](https://matplotlib.org/) (>=3.3.3)
* [seaborn](https://seaborn.pydata.org/) (>=0.11.1)
* [pingouin](https://pingouin-stats.org/) (>=0.3.10)
* [metadpy](https://github.com/EmbodiedComputationGroup/metadpy) (>=0.1.0)
* [pymc](https://www.pymc.io/welcome.html) (>=5.0)
