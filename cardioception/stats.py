# Author: Nicolas Legrand <nicolas.legrand@cas.au.dk>

from typing import List

import numpy as np
import pandas as pd


def cumulative_normal(x, alpha, beta):
    import pytensor.tensor as pt

    # Cumulative distribution function for the standard normal distribution
    return 0.5 + 0.5 * pt.erf((x - alpha) / (beta * pt.sqrt(2)))


def psychophysics(
    summary_df: pd.DataFrame,
    variables: List[str] = ["participant_id", "Modality"],
    additional_variables=[],
) -> pd.DataFrame:
    r"""Extract psychometric parameters from a set of result files from the HRD task.

    This function will use a Bayesian model to estimate psychophysics parameters and
    perform inference using MCMC sampling. The following parameters are returned:

    * Interoceptive bias

        * `bayesian_threshold` (the mean of the interoceptive bias)

        * `bayesian_slope` (the slope of the interoceptive bias)

    The interoceptive bias :math:`\alpha` represents the difference between the real
    heart rate and the cardiac belief. The interoceptive slope :math:`\beta` represents
    the precision of this bias (the standard deviation of the underlying cumulative
    normal function). These parameters are estimated using the following model:

    .. math::

        r_{i} & \sim \mathcal{Binomial}(\theta_{i},n_{i}) \\
        \Phi_{i}(x_{i}, \alpha, \beta) & = \frac{1}{2} + \frac{1}{2} * erf(\frac{x_{i}
        - \alpha}{\beta * \sqrt{2}}) \\
        \alpha & \sim \mathcal{Uniform}(-50.5, 50.5) \\
        \beta & \sim  \mathcal{Uniform}(.1, 30.0) \\

    Here :math:`x_i` is the proportion of positive response at the intensity :math:`i`.
    To compute the interoceptive bias, we use the `Alpha` value (the difference between
    the real heart rate and the tone that is presented at each trial). A negative value
    means that the tone needs to be slower than the heart rate for the participant to
    find it the same.

    * Cardiac beliefs

        * `belief_mean`

        * `belief_std`

    The mean of the cardiac belief :math:`\psi_{alpha}` represents the cardiac frequency
    that was inferred on average through the task. The precision of the cardiac belief
    :math:`\psi_{beta}` is the standard deviation around this belief. Under the
    hypothesis that the participant is not using any interoceptive information to
    perform the task, this value is the belief used to inform the decision by comparing
    it to the tones. These parameters are estimated using the following model:

    .. math::

        r_{i} & \sim \mathcal{Binomial}(\theta_{i},n_{i}) \\
        \Phi_{i}(x_{i}, \psi_{alpha}, \psi_{beta}) & = \frac{1}{2} + \frac{1}{2} *
        erf(\frac{x_{i} - \psi_{alpha}}{\psi_{beta} * \sqrt{2}}) \\
        \psi_{alpha} & \sim \mathcal{Uniform}(15.0, 200.0) \\
        \psi_{beta} & \sim  \mathcal{Uniform}(.1, 50.0) \\

    Here :math:`x_i` is the proportion of positive response at the intensity :math:`i`.
    To compute the interoceptive bias, we use the frequency of the tone presented
    during the decision phase only (assuming therefore that this is the only source of
    information used by the participant). The units are beat per minute (bpm).

    .. note::
        In the two equations above, $erf$ denotes the
        `error functions <https://en.wikipedia.org/wiki/Error_function>`_ and :math:`\phi`
        is the cumulative normal function.

    * Heart rate

        * `hr_mean` the mean of the averaged heart rates

        * `hr_std` the standard deviation of the averaged heart rates

    The mean of the averaged heart rates :math:`\omega_{alpha}` and the standard
    deviation of the averaged heart rates :math:`\omega_{beta}` are computed using the
    following model:

    .. math::

        r_{i} & \sim \mathcal{Normal}(\omega_{alpha},\omega_{beta}) \\
        \omega_{alpha} & \sim \mathcal{Uniform}(15.0, 200.0) \\
        \omega_{beta} & \sim  \mathcal{Uniform}(.1, 50.0) \\

    Here :math:`x_i` is the average heart rate at each trial.

    .. note::
        The heart rate that was recorded on every trial is the average of what was
        recorded over the 5 seconds of interoception during the listening phase. Here
        we are returning the mean and standard deviation of these values.

    .. warning::
        This function requires `PyMC <https://github.com/pymc-devs/pymc>`_.

    Parameters
    ----------
    summary_df :
        The data frame merges the individual result data frames. Multiple variables/
        condition can be specified using separate columns with the `variables` argument.
    variables :
        The variables coding for group/repeated measures. The default is
        `participant_id` and `Modality`.
    additional_variables :
        Additional variables for group/repeated measures.

    Returns
    -------
    results_df :
        The data frame containing, for each participant/condition/group, the
        psychometric variables.
    """
    import pymc as pm

    # create a list of variables to use to group the dataframe
    variables.extend(additional_variables)

    # the final data fram where results are saved
    results_df = pd.DataFrame()

    print("Extracting psychometric parameters from a large data frame.")
    print(f"... Independent variables provided: {variables}.")
    print(f"... {len(list(summary_df.groupby(variables)))} conditions in total.")

    # extract psychophysics parameters from trials for each sub data frame
    bias_x_total, bias_n_total, bias_r_total, bias_sub_total = [], [], [], []  # bias
    beliefs_x_total, beliefs_n_total, beliefs_r_total, beliefs_sub_total = (
        [],
        [],
        [],
        [],
    )  # beliefs
    hr_total, hr_sub_total = [], []  # heart rate
    print("... Extract trial-level psychophysics variables.")
    for i, grouped in enumerate(list(summary_df.groupby(variables))):
        cols, sub_df = grouped

        # update the independent variables
        results_df = pd.concat(
            [results_df, pd.Series(cols, index=variables).to_frame().T],
            ignore_index=True,
        )

        # extract trial-level psychometric parameters for bias
        # ------------------------------------------------------------------------------

        # intensity level, number of trials, number of positive responses
        x, n, r = np.zeros(203), np.zeros(203), np.zeros(203)
        for ii, intensity in enumerate(np.arange(-50.5, 51, 0.5)):
            x[ii] = intensity
            n[ii] = sum(sub_df.Alpha == intensity)
            r[ii] = sum((sub_df.Alpha == intensity) & (sub_df.Decision == "More"))

        # remove no responses trials
        validmask = n != 0
        xij, nij, rij = x[validmask], n[validmask], r[validmask]
        sub_vec = [i] * len(xij)

        bias_x_total.extend(xij)
        bias_n_total.extend(nij)
        bias_r_total.extend(rij)
        bias_sub_total.extend(sub_vec)

        # extract trial-level psychometric parameters for beliefs
        # ------------------------------------------------------------------------------

        # intensity level, number of trials, number of positive responses
        x, n, r = np.zeros(370), np.zeros(370), np.zeros(370)
        for ii, intensity in enumerate(np.arange(15, 200, 0.5)):
            x[ii] = intensity
            n[ii] = sum(sub_df.responseBPM == intensity)
            r[ii] = sum((sub_df.responseBPM == intensity) & (sub_df.Decision == "More"))

        # remove no responses trials
        validmask = n != 0
        xij, nij, rij = x[validmask], n[validmask], r[validmask]
        sub_vec = [i] * len(xij)

        beliefs_x_total.extend(xij)
        beliefs_n_total.extend(nij)
        beliefs_r_total.extend(rij)
        beliefs_sub_total.extend(sub_vec)

        # extract trial-level heart rate
        # ------------------------------------------------------------------------------

        # intensity level, number of trials, number of positive responses
        hr = sub_df.responseBPM.to_numpy()
        sub_vec = [i] * len(hr)

        hr_total.extend(hr)
        hr_sub_total.extend(sub_vec)

    # get the number of models to fit
    n = len(list(summary_df.groupby(variables)))

    # fit the model (thresholds and slopes)
    print("... Create the model and sample")
    with pm.Model():
        # Heart Rate -------------------------------------------------------------------
        hr_mean = pm.Uniform("hr_mean", lower=15.0, upper=200.0, shape=n)
        hr_std = pm.Uniform("hr_std", lower=0.1, upper=50.0, shape=n)
        _ = pm.Normal(
            "heart_rate",
            mu=hr_mean[hr_sub_total],
            sigma=hr_std[hr_sub_total],
            observed=hr_total,
        )

        # Cardiac beliefs --------------------------------------------------------------
        belief_mean = pm.Uniform("belief_mean", lower=15.0, upper=200.0, shape=n)
        belief_std = pm.Uniform("belief_std", lower=0.1, upper=50.0, shape=n)
        theta_beliefs = pm.Deterministic(
            "theta_beliefs",
            cumulative_normal(
                beliefs_x_total,
                belief_mean[beliefs_sub_total],
                belief_std[beliefs_sub_total],
            ),
        )
        _ = pm.Binomial(
            "p_beliefs", p=theta_beliefs, n=beliefs_n_total, observed=beliefs_r_total
        )

        # Slope and Threshold ----------------------------------------------------------
        threshold = pm.Uniform("threshold", lower=-50.5, upper=50.5, shape=n)
        slope = pm.Uniform("slope", lower=0.1, upper=30.0, shape=n)
        theta_bias = pm.Deterministic(
            "theta_bias",
            cumulative_normal(
                bias_x_total, threshold[bias_sub_total], slope[bias_sub_total]
            ),
        )
        _ = pm.Binomial("p_bias", p=theta_bias, n=bias_n_total, observed=bias_r_total)

        # sample
        idata = pm.sample(chains=4, cores=4)

    # save the mean of the parameter in the final dataframe
    results_df["bayesian_threshold"] = idata.posterior.threshold.mean(
        axis=(0, 1)
    ).to_numpy()
    results_df["bayesian_slope"] = idata.posterior.slope.mean(axis=(0, 1)).to_numpy()
    results_df["belief_mean"] = idata.posterior.belief_mean.mean(axis=(0, 1)).to_numpy()
    results_df["belief_std"] = idata.posterior.belief_std.mean(axis=(0, 1)).to_numpy()
    results_df["hr_mean"] = idata.posterior.hr_mean.mean(axis=(0, 1)).to_numpy()
    results_df["hr_std"] = idata.posterior.hr_std.mean(axis=(0, 1)).to_numpy()

    return results_df


def behaviours(
    summary_df: pd.DataFrame,
    variables: List[str] = ["participant_id", "Modality"],
    additional_variables=[],
) -> pd.DataFrame:
    r"""Extract behavioural parameters from a set of result files from the HRD task.

    For each participant/repeated measure/group, the following parameters are
    returned:

    * threshold
        The threshold of the psychometric curve as estimated during the task by the Psi
        staircase.
    * slope
        The slope of the psychometric curve as estimated during the task by the Psi
        staircase.
    * decision_mean_rt
        The average response time to decide whether the tone is faster or slower than
        the heart rate.
    * decision_median_rt
        The median response time to decide whether the tone is faster or slower than
        the heart rate.
    * confidence_mean_rt
        The average response time to provide the confidence ratings.
    * confidence_median_rt
        The median response time to provide the confidence ratings.
    * confidence_mean
        The average confidence level (using the same scale as what was used during
        the task).
    * dprime
        The sensitivity (SDT indices) in discriminating whether the tone is faster than
        the heart rate or not.
    * criterion
        The bias (SDT indices) in discriminating whether the tone is faster than the
        heart rate or not.

    .. warning::
        This function requires `metadpy <https://github.com/LegrandNico/metadpy>`_.

    Parameters
    ----------
    summary_df :
        The data frame merges the individual result data frames. Multiple variables /
        condition can be specified using separate columns with the `variables` argument.
    variables :
        The variables coding for group / repeated measures. The default is
        `participant_id` and `Modality`.
    additional_variables :
        Additional variables for group / repeated measures.

    Returns
    -------
    results_df :
        The data frame containing, for each participant/condition/group, the
        psychometric variables.
    """
    from metadpy import sdt

    # create a list of variables to use to group the dataframe
    variables.extend(additional_variables)

    # the final data fram where results are saved
    results_df = pd.DataFrame()

    print("Extracting behavioural indices from a large data frame.")
    print(f"... Independent variables provided: {variables}.")
    print(f"... {len(list(summary_df.groupby(variables)))} conditions in total.")

    for grouped in list(summary_df.groupby(variables)):
        cols, sub_df = grouped

        # psychophysics (Psi estimates)
        threshold = sub_df.EstimatedThreshold.dropna().iloc[-1]
        slope = sub_df.EstimatedSlope.dropna().iloc[-1]

        # response time
        # -------------
        decision_mean_rt = sub_df.DecisionRT.mean()
        decision_median_rt = sub_df.DecisionRT.median()

        confidence_mean_rt = sub_df.ConfidenceRT.mean()
        confidence_median_rt = sub_df.ConfidenceRT.median()

        # confidence
        # ----------
        confidence_mean = sub_df.Confidence.mean()

        # signal detection theory metrics
        # -------------------------------
        sub_df["Stimuli"] = sub_df.responseBPM > sub_df.listenBPM
        sub_df["Responses"] = sub_df.Decision == "More"

        # check that both signals have at least 5 valid trials each
        if (sub_df["Stimuli"].sum() > 5) & ((~sub_df["Stimuli"]).sum() > 5):
            hit, miss, fa, cr = sub_df.scores()
            hr, far = sdt.rates(hits=hit, misses=miss, fas=fa, crs=cr)
            dprime, criterion = sdt.dprime(hit_rate=hr, fa_rate=far), sdt.criterion(
                hit_rate=hr, fa_rate=far
            )
        else:
            (
                dprime,
                criterion,
            ) = (
                None,
                None,
            )

        # update the independent variables
        new_row = pd.Series(cols, index=variables).to_frame().T
        new_row["threshold"] = threshold
        new_row["slope"] = slope
        new_row["decision_mean_rt"] = decision_mean_rt
        new_row["decision_median_rt"] = decision_median_rt
        new_row["confidence_mean_rt"] = confidence_mean_rt
        new_row["confidence_median_rt"] = confidence_median_rt
        new_row["confidence_mean"] = confidence_mean
        new_row["dprime"] = dprime
        new_row["criterion"] = criterion

        results_df = pd.concat(
            [results_df, new_row],
            ignore_index=True,
        )

    return results_df


def metacognition(
    summary_df: pd.DataFrame,
    variables: List[str] = ["participant_id", "Modality"],
    additional_variables=[],
    bayesian: bool = True,
) -> pd.DataFrame:
    r"""Extract metacognitive parameters from a set of result files from the HRD task.

    For each participant/repeated measure/group, the following parameters are
    returned:


    .. warning::
        This function requires `metadpy <https://github.com/LegrandNico/metadpy>`_.

    Parameters
    ----------
    summary_df :
        The data frame merges the individual result data frames. Multiple variables/
        condition can be specified using separate columns with the `variables` argument.
    variables :
        The variables coding for group/repeated measures. The default is
        `participant_id` and `Modality`.
    additional_variables :
        Additional variables for group/repeated measures.

    Returns
    -------
    results_df :
        The data frame containing, for each participant/condition/group, the
        psychometric variables.
    """
