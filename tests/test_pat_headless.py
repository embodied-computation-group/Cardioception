# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Whole PAT sessions, run headlessly against a virtual heart.

The beat source is :class:`cardioception.devices.beat_source.VirtualBeatSource`
(as an ECG for the interoceptive session, and as the vibration's heart for the
exteroceptive one) and the tone player reports each sound as starting exactly
when it was due, both on the LSL clock the engine reads. Nothing here touches
an audio device: there is no ``psychopy.sound`` and no PsychPortAudio. A small
PsychoPy window opens, as for the HSD's headless sessions.

A :class:`cardioception.PAT._autopilot.PATAutopilot` turns the dial, presses
and rates. Sessions run in real time, two or three seconds a trial, so the
assertions share one session per class.
"""

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import cardioception.PAT.task as pat
from cardioception._log import start_session_log
from cardioception.devices.beat_source import VirtualBeatSource, default_clock
from cardioception.PAT._autopilot import PATAutopilot
from cardioception.PAT.parameters import EVENTS, getParameters
from cardioception.PAT.scoring import consistency_grid
from cardioception.PAT.task import FINAL_COLUMNS, TONE_COLUMNS, TUTORIAL_TRIAL

SEED = 314
TARGET = 120.0
PERIOD = 0.8


class Heart(VirtualBeatSource):
    """A virtual heart that the engine takes for an ECG: tones, no vibrations."""

    virtual = False


class SilentPlayer:
    """Reports every sound as starting when it was due, and plays nothing."""

    def __init__(self, clock):
        self.clock = clock
        self._waiting = {}
        self._handle = 0

    def schedule(self, when, kind="tone"):
        self._handle += 1
        self._waiting[self._handle] = when
        return self._handle

    def poll_onsets(self):
        now = self.clock()
        done = [(h, t) for h, t in self._waiting.items() if now >= t]
        for h, _ in done:
            del self._waiting[h]
        return done

    def close(self):
        pass


def counters():
    """One counting callback per PAT event."""
    counts = {event: 0 for event in EVENTS}

    def make(event):
        def callback():
            counts[event] += 1

        return callback

    return counts, {event: make(event) for event in EVENTS}


def run_session(tmp, extero=False, mode="relative", n_trials=4, n_practice=2):
    """One session on the virtual heart; returns what it produced."""
    clock = default_clock()
    counts, triggers = counters()
    params = getParameters(
        participant="HEADLESS",
        session="extero" if extero else mode,
        mode=mode,
        nTrials=n_trials,
        nPractice=n_practice,
        fullscr=False,
        resultPath=str(tmp),
        seed=SEED,
        extero=extero,
        markerStream=None,
        triggers=triggers,
        beat_source=None if extero else Heart(PERIOD, clock=clock, lead_in=0.2),
        tone_player=SilentPlayer(clock),
    )
    params["minTrialTime"] = 1.0
    params["tutorialListenTones"] = 2
    pilot = PATAutopilot(params["rng"], target=TARGET, spread=5.0)
    params["autopilot"] = pilot
    try:
        pat.run(params, runTutorial=not extero, confidenceRating=True)
    finally:
        params["win"].close()
        params["engine"].close()
        # Release the session log, so the run directory can be removed.
        start_session_log(None)
    paths = params["paths"]
    final = pd.read_csv(paths.path("final"), sep="\t")
    tones = pd.read_csv(paths.path("tones"), sep="\t")
    return params, pilot, counts, final, tones


def _circular(a, b):
    return np.abs((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0)


class TestRelativeSession(unittest.TestCase):
    """The interoceptive task in relative mode, tutorial included."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.params, cls.pilot, cls.counts, cls.df, cls.tones = run_session(cls.tmp)
        cls.paths = cls.params["paths"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_final_has_the_pinned_columns(self):
        self.assertEqual(list(self.df.columns), FINAL_COLUMNS)

    def test_one_row_per_trial(self):
        self.assertEqual(list(self.df.Trial), list(range(1, 7)))
        self.assertEqual(list(self.df.Block), ["practice"] * 2 + ["main"] * 4)
        self.assertEqual(
            list(self.df.StartPhaseDeg),
            self.params["startPhasePractice"] + self.params["startPhaseMain"],
        )
        self.assertFalse(self.df.Extero.astype(bool).any())
        self.assertTrue((self.df.Mode == "relative").all())

    def test_the_dial_stops_at_the_aim(self):
        """Within half a notch of each trial's aim, whatever the start phase."""
        aims = {
            e["trial"]: e["aim"]
            for e in self.pilot.log
            if e["event"] == "trial" and e["trial"] != TUTORIAL_TRIAL
        }
        chosen = self.df.set_index("Trial").ChosenPhaseDeg
        error = _circular(chosen.loc[list(aims)], list(aims.values()))
        self.assertTrue((error <= self.params["dialGainDeg"] / 2 + 1e-6).all(), error)

    def test_the_periods_are_the_heart_s(self):
        np.testing.assert_allclose(self.df.AnticipatedPeriodMs, PERIOD * 1000)
        np.testing.assert_allclose(self.df.ObservedPeriodMs, PERIOD * 1000)
        delay = self.df.ChosenPhaseDeg / 360 * PERIOD * 1000
        np.testing.assert_allclose(self.df.ChosenDelayMs, delay, atol=1e-6)

    def test_confidence_lies_on_the_scale(self):
        self.assertTrue(self.df.Confidence.between(1, 10).all())
        self.assertTrue((self.df.Confidence == self.df.Confidence.round()).all())
        np.testing.assert_allclose(self.df.ConfidenceUnit, (self.df.Confidence - 1) / 9)
        self.assertTrue((self.df.ConfidenceScale == "discrete").all())
        self.assertTrue((self.df.Device == "keyboard").all())

    def test_every_trial_has_its_tones(self):
        self.assertEqual(list(self.tones.columns), TONE_COLUMNS)
        self.assertEqual(set(self.tones.Trial), set(range(1, 7)))
        self.assertNotIn(TUTORIAL_TRIAL, set(self.tones.Trial))
        self.assertEqual(set(self.tones.Kind), {"tone"})
        self.assertTrue(self.tones.Onset.notna().all())
        self.assertTrue(set(self.tones.Anchor) <= {"real", "predicted"})
        played = self.tones.groupby("Trial").size()
        counted = self.df.set_index("Trial")[["nTonesReal", "nTonesPredicted"]]
        np.testing.assert_array_equal(played, counted.sum(axis=1))

    def test_every_event_fires_once_per_trial(self):
        self.assertEqual(self.counts, {event: 6 for event in EVENTS})

    def test_a_consistent_participant_scores_above_chance(self):
        grid = consistency_grid(self.df, n_sim=2000)
        cell = grid[
            (grid.mapping == "variable")
            & (grid.period == "anticipated")
            & (grid.weighting == "none")
        ].iloc[0]
        self.assertEqual(cell.n_trials, 4)
        self.assertGreater(cell.score, 0.95)

    def test_the_manifest_and_the_log(self):
        directory = Path(self.paths.directory)
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(manifest["task"], "PAT")
        self.assertEqual(manifest["seed"], SEED)
        self.assertEqual(manifest["mode"], "relative")
        self.assertIs(manifest["extero"], False)
        self.assertEqual(manifest["beat_source"], "Heart")
        self.assertEqual(manifest["tone_player"], "SilentPlayer")
        self.assertEqual(manifest["confidence"]["ConfidenceHigh"], 10)
        log = (directory / "session.log").read_text(encoding="utf-8")
        self.assertIn("main trial 6", log)

    def test_the_parameters_file_records_the_seed(self):
        saved = pd.read_csv(self.paths.path("parameters"), sep="\t")
        saved = saved.set_index("Parameter")["Value"]
        self.assertEqual(saved["seed"], str(SEED))
        for key in ("engine", "win", "rng", "autopilot", "triggers"):
            self.assertNotIn(key, saved.index)


class TestExteroSession(unittest.TestCase):
    """The exteroceptive task in absolute mode, on the simulated heart."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.params, cls.pilot, cls.counts, cls.df, cls.tones = run_session(
            cls.tmp, extero=True, mode="absolute", n_trials=3, n_practice=0
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_rows_are_exteroceptive(self):
        self.assertEqual(list(self.df.Trial), [1, 2, 3])
        self.assertTrue(self.df.Extero.astype(bool).all())
        self.assertTrue((self.df.Mode == "absolute").all())

    def test_vibrations_and_tones(self):
        self.assertEqual(set(self.tones.Kind), {"tone", "vibration"})
        vibrations = self.tones[self.tones.Kind == "vibration"]
        self.assertEqual(set(vibrations.Anchor), {"virtual"})
        self.assertTrue(self.tones.Onset.notna().all())

    def test_the_simulated_heart_varies(self):
        periods = self.df.AnticipatedPeriodMs
        self.assertTrue(periods.between(550, 1500).all())
        self.assertTrue(math.isfinite(periods.std()))

    def test_the_dial_stops_near_the_aim(self):
        """Absolute mode turns in ms, so a notch is 25 ms of a varying period."""
        aims = [e["aim"] for e in self.pilot.log if e["event"] == "trial"]
        error = _circular(self.df.ChosenPhaseDeg, aims)
        self.assertTrue((error < 25.0).all(), error)

    def test_the_manifest_says_exteroceptive(self):
        directory = Path(self.params["paths"].directory)
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertIs(manifest["extero"], True)
        self.assertEqual(manifest["beat_source"], "VirtualBeatSource")
        self.assertEqual(self.counts["trialStart"], 3)


if __name__ == "__main__":
    unittest.main()
