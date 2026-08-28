# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""`ContinuousOximeter` must be stock systole, only cheaper.

The point of the subclass is that a whole-session recording stays affordable.
That is worth nothing if the faster arithmetic is different arithmetic, so the
first test compares every derived list sample by sample against
`systole.recording.Oximeter` on the same input.
"""

import time
import unittest

import numpy as np
from systole.recording import Oximeter

from cardioception.devices import ContinuousOximeter

SFREQ = 75


def pulse(n: int, bpm: float = 72.0, seed: int = 7) -> list:
    """A waveform with peaks a detector will actually find."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SFREQ
    cycle = (t * (bpm / 60.0)) % 1.0
    signal = np.exp(-((cycle - 0.1) ** 2) / 0.002) * 100
    return (signal + rng.normal(0, 0.5, n)).tolist()


class DummySerial:
    """Enough of a port for the constructor, which never reads here."""

    def inWaiting(self):
        return 0

    def read(self, n):
        return b""

    def reset_input_buffer(self):
        pass


def feed(recorder, values):
    for v in values:
        recorder.add_paquet(v)
    return recorder


class TestSameArithmetic(unittest.TestCase):
    def test_every_derived_list_matches_stock_systole(self):
        values = pulse(2000)
        stock = feed(
            Oximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1), values
        )
        fast = feed(
            ContinuousOximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1),
            values,
        )

        self.assertEqual(stock.recording, fast.recording)
        self.assertEqual(stock.peaks, fast.peaks)
        self.assertEqual(stock.diff, fast.diff)
        self.assertEqual(stock.times, fast.times)
        np.testing.assert_allclose(stock.threshold, fast.threshold)
        # instant_rr carries NaN before the second peak, so compare with
        # equal_nan rather than ==.
        np.testing.assert_allclose(
            np.array(stock.instant_rr, dtype=float),
            np.array(fast.instant_rr, dtype=float),
            equal_nan=True,
        )

    def test_the_signal_really_does_contain_peaks(self):
        """Otherwise the comparison above is over two lists of zeros."""
        fast = feed(
            ContinuousOximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1),
            pulse(2000),
        )
        self.assertGreater(sum(fast.peaks), 20)

    def test_a_reset_forgets_the_peaks_it_cached(self):
        """`setup()` resets, and the task calls it at every break."""
        fast = feed(
            ContinuousOximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1),
            pulse(600),
        )
        self.assertGreater(sum(fast.peaks), 2)
        fast.reset(serial=DummySerial(), add_channels=1)
        self.assertEqual(fast.peaks, [])
        # A stale cache would report an interval spanning the wipe.
        feed(fast, pulse(200))
        self.assertTrue(np.isnan(fast.instant_rr[0]))

    def test_every_packet_carries_a_wall_clock_time(self):
        """`times` counts samples, so a dropped one is invisible in it."""
        before = time.time()
        fast = feed(
            ContinuousOximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1),
            pulse(300),
        )
        after = time.time()
        self.assertEqual(len(fast.wall_times), 300)
        self.assertGreaterEqual(fast.wall_times[0], before)
        self.assertLessEqual(fast.wall_times[-1], after)
        self.assertTrue(all(np.diff(fast.wall_times) >= 0))


class TestCostDoesNotGrow(unittest.TestCase):
    def test_it_is_much_cheaper_than_stock_over_a_long_recording(self):
        """The whole point: stock is O(N) per sample, this is O(1).

        The margin at 10 000 samples is roughly an order of magnitude, so a
        threshold of 2.5 leaves room for a noisy runner while still failing if
        the scan ever comes back.
        """
        values = pulse(10000)

        start = time.perf_counter()
        feed(Oximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1), values)
        stock_s = time.perf_counter() - start

        start = time.perf_counter()
        feed(
            ContinuousOximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1),
            values,
        )
        fast_s = time.perf_counter() - start

        self.assertLess(
            fast_s * 2.5,
            stock_s,
            f"stock {stock_s:.2f}s vs continuous {fast_s:.2f}s: the O(N) scan "
            f"looks like it is back",
        )
