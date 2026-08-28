# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The session generator, and the promise that a seed is always recoverable."""

import json
import unittest

import numpy as np

from cardioception._rng import make_rng


class TestMakeRng(unittest.TestCase):
    def test_same_seed_gives_the_same_draws(self):
        a, seed_a = make_rng(42)
        b, seed_b = make_rng(42)
        self.assertEqual(seed_a, 42)
        self.assertEqual(seed_b, 42)
        self.assertTrue(np.array_equal(a.permutation(50), b.permutation(50)))
        self.assertTrue(np.allclose(a.uniform(size=20), b.uniform(size=20)))

    def test_different_seeds_give_different_draws(self):
        a, _ = make_rng(1)
        b, _ = make_rng(2)
        self.assertFalse(np.array_equal(a.permutation(50), b.permutation(50)))

    def test_seed_none_still_returns_a_concrete_seed(self):
        """The point of the change: an unseeded session is still replayable."""
        _, seed = make_rng(None)
        self.assertIsInstance(seed, int)
        replay, replay_seed = make_rng(seed)
        self.assertEqual(replay_seed, seed)
        original, _ = make_rng(seed)
        self.assertTrue(
            np.array_equal(original.permutation(20), replay.permutation(20))
        )

    def test_seed_none_varies_between_sessions(self):
        seeds = {make_rng(None)[1] for _ in range(20)}
        self.assertGreater(len(seeds), 1)

    def test_auto_seed_survives_a_json_round_trip(self):
        """A seed that JSON rounds is not a seed anyone can replay from.

        numpy's full entropy is a 128 bit integer. JavaScript and some R JSON
        readers silently lose precision above 2**53, so the seed is truncated.
        """
        _, seed = make_rng(None)
        self.assertLess(seed, 2**53)
        self.assertEqual(json.loads(json.dumps({"seed": seed}))["seed"], seed)

    def test_returns_a_generator_not_the_global_state(self):
        rng, _ = make_rng(0)
        self.assertIsInstance(rng, np.random.Generator)


if __name__ == "__main__":
    unittest.main()
