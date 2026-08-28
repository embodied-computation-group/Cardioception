# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""`ReplayRecorder` has to produce the rate it is asked for.

It is the stand-in the whole headless suite measures heart rate through, so a
recorder that quietly returns a different rate does not make tests fail -- it
makes them assert something other than what they say. That happened: a tone
clamp test written against 42 BPM was in fact measuring 90.

These tests measure the recorder the way the task does, through
`systole.detection.ppg_peaks`, rather than trusting the peak mask the recorder
returns about itself.
"""

import unittest

import numpy as np
from systole.detection import ppg_peaks

from cardioception.devices import ReplayRecorder
from cardioception.HRD._constants import OXIMETER_SFREQ, PPG_SFREQ

#: Wide enough to cover a resting athlete and a startled child, and well past
#: the HRcutOff the task itself applies.
SWEEP = list(range(40, 185, 5))


def measured_rate(bpm: float, seconds: float = 6.0, seed: int = 7) -> float:
    """The rate the task's own pipeline recovers from this recorder."""
    recorder = ReplayRecorder(bpm=bpm, realtime=False, rng=np.random.default_rng(seed))
    recorder.setup()
    recorder.read(duration=seconds)
    signal = recorder.recording[-int(OXIMETER_SFREQ * seconds) :]
    _, peaks = ppg_peaks(
        signal, sfreq=OXIMETER_SFREQ, new_sfreq=PPG_SFREQ, clipping=True
    )
    ibi = np.diff(np.where(peaks)[0])
    if ibi.size == 0:
        return float("nan")
    return float(60000 / ibi.mean())


class TestTheRateIsTheRateAsked(unittest.TestCase):
    def test_every_rate_across_the_plausible_range(self):
        """The defect: everything at or below 60 BPM came back wrong.

        The cardiac period passed systole's one-second threshold window, the
        threshold collapsed between beats, and noise was detected as beats.
        42 measured 90, 55 measured 85, 60 measured 75. 72 and 100 were exact,
        and 72 is what every other test uses.
        """
        for bpm in SWEEP:
            with self.subTest(bpm=bpm):
                got = measured_rate(bpm)
                self.assertFalse(np.isnan(got), f"no beats detected at {bpm} BPM")
                self.assertAlmostEqual(
                    got,
                    bpm,
                    delta=1.0,
                    msg=f"asked {bpm} BPM, the task's pipeline recovers {got:.1f}",
                )

    def test_the_rates_that_used_to_fail(self):
        """Named individually, because these are the measurements in the bug."""
        for bpm in (42, 50, 55, 60):
            with self.subTest(bpm=bpm):
                self.assertAlmostEqual(measured_rate(bpm), bpm, delta=1.0)

    def test_a_slow_rate_is_stable_across_seeds(self):
        """The old failure was noise-driven, so it moved with the seed."""
        for seed in (1, 7, 13, 99):
            with self.subTest(seed=seed):
                self.assertAlmostEqual(measured_rate(45, seed=seed), 45, delta=1.0)


class TestTheWaveformItself(unittest.TestCase):
    def test_it_never_sits_flat(self):
        """The property the fix turns on.

        A near-zero baseline between narrow spikes is what let the rolling
        mean-plus-SD threshold collapse. Every one-second window must carry
        enough variance for that threshold to mean something, including at the
        slowest rate, where a window can fall entirely between beats.
        """
        recorder = ReplayRecorder(bpm=40.0, realtime=False)
        recorder.setup()
        recorder.read(duration=6.0)
        signal = np.asarray(recorder.recording)
        windows = [
            signal[i : i + OXIMETER_SFREQ]
            for i in range(0, len(signal) - OXIMETER_SFREQ, OXIMETER_SFREQ // 2)
        ]
        for i, window in enumerate(windows):
            with self.subTest(window=i):
                self.assertGreater(
                    window.std(),
                    5.0,
                    "a window of near-flat baseline collapses systole's threshold",
                )

    def test_the_peak_mask_lands_on_the_maxima(self):
        """The mask marks cycle boundaries, so the waveform must peak there.

        Within a sample: the mask marks the first sample of a new cycle and
        the waveform peaks at the boundary itself, which rarely coincides with
        a sampling instant. The previous waveform peaked a tenth of a cycle
        after the boundary, which at 40 BPM is eleven samples away.
        """
        recorder = ReplayRecorder(bpm=60.0, realtime=False)
        recorder.setup()
        recorder.read(duration=6.0)
        signal = np.asarray(recorder.recording)
        marked = np.where(np.asarray(recorder.peaks))[0]
        # Skip the first, which can fall on a partial cycle.
        for idx in marked[1:-1]:
            with self.subTest(sample=int(idx)):
                neighbourhood = signal[idx - 5 : idx + 6]
                self.assertLessEqual(
                    abs(int(np.argmax(neighbourhood)) - 5),
                    1,
                    "the marked sample is not within a sample of the maximum",
                )

    def test_an_artefact_read_still_defeats_detection(self):
        """The artefact path is how tests exercise a rejected window."""
        recorder = ReplayRecorder(bpm=72.0, realtime=False, artefact_every=1)
        recorder.setup()
        recorder.read(duration=6.0)
        signal = np.asarray(recorder.recording)
        self.assertLess(signal.std(), 5.0)


if __name__ == "__main__":
    unittest.main()
