# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Bayesian adaptive estimation of the heartbeat sensation envelope.

The heartbeat detection task of Brener, Liu and Ring (1993) presents a train
of tones, each a fixed delay ``d`` after a detected R-wave, and asks whether
the tones were simultaneous with the heartbeat sensation. Across delays the
probability of a "simultaneous" answer rises towards the delay at which the
sensation is felt and falls again after it. The classical method of constant
stimuli samples six delays twenty times each. The Heartbeat Synchrony
Discrimination task (HSD) is an adaptive version of it: this module chooses
each delay by expected information gain instead, in the manner of the Psi method of
Kontsevich and Tyler (1999), with the nuisance handling of Prins (2013).

The psychometric function is not monotonic, so PsychoPy's ``PsiHandler``
(which assumes a cumulative Gaussian) cannot be used. The envelope is modelled
as a Gaussian bump on a floor::

    P(yes | d) = floor + (peak - floor) * exp(-0.5 * ((d - mu) / sigma) ** 2)

``mu`` is the temporal location of the sensation relative to the R-wave,
``sigma`` its width, ``floor`` the rate of "yes" far from the sensation (lapses
towards "yes"), and ``peak`` the rate of "yes" at the sensation (one minus the
lapse towards "no"). The floor and the peak share one grid, so ``peak ==
floor`` is on it: a flat responder, who answers "yes" at the same rate at
every delay, is expressible at any rate from 0.03 to 0.97 and does not have
to be explained as a rise.

The stimulus axis need not be absolute delay: cardiac phase (the delay as a
fraction of the anticipated interbeat interval) is the same engine with a
different candidate set and explicit ``mu`` and ``sigma`` grids on that scale,
but the simulations in :mod:`cardioception.HSD.simulate` use absolute delay.

Everything here is plain NumPy. Nothing imports PsychoPy or touches a device,
so the procedure can be simulated and tested headless.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

PARAMETERS: Tuple[str, ...] = ("mu", "sigma", "floor", "peak")

Envelope = Callable[..., np.ndarray]
Values = Union[Sequence[float], np.ndarray]

#: The response rates shared by the ``floor`` and ``peak`` grids: finer near 0
#: and 1, where lapse rates sit, and spanning any flat responder.
RATES = np.array([0.03, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.97])


def gaussian_envelope(
    d: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    floor: np.ndarray,
    peak: np.ndarray,
) -> np.ndarray:
    """Probability of a "simultaneous" judgement at delay ``d``.

    All arguments broadcast against each other.
    """
    return floor + (peak - floor) * np.exp(-0.5 * ((d - mu) / sigma) ** 2)


def default_grids(
    max_delay: float = 600.0, mu_step: float = 10.0, n_sigma: int = 20
) -> Dict[str, np.ndarray]:
    """Parameter grids wide enough for the published range of observers.

    Preferred intervals of 100 to 400 ms and envelope widths (standard
    deviations) of 43 to 167 ms are reported by Brener and Kluvitse (1988);
    median intervals on the method of constant stimuli ran from 152 to 373 ms
    (Brener and Ring, 2016). The grids cover those with room to spare, because
    the point of estimating the location is not to assume it.

    ``floor`` and ``peak`` share :data:`RATES`, so every flat response rate
    from 0.03 to 0.97 is a grid point (``peak == floor``), whatever the bias
    of the responder. The pairs with ``peak < floor`` get no prior mass.
    """
    return {
        "mu": np.arange(0.0, max_delay + mu_step / 2, mu_step),
        "sigma": np.geomspace(20.0, 300.0, n_sigma),
        "floor": RATES.copy(),
        "peak": RATES.copy(),
    }


def _entropy(p: np.ndarray, axis: Optional[int] = None) -> np.ndarray:
    """Shannon entropy in nats, treating 0 log 0 as 0."""
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(p > 0, p * np.log(p), 0.0)
    return -np.sum(term, axis=axis)


class SynchronyPsi:
    """Posterior over the envelope parameters, and the next delay to test.

    Parameters
    ----------
    delays
        Candidate R-wave-to-tone delays in ms. The procedure chooses among
        these; the posterior can be updated with any realized delay.
    mu, sigma, floor, peak
        Grid values for each parameter. The posterior is discrete on their
        outer product. ``None`` takes :func:`default_grids`.
    prior
        Optional array of prior weights over ``mu`` only (same length as the
        ``mu`` grid). The prior over the other parameters is uniform; over
        ``sigma`` it is uniform on the supplied grid, so pass a log-spaced grid
        for a log-uniform prior. ``None`` is uniform over ``mu``.
    targets
        The parameters whose marginal posterior entropy the next delay should
        minimize (Prins, 2013). The others are nuisance parameters that stay in
        the posterior but do not steer stimulus placement. ``("mu",)`` targets
        the temporal location alone; ``("mu", "sigma")`` adds the width;
        ``PARAMETERS`` reproduces the joint objective of Kontsevich and Tyler.
    explore
        Probability that a trial ignores the objective and draws a delay
        uniformly from ``delays``. Keeps the outer delays sampled, which
        García-Pérez (2014) notes a pure Bayesian placement does not do.
    envelope
        Function computing ``P(yes | d, mu, sigma, floor, peak)``. Defaults to
        :func:`gaussian_envelope`.
    rng
        Generator used for tie breaking and exploration trials.
    rise_range
        ``(low, high)``, the delays over which :meth:`detection_evidence`
        and :meth:`detection_bayes_factor` measure the rise of the envelope.
        ``None`` measures it over the delays presented so far; see
        :meth:`rise_range`.
    """

    def __init__(
        self,
        delays: Values,
        mu: Optional[Values] = None,
        sigma: Optional[Values] = None,
        floor: Optional[Values] = None,
        peak: Optional[Values] = None,
        prior: Optional[Values] = None,
        targets: Sequence[str] = ("mu",),
        explore: float = 0.0,
        envelope: Envelope = gaussian_envelope,
        rng: Optional[np.random.Generator] = None,
        rise_range: Optional[Tuple[float, float]] = None,
    ) -> None:
        self.delays = np.asarray(delays, dtype=float)
        if self.delays.ndim != 1 or self.delays.size == 0:
            raise ValueError("delays must be a non-empty 1-D sequence")
        defaults = default_grids(max_delay=float(self.delays.max()))
        supplied = {"mu": mu, "sigma": sigma, "floor": floor, "peak": peak}
        self.grids: Dict[str, np.ndarray] = {
            name: np.asarray(defaults[name] if value is None else value, dtype=float)
            for name, value in supplied.items()
        }
        for name in PARAMETERS:
            grid = self.grids[name]
            if grid.ndim != 1 or grid.size == 0:
                raise ValueError(f"{name} grid must be a non-empty 1-D sequence")
            if not np.all(np.isfinite(grid)):
                raise ValueError(f"{name} grid must be finite")
            # The credible intervals read quantiles off the cumulative
            # marginal, which is only meaningful on an increasing grid.
            if np.any(np.diff(grid) <= 0):
                raise ValueError(f"{name} grid must be strictly increasing")
        if np.any(self.grids["sigma"] <= 0):
            raise ValueError("sigma grid must be positive")
        for name in ("floor", "peak"):
            if np.any(self.grids[name] < 0) or np.any(self.grids[name] > 1):
                raise ValueError(f"{name} grid must lie in [0, 1]")
        bad = [t for t in targets if t not in PARAMETERS]
        if bad or not targets:
            raise ValueError(f"targets must be a non-empty subset of {PARAMETERS}")
        if not 0.0 <= explore <= 1.0:
            raise ValueError("explore must be a probability")
        self.targets = tuple(targets)
        self.explore = float(explore)
        self.envelope = envelope
        self.rng = rng if rng is not None else np.random.default_rng()
        self.shape = tuple(self.grids[name].size for name in PARAMETERS)

        # Parameter values at every grid point, flattened in C order so that
        # reshape(self.shape) recovers the (mu, sigma, floor, peak) axes.
        mesh = np.meshgrid(*(self.grids[name] for name in PARAMETERS), indexing="ij")
        self.theta: Dict[str, np.ndarray] = {
            name: m.reshape(-1) for name, m in zip(PARAMETERS, mesh)
        }
        # A peak below the floor would be an inverted envelope. Give those
        # grid points zero prior mass rather than refusing the grid, so the
        # floor and the peak can share one grid. A peak equal to the floor is
        # a flat responder.
        valid = self.theta["peak"] >= self.theta["floor"]

        # P(yes | delay, theta) for every candidate delay: (n_delays, n_theta).
        self.likelihood = self._p_yes(self.delays[:, None])
        if np.any(self.likelihood < 0) or np.any(self.likelihood > 1):
            raise ValueError("envelope returned a value outside [0, 1]")

        prior_mu: np.ndarray
        if prior is None:
            prior_mu = np.ones(self.grids["mu"].size)
        else:
            prior_mu = np.asarray(prior, dtype=float)
            if prior_mu.shape != self.grids["mu"].shape or np.any(prior_mu < 0):
                raise ValueError("prior must be non-negative, one weight per mu value")
        full: np.ndarray = np.broadcast_to(
            prior_mu[:, None, None, None], self.shape
        ).reshape(-1)
        full = full * valid
        if full.sum() <= 0:
            raise ValueError("prior has no mass on any valid grid point")
        self.prior = full / full.sum()
        self.posterior = self.prior.copy()
        self.history: List[Tuple[float, int, bool]] = []
        span: Optional[Tuple[float, float]] = None
        if rise_range is not None:
            low, high = (float(v) for v in rise_range)
            if not (np.isfinite(low) and np.isfinite(high) and low < high):
                raise ValueError("rise_range must be finite, with low < high")
            span = (low, high)
        self._rise_range = span
        self._rise_cache: Optional[Tuple[Tuple[float, float], np.ndarray]] = None

    # ------------------------------------------------------------------ model

    def _p_yes(self, d: Union[float, np.ndarray]) -> np.ndarray:
        """Envelope evaluated at delay(s) ``d`` for every grid point."""
        return self.envelope(
            np.asarray(d, dtype=float),
            self.theta["mu"],
            self.theta["sigma"],
            self.theta["floor"],
            self.theta["peak"],
        )

    def _nuisance_axes(self) -> Tuple[int, ...]:
        """Axes of the reshaped posterior that are nuisance parameters."""
        return tuple(i for i, name in enumerate(PARAMETERS) if name not in self.targets)

    # ------------------------------------------------------------- selection

    def expected_entropy(self, allowed: Optional[np.ndarray] = None) -> np.ndarray:
        """Expected posterior entropy of the target marginal after one trial.

        Returns one value per candidate delay; ``inf`` for delays excluded by
        ``allowed`` (a boolean mask over ``self.delays``).
        """
        n_d = self.delays.size
        like = self.likelihood  # (n_d, n_theta)
        p_yes = like @ self.posterior  # (n_d,)
        p_yes = np.clip(p_yes, 1e-12, 1 - 1e-12)

        post_yes = like * self.posterior[None, :] / p_yes[:, None]
        post_no = (1.0 - like) * self.posterior[None, :] / (1.0 - p_yes)[:, None]

        nuisance = tuple(1 + ax for ax in self._nuisance_axes())
        if nuisance:
            post_yes = post_yes.reshape((n_d,) + self.shape).sum(axis=nuisance)
            post_no = post_no.reshape((n_d,) + self.shape).sum(axis=nuisance)
        post_yes = post_yes.reshape(n_d, -1)
        post_no = post_no.reshape(n_d, -1)

        h = p_yes * _entropy(post_yes, axis=1) + (1 - p_yes) * _entropy(post_no, axis=1)
        if allowed is not None:
            h = np.where(np.asarray(allowed, dtype=bool), h, np.inf)
        return h

    def next_delay(
        self, min_delay: Optional[float] = None, max_delay: Optional[float] = None
    ) -> Tuple[float, bool]:
        """The delay to present on the next trial, and whether it was explored.

        ``min_delay`` and ``max_delay`` restrict the candidates for this trial
        only: the floor is the latency at which the system can react to a
        detected R-wave, and the ceiling keeps the tone clear of the next beat
        (the envelope is periodic in the interbeat interval, which the model
        ignores).
        """
        allowed = np.ones(self.delays.size, dtype=bool)
        if min_delay is not None:
            allowed &= self.delays >= min_delay
        if max_delay is not None:
            allowed &= self.delays <= max_delay
        if not allowed.any():
            raise ValueError("no candidate delay lies inside the allowed range")
        if self.explore > 0 and self.rng.random() < self.explore:
            return float(self.rng.choice(self.delays[allowed])), True
        h = self.expected_entropy(allowed)
        best = np.flatnonzero(np.isclose(h, h.min()))
        return float(self.delays[self.rng.choice(best)]), False

    # ---------------------------------------------------------------- update

    def update(self, delay: float, response: bool, explored: bool = False) -> None:
        """Condition the posterior on one judgement.

        ``delay`` is the delay the trial is credited with, in engine units,
        which need not be one of the candidates: the likelihood is recomputed
        from the envelope at that value. The task passes the realized delay
        its scheduler reports, which differs from the request only when a
        tone started late. It is not a measurement of what the participant
        heard (see :mod:`cardioception.HSD._outcome`).
        """
        delay = float(delay)
        if not np.isfinite(delay):
            raise ValueError("delay must be finite")
        like = self._p_yes(delay)
        # Compute into a new array and only then replace the posterior, so a
        # collapse leaves the session as it was rather than full of NaN.
        new = self.posterior * (like if response else (1.0 - like))
        total = new.sum()
        if not np.isfinite(total) or total <= 0:
            raise FloatingPointError(
                "posterior collapsed; the grid cannot explain the data"
            )
        self.posterior = new / total
        self.history.append((float(delay), int(bool(response)), bool(explored)))

    # ------------------------------------------------------------- estimates

    def marginal(self, name: str) -> np.ndarray:
        """Marginal posterior over one parameter, on its grid."""
        if name not in PARAMETERS:
            raise ValueError(f"unknown parameter {name!r}")
        axes = tuple(i for i, other in enumerate(PARAMETERS) if other != name)
        return self.posterior.reshape(self.shape).sum(axis=axes)

    def estimate(self, name: str, ci: float = 0.95) -> Dict[str, float]:
        """Posterior mean, median, mode, SD and central credible interval.

        Quantiles are the smallest grid value whose cumulative mass reaches
        the level, so the interval is quantized to the grid spacing.
        """
        if not 0.0 < ci < 1.0:
            raise ValueError("ci must lie strictly between 0 and 1")
        p = self.marginal(name)
        grid = self.grids[name]
        mean = float(np.sum(grid * p))
        sd = float(np.sqrt(np.sum((grid - mean) ** 2 * p)))
        cdf = np.cumsum(p)
        lo, hi = (1 - ci) / 2, 1 - (1 - ci) / 2
        last = grid.size - 1

        def quantile(q: float) -> float:
            # The last index guards a cumulative sum that rounds to just
            # below the level at the top of the grid.
            return float(grid[min(int(np.searchsorted(cdf, q)), last)])

        return {
            "mean": mean,
            "median": quantile(0.5),
            "mode": float(grid[int(np.argmax(p))]),
            "sd": sd,
            "ci_low": quantile(lo),
            "ci_high": quantile(hi),
        }

    def summary(self) -> Dict[str, Dict[str, float]]:
        return {name: self.estimate(name) for name in PARAMETERS}

    def ci_width(self, name: str = "mu", ci: float = 0.95) -> float:
        est = self.estimate(name, ci)
        return est["ci_high"] - est["ci_low"]

    def converged(self, width: float, name: str = "mu", ci: float = 0.95) -> bool:
        """True once the credible interval for ``name`` is at most ``width``."""
        return self.ci_width(name, ci) <= width

    def rise_range(self) -> Tuple[float, float]:
        """The delay range over which the envelope's rise is measured.

        ``rise_range`` if one was given to the constructor. Otherwise the
        range of the delays the posterior has been updated with, which is
        what the task could present to this participant: the latency floor,
        the ceiling set by their heart period, and any late tone. Before two
        different delays have been presented it is the candidate range.
        """
        if self._rise_range is not None:
            return self._rise_range
        presented = [h[0] for h in self.history]
        if presented and min(presented) < max(presented):
            return float(min(presented)), float(max(presented))
        return float(self.delays.min()), float(self.delays.max())

    def visible_rise(self) -> np.ndarray:
        """Rise of the envelope inside :meth:`rise_range`, per grid point.

        The largest minus the smallest ``P(yes | d)`` over the range,
        evaluated at both ends and at every ``mu`` grid value and candidate
        delay inside. For the Gaussian envelope that is exact: the maximum
        is at ``mu`` or at an end, the minimum at an end. So a bump whose
        ``mu`` lies outside what the task can present, and whose flank does
        not reach into it, rises by about 0 here however high its peak sits
        above its floor, and a very wide ``sigma`` rises only by the part of
        the bump the range covers. Cached until the range changes.
        """
        lo, hi = self.rise_range()
        if self._rise_cache is not None and self._rise_cache[0] == (lo, hi):
            return self._rise_cache[1]
        inside = np.concatenate([self.grids["mu"], self.delays])
        inside = inside[(inside > lo) & (inside < hi)]
        points = np.unique(np.concatenate([[lo, hi], inside]))
        top = np.full(self.posterior.size, -np.inf)
        bottom = np.full(self.posterior.size, np.inf)
        for d in points:
            p = self._p_yes(d)
            np.maximum(top, p, out=top)
            np.minimum(bottom, p, out=bottom)
        rise = top - bottom
        self._rise_cache = ((lo, hi), rise)
        return rise

    def _rises(self, rise: float) -> np.ndarray:
        """Grid points whose envelope rises by more than ``rise`` in range."""
        # The tolerance makes the boundary explicit: a rise of exactly 0.2
        # can compute as 0.2 or as 0.19999999999999996 depending on the
        # pair, and both should count as "not above".
        return self.visible_rise() > rise + 1e-9

    def detection_evidence(self, rise: float = 0.2) -> float:
        """Posterior probability that the envelope rises inside the range.

        A non-detector answers at a rate that does not depend on delay. On
        the grid that is a peak equal to the floor, at any of the shared
        rates, or a bump that does not reach into the delays presented
        (:meth:`visible_rise`). The evidence is the posterior mass on a rise
        of more than ``rise`` inside :meth:`rise_range`. It is a sanity
        check, not a classification. Its prior value depends on the range:
        on the default grids it is about 0.57 over 0 to 600 ms and 0.47 over
        140 to 500 ms. Read it against :meth:`detection_bayes_factor`, which
        removes the prior.
        """
        return float(self.posterior[self._rises(rise)].sum())

    def detection_bayes_factor(self, rise: float = 0.2) -> float:
        """Bayes factor for a rise of more than ``rise`` against a flatter one.

        The posterior odds of a rise above ``rise`` inside
        :meth:`rise_range` (see :meth:`visible_rise`) divided by its prior
        odds, so values above 1 mean the data favour an envelope that rises
        across the delays presented and values below 1 favour a (nearly)
        flat responder, at whatever rate they answer. NaN if the prior gives
        either side no mass: the grid then cannot express the comparison,
        and the data cannot move odds that are fixed at zero or infinity.
        """
        rises = self._rises(rise)
        prior_yes = float(self.prior[rises].sum())
        prior_no = float(self.prior[~rises].sum())
        post_yes = float(self.posterior[rises].sum())
        post_no = float(self.posterior[~rises].sum())
        if prior_yes == 0.0 or prior_no == 0.0:
            # No grid point rises, or every one does: nothing to compare.
            return float("nan")
        if post_no == 0.0:
            return float("inf")
        return (post_yes / post_no) / (prior_yes / prior_no)

    def predicted_envelope(self, d: Optional[np.ndarray] = None) -> np.ndarray:
        """Posterior predictive P(yes | d), for plotting against the data."""
        d = self.delays if d is None else np.asarray(d, dtype=float)
        return self._p_yes(d[:, None]) @ self.posterior

    # ----------------------------------------------------------------- state

    def state(self) -> Dict[str, object]:
        """Everything needed to resume or re-analyze the session."""
        return {
            "delays": self.delays.tolist(),
            "grids": {k: v.tolist() for k, v in self.grids.items()},
            "targets": list(self.targets),
            "explore": self.explore,
            "rise_range": list(self.rise_range()),
            "posterior": self.posterior.reshape(self.shape).tolist(),
            "history": [list(h) for h in self.history],
        }
