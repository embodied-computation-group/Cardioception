# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""An HSD session on a synthetic ECG streamed over LSL on this machine.

The ECG of ``tests/test_lsl.py`` is streamed at 1000 Hz by its ``FakeHub``,
read through :class:`~cardioception.devices.LSLRecorder`, and its R-waves are
found online by the shared
:class:`~cardioception.devices.beat_source.LSLBeatSource`, the beat source a
behavioral session uses. The tone player is a fake that reports each tone as
starting 2 ms after its target and plays nothing, so the test is silent. It
checks what the hardware dry run will check, against a signal whose R-waves
are known: that the realized delays, measured against the stamped R-waves and
corrected by the latency bias, are the requested ones.

Needs pylsl, and skips without it. Runs in real time, about half a minute.
"""

import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pylsl = pytest.importorskip("pylsl")

from test_hsd_headless import SilentPlayer  # noqa: E402
from test_lsl import SFREQ, FakeHub  # noqa: E402

import cardioception.HSD.task as hsd  # noqa: E402
from cardioception.devices import LSLRecorder  # noqa: E402
from cardioception.devices.beat_source import LSLBeatSource  # noqa: E402
from cardioception.HSD._autopilot import HSDAutopilot  # noqa: E402
from cardioception.HSD.config import TaskConfig  # noqa: E402
from cardioception.HSD.parameters import getParameters  # noqa: E402
from cardioception.HSD.simulate import Observer  # noqa: E402

BPM = 72.0
N_TRIALS = 4
#: Where ``synthetic_ecg`` puts the R peak, as a fraction of the period.
R_PHASE = 0.32
#: Seconds the fake player reports each onset after its target, so that the
#: delivery check measures the onset rather than repeating the target.
ONSET_ERROR = 0.002
#: The tolerance of the hardware dry run, in ms.
TOLERANCE_MS = 5.0
#: Seconds by which LSL's dejitter may put a sample's stamp after the clock
#: time it was pulled at.
DEJITTER = 0.002


class TappedInlet:
    """The recorder's inlet, keeping the ``nSeq`` and stamp of every sample.

    So the test can find the true R peak behind each detected one, while the
    shared beat source reads the stream exactly as it would in a session.
    """

    def __init__(self, inlet):
        self.inlet = inlet
        self.seq = []
        self.stamps = []

    def flush(self):
        self.seq, self.stamps = [], []
        return self.inlet.flush()

    def pull_chunk(self, *args, **kwargs):
        samples, stamps = self.inlet.pull_chunk(*args, **kwargs)
        self.seq.extend(int(s[0]) for s in samples)
        self.stamps.extend(stamps)
        return samples, stamps


class TappedRecorder:
    """What LSLBeatSource reads of a recorder, with the inlet tapped."""

    def __init__(self, recorder):
        self.inlet = TappedInlet(recorder.inlet)
        self.channel = recorder.channel
        self.sfreq = recorder.sfreq


class TestHSDOverLSL(unittest.TestCase):
    """Four trials on a 72 bpm synthetic ECG, shared by the assertions."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.hub = FakeHub(bpm=BPM, seconds=90.0).__enter__()
        markers = f"hsd-markers-{uuid.uuid4().hex[:8]}"
        try:
            recorder = LSLRecorder(
                name=cls.hub.name,
                channel="ECG2",
                signal_type="ecg",
                marker_stream=markers,
                timeout=10,
            )
        except RuntimeError as error:
            cls.hub.__exit__(None, None, None)
            raise unittest.SkipTest(f"LSL stream not resolved: {error}")
        found = pylsl.resolve_byprop("name", markers, timeout=10)
        if not found:
            recorder.close()
            cls.hub.__exit__(None, None, None)
            raise unittest.SkipTest("marker stream not resolved within 10 s")
        cls.marker_inlet = pylsl.StreamInlet(found[0])
        cls.marker_inlet.open_stream(timeout=10)

        clock = pylsl.local_clock
        cls.tap = TappedRecorder(recorder)
        cls.source = LSLBeatSource(cls.tap)
        params = getParameters(
            participant="LSL",
            session="1",
            setup="test",
            axis="absolute",
            nTrials=N_TRIALS,
            fullscr=False,
            nBreaking=0,
            resultPath=cls.tmp,
            seed=99,
            recorder=recorder,
            beat_source=cls.source,
            tone_player=SilentPlayer(clock, onset_error=ONSET_ERROR),
            config=TaskConfig(minTrials=N_TRIALS),
            clock=clock,
        )
        params["autopilot"] = HSDAutopilot(
            params["rng"], Observer(mu=250.0, sigma=80.0, floor=0.05, peak=0.95)
        )
        try:
            hsd.run(params, confidenceRating=True, runTutorial=False)
        finally:
            params["win"].close()
            cls.markers = []
            while True:
                chunk, _ = cls.marker_inlet.pull_chunk(timeout=1.0)
                if not chunk:
                    break
                cls.markers.extend(json.loads(sample[0]) for sample in chunk)
            recorder.close()
            cls.hub.__exit__(None, None, None)
        cls.params = params
        cls.df = pd.read_csv(params["paths"].path("final"))
        cls.tones = pd.read_csv(params["paths"].path("tones"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_trial_delivered_a_train(self):
        """The online detector found enough beats for every train."""
        self.assertEqual(len(self.df), N_TRIALS)
        self.assertTrue((self.df.nDelivered > 0).all())

    def test_detected_r_waves_are_the_true_ones(self):
        """Each tone's R-wave is within 5 ms of a true R peak of the ECG."""
        stamps = np.asarray(self.tap.inlet.stamps)
        seq = np.asarray(self.tap.inlet.seq)
        samples_per_beat = 60.0 / BPM * SFREQ
        played = self.tones[~self.tones.skipped.astype(bool)]
        self.assertGreater(len(played), 0)
        for tone in played.itertuples():
            i = int(np.argmin(np.abs(stamps - tone.r_time)))
            self.assertAlmostEqual(stamps[i], tone.r_time, places=9)
            k = round(seq[i] / samples_per_beat - R_PHASE)
            true_index = (k + R_PHASE) * samples_per_beat
            self.assertLessEqual(abs(seq[i] - true_index), 5)

    def test_realized_delays_match_the_requested_ones(self):
        """Against the stamped true R peak, each tone lands within 5 ms.

        Within 5 ms plus the 2 ms the fake player reports its onsets late,
        once the latency bias the tone was scheduled early by is added back.
        """
        bias_ms = self.params["latencyBias"] * 1000.0
        stamps = np.asarray(self.tap.inlet.stamps)
        seq = np.asarray(self.tap.inlet.seq)
        samples_per_beat = 60.0 / BPM * SFREQ
        requested = self.df.set_index("Trial").RequestedDelay
        played = self.tones[~self.tones.skipped.astype(bool)]
        for tone in played.itertuples():
            i = int(np.argmin(np.abs(stamps - tone.r_time)))
            k = round(seq[i] / samples_per_beat - R_PHASE)
            j = i + int(round((k + R_PHASE) * samples_per_beat)) - seq[i]
            allowed = TOLERANCE_MS + ONSET_ERROR * 1000.0
            realized_ms = (tone.onset - stamps[j]) * 1000.0 + bias_ms
            self.assertLess(abs(realized_ms - requested.loc[tone.Trial]), allowed)
            # And against the R-wave the detector stamped.
            self.assertLess(
                abs(tone.realized * 1000.0 + bias_ms - requested.loc[tone.Trial]),
                allowed,
            )
            self.assertAlmostEqual(tone.onset - tone.target, ONSET_ERROR, places=9)

    def test_the_marker_stream_received_the_tones(self):
        """Every delivered tone has a tone_onset marker on the LSL outlet."""
        kinds = [m["kind"] for m in self.markers]
        onsets = [m for m in self.markers if m["kind"] == "tone_onset"]
        self.assertEqual(len(onsets), int(self.df.nDelivered.sum()))
        self.assertIn("tone_scheduled", kinds)
        self.assertIn("beat", kinds)
        triggers = [m["name"] for m in self.markers if m["kind"] == "trigger"]
        self.assertEqual(triggers.count("TRIAL_START"), N_TRIALS)

    def test_the_manifest_describes_the_recording(self):
        """The LSL recorder's description reaches the manifest."""
        manifest = json.loads(
            open(
                f"{self.params['paths'].directory}/manifest.json", encoding="utf-8"
            ).read()
        )
        self.assertEqual(manifest["recording"]["recorder"], "lsl")
        self.assertEqual(manifest["recording"]["channel"], "ECG2")
        self.assertEqual(manifest["clock"], "pylsl.local_clock")

    def test_no_empty_recording_file_is_written(self):
        """The beat source reads the inlet, so the ECG lives in the XDF only."""
        recording = self.params["paths"].path("recording")
        self.assertFalse(Path(recording).exists())

    def test_beat_markers_carry_the_commit_time(self):
        """The dry-run report reads the detection lag from commit_time."""
        beats = [m for m in self.markers if m["kind"] == "beat"]
        self.assertGreater(len(beats), 0)
        for beat in beats:
            # The stamp of the sample the detector committed on, which comes
            # after the R peak and no later than the poll that returned it,
            # give or take what LSL's dejitter moves a stamp (a fraction of a
            # millisecond here).
            self.assertGreaterEqual(beat["commit_time"], beat["r_time"])
            self.assertLessEqual(beat["commit_time"], beat["seen_time"] + DEJITTER)
        scheduled = [m for m in self.markers if m["kind"] == "tone_scheduled"]
        self.assertGreater(len(scheduled), 0)
        for tone in scheduled:
            # Beat known to tone scheduled: the poll and the loop, not the
            # detector, so well under the 50 ms audio lead.
            self.assertGreaterEqual(tone["latency"], -DEJITTER)
            self.assertLess(tone["latency"], 0.05)
        onsets = [m for m in self.markers if m["kind"] == "tone_onset"]
        for onset in onsets:
            self.assertEqual(onset["anchor"], "real")
            self.assertIn("phase_deg", onset)
            self.assertIn("delay_ms", onset)


if __name__ == "__main__":
    unittest.main()
