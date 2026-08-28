# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Whole sessions run headlessly against the replay recorder.

Sessions are slow, so most assertions share one. Four trials gives two of each
modality and one break; listeningDuration is shortened because none of this
tests tone timing.
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
from cardioception.validate import check_trials

N_TRIALS = 4
SEED = 4242
BPM = 72.0
# The task blocks in real time while an exteroceptive tone plays. At the default
# of 5 seconds that is about 70% of a session's wall clock and none of it
# exercises anything these tests assert on.
LISTENING = 0.05

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


def run_session(
    tmp,
    device="keyboard",
    p_miss=0.0,
    seed=SEED,
    bpm=BPM,
    n_trials=N_TRIALS,
    recorder_kw=None,
    **kw,
):
    """One session, returning its parameters and its results table."""
    recorder = ReplayRecorder(bpm=bpm, realtime=False, **(recorder_kw or {}))
    params = getParameters(
        participant="HEADLESS",
        session="1",
        setup="test",
        nTrials=n_trials,
        exteroception=True,
        device=device,
        nBreaking=max(n_trials // 2, 1),
        resultPath=str(tmp),
        language="english",
        seed=seed,
        recorder=recorder,
        **kw,
    )
    params["listeningDuration"] = LISTENING
    params["recorder"] = recorder
    params["autopilot"] = AutoResponder(params["rng"], accuracy=0.8, p_miss=p_miss)
    try:
        run(params, confidenceRating=True, runTutorial=False)
    finally:
        params["win"].close()
    return params, pd.read_csv(Path(tmp, "HEADLESS1_final.txt"))


class TestReferenceSession(unittest.TestCase):
    """Assertions that can all share one clean, fully answered session."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.params, cls.df = run_session(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_session_completes_and_writes_the_expected_schema(self):
        self.assertEqual(len(self.df), N_TRIALS)
        self.assertEqual(list(self.df.columns), EXPECTED_COLUMNS)

    def test_modalities_are_balanced(self):
        self.assertEqual(
            self.df.Modality.value_counts().to_dict(),
            {"Intero": N_TRIALS // 2, "Extero": N_TRIALS // 2},
        )

    def test_behavioural_invariants_hold(self):
        expected = (self.df.listenBPM + self.df.Alpha).clip(15.0, 199.0)
        pd.testing.assert_series_equal(
            self.df.responseBPM, expected, check_names=False, check_dtype=False
        )
        answered = self.df[self.df.DecisionProvided.astype(bool)]
        self.assertTrue(
            (
                answered.ResponseCorrect.astype(bool)
                == (answered.Decision == answered.Condition)
            ).all()
        )

    def test_every_session_invariant_holds(self):
        """The same checks used to validate a real hardware session."""
        failures = [
            c
            for c in check_trials(self.df, resp_max=self.params["respMax"])
            if not c.passed
        ]
        self.assertEqual(failures, [], f"invariants broken: {failures}")

    def test_the_task_recovers_the_heart_rate_the_recorder_produced(self):
        """The whole physiology path, end to end, against a known rate."""
        observed = self.df[self.df.Modality == "Intero"].listenBPM.unique()
        self.assertEqual(list(observed), [BPM])

    def test_all_five_trigger_codes_reach_the_recorder(self):
        self.assertEqual(set(self.params["recorder"].trigger_codes), {1, 2, 3, 4, 5})

    def test_stored_posteriors_do_not_pin_the_staircase_arrays(self):
        """``_probLambda[0, :, :, 0]`` is a view onto a 40 MB array per trial."""
        stored = [
            arr
            for slices in self.params["staircaisePosteriors"].values()
            for arr in slices
        ]
        self.assertTrue(stored, "no posteriors were stored")
        for arr in stored:
            self.assertIsNone(arr.base, "posterior is a view, not a copy")

    def test_the_pickle_does_not_duplicate_the_large_artefacts(self):
        """Each of these is already written to its own file."""
        import pickle

        with open(Path(self.tmp, "HEADLESS_parameters.pickle"), "rb") as fh:
            saved = pickle.load(fh)
        for key in ("staircaisePosteriors", "signal_df", "results_df"):
            self.assertNotIn(key, saved)
        self.assertIn("seed", saved)


class TestSessionVariants(unittest.TestCase):
    """Each of these needs a configuration of its own."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_mouse_path_completes(self):
        _, df = run_session(self.tmp, device="mouse")
        self.assertEqual(len(df), N_TRIALS)

    def test_a_missed_trial_never_reaches_the_staircase(self):
        """The bug this replaces silently fabricated a "Less" response.

        ``decision`` is None on a timeout, so ``isMore = 1 if decision ==
        "More" else 0`` collapsed to 0 and the staircase was told the
        participant said "Less".
        """
        params, df = run_session(self.tmp, p_miss=1.0, onMissedTrial="skip", n_trials=2)
        self.assertEqual(int(df.DecisionProvided.astype(bool).sum()), 0)
        seen = sum(len(v) for v in params["staircaisePosteriors"].values())
        self.assertEqual(seen, 0, "a missed trial reached the staircase")

    def test_skip_mode_presents_exactly_the_planned_number_of_trials(self):
        _, df = run_session(self.tmp, p_miss=1.0, onMissedTrial="skip", n_trials=2)
        self.assertEqual(len(df), 2)

    def test_represent_mode_repeats_missed_trials_up_to_the_cap(self):
        """A participant who never responds must still reach the end."""
        _, df = run_session(
            self.tmp,
            p_miss=1.0,
            onMissedTrial="represent",
            maxRepresentations=2,
            n_trials=2,
        )
        self.assertEqual(len(df), 4)
        self.assertEqual(int(df.DecisionProvided.astype(bool).sum()), 0)

    def test_an_undetectable_signal_does_not_hang_the_session(self):
        """The HRcutOff retry path, which no test had ever executed.

        Every read gives noise with no detectable beats, so the loop can never
        accept a rate. It has to give up rather than hold the participant on
        the listening screen.
        """
        _, df = run_session(
            self.tmp,
            n_trials=2,
            recorder_kw={"artefact_every": 1},
            maxHeartRateAttempts=2,
        )
        self.assertEqual(len(df), 2)

    def test_an_unknown_setup_fails_before_the_window_opens(self):
        """It used to return a dict with no oxiTask and die inside run()."""
        with self.assertRaises(ValueError):
            getParameters(
                participant="X",
                session="1",
                setup="fMRI",
                resultPath=str(self.tmp),
                nTrials=2,
            )

    def test_same_seed_gives_the_same_design(self):
        p1, _ = run_session(self.tmp, seed=99, n_trials=2)
        p2, _ = run_session(self.tmp, seed=99, n_trials=2)
        self.assertEqual(list(p1["Modality"]), list(p2["Modality"]))
        self.assertEqual(p1["seed"], p2["seed"])


if __name__ == "__main__":
    unittest.main()
