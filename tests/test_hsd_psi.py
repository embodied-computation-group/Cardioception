# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The HSD engine: posterior bookkeeping, placement, recovery."""

import itertools
import math
import unittest

import numpy as np

from cardioception._rng import make_rng
from cardioception.HSD.psi import PARAMETERS, SynchronyPsi, gaussian_envelope
from cardioception.HSD.simulate import (
    DEFAULT_DELAYS,
    Observer,
    run_adaptive,
    run_mcs,
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
        Seeds 0 to 7 all pass at the 80 ms floor; seed 1 gives about 255
        [240, 270].
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

        The posterior mass is not: 33 of the 36 default (floor, peak) pairs
        rise by more than 0.2, so detection_evidence starts at 0.92.
        """
        psi = SynchronyPsi(DEFAULT_DELAYS)
        self.assertAlmostEqual(psi.detection_evidence(), 33 / 36, places=6)
        self.assertAlmostEqual(psi.detection_bayes_factor(), 1.0, places=9)
        # No grid point rises by more than 0.2: there is nothing to compare,
        # and the answer must not read as evidence for detection.
        flat = SynchronyPsi(DEFAULT_DELAYS, floor=[0.4], peak=[0.5])
        self.assertTrue(math.isnan(flat.detection_bayes_factor()))

    def test_non_detector_gives_a_bayes_factor_below_one(self):
        """Seeds 1 to 5: a flat 0.4 responder favours no rise after 80 trials.

        log10 of the detection Bayes factor must be below 0 for every seed,
        so the check is on the procedure rather than on one lucky draw. At the
        80 ms floor seeds 0 to 12 gave log10 values from -1.30 to -0.09.
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
        acquisition chain cannot realize (80 ms by default); the floor is
        recorded per row, and is NaN for MCS, which keeps its 0 ms level."""
        observer = Observer(150.0, 50.0, 0.05, 0.95)
        for explore in (0.0, 1.0):
            rows = run_adaptive(observer, 15, make_rng(9)[0], explore=explore)
            self.assertGreaterEqual(min(row["delay"] for row in rows), 80.0)
        df = study([observer], ["mcs", "psi_mu_x10"], reps=1, seed=3, n_trials=12)
        adaptive = df[df["method"] == "psi_mu_x10"]
        self.assertTrue((adaptive["min_delay"] == 80.0).all())
        self.assertTrue((adaptive["delay"] >= 80.0).all())
        self.assertTrue(df.loc[df["method"] == "mcs", "min_delay"].isna().all())
        lower = study(
            [observer], ["psi_mu_x10"], reps=1, seed=3, n_trials=12, min_delay=40.0
        )
        self.assertTrue((lower["min_delay"] == 40.0).all())

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
