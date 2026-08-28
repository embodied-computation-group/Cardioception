# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""A whole session, start to finish, with no human at the keyboard.

Before the autopilot existed there was no way to run either task unattended:
``run()`` blocks in ``waitInput`` and the decision phase waits on real hardware.
That is why no continuous integration job has ever run the task, and why the
response paths in ``responseDecision`` had no test coverage at all.

These are slow because the task still spends five seconds per trial reading the
simulated oximeter in real time. The replay backend removes that; until then,
mark them and keep the trial count small.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cardioception._autopilot import AutoResponder
from cardioception.devices import ReplayRecorder
from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run

N_TRIALS = 8
SEED = 4242
BPM = 72.0

EXPECTED_COLUMNS = [
    "TrialType",
    "Condition",
    "Modality",
    "StairCond",
    "Decision",
    "DecisionRT",
    "Confidence",
    "ConfidenceRT",
    "Alpha",
    "listenBPM",
    "responseBPM",
    "ResponseCorrect",
    "DecisionProvided",
    "RatingProvided",
    "nTrials",
    "EstimatedThreshold",
    "EstimatedSlope",
    "StartListening",
    "StartDecision",
    "ResponseMade",
    "RatingStart",
    "RatingEnds",
    "endTrigger",
]


def _session(tmp, device, p_miss=0.0, seed=SEED, bpm=BPM, **recorder_kw):
    recorder = ReplayRecorder(bpm=bpm, realtime=False, **recorder_kw)
    params = getParameters(
        participant="HEADLESS",
        session="1",
        setup="test",
        nTrials=N_TRIALS,
        exteroception=True,
        device=device,
        nBreaking=N_TRIALS // 2,
        resultPath=str(tmp),
        language="english",
        seed=seed,
        recorder=recorder,
    )
    params["recorder"] = recorder
    params["autopilot"] = AutoResponder(params["rng"], accuracy=0.8, p_miss=p_miss)
    try:
        run(params, confidenceRating=True, runTutorial=False)
    finally:
        params["win"].close()
    return params, pd.read_csv(Path(tmp, "HEADLESS1_final.txt"))


class TestHeadlessSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_keyboard_session_completes_and_writes_the_expected_schema(self):
        _, df = _session(self.tmp, "keyboard")
        self.assertEqual(len(df), N_TRIALS)
        self.assertEqual(list(df.columns), EXPECTED_COLUMNS)
        self.assertEqual(
            df.Modality.value_counts().to_dict(),
            {"Intero": N_TRIALS // 2, "Extero": N_TRIALS // 2},
        )

    def test_mouse_session_completes(self):
        _, df = _session(self.tmp, "mouse")
        self.assertEqual(len(df), N_TRIALS)

    def test_missed_trials_do_not_crash_the_session(self):
        _, df = _session(self.tmp, "mouse", p_miss=0.4)
        self.assertEqual(len(df), N_TRIALS)
        # Whatever the miss rate, every trial is still written and flagged.
        self.assertTrue(df.DecisionProvided.isin([True, False]).all())

    def test_behavioural_invariants_hold(self):
        _, df = _session(self.tmp, "keyboard")
        expected = (df.listenBPM + df.Alpha).clip(15.0, 199.0)
        pd.testing.assert_series_equal(
            df.responseBPM, expected, check_names=False, check_dtype=False
        )
        self.assertTrue(
            (df.Condition == df.Alpha.map(lambda a: "Less" if a < 0 else "More")).all()
        )
        answered = df[df.DecisionProvided.astype(bool)]
        self.assertTrue(
            (
                answered.ResponseCorrect.astype(bool)
                == (answered.Decision == answered.Condition)
            ).all()
        )

    def test_the_task_recovers_the_heart_rate_the_recorder_produced(self):
        """The whole physiology path, end to end, against a known rate.

        The recorder synthesises a pulse at an exact BPM, so this asserts that
        the raw signal, the peak detection and the task's own averaging agree
        with the rate that went in. Nothing previously tested this.
        """
        _, df = _session(self.tmp, "keyboard", bpm=72.0)
        observed = df[df.Modality == "Intero"].listenBPM.unique()
        self.assertEqual(list(observed), [72.0])

    def test_all_five_trigger_codes_reach_the_recorder(self):
        params, _ = _session(self.tmp, "keyboard")
        self.assertEqual(set(params["recorder"].trigger_codes), {1, 2, 3, 4, 5})

    def test_the_recording_is_saved_at_breaks_and_at_the_end(self):
        params, _ = _session(self.tmp, "keyboard")
        # One save at the single break, one at the end of the session.
        self.assertEqual(params["recorder"].n_saves, 2)

    def test_same_seed_gives_the_same_design(self):
        p1, _ = _session(self.tmp, "keyboard", seed=99)
        first = list(p1["Modality"]), list(p1["staircaseType"])
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp = tempfile.mkdtemp()
        p2, _ = _session(self.tmp, "keyboard", seed=99)
        self.assertEqual(first, (list(p2["Modality"]), list(p2["staircaseType"])))
        self.assertEqual(p1["seed"], p2["seed"])


if __name__ == "__main__":
    unittest.main()
