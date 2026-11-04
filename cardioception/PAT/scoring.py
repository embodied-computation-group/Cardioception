# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Consistency scores for the phase adjustment task (PAT).

A PAT trial has no correct answer. What is scored is how consistently a
participant places the tone in the cardiac cycle across trials. Each chosen
delay ``d`` (ms after the R-wave) is turned into a phase angle with a heart
period ``p`` (ms), ``theta = 2 pi d / p``, and the consistency is the mean
resultant length (MRL) of those angles, from 0 (spread evenly round the cycle)
to 1 (every trial at the same phase). Confidence ratings can weight the trials.

Following Hodgetts et al. (2026, Psychophysiology 63:e70415), the score is
computed eight ways, crossing three factors:

- mapping: *variable* (each trial's own period, phase-based consistency) or
  *fixed* (the participant's median period for every trial, delay-based
  consistency; trials whose delay exceeds that median are dropped);
- period: the *anticipated* period used online (mean of the last 3 R-R
  intervals) or the *observed* R-R interval that contained the key press;
- weighting: *none* or *confidence*.

Before scoring, trials whose period lies more than 5 robust standard
deviations (1.4826 times the median absolute deviation) from the
participant's median are removed, separately for each period type.

Each score is compared with its own chance threshold: the 95th percentile of
the MRL of the same number of trials with delays drawn uniformly over the
period, by Monte Carlo. A score above the threshold is labelled
*interoceptive*. The label is descriptive.

Everything here is plain numpy and pandas, so it runs without PsychoPy.
"""

from typing import Dict, List, Optional, TypeAlias, Union

import numpy as np
import numpy.typing as npt
import pandas as pd

#: Factor converting the median absolute deviation into a robust standard
#: deviation for normally distributed data.
ROBUST_SD = 1.4826

#: Default seed for the Monte Carlo thresholds, so that the same file always
#: gives the same thresholds. Pass ``seed=None`` for fresh randomness.
DEFAULT_SEED = 0

#: ``final.txt`` columns the grid reads.
FINAL_COLUMNS = (
    "Block",
    "ChosenDelayMs",
    "AnticipatedPeriodMs",
    "ObservedPeriodMs",
    "Confidence",
)

#: Period type of the grid, and the ``final.txt`` column holding it.
PERIOD_COLUMNS: Dict[str, str] = {
    "anticipated": "AnticipatedPeriodMs",
    "observed": "ObservedPeriodMs",
}

#: Columns of the DataFrame returned by :func:`consistency_grid`.
GRID_COLUMNS = [
    "mapping",
    "period",
    "weighting",
    "n_trials",
    "score",
    "threshold",
    "interoceptive",
]

#: Upper bound on the number of simulated angles held in memory at once.
_CHUNK_VALUES = 2_000_000

Seed = Union[int, np.random.Generator, None]
FloatArray: TypeAlias = npt.NDArray[np.float64]


def phase_angles(delay_ms: npt.ArrayLike, period_ms: npt.ArrayLike) -> FloatArray:
    """Turn delays after the R-wave into phase angles of the cardiac cycle.

    Parameters
    ----------
    delay_ms : array-like
        Delays from the R-wave to the tone, in ms.
    period_ms : array-like
        Heart periods, in ms, one per delay or a single value for all.

    Returns
    -------
    theta : np.ndarray
        ``2 pi delay / period`` wrapped into [0, 2 pi), in radians. NaN where
        either input is NaN.
    """
    delay = np.asarray(delay_ms, dtype=float)
    period = np.asarray(period_ms, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        theta = np.mod(2 * np.pi * delay / period, 2 * np.pi)
    return np.asarray(theta, dtype=float)


def mean_resultant_length(
    theta: npt.ArrayLike, weights: Optional[npt.ArrayLike] = None
) -> float:
    """Mean resultant length of a set of angles.

    ``R = |sum_r w_r exp(i theta_r)| / sum_r w_r``, with all weights 1 when
    ``weights`` is None.

    Parameters
    ----------
    theta : array-like
        Angles in radians.
    weights : array-like or None
        Non-negative weights, one per angle (confidence ratings, for example).

    Returns
    -------
    R : float
        Between 0 and 1. Angles or weights that are NaN are ignored. NaN when no
        angle is left or the weights sum to 0.
    """
    angles = np.asarray(theta, dtype=float).ravel()
    if weights is None:
        w = np.ones_like(angles)
    else:
        w = np.asarray(weights, dtype=float).ravel()
        if w.shape != angles.shape:
            raise ValueError(
                f"weights has {w.size} values but theta has {angles.size}."
            )
        if np.any(w[np.isfinite(w)] < 0):
            raise ValueError("weights must be non-negative.")
    valid = np.isfinite(angles) & np.isfinite(w)
    angles, w = angles[valid], w[valid]
    total = w.sum()
    if angles.size == 0 or total <= 0:
        return float("nan")
    resultant = np.hypot(np.sum(w * np.cos(angles)), np.sum(w * np.sin(angles)))
    return float(resultant / total)


def mad_outliers(x: npt.ArrayLike, k: float = 5.0) -> npt.NDArray[np.bool_]:
    """Flag values more than ``k`` robust standard deviations from the median.

    The robust standard deviation is 1.4826 times the median absolute
    deviation (Leys et al., 2013).

    Parameters
    ----------
    x : array-like
        Values, typically one participant's heart periods in ms.
    k : float
        Cut-off in robust standard deviations. Hodgetts et al. (2026) use 5.

    Returns
    -------
    mask : np.ndarray of bool
        True for outliers. NaN values are not flagged: they are missing, not
        outlying, and callers drop them separately.
    """
    if not k > 0:
        raise ValueError(f"k must be positive, got {k}.")
    values = np.asarray(x, dtype=float)
    finite = np.isfinite(values)
    mask = np.zeros(values.shape, dtype=bool)
    if not finite.any():
        return mask
    median = np.median(values[finite])
    robust_sd = ROBUST_SD * np.median(np.abs(values[finite] - median))
    mask[finite] = np.abs(values[finite] - median) > k * robust_sd
    return mask


def monte_carlo_threshold(
    periods_ms: npt.ArrayLike,
    n_trials: int,
    n_sim: int = 100_000,
    q: float = 0.95,
    fixed: bool = False,
    seed: Seed = DEFAULT_SEED,
    weights: Optional[npt.ArrayLike] = None,
) -> float:
    """Chance threshold for the mean resultant length, by Monte Carlo.

    Each simulated participant makes ``n_trials`` choices with delays drawn
    uniformly on [0, p), turned into angles with the same period ``p``, and the
    MRL is computed. The threshold is the ``q`` quantile of ``n_sim`` such MRLs.

    Parameters
    ----------
    periods_ms : array-like
        The participant's heart periods in ms (NaN ignored). With
        ``fixed=False`` each trial uses its own period: when there are exactly
        ``n_trials`` of them they are used as they are, otherwise each
        simulated trial draws one at random. With ``fixed=True`` every trial
        uses their median.
    n_trials : int
        Number of trials in each simulated participant.
    n_sim : int
        Number of simulated participants. 100,000 in the paper; fewer is fine
        for tests.
    q : float
        Quantile of the simulated MRLs, 0.95 in the paper.
    fixed : bool
        Fixed mapping (one period for all trials) rather than variable mapping.
    seed : int, np.random.Generator or None
        Seed of the random generator. The default is fixed, so thresholds are
        reproducible; None draws fresh entropy.
    weights : array-like or None
        Confidence weights, one per trial. When given, the null distribution is
        that of the weighted MRL with these weights and random angles.

    Returns
    -------
    threshold : float
    """
    periods = np.asarray(periods_ms, dtype=float).ravel()
    periods = periods[np.isfinite(periods)]
    if periods.size == 0:
        raise ValueError("periods_ms holds no finite period.")
    if np.any(periods <= 0):
        raise ValueError("periods_ms must be positive.")
    n_trials = int(n_trials)
    if n_trials < 1:
        raise ValueError(f"n_trials must be at least 1, got {n_trials}.")
    n_sim = int(n_sim)
    if n_sim < 1:
        raise ValueError(f"n_sim must be at least 1, got {n_sim}.")
    if not 0 < q < 1:
        raise ValueError(f"q must be between 0 and 1, got {q}.")

    if weights is None:
        w = np.ones(n_trials)
    else:
        w = np.asarray(weights, dtype=float).ravel()
        if w.size != n_trials:
            raise ValueError(f"weights has {w.size} values, n_trials is {n_trials}.")
        if not np.all(np.isfinite(w)) or np.any(w < 0) or w.sum() <= 0:
            raise ValueError("weights must be finite, non-negative and not all 0.")

    rng = np.random.default_rng(seed)
    chunk = max(1, min(n_sim, _CHUNK_VALUES // n_trials))
    scores = np.empty(n_sim)
    done = 0
    while done < n_sim:
        size = min(chunk, n_sim - done)
        if fixed:
            p: FloatArray = np.full((size, n_trials), np.median(periods))
        elif periods.size == n_trials:
            p = np.broadcast_to(periods, (size, n_trials))
        else:
            p = rng.choice(periods, size=(size, n_trials))
        delays = rng.uniform(0.0, 1.0, size=(size, n_trials)) * p
        theta = phase_angles(delays, p)
        resultant = np.hypot(np.cos(theta) @ w, np.sin(theta) @ w)
        end = done + size
        scores[done:end] = resultant / w.sum()
        done = end
    return float(np.quantile(scores, q))


def extero_threshold(
    n_trials: int,
    period_ms: float = 1000.0,
    n_sim: int = 100_000,
    q: float = 0.95,
    seed: Seed = DEFAULT_SEED,
) -> float:
    """Chance threshold for the exteroceptive task with a fixed period.

    Hodgetts et al. (2026) simulate 28 trials at a fixed 1000 ms period and get
    R = 0.33. Participants below it on the exteroceptive task are screened out
    before the PAT analysis.
    """
    return monte_carlo_threshold(
        [period_ms], n_trials, n_sim=n_sim, q=q, fixed=True, seed=seed
    )


def _numeric(df: pd.DataFrame, column: str) -> FloatArray:
    return np.asarray(pd.to_numeric(df[column], errors="coerce"), dtype=float)


def consistency_grid(
    final_df: pd.DataFrame,
    n_sim: int = 100_000,
    q: float = 0.95,
    seed: Seed = DEFAULT_SEED,
    k: float = 5.0,
) -> pd.DataFrame:
    """Score one participant on the 2 x 2 x 2 grid of Hodgetts et al. (2026).

    Parameters
    ----------
    final_df : pd.DataFrame
        The task's ``final.txt``. Columns used: ``Block`` (only ``"main"``
        rows count), ``ChosenDelayMs``, ``AnticipatedPeriodMs``,
        ``ObservedPeriodMs`` and ``Confidence``.
    n_sim, q, seed :
        Passed to :func:`monte_carlo_threshold`. With an int seed (the default)
        the thresholds are reproducible.
    k : float
        Outlier cut-off for the periods, in robust standard deviations.

    Returns
    -------
    grid : pd.DataFrame
        Eight rows with the columns ``mapping`` (``variable``/``fixed``),
        ``period`` (``anticipated``/``observed``), ``weighting``
        (``none``/``confidence``), ``n_trials`` (trials scored), ``score``
        (MRL), ``threshold`` and ``interoceptive`` (score above threshold).
        A cell with no usable trial (no observed periods, or no confidence
        ratings for the weighted cells) has NaN score and threshold and is not
        interoceptive.

    Notes
    -----
    Per period type, trials with a missing delay or period are dropped, then
    trials whose period is a :func:`mad_outliers` outlier. Fixed mapping uses
    the median of the remaining periods for every trial and drops trials whose
    delay exceeds it. Weighted cells drop trials without a confidence rating.
    """
    missing = [c for c in FINAL_COLUMNS if c not in final_df.columns]
    if missing:
        raise ValueError(f"final_df lacks the column(s) {', '.join(missing)}.")

    main = final_df[final_df["Block"].astype(str) == "main"]
    delay = _numeric(main, "ChosenDelayMs")
    confidence = _numeric(main, "Confidence")

    rows: List[dict] = []
    for mapping in ("variable", "fixed"):
        for period_name, column in PERIOD_COLUMNS.items():
            period = _numeric(main, column)
            valid = np.isfinite(delay) & np.isfinite(period) & (period > 0)
            keep = valid & ~mad_outliers(np.where(valid, period, np.nan), k=k)
            d, p, conf = delay[keep], period[keep], confidence[keep]
            if mapping == "fixed" and p.size > 0:
                median = float(np.median(p))
                within = d <= median
                d, conf = d[within], conf[within]
                p = np.full(d.size, median)
            theta = phase_angles(d, p)

            for weighting in ("none", "confidence"):
                weights: Optional[FloatArray] = None
                th, pp = theta, p
                if weighting == "confidence":
                    rated = np.isfinite(conf) & (conf >= 0)
                    th, pp, weights = theta[rated], p[rated], conf[rated]
                n = int(th.size)
                score = threshold = float("nan")
                if n > 0 and (weights is None or weights.sum() > 0):
                    score = mean_resultant_length(th, weights)
                    threshold = monte_carlo_threshold(
                        pp,
                        n,
                        n_sim=n_sim,
                        q=q,
                        fixed=mapping == "fixed",
                        seed=seed,
                        weights=weights,
                    )
                rows.append(
                    {
                        "mapping": mapping,
                        "period": period_name,
                        "weighting": weighting,
                        "n_trials": n,
                        "score": score,
                        "threshold": threshold,
                        "interoceptive": bool(score > threshold),
                    }
                )
    return pd.DataFrame(rows, columns=GRID_COLUMNS)


__all__ = [
    "phase_angles",
    "mean_resultant_length",
    "mad_outliers",
    "monte_carlo_threshold",
    "extero_threshold",
    "consistency_grid",
]
