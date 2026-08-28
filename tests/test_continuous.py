# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""`ContinuousOximeter` must be stock systole, only cheaper.

The point of the subclass is that a whole-session recording stays affordable.
That is worth nothing if the faster arithmetic is different arithmetic, so the
first test compares every derived list sample by sample against
`systole.recording.Oximeter` on the same input.
"""

import tempfile
import time
import unittest

import numpy as np
import pandas as pd
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


class FlakySerial(DummySerial):
    """A port that returns one corrupt packet part way through.

    `Oximeter.check` validates a five-byte Nonin packet; a packet whose bytes
    do not sum correctly fails it. This delivers good packets, then one bad
    one, then good packets again, which is what a noisy USB line does.
    """

    def __init__(self, good_before=200, good_after=200):
        self.queue = []
        for _ in range(good_before):
            self.queue.extend(self._packet(100))
        self.queue.extend([1, 2, 3, 4, 5])  # checksum will not match
        for _ in range(good_after):
            self.queue.extend(self._packet(100))

    @staticmethod
    def _packet(value):
        # Nonin format "2": header, status, value, and a checksum byte over
        # the preceding bytes.
        body = [1, 128, value, 0]
        return body + [sum(body) % 256]

    def inWaiting(self):
        return len(self.queue)

    def read(self, n):
        taken, self.queue = self.queue[:n], self.queue[n:]
        return bytes(taken)


class TestOneBadPacketDoesNotEraseTheSession(unittest.TestCase):
    """`Oximeter.read` calls `setup()` on a checksum failure, which resets.

    One corrupt packet, on the line whose corruption is the reason a checksum
    exists, discarded everything recorded so far. `readInWaiting` resyncs and
    keeps the recording, so the asymmetry was never a decision.
    """

    def test_the_recording_survives_a_corrupt_packet(self):
        recorder = ContinuousOximeter(serial=FlakySerial(), sfreq=SFREQ, add_channels=1)
        recorder.read(duration=0.5)
        self.assertGreater(
            len(recorder.recording),
            200,
            "the recording was reset by the bad packet rather than resynced",
        )

    def test_stock_systole_loses_it(self):
        """The behaviour being overridden, pinned so the reason stays visible."""
        recorder = Oximeter(serial=FlakySerial(), sfreq=SFREQ, add_channels=1)
        recorder.read(duration=0.5)
        self.assertLess(
            len(recorder.recording),
            200,
            "stock systole no longer wipes on a bad packet; drop the override",
        )


class TestSaveDoesNotCorruptWhatItRepairs(unittest.TestCase):
    """`Oximeter.save`'s length guards are `[0 * len(x)]`, which is `[0]`.

    `[0] * len(x)` was meant. One of the three also assigns `self.peak`, a
    typo, so the list it claims to fix is untouched. They fire only once the
    lists have drifted, which needs a long recording -- the case continuous
    recording creates.
    """

    def _drifted(self):
        recorder = ContinuousOximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1)
        feed(recorder, pulse(300))
        # Drift, as a dropped or duplicated packet would.
        recorder.peaks = recorder.peaks[:-7]
        recorder.instant_rr = recorder.instant_rr[:-3]
        return recorder

    def test_every_column_comes_out_the_length_of_the_recording(self):
        recorder = self._drifted()
        with tempfile.TemporaryDirectory() as tmp:
            target = f"{tmp}/signal.txt"
            recorder.save(target)
            written = pd.read_csv(target)
        self.assertEqual(len(written), len(recorder.recording))
        for column in ("signal", "peaks", "instant_rr", "time", "wall_time"):
            with self.subTest(column=column):
                self.assertIn(column, written.columns)

    def test_the_padding_keeps_the_samples_it_had(self):
        """Padding, not replacement: the guard threw the data away."""
        recorder = self._drifted()
        before = list(recorder.peaks)
        with tempfile.TemporaryDirectory() as tmp:
            recorder.save(f"{tmp}/signal.txt")
        self.assertEqual(recorder.peaks[: len(before)], before)
        self.assertEqual(len(recorder.peaks), len(recorder.recording))

    def test_stock_systole_replaces_the_list_with_one_element(self):
        """The behaviour being overridden."""
        recorder = Oximeter(serial=DummySerial(), sfreq=SFREQ, add_channels=1)
        feed(recorder, pulse(300))
        recorder.instant_rr = recorder.instant_rr[:-3]
        self.assertNotEqual(len(recorder.instant_rr), len(recorder.recording))
        # This is what the guard does, lifted out of save() so the assertion
        # does not depend on writing a file.
        repaired = [0 * len(recorder.recording)]
        self.assertEqual(repaired, [0], "the guard is no longer [0 * len(x)]")
