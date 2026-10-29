# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""LSLRecorder against a synthetic ECG streamed over LSL on this machine.

The outlet runs in real time in a background thread, so these tests take a few
seconds each. They need pylsl, and skip without it.
"""

import shutil
import tempfile
import threading
import time
import unittest
import uuid

import numpy as np
import pandas as pd
import pytest

pylsl = pytest.importorskip("pylsl")

from cardioception.devices import LSLRecorder  # noqa: E402
from cardioception.devices._beats import detect_beats, snap_to_qrs  # noqa: E402
from cardioception.HRD._constants import PPG_SFREQ, Trigger  # noqa: E402

SFREQ = 1000


def synthetic_ecg(seconds: float, bpm: float, sfreq: int = SFREQ, seed: int = 0):
    """P, QRS and T waves as Gaussians, at a fixed rate, with a little noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sfreq)) / sfreq
    phase = (t * bpm / 60.0) % 1.0
    period = 60.0 / bpm

    def wave(centre, width, height):
        d = (phase - centre) * period
        return height * np.exp(-0.5 * (d / width) ** 2)

    ecg = (
        wave(0.15, 0.025, 0.15)  # P
        + wave(0.3, 0.008, -0.1)  # Q
        + wave(0.32, 0.01, 1.0)  # R
        + wave(0.34, 0.008, -0.2)  # S
        + wave(0.6, 0.06, 0.3)  # T
    )
    # Raw ADC counts, as a biosignalsplux hub sends them.
    return (32768 + 8000 * ecg + rng.normal(0, 40, t.size)).astype(np.int32)


class FakeHub:
    """An LSL outlet shaped like the PLUX bridge: nSeq, then the sensors."""

    def __init__(self, bpm: float = 72.0, seconds: float = 60.0):
        self.name = f"test-{uuid.uuid4().hex[:8]}"
        info = pylsl.StreamInfo(
            self.name, "Biosignals", 3, SFREQ, pylsl.cf_int32, self.name
        )
        channels = info.desc().append_child("channels")
        for label in ("nSeq", "RESP1", "ECG2"):
            channels.append_child("channel").append_child_value("label", label)
        self.outlet = pylsl.StreamOutlet(info, chunk_size=10)
        self.ecg = synthetic_ecg(seconds, bpm)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._stream, daemon=True)

    def _stream(self):
        start = time.perf_counter()
        sent = 0
        while not self._stop.is_set() and sent < self.ecg.size:
            due = min(int((time.perf_counter() - start) * SFREQ), self.ecg.size)
            if due > sent:
                chunk = [[i, 0, int(self.ecg[i])] for i in range(sent, due)]
                self.outlet.push_chunk(chunk)
                sent = due
            time.sleep(0.005)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


class TestLSLRecorder(unittest.TestCase):
    def test_finds_the_channel_by_label(self):
        with FakeHub() as hub:
            recorder = LSLRecorder(name=hub.name, channel="ECG2", timeout=5)
            self.assertEqual(recorder.channel, 2)
            self.assertEqual(recorder.sfreq, SFREQ)
            recorder.close()

    def test_unknown_channel_lists_the_ones_there_are(self):
        with FakeHub() as hub:
            with self.assertRaisesRegex(ValueError, "nSeq, RESP1, ECG2"):
                LSLRecorder(name=hub.name, channel="ECG9", timeout=5)

    def test_missing_stream_says_so(self):
        with self.assertRaisesRegex(RuntimeError, "No LSL stream"):
            LSLRecorder(name=f"absent-{uuid.uuid4().hex}", timeout=0.5)

    def test_reads_in_real_time(self):
        with FakeHub() as hub:
            recorder = LSLRecorder(name=hub.name, channel="ECG2", timeout=5)
            recorder.setup().read(duration=2)
            n = len(recorder.recording)
            # Three seconds requested; allow for the first chunk's latency.
            self.assertGreater(n, 2.5 * SFREQ)
            self.assertLess(n, 3.5 * SFREQ)
            for column in (recorder.times, recorder.lsl_times, recorder.peaks):
                self.assertEqual(len(column), n)
            self.assertEqual(len(recorder.channels["Channel_0"]), n)
            recorder.close()

    def test_heart_rate_over_a_listening_window(self):
        for bpm in (50.0, 72.0, 110.0):
            with self.subTest(bpm=bpm), FakeHub(bpm=bpm) as hub:
                recorder = LSLRecorder(name=hub.name, channel="ECG2", timeout=5)
                recorder.setup().read(duration=6)
                signal = recorder.recording[-6 * SFREQ :]
                _, peaks = detect_beats(signal, recorder.sfreq, "ecg", PPG_SFREQ)
                ibi = np.diff(np.flatnonzero(peaks[-5 * PPG_SFREQ :]))
                self.assertAlmostEqual(60000 / ibi.mean(), bpm, delta=1.0)
                recorder.close()

    def test_triggers_reach_the_marker_stream(self):
        with FakeHub() as hub:
            markers = f"markers-{uuid.uuid4().hex[:8]}"
            recorder = LSLRecorder(
                name=hub.name, channel="ECG2", marker_stream=markers, timeout=5
            )
            found = pylsl.resolve_byprop("name", markers, timeout=5)
            inlet = pylsl.StreamInlet(found[0])
            inlet.open_stream(timeout=5)
            recorder.setup()

            recorder.readInWaiting()
            recorder.channels["Channel_0"][-1] = Trigger.LISTENING_START
            recorder.channels["Channel_0"][-1] = 7

            received = []
            deadline = time.time() + 5
            while len(received) < 2 and time.time() < deadline:
                sample, _ = inlet.pull_sample(timeout=0.5)
                if sample:
                    received.append(sample[0])
            self.assertEqual(received, ["LISTENING_START", "7"])
            # Still written to the channel, as the Nonin recording has it.
            self.assertEqual(recorder.channels["Channel_0"][-1], 7)
            recorder.close()

    def test_wait_beat_returns_on_a_new_beat(self):
        with FakeHub() as hub:
            recorder = LSLRecorder(name=hub.name, channel="ECG2", timeout=5)
            recorder.setup(read_duration=3)
            start = time.time()
            recorder.waitBeat()
            # At 72 BPM a new beat is at most 0.83 s away; detection adds some.
            self.assertLess(time.time() - start, 2.5)
            self.assertEqual(sum(recorder.peaks), 1)
            recorder.close()

    def test_save_writes_beats_and_timestamps(self):
        with FakeHub(bpm=60.0) as hub:
            recorder = LSLRecorder(name=hub.name, channel="ECG2", timeout=5)
            recorder.setup().read(duration=9)
            directory = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, directory, True)
            path = f"{directory}/ecg.txt"
            recorder.save(path)
            df = pd.read_csv(path)
            self.assertEqual(
                list(df.columns),
                [
                    "signal",
                    "peaks",
                    "instant_rr",
                    "time",
                    "lsl_time",
                    "wall_time",
                    "Channel_0",
                ],
            )
            self.assertAlmostEqual(df.peaks.sum(), len(df) / SFREQ, delta=1.5)
            self.assertAlmostEqual(df.instant_rr.median(), 1000, delta=5)
            recorder.close()


class TestSnapToQRS(unittest.TestCase):
    def test_a_late_or_early_mark_moves_to_the_r_peak(self):
        ecg = synthetic_ecg(10, 60).astype(float)
        r_peaks = np.flatnonzero(detect_beats(ecg, SFREQ, "ecg", SFREQ)[1])
        for shift in (-60, -20, 40, 90):
            for signal in (ecg, 2 * ecg.mean() - ecg):  # either polarity
                with self.subTest(shift=shift):
                    marked = np.zeros(ecg.size, dtype=bool)
                    marked[np.clip(r_peaks + shift, 0, ecg.size - 1)] = True
                    snapped = np.flatnonzero(snap_to_qrs(signal, marked, SFREQ))
                    np.testing.assert_array_equal(snapped, r_peaks)


class TestSession(unittest.TestCase):
    """A whole HRD session on ECG over LSL, as a study would run it."""

    N_TRIALS = 4
    BPM = 66.0

    @classmethod
    def setUpClass(cls):
        from cardioception._autopilot import AutoResponder
        from cardioception.HRD.parameters import getParameters
        from cardioception.HRD.task import run

        cls.tmp = tempfile.mkdtemp()
        cls.hub = FakeHub(bpm=cls.BPM, seconds=600).__enter__()
        markers = f"markers-{uuid.uuid4().hex[:8]}"
        recorder = LSLRecorder(
            name=cls.hub.name, channel="ECG2", marker_stream=markers, timeout=5
        )
        inlet = pylsl.StreamInlet(pylsl.resolve_byprop("name", markers, timeout=5)[0])
        inlet.open_stream(timeout=5)

        cls.params = getParameters(
            participant="LSL",
            session="1",
            setup="test",
            nTrials=cls.N_TRIALS,
            nBreaking=cls.N_TRIALS // 2,
            device="keyboard",
            resultPath=cls.tmp,
            seed=4242,
            recorder=recorder,
        )
        cls.params["listeningDuration"] = 3.0
        cls.params["autopilot"] = AutoResponder(cls.params["rng"], accuracy=0.8)
        try:
            run(cls.params, confidenceRating=True, runTutorial=False)
        finally:
            cls.params["win"].close()
        cls.df = pd.read_csv(cls.params["paths"].path("final"))
        cls.markers, _ = inlet.pull_chunk(timeout=1.0, max_samples=1000)
        recorder.close()

    @classmethod
    def tearDownClass(cls):
        cls.hub.__exit__(None, None, None)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_tone_matches_the_heart(self):
        intero = self.df[self.df.Modality == "Intero"]
        self.assertTrue(len(intero))
        self.assertTrue(intero.HeartRateAccepted.all())
        for bpm in intero.listenBPM:
            self.assertAlmostEqual(bpm, self.BPM, delta=1.0)

    def test_every_trial_is_marked_on_the_marker_stream(self):
        labels = [m[0] for m in self.markers]
        self.assertEqual(labels.count("TRIAL_START"), self.N_TRIALS)
        self.assertEqual(labels.count("TRIAL_STOP"), self.N_TRIALS)

    def test_the_manifest_says_what_was_recorded(self):
        import json

        with open(f"{self.params['paths'].directory}/manifest.json") as f:
            recording = json.load(f)["recording"]
        self.assertEqual(recording["stream"], self.hub.name)
        self.assertEqual(recording["channel"], "ECG2")
        self.assertEqual(recording["signal_type"], "ecg")


if __name__ == "__main__":
    unittest.main()
