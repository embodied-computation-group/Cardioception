# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Simulation study: Heartbeat Synchrony Discrimination (HSD) against constant stimuli.

How many five-tone trials does :class:`~cardioception.HSD.psi.SynchronyPsi`
need to recover the location ``mu`` of the heartbeat sensation, compared with
the classical method of constant stimuli (MCS) of Brener and Ring (2016), six
delays from 0 to 500 ms twenty times each? And does Bayesian placement bias
the estimate or starve the tails of data (García-Pérez, 2014)?

Simulated observers answer "synchronous" with the probability given by an
envelope over delay. Detectors have a Gaussian envelope of the model's own
form; asymmetric observers have a right-hand width twice the left-hand one,
so the fitted model is misspecified; non-detectors answer at a flat rate,
from always "no" to always "yes". Every method runs for the same number of
trials and records its posterior after every trial, so accuracy can be read
off at any trial count.

By default the study simulates the task as it runs, not an ideal one:

- ``--min-delay`` (default 130 ms) is the shortest delay the adaptive
  methods may choose, the task's ``TaskConfig.minDelay``. On the 20 ms grid
  the shortest presented is 140 ms.
- ``--period LOW HIGH`` (default 0.8 1.1 s): each simulated participant has a
  resting heart period drawn uniformly from this range, the same for every
  method, and the adaptive methods take their ceiling from
  :meth:`TaskConfig.bounds <cardioception.HSD.config.TaskConfig.bounds>` at
  that period, about 0.71 of it. ``--no-ceiling`` removes it.
- ``--jitter-sd`` (default 26 ms) adds Gaussian noise to the delay the
  observer responds to, while the engine is updated with the nominal one.
  The stamped R-wave the task times from jitters by about that much on the
  test desktop's Bluetooth link, and by about 6 ms on the lab PC. One draw per
  trial, which is pessimistic if the five tones of a train average out.
- ``--train-loss`` (default 0.07) is the probability that a trial yields no
  update, as when no tone of a train can be delivered. The trial still counts
  towards the trial number. The dry run lost 4 of 60 trains.

MCS keeps its published levels of 0 to 500 ms, as the historical comparator,
whatever ``--min-delay`` and the ceiling say; jitter and train loss apply to
it too. Run from the repository root::

    python -m cardioception.HSD.simulate --out results/hsd --reps 10

``--processes`` sets the worker count (default one fewer than the CPUs),
``--trials`` the trials per run (default 120), ``--methods`` a subset of
:data:`METHODS`. The script writes ``trials.csv`` (one row per trial per run),
``summary.csv`` (accuracy per method and trial count), ``evidence.csv``
(detection evidence per observer group), ``stopping.csv`` (the stopping rule
applied to every run), ``delays.csv`` (how often each delay was presented),
``figure.png`` and ``table.md``. Each run is seeded from the study seed, the
observer index, the method name and the rep, so results do not depend on how
the runs are scheduled across processes; the heart period is seeded from the
study seed, the observer and the rep only.

Nothing here imports PsychoPy.
"""

from __future__ import annotations

import argparse
import importlib
import os
import zlib
from dataclasses import asdict, dataclass
from multiprocessing import Pool
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from cardioception._rng import make_rng

from .config import TaskConfig
from .psi import SynchronyPsi, Values

DEFAULT_DELAYS = np.arange(0.0, 601.0, 20.0)
MCS_LEVELS: Tuple[float, ...] = (0.0, 100.0, 200.0, 300.0, 400.0, 500.0)
TABLE_TRIALS: Tuple[int, ...] = (15, 20, 30, 40, 60, 120)
# The task's floor, TaskConfig.minDelay, in ms: the 31 ms (p95) it takes to
# know of a beat, the 50 ms audio lead and the 50 ms latency bias.
DEFAULT_MIN_DELAY = 130.0
# Range of resting heart periods, s, one drawn per simulated participant.
DEFAULT_PERIOD: Tuple[float, float] = (0.8, 1.1)
# SD of the timing error of the stamped R-wave on the test desktop, ms.
DEFAULT_JITTER_SD = 26.0
# Probability that a trial delivers no train and so gives no update.
DEFAULT_TRAIN_LOSS = 0.07
# Stopping widths, ms, at which stopping.csv reports the median trial.
STOP_WIDTHS: Tuple[float, ...] = (150.0, 100.0, 80.0, 60.0, 40.0)

# Each adaptive objective with and without 10 percent exploration trials.
METHODS: Dict[str, Dict[str, Any]] = {
    "mcs": {"kind": "mcs"},
    "psi_mu": {"kind": "adaptive", "targets": ("mu",), "explore": 0.0},
    "psi_mu_x10": {"kind": "adaptive", "targets": ("mu",), "explore": 0.1},
    "psi_mu_sigma": {"kind": "adaptive", "targets": ("mu", "sigma"), "explore": 0.0},
    "psi_mu_sigma_x10": {
        "kind": "adaptive",
        "targets": ("mu", "sigma"),
        "explore": 0.1,
    },
    "psi_joint": {
        "kind": "adaptive",
        "targets": ("mu", "sigma", "floor", "peak"),
        "explore": 0.0,
    },
    "psi_joint_x10": {
        "kind": "adaptive",
        "targets": ("mu", "sigma", "floor", "peak"),
        "explore": 0.1,
    },
}


@dataclass(frozen=True)
class Observer:
    """A simulated participant.

    ``mu`` is the delay (ms after the R-wave) at which "synchronous" is most
    likely, ``sigma`` the envelope width, ``floor`` the rate far from ``mu``
    and ``peak`` the rate at ``mu``. With ``shape="asymmetric"`` the width
    right of ``mu`` is ``2 * sigma``, which the fitted Gaussian cannot
    express. A non-detector has ``floor == peak``; its ``mu`` and ``sigma``
    are then irrelevant and may be NaN.
    """

    mu: float
    sigma: float
    floor: float
    peak: float
    shape: str = "gaussian"

    def __post_init__(self) -> None:
        if self.shape not in ("gaussian", "asymmetric"):
            raise ValueError("shape must be 'gaussian' or 'asymmetric'")
        if not 0.0 <= self.floor <= self.peak <= 1.0:
            raise ValueError("need 0 <= floor <= peak <= 1")
        if self.detector and not (np.isfinite(self.mu) and self.sigma > 0):
            raise ValueError("a detector needs a finite mu and a positive sigma")

    @property
    def detector(self) -> bool:
        return self.floor < self.peak

    @property
    def kind(self) -> str:
        if not self.detector:
            return "non-detector"
        return "asymmetric" if self.shape == "asymmetric" else "detector"

    def p_yes(self, d: Any) -> np.ndarray:
        """Probability of answering "synchronous" at delay(s) ``d``."""
        d = np.asarray(d, dtype=float)
        if not self.detector:
            return np.full(d.shape, self.floor)
        if self.shape == "asymmetric":
            width = np.where(d < self.mu, self.sigma, 2.0 * self.sigma)
        else:
            width = np.full(d.shape, self.sigma)
        bump = np.exp(-0.5 * ((d - self.mu) / width) ** 2)
        return self.floor + (self.peak - self.floor) * bump

    def respond(
        self, d: float, rng: np.random.Generator, jitter_sd: float = 0.0
    ) -> bool:
        """One simulated judgement at delay ``d``: True for "synchronous".

        With ``jitter_sd`` above 0 the observer responds to ``d`` plus
        Gaussian noise of that SD, the error in timing the tones from a
        jittered R-wave stamp. No noise is drawn at 0, so the random stream
        is that of an exact delivery.
        """
        if jitter_sd > 0:
            d = d + rng.normal(0.0, jitter_sd)
        return bool(rng.random() < float(self.p_yes(d)))


def _row(
    psi: SynchronyPsi,
    trial: int,
    delay: float,
    response: Optional[bool],
    explored: bool,
) -> Dict[str, Any]:
    """Per-trial record: the stimulus, the answer and the posterior after it.

    ``response`` is None for a lost train: the trial gave no update.
    """
    mu = psi.estimate("mu")
    sigma = psi.estimate("sigma")
    return {
        "trial": trial,
        "delay": delay,
        "response": float("nan") if response is None else int(response),
        "lost": response is None,
        "n_updates": len(psi.history),
        "explored": bool(explored),
        "mu_mean": mu["mean"],
        "mu_median": mu["median"],
        "mu_ci_low": mu["ci_low"],
        "mu_ci_high": mu["ci_high"],
        "mu_ci_width": mu["ci_high"] - mu["ci_low"],
        "sigma_mean": sigma["mean"],
        "sigma_median": sigma["median"],
        "sigma_ci_low": sigma["ci_low"],
        "sigma_ci_high": sigma["ci_high"],
        "floor_mean": psi.estimate("floor")["mean"],
        "peak_mean": psi.estimate("peak")["mean"],
        "detection_evidence": psi.detection_evidence(),
        "detection_bf": psi.detection_bayes_factor(),
    }


def run_adaptive(
    observer: Observer,
    n_trials: int,
    rng: np.random.Generator,
    targets: Sequence[str] = ("mu",),
    explore: float = 0.0,
    delays: Optional[Values] = None,
    min_delay: Optional[float] = DEFAULT_MIN_DELAY,
    max_delay: Optional[float] = None,
    jitter_sd: float = 0.0,
    train_loss: float = 0.0,
) -> List[Dict[str, Any]]:
    """One adaptive session; one row per trial.

    ``min_delay`` is the shortest delay the system can realize after a
    detected R-wave, 130 ms by default (``TaskConfig.minDelay``), and
    ``max_delay`` the ceiling the heart period sets. ``jitter_sd`` and
    ``train_loss`` are as for :meth:`Observer.respond` and the module
    docstring; both default to an exact delivery here, and :func:`study`
    passes the task's values.
    """
    psi = SynchronyPsi(
        DEFAULT_DELAYS if delays is None else delays,
        targets=targets,
        explore=explore,
        rng=rng,
    )
    rows = []
    for trial in range(1, n_trials + 1):
        delay, explored = psi.next_delay(min_delay=min_delay, max_delay=max_delay)
        response: Optional[bool] = None
        if not (train_loss > 0 and rng.random() < train_loss):
            response = observer.respond(delay, rng, jitter_sd)
            psi.update(delay, response, explored)
        rows.append(_row(psi, trial, delay, response, explored))
    return rows


def classical_measures(
    delays: np.ndarray, responses: np.ndarray
) -> Tuple[float, float]:
    """Median interval and interquartile range of the delays answered "yes".

    These are the MI and IQR of Brener and Ring (2016). NaN if no trial was
    answered "yes".
    """
    yes = np.asarray(delays, dtype=float)[np.asarray(responses, dtype=bool)]
    if yes.size == 0:
        return float("nan"), float("nan")
    q25, q50, q75 = np.percentile(yes, [25, 50, 75])
    return float(q50), float(q75 - q25)


def run_mcs(
    observer: Observer,
    n_per_level: int,
    rng: np.random.Generator,
    levels: Sequence[float] = MCS_LEVELS,
    delays: Optional[Values] = None,
    n_trials: Optional[int] = None,
    jitter_sd: float = 0.0,
    train_loss: float = 0.0,
) -> List[Dict[str, Any]]:
    """Method of constant stimuli, analyzed on the same grid posterior.

    Every level is presented ``n_per_level`` times in a random order. If
    ``n_trials`` is given it replaces ``n_per_level`` and the session has
    exactly that many trials: each level is presented ``n_trials // k``
    times (``k`` levels) and a random ``n_trials % k`` of the levels once
    more, so every level gets the floor or the ceiling of ``n_trials / k``.
    At 120 trials and six levels that is the published 20 per level, and
    the random draws are the same as with ``n_per_level=20``.

    The posterior is updated after each trial exactly as in the adaptive
    runs, but plays no part in choosing the delay. The rows carry two extra
    columns, ``mi`` and ``iqr``, the classical measures over the trials
    delivered; they are NaN on every row but the last, because the classical
    analysis is defined on the whole session only. ``jitter_sd`` and
    ``train_loss`` are as for :func:`run_adaptive`; a lost trial is left out
    of the classical measures too.
    """
    psi = SynchronyPsi(DEFAULT_DELAYS if delays is None else delays, rng=rng)
    level_values = np.asarray(levels, dtype=float)
    if n_trials is None:
        stimuli = np.repeat(level_values, n_per_level)
    else:
        if n_trials < 0:
            raise ValueError("n_trials must be non-negative")
        whole, extra = divmod(int(n_trials), level_values.size)
        stimuli = np.repeat(level_values, whole)
        if extra:
            # Drawn only when needed, so a divisible n_trials consumes the
            # same random numbers as the n_per_level form.
            topped = rng.choice(level_values, size=extra, replace=False)
            stimuli = np.concatenate([stimuli, topped])
    order = rng.permutation(stimuli)
    responses = np.zeros(order.size, dtype=bool)
    kept = np.ones(order.size, dtype=bool)
    rows = []
    for i, delay in enumerate(order):
        response: Optional[bool] = None
        if train_loss > 0 and rng.random() < train_loss:
            kept[i] = False
        else:
            response = observer.respond(float(delay), rng, jitter_sd)
            responses[i] = response
            psi.update(float(delay), response)
        row = _row(psi, i + 1, float(delay), response, False)
        row["mi"], row["iqr"] = float("nan"), float("nan")
        rows.append(row)
    if rows:
        rows[-1]["mi"], rows[-1]["iqr"] = classical_measures(
            order[kept], responses[kept]
        )
    return rows


def default_observers() -> List[Observer]:
    """The observer bank of the simulation study.

    30 Gaussian detectors (mu 150 to 350 ms, sigma 50, 100 or 150 ms, and a
    clean or a noisy floor and peak), two non-detectors answering at a flat
    0.3 and 0.5, two asymmetric observers at mu 200 and 300 ms, and four
    biased non-detectors: always "yes", always "no", and a flat 0.1 and 0.9.
    The biased non-detectors come last, so the indices, and the run seeds,
    of the first 34 are those of the earlier studies.
    """
    nan = float("nan")
    bank = [
        Observer(mu, sigma, floor, peak)
        for mu in (150.0, 200.0, 250.0, 300.0, 350.0)
        for sigma in (50.0, 100.0, 150.0)
        for floor, peak in ((0.05, 0.95), (0.2, 0.8))
    ]
    bank += [Observer(nan, nan, r, r) for r in (0.3, 0.5)]
    bank += [Observer(mu, 100.0, 0.05, 0.95, "asymmetric") for mu in (200.0, 300.0)]
    bank += [Observer(nan, nan, r, r) for r in (1.0, 0.0, 0.1, 0.9)]
    return bank


def _run_seed(seed: int, observer_index: int, method: str, rep: int) -> int:
    """A 32-bit seed for one run, independent of scheduling and of subsetting.

    The method enters by a hash of its name rather than its position, so a
    study run with ``--methods`` reproduces the same runs as the full study.
    """
    key = [seed, observer_index, zlib.crc32(method.encode()), rep]
    return int(np.random.SeedSequence(key).generate_state(1)[0])


def _period(
    seed: int, observer_index: int, rep: int, period: Optional[Tuple[float, float]]
) -> float:
    """The resting heart period of one simulated participant, in s.

    Seeded from the study seed, the observer and the rep, not the method, so
    every method meets the same participants. NaN without a period range.
    """
    if period is None:
        return float("nan")
    key = [seed, observer_index, rep, zlib.crc32(b"period")]
    rng = np.random.default_rng(np.random.SeedSequence(key))
    return float(rng.uniform(*period))


def _run_job(
    job: Tuple[int, Observer, str, int, int, int, Dict[str, Any]],
) -> pd.DataFrame:
    """Worker: one observer, one method, one rep. Module level for spawn.

    The ``min_delay`` and ``max_delay`` columns record the bounds the
    adaptive methods used; they are NaN for MCS, which presents its fixed
    levels regardless. ``period`` is the participant's heart period (NaN
    without a ceiling).
    """
    index, observer, method, rep, seed, n_trials, options = job
    min_delay = options.get("min_delay")
    jitter_sd = float(options.get("jitter_sd", 0.0))
    train_loss = float(options.get("train_loss", 0.0))
    run_seed = _run_seed(seed, index, method, rep)
    rng, _ = make_rng(run_seed)
    period = _period(seed, index, rep, options.get("period"))
    spec = METHODS[method]
    if spec["kind"] == "mcs":
        rows = run_mcs(
            observer,
            0,
            rng,
            n_trials=n_trials,
            jitter_sd=jitter_sd,
            train_loss=train_loss,
        )
        floor_used = ceiling_used = float("nan")
    else:
        ceiling: Optional[float] = None
        if np.isfinite(period):
            ceiling = TaskConfig().bounds(period)[1]
        rows = run_adaptive(
            observer,
            n_trials,
            rng,
            targets=spec["targets"],
            explore=spec["explore"],
            min_delay=min_delay,
            max_delay=ceiling,
            jitter_sd=jitter_sd,
            train_loss=train_loss,
        )
        floor_used = float("nan") if min_delay is None else float(min_delay)
        ceiling_used = float("nan") if ceiling is None else float(ceiling)
    df = pd.DataFrame(rows)
    params = asdict(observer)
    df.insert(0, "observer", index)
    df.insert(1, "kind", observer.kind)
    df.insert(2, "shape", params["shape"])
    for i, name in enumerate(("mu", "sigma", "floor", "peak")):
        df.insert(3 + i, f"true_{name}", params[name])
    df.insert(7, "method", method)
    df.insert(8, "rep", rep)
    df.insert(9, "run_seed", run_seed)
    df.insert(10, "min_delay", floor_used)
    df.insert(11, "max_delay", ceiling_used)
    df.insert(12, "period", period)
    df.insert(13, "jitter_sd", jitter_sd)
    df.insert(14, "train_loss", train_loss)
    return df


def study(
    observers: Optional[Sequence[Observer]] = None,
    methods: Optional[Sequence[str]] = None,
    reps: int = 10,
    seed: int = 2026,
    processes: int = 1,
    n_trials: int = 120,
    min_delay: Optional[float] = DEFAULT_MIN_DELAY,
    period: Optional[Tuple[float, float]] = DEFAULT_PERIOD,
    jitter_sd: float = DEFAULT_JITTER_SD,
    train_loss: float = DEFAULT_TRAIN_LOSS,
) -> pd.DataFrame:
    """Every observer under every method, ``reps`` times; one row per trial.

    MCS presents exactly ``n_trials`` trials at its published levels, the
    floor or the ceiling of ``n_trials / 6`` per level (20 each at the
    default of 120). ``min_delay`` and the ceiling that ``period`` sets
    apply to the adaptive methods only; ``jitter_sd`` and ``train_loss`` to
    every method. The defaults are the task as it runs (see the module
    docstring); ``period=None``, ``jitter_sd=0`` and ``train_loss=0`` give
    an exact delivery with no ceiling. The run seed does not depend on these
    options, so studies under different options share their seeds.
    ``processes`` of 1 runs serially in this process.
    """
    if not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError(f"seed must be a non-negative integer, not {seed!r}")
    observers = default_observers() if observers is None else list(observers)
    methods = list(METHODS) if methods is None else list(methods)
    unknown = [m for m in methods if m not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods {unknown}; choose from {list(METHODS)}")
    if period is not None and not 0 < period[0] <= period[1]:
        raise ValueError(f"period must be (low, high) seconds, not {period!r}")
    if jitter_sd < 0 or not 0 <= train_loss < 1:
        raise ValueError("need jitter_sd >= 0 and 0 <= train_loss < 1")
    options = {
        "min_delay": min_delay,
        "period": None if period is None else tuple(period),
        "jitter_sd": jitter_sd,
        "train_loss": train_loss,
    }
    jobs = [
        (i, obs, method, rep, seed, n_trials, options)
        for i, obs in enumerate(observers)
        for method in methods
        for rep in range(reps)
    ]
    if processes <= 1:
        frames = [_run_job(job) for job in jobs]
    else:
        # Refer to the worker through the importable module rather than
        # __main__, so spawned processes on Windows can unpickle it.
        worker = importlib.import_module("cardioception.HSD.simulate")._run_job
        # One BLAS thread per worker, or the processes compete for cores.
        # Spawned children read these when they import NumPy.
        saved = {}
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            saved[var] = os.environ.get(var)
            os.environ[var] = "1"
        try:
            with Pool(processes) as pool:
                frames = list(pool.imap_unordered(worker, jobs, chunksize=1))
        finally:
            for var, value in saved.items():
                if value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = value
    df = pd.concat(frames, ignore_index=True)
    df["method"] = pd.Categorical(df["method"], categories=methods)
    df = df.sort_values(["observer", "method", "rep", "trial"], ignore_index=True)
    df["method"] = df["method"].astype(str)
    return df


def _rmse(errors: pd.Series) -> float:
    return float(np.sqrt(np.mean(np.square(errors))))


def summarize(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Accuracy per method and trial count, and the delays each method used.

    Returns ``(summary, delays)``. ``summary`` has one row per method and
    trial with, over the Gaussian detectors: RMSE, median absolute error and
    mean signed error (bias) of the posterior mean of mu, the mean width of
    the 95 percent interval on mu, its coverage of the true mu, and the RMSE
    of the posterior mean of sigma. The same mu metrics, prefixed ``asym_``,
    cover the misspecified observers, against their mode. Then, for the
    detectors (Gaussian and asymmetric) and for the non-detectors, the mean
    detection evidence (posterior mass) and the median log10 detection
    Bayes factor, which removes the prior and is the one to interpret; and,
    where the method records it (MCS, final trial), the RMSE of the classical median
    interval against the true mu. ``delays`` counts how often each delay was
    presented, per method and observer kind.
    """
    df = df.copy()
    df["mu_err"] = df["mu_mean"] - df["true_mu"]
    df["sigma_err"] = df["sigma_mean"] - df["true_sigma"]
    df["covered"] = (df["mu_ci_low"] <= df["true_mu"]) & (
        df["true_mu"] <= df["mu_ci_high"]
    )
    keys = ["method", "trial"]

    def mu_metrics(sub: pd.DataFrame, prefix: str) -> pd.DataFrame:
        g = sub.groupby(keys)
        return pd.DataFrame(
            {
                f"{prefix}n_runs": g.size(),
                f"{prefix}mu_rmse": g["mu_err"].apply(_rmse),
                f"{prefix}mu_mae": g["mu_err"].apply(lambda e: np.median(np.abs(e))),
                f"{prefix}mu_bias": g["mu_err"].mean(),
                f"{prefix}mu_ci_width": g["mu_ci_width"].mean(),
                f"{prefix}mu_coverage": g["covered"].mean(),
            }
        )

    det = df[df["kind"] == "detector"]
    parts = [
        mu_metrics(det, ""),
        det.groupby(keys)["sigma_err"].apply(_rmse).rename("sigma_rmse").to_frame(),
    ]
    asym = df[df["kind"] == "asymmetric"]
    if not asym.empty:
        parts.append(mu_metrics(asym, "asym_"))
    with np.errstate(divide="ignore"):
        df["log10_bf"] = np.log10(df["detection_bf"])
    for prefix, sub in (
        ("detector", df[df["kind"] != "non-detector"]),
        ("nondetector", df[df["kind"] == "non-detector"]),
    ):
        if sub.empty:
            continue
        g = sub.groupby(keys)
        parts.append(
            pd.DataFrame(
                {
                    f"{prefix}_evidence": g["detection_evidence"].mean(),
                    f"{prefix}_log10_bf": g["log10_bf"].median(),
                }
            )
        )
    if "mi" in df.columns:
        mi = det.dropna(subset=["mi"])
        if not mi.empty:
            parts.append(
                (mi["mi"] - mi["true_mu"])
                .groupby([mi["method"], mi["trial"]])
                .apply(_rmse)
                .rename("mi_rmse")
                .to_frame()
            )
    summary = pd.concat(parts, axis=1).reset_index()
    order = {m: i for i, m in enumerate(dict.fromkeys(df["method"]))}
    summary = summary.sort_values(
        ["method", "trial"], key=lambda s: s.map(order) if s.name == "method" else s
    ).reset_index(drop=True)

    counts = (
        df.groupby(["method", "kind", "delay"]).size().rename("count").reset_index()
    )
    totals = counts.groupby(["method", "kind"])["count"].transform("sum")
    counts["proportion"] = counts["count"] / totals
    return summary, counts


def _group(df: pd.DataFrame) -> pd.Series:
    """Observer group per row: clean or noisy detector, asymmetric, or the
    non-detector's response rate ("always no", "flat 0.3", "always yes")."""

    def label(kind: str, floor: float) -> str:
        if kind == "detector":
            return "clean detector" if floor < 0.1 else "noisy detector"
        if kind == "asymmetric":
            return "asymmetric"
        if floor <= 0.0:
            return "always no"
        if floor >= 1.0:
            return "always yes"
        return f"flat {floor:g}"

    return pd.Series(
        [label(k, f) for k, f in zip(df["kind"], df["true_floor"])],
        index=df.index,
        name="group",
    )


def evidence(df: pd.DataFrame, trials: Sequence[int] = TABLE_TRIALS) -> pd.DataFrame:
    """Detection evidence per method, trial count and observer group.

    For each group: the number of runs, the median log10 detection Bayes
    factor, the share of runs above 0 (the data favour a rise) and above 1
    (a factor of 10), and the mean posterior detection evidence.
    """
    sub = df[df["trial"].isin(list(trials))].copy()
    sub["group"] = _group(sub)
    with np.errstate(divide="ignore"):
        sub["log10_bf"] = np.log10(sub["detection_bf"])
    g = sub.groupby(["method", "group", "trial"], sort=False)
    out = pd.DataFrame(
        {
            "n_runs": g.size(),
            "median_log10_bf": g["log10_bf"].median(),
            "share_log10_bf_above_0": g["log10_bf"].apply(lambda v: np.mean(v > 0)),
            "share_log10_bf_above_1": g["log10_bf"].apply(lambda v: np.mean(v > 1)),
            "mean_evidence": g["detection_evidence"].mean(),
        }
    )
    return out.reset_index()


def stopping(
    df: pd.DataFrame,
    min_trials: Optional[int] = None,
    max_trials: Optional[int] = None,
    ci_width: Optional[float] = None,
    widths: Sequence[float] = STOP_WIDTHS,
) -> pd.DataFrame:
    """The stopping rule applied to every run, per method and observer group.

    The rule is the task's: stop at the first trial with at least
    ``min_trials`` updates (lost trains do not count) and a 95 percent
    interval on ``mu`` no wider than ``ci_width``, or at ``max_trials``.
    ``None`` takes :class:`~cardioception.HSD.config.TaskConfig`'s default.
    Columns: runs; median trial and share of runs stopped before the
    maximum; RMSE of the posterior mean of ``mu`` at the stop, at
    ``min_trials`` and at ``max_trials`` (NaN for non-detectors); the median
    interval width at ``min_trials`` and ``max_trials``; and, for each of
    ``widths``, the first trial at which the median width over the group's
    runs is at most that width (NaN if never, within the runs).
    """
    config = TaskConfig()
    min_trials = config.minTrials if min_trials is None else min_trials
    max_trials = config.maxTrials if max_trials is None else max_trials
    ci_width = config.ciWidth if ci_width is None else ci_width
    df = df.copy()
    df["group"] = _group(df)
    detector_groups = df.loc[df["kind"] != "non-detector", "group"].unique()
    df["err"] = df["mu_mean"] - df["true_mu"]
    run = ["method", "group", "observer", "rep"]
    rows = []
    for (method, group), sub in df.groupby(["method", "group"], sort=False):
        meets = (
            (sub["n_updates"] >= min_trials)
            & (sub["mu_ci_width"] <= ci_width)
            & (sub["trial"] <= max_trials)
        )
        at_max = sub[sub["trial"] == max_trials].set_index(run[2:])
        first = sub[meets].groupby(run[2:])["trial"].min()
        stop = first.reindex(at_max.index).fillna(max_trials).astype(int)
        stopped = sub.set_index(run[2:] + ["trial"]).loc[
            [(o, r, t) for (o, r), t in stop.items()]
        ]
        at_min = sub[sub["trial"] == min_trials]
        median_width = sub.groupby("trial")["mu_ci_width"].median()
        is_detector = group in detector_groups
        row: Dict[str, Any] = {
            "method": method,
            "group": group,
            "n_runs": len(stop),
            "median_stop_trial": float(stop.median()),
            "share_stopped_early": float(np.mean(stop < max_trials)),
            "rmse_at_stop": _rmse(stopped["err"]) if is_detector else float("nan"),
            f"rmse_at_{min_trials}": (
                _rmse(at_min["err"]) if is_detector else float("nan")
            ),
            f"rmse_at_{max_trials}": (
                _rmse(at_max["err"]) if is_detector else float("nan")
            ),
            f"median_width_at_{min_trials}": float(at_min["mu_ci_width"].median()),
            f"median_width_at_{max_trials}": float(at_max["mu_ci_width"].median()),
        }
        for width in widths:
            reached = median_width.index[median_width <= width]
            row[f"trial_median_width_{width:g}"] = (
                float(reached.min()) if reached.size else float("nan")
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _markdown(df: pd.DataFrame, formats: Dict[str, str]) -> str:
    """A Markdown table of the ``formats`` columns of ``df``; NaN is blank."""
    columns = [c for c in formats if c in df.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for _, row in df.iterrows():
        cells = []
        for key in columns:
            value = row[key]
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                cells.append("")
            else:
                cells.append(formats[key].format(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def plot(summary: pd.DataFrame, path: str) -> None:
    """RMSE of mu and mean 95 percent interval width against trial number.

    One line per method, over the Gaussian detectors. Colour marks the
    placement objective; dashed lines are the variants with exploration.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colours = {
        "mcs": "#555555",
        "psi_mu": "#0072B2",
        "psi_mu_sigma": "#E69F00",
        "psi_joint": "#009E73",
    }
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True)
    for method, sub in summary.groupby("method", sort=False):
        name = str(method)
        explored = name.endswith("_x10")
        base = name[: -len("_x10")] if explored else name
        style = "--" if explored else "-"
        colour = colours.get(base)
        axes[0].plot(sub["trial"], sub["mu_rmse"], style, color=colour, label=name)
        axes[1].plot(sub["trial"], sub["mu_ci_width"], style, color=colour)
    axes[0].set_ylabel("RMSE of posterior mean mu (ms)")
    axes[1].set_ylabel("Mean width of 95% interval on mu (ms)")
    for ax in axes:
        ax.set_xlabel("Trial")
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def table(summary: pd.DataFrame, trials: Sequence[int] = TABLE_TRIALS) -> str:
    """Markdown table of the main metrics at a few trial counts."""
    columns = [
        ("method", "Method", "{}"),
        ("trial", "Trials", "{:d}"),
        ("mu_rmse", "mu RMSE (ms)", "{:.1f}"),
        ("mu_mae", "mu median abs. error (ms)", "{:.1f}"),
        ("mu_bias", "mu bias (ms)", "{:+.1f}"),
        ("mu_ci_width", "95% CI width (ms)", "{:.1f}"),
        ("mu_coverage", "Coverage", "{:.2f}"),
        ("sigma_rmse", "sigma RMSE (ms)", "{:.1f}"),
        ("asym_mu_rmse", "Asymmetric mu RMSE (ms)", "{:.1f}"),
        ("detector_log10_bf", "Median log10 BF, detectors", "{:+.1f}"),
        ("nondetector_evidence", "Detection evidence, non-detectors", "{:.2f}"),
        ("nondetector_log10_bf", "Median log10 BF, non-detectors", "{:+.2f}"),
    ]
    columns = [c for c in columns if c[0] in summary.columns]
    sub = summary[summary["trial"].isin(list(trials))]
    lines = [
        "| " + " | ".join(c[1] for c in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for _, row in sub.iterrows():
        cells = []
        for key, _, fmt in columns:
            value = row[key]
            if key == "trial":
                cells.append(fmt.format(int(value)))
            elif isinstance(value, float) and not np.isfinite(value):
                cells.append("")
            else:
                cells.append(fmt.format(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _non_negative_int(text: str) -> int:
    """argparse type: SeedSequence refuses negative seeds."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not an integer")
    if value < 0:
        raise argparse.ArgumentTypeError(f"seed must be non-negative, not {value}")
    return value


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Command line entry point; see the module docstring."""
    parser = argparse.ArgumentParser(
        description="Adaptive heartbeat synchrony discrimination against constant stimuli."
    )
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--reps", type=int, default=10)
    parser.add_argument(
        "--processes", type=int, default=max(1, (os.cpu_count() or 2) - 1)
    )
    parser.add_argument("--seed", type=_non_negative_int, default=2026)
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help="shortest delay (ms) the adaptive methods may choose",
    )
    parser.add_argument(
        "--period",
        type=float,
        nargs=2,
        default=list(DEFAULT_PERIOD),
        metavar=("LOW", "HIGH"),
        help="range of resting heart periods (s) that set the delay ceiling",
    )
    parser.add_argument(
        "--no-ceiling", action="store_true", help="no period-based delay ceiling"
    )
    parser.add_argument(
        "--jitter-sd",
        type=float,
        default=DEFAULT_JITTER_SD,
        help="SD (ms) of the timing error of each trial's delay",
    )
    parser.add_argument(
        "--train-loss",
        type=float,
        default=DEFAULT_TRAIN_LOSS,
        help="probability that a trial delivers no train and gives no update",
    )
    parser.add_argument("--methods", nargs="+", choices=list(METHODS), default=None)
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    df = study(
        methods=args.methods,
        reps=args.reps,
        seed=args.seed,
        processes=args.processes,
        n_trials=args.trials,
        min_delay=args.min_delay,
        period=None if args.no_ceiling else (args.period[0], args.period[1]),
        jitter_sd=args.jitter_sd,
        train_loss=args.train_loss,
    )
    summary, delays = summarize(df)
    ev = evidence(df)
    stops = stopping(df)
    df.to_csv(os.path.join(args.out, "trials.csv"), index=False)
    summary.to_csv(os.path.join(args.out, "summary.csv"), index=False)
    ev.to_csv(os.path.join(args.out, "evidence.csv"), index=False)
    stops.to_csv(os.path.join(args.out, "stopping.csv"), index=False)
    delays.to_csv(os.path.join(args.out, "delays.csv"), index=False)
    plot(summary, os.path.join(args.out, "figure.png"))
    with open(os.path.join(args.out, "table.md"), "w", encoding="utf-8") as f:
        f.write(table(summary))
        f.write("\n")
        f.write(
            _markdown(
                ev,
                {
                    "method": "{}",
                    "group": "{}",
                    "trial": "{:d}",
                    "n_runs": "{:d}",
                    "median_log10_bf": "{:+.2f}",
                    "share_log10_bf_above_0": "{:.2f}",
                    "share_log10_bf_above_1": "{:.2f}",
                    "mean_evidence": "{:.2f}",
                },
            )
        )
        f.write("\n")
        formats = {c: "{:.1f}" for c in stops.columns}
        formats.update({"method": "{}", "group": "{}", "n_runs": "{:d}"})
        formats["share_stopped_early"] = "{:.2f}"
        f.write(_markdown(stops, formats))
    n_runs = df.groupby(["observer", "method", "rep"]).ngroups
    print(f"{n_runs} runs written to {args.out}")


if __name__ == "__main__":
    main()
