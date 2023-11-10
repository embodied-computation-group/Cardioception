# Author: Nicolas Legrand <nicolas.legrand@cas.au.dk>

import os
import subprocess
from os import PathLike
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import pkg_resources  # type: ignore


def cumulative_normal(x, alpha, beta):
    import pytensor.tensor as pt

    # Cumulative distribution function for the standard normal distribution
    return 0.5 + 0.5 * pt.erf((x - alpha) / (beta * pt.sqrt(2)))


def preprocessing(results: Union[PathLike, pd.DataFrame]) -> pd.DataFrame:
    """From the main behavioural data frame, extract summary metrics of behavioural,
    metacognitive and interoceptive performances.

    The slope and thresholds of the interoceptive/exteroceptive psychometric function
    are reported both using the online estimate outputted by the Psi staircase (i.e.
    `slope` and `threshold`), and using a Bayesian estimation (i.e. `bayesian_slope` and
    `bayesian_threshold`). The Bayesian estimation is the recommended value to use to
    report the results. Removing outliers before fitting will change the estimation,
    which is not the case for the Psi values.

    The d-prime and criterion are also computed using a classical SDT approach
    (`dprime` and `criterion`), as well as a Bayesian estimation performed when
    estimating the metacognitive sensitivity meta-d' (`bayesian_dprime`,
    `bayesian_criterion`, `bayesian_meta_d`, `bayesian_m_ratio`). The dprime and
    criterion can vary between the two methods. It is recommended to use the estimates
    consistently. Before the estimation of SDT and metacognitive metrics, the function
    ensure that at least 5 valid trials of each signal are present, otherwise returns
    `None`.

    When using this function for analysing results from the Heart Rate Discrimination
    task, the following packages should be credited: Systole [1]_, metadpy [2]_ and
    cardioception [3]_.

    Parameters
    ----------
    results : pd.DataFrame | PathLike
        Either the path to the result file, or the Pandas Data Frame.

    Returns
    -------
    summary_df : pd.DataFrame
        The summary statistic for this participant, splitting for interoception and
        exteroception if the two conditions were used.

    Notes
    -----
    This function will require [PyMC](https://github.com/pymc-devs/pymc) (>= 5.0) and
    [metadpy](https://github.com/LegrandNico/metadpy) (>=0.1.0).

    References
    ----------
    .. [1] Legrand et al., (2022). Systole: A python package for cardiac signal
        synchrony and analysis. Journal of Open Source Software, 7(69), 3832,
        https://doi.org/10.21105/joss.03832
    .. [2] https://github.com/LegrandNico/metadpy
    .. [3] Legrand, N., Nikolova, N., Correa, C., Brændholt, M., Stuckert, A., Kildahl,
        N., Vejlø, M., Fardo, F., & Allen, M. (2021). The Heart Rate Discrimination
        Task: A psychophysical method to estimate the accuracy and precision of
        interoceptive beliefs. Biological Psychology, 108239.
        https://doi.org/10.1016/j.biopsycho.2021.108239

    """
    import arviz as az
    import pymc as pm
    from metadpy import bayesian, sdt
    from metadpy.utils import discreteRatings

    # read the input file if only the path was provided
    if not isinstance(results, pd.DataFrame):
        results = pd.read_csv(results)

    summary_df = pd.DataFrame([])

    for modality in ["Intero", "Extero"]:
        this_modality = results[results.Modality == modality].copy()

        if len(this_modality) > 10:
            # response time
            # -------------
            decision_mean_rt = this_modality.DecisionRT.mean()
            decision_median_rt = this_modality.DecisionRT.median()

            confidence_mean_rt = this_modality.ConfidenceRT.mean()
            confidence_median_rt = this_modality.ConfidenceRT.median()

            # signal detection theory metrics
            # -------------------------------
            this_modality["Stimuli"] = (
                this_modality.responseBPM > this_modality.listenBPM
            )
            this_modality["Responses"] = this_modality.Decision == "More"

            # check that both signals have at least 5 valid trials each
            if (this_modality["Stimuli"].sum() > 5) & (
                (~this_modality["Stimuli"]).sum() > 5
            ):
                hit, miss, fa, cr = this_modality.scores()
                hr, far = sdt.rates(hits=hit, misses=miss, fas=fa, crs=cr)
                d, c = sdt.dprime(hit_rate=hr, fa_rate=far), sdt.criterion(
                    hit_rate=hr, fa_rate=far
                )
            else:
                (
                    d,
                    c,
                ) = (
                    None,
                    None,
                )

            # metacognitive sensitivity
            # -------------------------
            (
                bayesian_dprime,
                bayesian_criterion,
                bayesian_meta_d,
                bayesian_m_ratio,
            ) = (None, None, None, None)

            this_modality = this_modality[
                ~this_modality.Confidence.isna()
            ].copy()  # Drop trials with NaN in confidence rating
            this_modality.loc[:, "Accuracy"] = (
                (this_modality["Stimuli"] & this_modality["Responses"])
                | (~this_modality["Stimuli"] & ~this_modality["Responses"])
            ).copy()

            # check that both signals have at least 5 valid trials each
            if (this_modality["Stimuli"].sum() > 5) & (
                (~this_modality["Stimuli"]).sum() > 5
            ):
                try:
                    new_ratings, _ = discreteRatings(
                        this_modality.Confidence.to_numpy(), verbose=False
                    )
                    this_modality.loc[:, "discrete_confidence"] = new_ratings

                    metad = bayesian.hmetad(
                        data=this_modality,
                        stimuli="Stimuli",
                        accuracy="Accuracy",
                        confidence="discrete_confidence",
                        nRatings=4,
                        output="dataframe",
                    )
                    bayesian_dprime = metad["d"].values[0]
                    bayesian_criterion = metad["c"].values[0]
                    bayesian_meta_d = metad["meta_d"].values[0]
                    bayesian_m_ratio = metad["m_ratio"].values[0]

                except ValueError:
                    print(
                        (
                            f"Cannot discretize ratings for modality: {modality}. "
                            "The metacognitive efficiency will not be reported."
                        )
                    )

            # bayesian psychophysics
            # ----------------------
            x, n, r = np.zeros(203), np.zeros(203), np.zeros(203)

            for ii, intensity in enumerate(np.arange(-50.5, 51, 0.5)):
                x[ii] = intensity
                n[ii] = sum(this_modality.Alpha == intensity)
                r[ii] = sum(
                    (this_modality.Alpha == intensity)
                    & (this_modality.Decision == "More")
                )
            validmask = n != 0  # remove no responses trials
            xij, nij, rij = x[validmask], n[validmask], r[validmask]

            with pm.Model():
                alpha = pm.Uniform("alpha", lower=-40.5, upper=40.5)
                beta = pm.HalfNormal("beta", 10)
                thetaij = pm.Deterministic(
                    "thetaij", cumulative_normal(xij, alpha, beta)
                )
                _ = pm.Binomial("rij", p=thetaij, n=nij, observed=rij)
                idata = pm.sample(chains=4, cores=4)
            res = az.summary(idata)
            bayesian_threshold = res["mean"].alpha
            bayesian_slope = res["mean"].beta

            # Psi estimates
            threshold = this_modality.EstimatedThreshold.iloc[-1]
            slope = this_modality.EstimatedSlope.iloc[-1]

            # concatenate the summary statistics
            summary_df = pd.concat(
                [
                    summary_df,
                    pd.DataFrame(
                        {
                            "modality": modality,
                            "decision_mean_rt": decision_mean_rt,
                            "decision_median_rt": decision_median_rt,
                            "confidence_mean_rt": confidence_mean_rt,
                            "confidence_median_rt": confidence_median_rt,
                            "dprime": d,
                            "criterion": c,
                            "bayesian_dprime": bayesian_dprime,
                            "bayesian_criterion": bayesian_criterion,
                            "bayesian_meta_d": bayesian_meta_d,
                            "bayesian_m_ratio": bayesian_m_ratio,
                            "threshold": threshold,
                            "slope": slope,
                            "bayesian_threshold": bayesian_threshold,
                            "bayesian_slope": bayesian_slope,
                        },
                        index=[0],
                    ),
                ],
                ignore_index=True,
            )

    return summary_df


def report(
    result_path: PathLike, report_path: Optional[PathLike] = None, task: str = "HRD"
):
    """From the results folders, create HTML reports of behavioural and physiological
    data.

    Parameters
    ----------
    resultPath : PathLike
        Path variable. Where the results are stored (one participant only).
    reportPath : PathLike, optional
        Where the HTML report should be saved. If `None`, default will be in the
        provided `resultPath`.
    task : str, optional
        The task ("HRD" or "HBC"), by default "HRD".

    """
    from papermill import execute_notebook

    if report_path is None:
        report_path = result_path
    temp_notebook = Path(report_path, "temp.ipynb")
    htmlreport = Path(report_path, f"{task}_report.html")

    if task == "HRD":
        template = "HeartRateDiscrimination.ipynb"
    elif task == "HBC":
        template = "HeartBeatCounting.ipynb"

    execute_notebook(
        pkg_resources.resource_filename("cardioception.notebooks", template),
        temp_notebook,
        parameters=dict(resultPath=str(result_path), reportPath=str(report_path)),
    )
    command = (
        "jupyter nbconvert --to html --execute "
        + f"--TemplateExporter.exclude_input=True {temp_notebook} --output {htmlreport}"
    )
    subprocess.call(command, shell=True)
    os.remove(temp_notebook)
