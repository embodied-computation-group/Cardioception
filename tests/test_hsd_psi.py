# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The HSD engine: posterior bookkeeping, placement, recovery."""

import itertools
import math
import unittest

import numpy as np

from cardioception._rng import make_rng
from cardioception.HSD.config import TaskConfig
from cardioception.HSD.psi import PARAMETERS, RATES, SynchronyPsi, gaussian_envelope
from cardioception.HSD.simulate import (
    DEFAULT_DELAYS,
    Observer,
    default_observers,
    evidence,
    run_adaptive,
    run_mcs,
    stopping,
    study,
)


class TestPosterior(unittest.TestCase):
    def test_posterior_sums_to_one_after_updates(self):
        """Each update renormalizes, so the posterior stays a distribution."""
        psi = SynchronyPsi(DEFAULT_DELAYS, rng=make_rng(0)[0])
        self.assertAlmostEqual(psi.posterior.sum(), 1.0, places=12)
        for delay, response in [(100, True), (300, False), (500, True), (0, False)]:
            psi.update(delay, response)
            self.assertAlmostEqual(psi.posterior.sum(), 1.0, places=12)
            self.assertTrue(np.all(psi.posterior >= 0))
        for name in PARAMETERS:
            self.assertAlmostEqual(psi.marginal(name).sum(), 1.0, places=12)

    def test_update_accepts_a_realized_delay_off_the_grid(self):
        """The posterior is conditioned on what was played, not what was asked.

        A realized delay of 137.3 ms is not a candidate; the likelihood is
        recomputed from the envelope, so it must still be usable.
        """
        psi = SynchronyPsi(DEFAULT_DELAYS)
        before = psi.posterior.copy()
        psi.update(137.3, True)
        self.assertAlmostEqual(psi.posterior.sum(), 1.0, places=12)
        self.assertFalse(np.allclose(psi.posterior, before))
        self.assertEqual(psi.history[-1][0], 137.3)

    def test_non_finite_delay_raises_and_leaves_the_posterior_intact(self):
        """A NaN delay (a failed latency measurement) must not poison the session."""
        psi = SynchronyPsi(DEFAULT_DELAYS)
        psi.update(200.0, True)
        before = psi.posterior.copy()
        with self.assertRaises(ValueError):
            psi.update(float("nan"), True)
        self.assertTrue(np.array_equal(psi.posterior, before))
        self.assertEqual(len(psi.history), 1)

    def test_state_posterior_has_the_grid_shape(self):
        """state() must be reloadable onto the (mu, sigma, floor, peak) grid.

        Not just the shape: entry [i][j][k][m] must be the posterior mass of
        the grid point with mu = grids["mu"][i], sigma = grids["sigma"][j]
        and so on, or a reloaded session would silently permute parameters.
        """
        psi = SynchronyPsi(DEFAULT_DELAYS)
        for delay, response in [(250.0, True), (90.0, False), (420.0, False)]:
            psi.update(delay, response)
        state = psi.state()
        expected = tuple(len(state["grids"][name]) for name in PARAMETERS)
        self.assertEqual(np.asarray(state["posterior"]).shape, expected)
        self.assertEqual(expected, psi.shape)
        self.assertEqual(state["history"][0], [250.0, 1, False])
        rng = make_rng(4)[0]
        picks = [tuple(int(rng.integers(n)) for n in expected) for _ in range(25)]
        picks += [(0, 0, 0, 0), tuple(n - 1 for n in expected)]
        for i, j, k, m in picks:
            match = np.ones(psi.posterior.size, dtype=bool)
            for name, index in zip(PARAMETERS, (i, j, k, m)):
                match &= psi.theta[name] == state["grids"][name][index]
            self.assertEqual(match.sum(), 1)
            self.assertEqual(
                state["posterior"][i][j][k][m], psi.posterior[np.flatnonzero(match)[0]]
            )


class TestPlacement(unittest.TestCase):
    def test_next_delay_respects_the_allowed_range(self):
        """The latency floor and the next-beat ceiling bound every trial,
        explored or not; an empty range is an error, not a silent default."""
        for explore in (0.0, 1.0):
            psi = SynchronyPsi(DEFAULT_DELAYS, explore=explore, rng=make_rng(3)[0])
            for _ in range(15):
                delay, _ = psi.next_delay(min_delay=100.0, max_delay=300.0)
                self.assertGreaterEqual(delay, 100.0)
                self.assertLessEqual(delay, 300.0)
                psi.update(delay, bool(psi.rng.random() < 0.5))
        psi = SynchronyPsi(DEFAULT_DELAYS)
        with self.assertRaises(ValueError):
            psi.next_delay(min_delay=350.0, max_delay=300.0)
        with self.assertRaises(ValueError):
            psi.next_delay(min_delay=601.0)

    def test_explore_flag_marks_explored_trials(self):
        """The saved trial type must say which delays the objective did not choose."""
        observer = Observer(250.0, 80.0, 0.05, 0.95)
        rows = run_adaptive(observer, 10, make_rng(5)[0], explore=1.0)
        self.assertTrue(all(row["explored"] for row in rows))
        rows = run_adaptive(observer, 10, make_rng(5)[0], explore=0.0)
        self.assertFalse(any(row["explored"] for row in rows))
        psi = SynchronyPsi(DEFAULT_DELAYS, explore=0.5, rng=make_rng(6)[0])
        flags = []
        for _ in range(20):
            delay, explored = psi.next_delay()
            psi.update(delay, True, explored)
            flags.append(explored)
        self.assertEqual([h[2] for h in psi.history], flags)
        self.assertTrue(any(flags) and not all(flags))

    def test_mu_objective_does_not_collapse_onto_one_delay(self):
        """Answers García-Pérez (2014): targeting mu alone must still spread
        trials over the flanks of the envelope, not one narrow band."""
        observer = Observer(250.0, 80.0, 0.05, 0.95)
        rows = run_adaptive(observer, 40, make_rng(7)[0], targets=("mu",))
        delays = np.array([row["delay"] for row in rows])
        self.assertGreaterEqual(np.unique(delays).size, 2)
        self.assertGreater(np.ptp(delays), 20.0)
        # Both flanks, not just a spread on one side of the bump.
        self.assertTrue(np.any(delays < 250.0 - 80.0 / 2))
        self.assertTrue(np.any(delays > 250.0 + 80.0 / 2))

    def test_expected_entropy_matches_brute_force(self):
        """The vectorized objective against a loop over grid points and answers.

        On a 13 x 3 x 3 x 2 grid after a few updates, for a target of mu
        alone, of (sigma, peak), and the joint, to 1e-10.
        """
        grids = {
            "mu": np.arange(0.0, 601.0, 50.0),
            "sigma": np.array([40.0, 100.0, 200.0]),
            "floor": np.array([0.0, 0.1, 0.3]),
            "peak": np.array([0.6, 0.9]),
        }
        delays = np.arange(0.0, 601.0, 100.0)
        history = [(100.0, True), (250.0, True), (480.0, False), (37.5, False)]
        shape = tuple(grids[name].size for name in PARAMETERS)
        points = list(itertools.product(*(range(n) for n in shape)))

        def p_yes(d, idx):
            theta = [grids[name][i] for name, i in zip(PARAMETERS, idx)]
            return float(gaussian_envelope(d, *theta))

        # Posterior from scratch, one grid point at a time.
        post = {}
        for idx in points:
            weight = 1.0
            for delay, response in history:
                p = p_yes(delay, idx)
                weight *= p if response else 1.0 - p
            post[idx] = weight
        total = sum(post.values())
        post = {idx: w / total for idx, w in post.items()}

        for targets in [("mu",), ("sigma", "peak"), PARAMETERS]:
            with self.subTest(targets=targets):
                psi = SynchronyPsi(delays, targets=targets, **grids)
                for delay, response in history:
                    psi.update(delay, response)
                keep = [PARAMETERS.index(t) for t in targets]
                brute = []
                for d in delays:
                    h = 0.0
                    for response in (True, False):
                        joint = {}
                        for idx in points:
                            p = p_yes(d, idx)
                            joint[idx] = post[idx] * (p if response else 1.0 - p)
                        p_r = sum(joint.values())
                        marg = {}
                        for idx, w in joint.items():
                            key = tuple(idx[i] for i in keep)
                            marg[key] = marg.get(key, 0.0) + w / p_r
                        ent = -sum(q * math.log(q) for q in marg.values() if q > 0)
                        h += p_r * ent
                    brute.append(h)
                np.testing.assert_allclose(
                    psi.expected_entropy(), brute, rtol=0, atol=1e-10
                )


class TestValidation(unittest.TestCase):
    def test_invalid_grids_raise(self):
        """Grids the quantile and likelihood code cannot handle are refused."""
        bad = [
            {"delays": []},
            {"delays": [[0, 100], [200, 300]]},
            {"delays": DEFAULT_DELAYS, "mu": []},
            {"delays": DEFAULT_DELAYS, "mu": [300.0, 200.0, 100.0]},
            {"delays": DEFAULT_DELAYS, "sigma": [0.0, 50.0]},
            {"delays": DEFAULT_DELAYS, "sigma": [50.0, np.nan]},
            {"delays": DEFAULT_DELAYS, "floor": [-0.1, 0.1]},
            {"delays": DEFAULT_DELAYS, "peak": [0.9, 1.2]},
            {"delays": DEFAULT_DELAYS, "floor": [0.6], "peak": [0.5]},
            {"delays": DEFAULT_DELAYS, "prior": [1.0, 2.0]},
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    SynchronyPsi(**kwargs)

    def test_invalid_targets_and_explore_raise(self):
        """Only model parameters can steer placement, and explore is a probability."""
        for targets in [(), ("tau",), ("mu", "lapse"), "mu"]:
            with self.subTest(targets=targets):
                with self.assertRaises(ValueError):
                    SynchronyPsi(DEFAULT_DELAYS, targets=targets)
        for explore in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                SynchronyPsi(DEFAULT_DELAYS, explore=explore)
        with self.assertRaises(ValueError):
            SynchronyPsi(DEFAULT_DELAYS).estimate("mu", ci=1.0)


class TestRecovery(unittest.TestCase):
    def test_gaussian_observer_is_recovered(self):
        """Seed 1: 80 trials of the mu objective find mu = 250 ms.

        Observer mu 250, sigma 80, floor 0.05, peak 0.95. The posterior mean
        must be within 40 ms and the 95 percent interval must contain 250.
        Seeds 0 to 7 all pass at the 130 ms floor; seed 1 gives about 258
        [240, 280].
        """
        observer = Observer(250.0, 80.0, 0.05, 0.95)
        last = run_adaptive(observer, 80, make_rng(1)[0])[-1]
        self.assertLess(abs(last["mu_mean"] - 250.0), 40.0)
        self.assertLessEqual(last["mu_ci_low"], 250.0)
        self.assertGreaterEqual(last["mu_ci_high"], 250.0)
        self.assertGreater(last["detection_evidence"], 0.95)
        self.assertGreater(last["detection_bf"], 100.0)

    def test_detection_bayes_factor_starts_at_one(self):
        """The Bayes factor removes the prior, so before any data it is 1.

        The posterior mass is not. On the default grids over the candidate
        range, 0 to 600 ms, about 0.57 of the prior rises by more than 0.2:
        an honest prior, near even, where the old floor and peak grids put
        0.92 on a rise because they could not express most flat responders.
        """
        psi = SynchronyPsi(DEFAULT_DELAYS)
        self.assertGreater(psi.detection_evidence(), 0.45)
        self.assertLess(psi.detection_evidence(), 0.6)
        self.assertAlmostEqual(psi.detection_bayes_factor(), 1.0, places=9)
        # No grid point rises by more than 0.2: there is nothing to compare,
        # and the answer must not read as evidence for detection.
        flat = SynchronyPsi(DEFAULT_DELAYS, floor=[0.4], peak=[0.5])
        self.assertTrue(math.isnan(flat.detection_bayes_factor()))

    def test_every_flat_rate_is_on_the_grid(self):
        """A flat responder at any rate from 0.03 to 0.97 is a grid point
        (peak equal to floor) with prior mass, so a biased non-detector does
        not have to be explained as a rise."""
        psi = SynchronyPsi(DEFAULT_DELAYS)
        self.assertEqual(psi.grids["floor"].tolist(), RATES.tolist())
        self.assertEqual(psi.grids["peak"].tolist(), RATES.tolist())
        self.assertLessEqual(RATES.min(), 0.03)
        self.assertGreaterEqual(RATES.max(), 0.97)
        for rate in RATES:
            flat = (psi.theta["floor"] == rate) & (psi.theta["peak"] == rate)
            self.assertGreater(psi.prior[flat].sum(), 0.0)
            # A flat envelope never rises, wherever mu and sigma sit.
            self.assertTrue(np.all(psi.visible_rise()[flat] < 1e-12))

    def test_a_rise_outside_the_presented_range_is_not_a_rise(self):
        """A bump the task cannot present counts as flat.

        Over 140 to 500 ms, a narrow bump at 0 or 600 ms rises by almost
        nothing, whatever its peak; the same bump at 300 ms rises by the
        whole of peak minus floor. Without a fixed range the rise is measured
        over the delays presented so far.
        """
        psi = SynchronyPsi(DEFAULT_DELAYS, rise_range=(140.0, 500.0))
        rise = psi.visible_rise()
        point = (
            (psi.theta["floor"] == 0.03)
            & (psi.theta["peak"] == 0.97)
            & np.isclose(psi.theta["sigma"], psi.grids["sigma"][0])
        )
        for mu, expected in ((0.0, 0.0), (600.0, 0.0), (300.0, 0.94)):
            with self.subTest(mu=mu):
                at = point & (psi.theta["mu"] == mu)
                self.assertAlmostEqual(float(rise[at][0]), expected, delta=1e-4)
        self.assertEqual(psi.state()["rise_range"], [140.0, 500.0])
        free = SynchronyPsi(DEFAULT_DELAYS)
        self.assertEqual(free.rise_range(), (0.0, 600.0))
        free.update(200.0, True)
        self.assertEqual(free.rise_range(), (0.0, 600.0))
        free.update(460.0, False)
        self.assertEqual(free.rise_range(), (200.0, 460.0))
        for bad in ((500.0, 140.0), (0.0, float("inf"))):
            with self.assertRaises(ValueError):
                SynchronyPsi(DEFAULT_DELAYS, rise_range=bad)

    def test_flat_responders_do_not_look_like_detectors(self):
        """Seeds 0 to 2, 60 trials of the task's own configuration.

        Bounds 130 to 513 ms (a 0.72 s heart period), explore 0.1. Answering
        always "yes", always "no", or at a flat 0.1 or 0.9, the log10
        detection Bayes factor must be at most 0: biased non-detectors used
        to reach +3 to +10, because the old grids could express a flat rate
        only from about 0.3 to 0.6. A detector (mu 250, sigma 50, floor 0.1,
        peak 0.9) must be clearly positive. Seeds 0 to 7 gave -2.0 (all no),
        -4.3 (all yes), -1.5 to -0.7 (0.1), -3.2 to -0.5 (0.9) and +1.9 to
        +3.2 (the detector).
        """
        config = TaskConfig()
        low, high = config.bounds(0.72)
        nan = float("nan")
        cases = {
            "all no": (Observer(nan, nan, 0.0, 0.0), None, 0.0),
            "all yes": (Observer(nan, nan, 1.0, 1.0), None, 0.0),
            "flat 0.1": (Observer(nan, nan, 0.1, 0.1), None, 0.0),
            "flat 0.9": (Observer(nan, nan, 0.9, 0.9), None, 0.0),
            "detector": (Observer(250.0, 50.0, 0.1, 0.9), 1.0, None),
        }
        for name, (observer, above, below) in cases.items():
            for seed in range(3):
                with self.subTest(observer=name, seed=seed):
                    rng = np.random.default_rng(seed)
                    psi = config.engine(rng=rng)
                    for _ in range(60):
                        delay, explored = psi.next_delay(low, high)
                        psi.update(delay, observer.respond(delay, rng), explored)
                    log_bf = np.log10(psi.detection_bayes_factor())
                    if above is not None:
                        self.assertGreater(log_bf, above)
                    if below is not None:
                        self.assertLessEqual(log_bf, below)

    def test_mu_is_estimated_given_a_rise(self):
        """mu and sigma come from the posterior conditioned on a rise.

        A sharp observer (mu 250, sigma 40, floor 0.02, peak 0.98) after 12
        trials of the task's configuration at a 0.6 s period, seed 0. While
        a flat envelope keeps mass, the marginal mu is spread over the grid;
        the conditional one is not. The estimate matches the masked and
        renormalized posterior, floor and peak stay marginal, and the
        stopping rule reads the conditional width. Seeds 0 to 2 gave
        conditional widths of 70 to 170 ms against marginal ones of 160 to
        420 ms.
        """
        config = TaskConfig()
        low, high = config.bounds(0.6)
        rng = np.random.default_rng(0)
        observer = Observer(250.0, 40.0, 0.02, 0.98)
        psi = config.engine(rng=rng)
        for _ in range(12):
            delay, explored = psi.next_delay(low, high)
            psi.update(delay, observer.respond(delay, rng), explored)
        self.assertTrue(psi.rise_supported())
        conditional = psi.estimate("mu")
        marginal = psi.estimate("mu", conditional=False)
        width = conditional["ci_high"] - conditional["ci_low"]
        self.assertLess(width, marginal["ci_high"] - marginal["ci_low"])
        self.assertLessEqual(conditional["ci_low"], 250.0)
        self.assertGreaterEqual(conditional["ci_high"], 250.0)
        self.assertEqual(psi.ci_width(), width)
        self.assertEqual(psi.converged(width), True)
        weights = np.where(psi.visible_rise() > 0.2 + 1e-9, psi.posterior, 0.0)
        weights = weights.reshape(psi.shape).sum(axis=(1, 2, 3))
        weights = weights / weights.sum()
        self.assertAlmostEqual(
            conditional["mean"], float(np.sum(psi.grids["mu"] * weights)), places=9
        )
        floor = psi.estimate("floor")
        self.assertEqual(floor, psi.estimate("floor", conditional=False))
        self.assertTrue(psi.summary()["conditional"])

    def test_conditional_estimate_falls_back_without_a_rise(self):
        """With no mass on a rise the estimates are the marginal ones, and
        the summary says so."""
        flat = SynchronyPsi(DEFAULT_DELAYS, floor=[0.4], peak=[0.5])
        self.assertFalse(flat.rise_supported())
        self.assertEqual(flat.estimate("mu"), flat.estimate("mu", conditional=False))
        self.assertFalse(flat.summary()["conditional"])
        config = TaskConfig()
        psi = config.engine(rng=np.random.default_rng(0))
        for delay in np.linspace(140.0, 500.0, 60):
            psi.update(float(delay), True)
        self.assertLess(psi.detection_evidence(), 0.01)
        self.assertFalse(psi.rise_supported())
        self.assertEqual(psi.estimate("mu"), psi.estimate("mu", conditional=False))

    def test_non_detector_gives_a_bayes_factor_below_one(self):
        """Seeds 1 to 5: a flat 0.4 responder favours no rise after 80 trials.

        log10 of the detection Bayes factor must be below 0 for every seed,
        so the check is on the procedure rather than on one lucky draw. At the
        130 ms floor seeds 0 to 12 gave log10 values from -0.94 to -0.05.
        """
        observer = Observer(float("nan"), float("nan"), 0.4, 0.4)
        for seed in range(1, 6):
            with self.subTest(seed=seed):
                last = run_adaptive(observer, 80, make_rng(seed)[0])[-1]
                self.assertLess(np.log10(last["detection_bf"]), 0.0)


class TestSimulation(unittest.TestCase):
    def test_run_mcs_presents_every_level_equally(self):
        """MCS is a balanced design; the classical measures sit on the last row."""
        levels = (0.0, 250.0, 500.0)
        observer = Observer(250.0, 80.0, 0.05, 0.95)
        rows = run_mcs(observer, 4, make_rng(8)[0], levels=levels)
        self.assertEqual(len(rows), len(levels) * 4)
        order = [row["delay"] for row in rows]
        delays, counts = np.unique(order, return_counts=True)
        self.assertEqual(delays.tolist(), list(levels))
        self.assertTrue(np.all(counts == 4))
        self.assertNotEqual(order, sorted(order))
        self.assertTrue(all(np.isnan(row["mi"]) for row in rows[:-1]))
        yes = [row["delay"] for row in rows if row["response"]]
        self.assertEqual(rows[-1]["mi"], np.median(yes))

    def test_run_mcs_delivers_exactly_n_trials(self):
        """A trial count not divisible by six still gives that many trials,
        each level the floor or the ceiling of n / 6; 120 is the published
        20 per level and draws the same numbers as n_per_level=20."""
        observer = Observer(250.0, 80.0, 0.05, 0.95)
        for n in (20, 40):
            with self.subTest(n=n):
                rows = run_mcs(observer, 0, make_rng(10)[0], n_trials=n)
                self.assertEqual(len(rows), n)
                _, counts = np.unique([r["delay"] for r in rows], return_counts=True)
                self.assertEqual(counts.size, 6)
                self.assertTrue(set(counts.tolist()) <= {n // 6, -(-n // 6)})
        a = run_mcs(observer, 0, make_rng(10)[0], n_trials=120)
        b = run_mcs(observer, 20, make_rng(10)[0])
        self.assertEqual([r["delay"] for r in a], [r["delay"] for r in b])
        self.assertEqual(a[-1]["mi"], b[-1]["mi"])

    def test_asymmetric_observer_is_wider_on_the_right(self):
        """The misspecified observer must differ from the fitted envelope."""
        observer = Observer(200.0, 50.0, 0.0, 1.0, "asymmetric")
        self.assertAlmostEqual(float(observer.p_yes(200.0)), 1.0)
        self.assertGreater(float(observer.p_yes(300.0)), float(observer.p_yes(100.0)))
        for k in (0.5, 1.0, 2.0):
            with self.subTest(k=k):
                self.assertAlmostEqual(
                    float(observer.p_yes(200.0 - k * 50.0)),
                    float(observer.p_yes(200.0 + 2 * k * 50.0)),
                    places=12,
                )

    def test_adaptive_runs_respect_the_latency_floor(self):
        """No adaptive trial, explored or chosen, may ask for a delay the
        acquisition chain cannot realize (130 ms by default, the task's
        floor) or one above the ceiling the participant's heart period sets;
        both are recorded per row, and are NaN for MCS, which keeps its
        levels of 0 to 500 ms."""
        observer = Observer(150.0, 50.0, 0.05, 0.95)
        for explore in (0.0, 1.0):
            rows = run_adaptive(observer, 15, make_rng(9)[0], explore=explore)
            self.assertGreaterEqual(min(row["delay"] for row in rows), 130.0)
        df = study([observer], ["mcs", "psi_mu_x10"], reps=2, seed=3, n_trials=12)
        adaptive = df[df["method"] == "psi_mu_x10"]
        self.assertTrue((adaptive["min_delay"] == 130.0).all())
        self.assertTrue((adaptive["delay"] >= 130.0).all())
        self.assertTrue((adaptive["delay"] <= adaptive["max_delay"]).all())
        self.assertTrue(df.loc[df["method"] == "mcs", "min_delay"].isna().all())
        self.assertTrue(df.loc[df["method"] == "mcs", "max_delay"].isna().all())
        lower = study(
            [observer], ["psi_mu_x10"], reps=1, seed=3, n_trials=12, min_delay=40.0
        )
        self.assertTrue((lower["min_delay"] == 40.0).all())

    def test_heart_period_sets_the_ceiling_per_participant(self):
        """Each simulated participant has one heart period in 0.8 to 1.1 s,
        shared by every method, and the adaptive ceiling is the task's
        bound at that period; without a period range there is no ceiling."""
        observer = Observer(250.0, 80.0, 0.05, 0.95)
        df = study([observer], ["mcs", "psi_mu"], reps=3, seed=5, n_trials=3)
        periods = df.groupby("rep")["period"].agg(["min", "max"])
        self.assertTrue((periods["min"] == periods["max"]).all())
        self.assertTrue(periods["min"].between(0.8, 1.1).all())
        self.assertEqual(periods["min"].nunique(), 3)
        adaptive = df[df["method"] == "psi_mu"]
        for period, ceiling in zip(adaptive["period"], adaptive["max_delay"]):
            self.assertEqual(ceiling, TaskConfig().bounds(period)[1])
        free = study([observer], ["psi_mu"], reps=1, seed=5, n_trials=3, period=None)
        self.assertTrue(free["max_delay"].isna().all())
        self.assertTrue(free["period"].isna().all())

    def test_jitter_and_train_loss(self):
        """Jitter moves the delay the observer responds to, not the one the
        engine is updated with; at 0 it draws nothing, so the run is the
        exact one. A lost train gives no response and no update."""
        observer = Observer(250.0, 20.0, 0.0, 1.0)
        rng = make_rng(4)[0]
        exact = [observer.respond(250.0, rng) for _ in range(200)]
        self.assertTrue(all(exact))
        jittered = [observer.respond(250.0, rng, 60.0) for _ in range(200)]
        self.assertLess(np.mean(jittered), 0.6)
        a = run_adaptive(observer, 10, make_rng(6)[0])
        b = run_adaptive(observer, 10, make_rng(6)[0], jitter_sd=0.0, train_loss=0.0)
        self.assertEqual(a, b)
        rows = run_adaptive(observer, 30, make_rng(6)[0], train_loss=0.5)
        lost = [row for row in rows if row["lost"]]
        self.assertGreater(len(lost), 5)
        self.assertTrue(all(math.isnan(row["response"]) for row in lost))
        self.assertEqual(rows[-1]["n_updates"], 30 - len(lost))
        for before, after in zip(rows, rows[1:]):
            if after["lost"]:
                self.assertEqual(before["mu_mean"], after["mu_mean"])
        with self.assertRaises(ValueError):
            study([observer], ["psi_mu"], reps=1, n_trials=2, train_loss=1.0)

    def test_observer_bank_includes_biased_non_detectors(self):
        """The four biased non-detectors come after the original 34, so the
        earlier observers keep their indices and run seeds."""
        bank = default_observers()
        self.assertEqual(len(bank), 38)
        self.assertEqual([o.floor for o in bank[34:]], [1.0, 0.0, 0.1, 0.9])
        self.assertTrue(all(o.kind == "non-detector" for o in bank[34:]))
        self.assertEqual(bank[32].kind, "asymmetric")

    def test_evidence_and_stopping_tables(self):
        """The stopping rule never runs past the maximum, counts only
        updates towards the minimum, and the evidence table has one row per
        method, group and trial count."""
        observers = [Observer(250.0, 50.0, 0.05, 0.95), Observer(0, 0, 1.0, 1.0)]
        df = study(observers, ["psi_mu"], reps=2, seed=1, n_trials=12)
        stops = stopping(df, min_trials=5, max_trials=10, ci_width=600.0)
        self.assertEqual(sorted(stops["group"]), ["always yes", "clean detector"])
        self.assertTrue((stops["median_stop_trial"] <= 10).all())
        self.assertTrue((stops["median_stop_trial"] >= 5).all())
        self.assertTrue(
            math.isnan(stops.set_index("group").loc["always yes", "rmse_at_stop"])
        )
        ev = evidence(df, trials=(5, 10))
        self.assertEqual(len(ev), 2 * 2)
        self.assertTrue((ev["n_runs"] == 2).all())

    def test_study_is_reproducible(self):
        """Each run is seeded from (seed, observer, method, rep), not from order.

        So a serial and a two-process study agree exactly, with an adaptive
        method whose exploration draws would expose any shared generator, and
        a run of a subset of methods reproduces that slice of the full study.
        A negative seed, which SeedSequence refuses, is a clear ValueError.
        """
        observers = [Observer(250.0, 80.0, 0.05, 0.95), Observer(200.0, 50.0, 0.2, 0.8)]
        methods = ["mcs", "psi_mu_x10"]
        serial = study(observers, methods, reps=1, seed=11, n_trials=10)
        parallel = study(observers, methods, reps=1, seed=11, n_trials=10, processes=2)
        self.assertEqual(len(serial), 2 * 2 * 10)
        self.assertTrue(serial.equals(parallel))
        self.assertTrue(serial["explored"].any())
        subset = study(observers, ["psi_mu_x10"], reps=1, seed=11, n_trials=10)
        part = serial[serial["method"] == "psi_mu_x10"].drop(columns=["mi", "iqr"])
        self.assertTrue(part.reset_index(drop=True).equals(subset))
        self.assertEqual(serial["run_seed"].nunique(), 4)
        with self.assertRaises(ValueError):
            study(observers, ["mcs"], reps=1, seed=-1, n_trials=2)


if __name__ == "__main__":
    unittest.main()
