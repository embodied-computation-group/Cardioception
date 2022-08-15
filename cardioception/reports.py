# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import os
import subprocess
from typing import Optional

import papermill as pm
import pkg_resources  # type: ignore


def report(resultPath: str, reportPath: Optional[str] = None, task: str = "HRD"):
    """Create HTML Report

    Parameters
    ----------
    resultPath : str
        Path variable. Where the results are stored (one participant only).
    reportPath : Optional[str], optional
        Where the HTML report should be saved. If `None`, default will be in
        the provided `resultPath`.
    task : str, optional
        The task ("HRD" or "HBC"), by default "HRD".
    """
    if reportPath is None:
        reportPath = resultPath
    temp_notebook = os.path.join(reportPath, "temp.ipynb")
    htmlreport = os.path.join(reportPath, f"{task}_report.html")

    if task == "HRD":
        template = "HeartRateDiscrimination.ipynb"
    elif task == "HBC":
        template = "HeartBeatCounting.ipynb"

    pm.execute_notebook(
        pkg_resources.resource_filename("cardioception.notebooks", template),
        temp_notebook,
        parameters=dict(resultPath=resultPath, reportPath=reportPath),
    )
    command = (
        "jupyter nbconvert --to html --execute "
        + f"--TemplateExporter.exclude_input=True {temp_notebook} --output {htmlreport}"
    )
    subprocess.call(command)
    os.remove(temp_notebook)
