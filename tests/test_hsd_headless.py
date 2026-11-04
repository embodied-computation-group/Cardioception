# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Whole HSD sessions, run headlessly against a virtual heart.

The beat source produces a beat every ``PERIOD`` seconds of real time and the
tone player reports each tone as starting exactly when it was asked to, both
on ``time.perf_counter``, which is also passed to ``getParameters`` as the
session clock. Nothing here touches an audio device: there is no
``psychopy.sound`` and no PsychPortAudio. A small PsychoPy window opens, as
``setup="test"`` does for the HRD.

Sessions run in real time, about five seconds a trial, so most assertions
share one.
"""

import json
import math
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import cardioception.HSD.task as hsd
from cardioception.HSD._autopilot import HSDAutopilot
from cardioception.HSD._constants import EVENTS
from cardioception.HSD._stimulus import ToneRecord, TrainResult
from cardioception.HSD.config import TaskConfig
from cardioception.HSD.parameters import getParameters
from cardioception.HSD.simulate import Observer

SEED = 2718
PERIOD = 0.9
N_TRIALS = 6
MIN_TRIALS = 3
# The convergence session: a sharp observer, and a credible-interval width
# that this seed reaches after more than CONVERGE_MIN trials and before
# CONVERGE_MAX. The interval of mu is conditioned on a rise across the delays
# presented, which already rules out locations no presented delay could show,
# so it starts near 540 ms after two trials; 450 ms needs real information.
# This seed converges after 8 trials, at 400 ms.
CONVERGE_MIN = 2
CONVERGE_MAX = 10
CONVERGE_WIDTH = 450.0

EXPECTED_COLUMNS = [
    "Trial",
    "Axis",
    "RequestedDelay",
    "RealizedDelay",
    "RealizedCorrected",
    "nDelivered",
    "nSkipped",
    "Aborted",
    "AbortReason",
    "Explored",
    "Decision",
    "DecisionRT",
    "Confidence",
    "ConfidenceRT",
    "ConfidenceUnit",
    "Device",
    "ConfidenceScale",
    "ConfidenceLow",
    "ConfidenceHigh",
    "ConfidenceGranularity",
    "ConfidenceLevels",
    "ConfidenceSigned",
    "DecisionProvided",
    "RatingProvided",
    "nTrials",
    "MuMean",
    "MuMedian",
    "MuCILow",
    "MuCIHigh",
    "SigmaMean",
    "SigmaMedian",
    "SigmaCILow",
    "SigmaCIHigh",
    "MuConditional",
    "FloorMean",
    "PeakMean",
    "DetectionEvidence",
    "DetectionBF",
    "PeriodMean",
    "nTrains",
    "EndReason",
    "nBeatsSeen",
    "DroppedFrames",
    "StartTrigger",
    "TrainStart",
    "TrainStop",
    "DecisionStart",
    "ResponseMade",
    "RatingStart",
    "RatingEnds",
    "endTrigger",
]


class Beat:
    def __init__(self, r_time, period):
        self.r_time = r_time
        self.period = period


class VirtualHeart:
    """A beat every ``period`` seconds of ``clock``, known ``latency`` after it.

    Satisfies :class:`cardioception.HSD._stimulus.BeatSource`. The clock must
    be the session's: the scheduler compares beat times with it.
    """

    def __init__(self, clock, period=PERIOD, latency=0.02):
        self.clock = clock
        self._period = period
        self.latency = latency
        self._next_r = None

    @property
    def period(self):
        return self._period if self._next_r is not None else None

    def start(self):
        if self._next_r is None:
            self._next_r = self.clock() + 0.1

    def stop(self):
        self._next_r = None

    def poll(self):
        if self._next_r is None:
            return []
        beats, now = [], self.clock()
        while self._next_r + self.latency <= now:
            beats.append(Beat(self._next_r, self._period))
            self._next_r += self._period
        return beats


class SilentPlayer:
    """Reports every tone as starting ``onset_error`` s after it was due.

    Satisfies :class:`cardioception.HSD._stimulus.TonePlayer` and plays
    nothing. Takes the session clock, like the beat source.
    """

    def __init__(self, clock, onset_error=0.0):
        self.clock = clock
        self.onset_error = onset_error
        self._waiting = {}
        self._stopped = []
        self._handle = 0
        self.scheduled = {}

    def schedule(self, when, kind="tone"):
        self._handle += 1
        self._waiting[self._handle] = when + self.onset_error
        self.scheduled[self._handle] = when
        return self._handle

    def poll_onsets(self):
        now = self.clock()
        done = [(h, t) for h, t in self._waiting.items() if now >= t]
        for h, _ in done:
            del self._waiting[h]
        done, self._stopped = self._stopped + done, []
        return done

    @property
    def busy(self):
        return bool(self._waiting)

    def stop_all(self):
        self._stopped += [(h, math.nan) for h in self._waiting]
        self._waiting = {}

    def close(self):
        pass

    def describe(self):
        return {"backend": "silent test player"}


def counters():
    """One counting callback per HSD event."""
    counts = {event: 0 for event in EVENTS}

    def make(event):
        def callback():
            counts[event] += 1

        return callback

    return counts, {event: make(event) for event in EVENTS}


def run_session(
    tmp,
    axis="absolute",
    observer=None,
    n_trials=N_TRIALS,
    min_trials=MIN_TRIALS,
    period=PERIOD,
    triggers=None,
    run_tutorial=False,
    n_breaking=3,
    autopilot=HSDAutopilot,
    **config,
):
    """One session on the virtual heart; returns its parameters and results."""
    clock = time.perf_counter
    if observer is None:
        observer = Observer(mu=250.0, sigma=80.0, floor=0.05, peak=0.95)
    params = getParameters(
        participant="HEADLESS",
        session=axis,
        setup="test",
        axis=axis,
        nTrials=n_trials,
        fullscr=False,
        nBreaking=n_breaking,
        resultPath=str(tmp),
        seed=SEED,
        beat_source=VirtualHeart(clock, period=period),
        tone_player=SilentPlayer(clock),
        triggers=triggers,
        config=TaskConfig(minTrials=min_trials, **config),
        clock=clock,
    )
    params["autopilot"] = autopilot(params["rng"], observer)
    try:
        hsd.run(params, confidenceRating=True, runTutorial=run_tutorial)
    finally:
        params["win"].close()
    return params, pd.read_csv(params["paths"].path("final"))


class TestAbsoluteSession(unittest.TestCase):
    """One session on the absolute axis, shared by the assertions below."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.counts, triggers = counters()
        cls.params, cls.df = run_session(cls.tmp, triggers=triggers)
        cls.paths = cls.params["paths"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_final_has_the_pinned_columns(self):
        """The column names and their order are those of HSDTrialOutcome.row."""
        self.assertEqual(list(self.df.columns), EXPECTED_COLUMNS)

    def test_one_row_per_trial_within_the_stopping_rule(self):
        """At least minTrials rows, at most nTrials, each a delivered train."""
        self.assertGreaterEqual(len(self.df), MIN_TRIALS)
        self.assertLessEqual(len(self.df), N_TRIALS)
        self.assertEqual(list(self.df.Trial), list(range(len(self.df))))
        self.assertTrue((self.df.nDelivered > 0).all())
        self.assertTrue(self.df.DecisionProvided.all())
        self.assertTrue((self.df.Axis == "absolute").all())

    def test_decisions_are_the_two_labels(self):
        """Every decision is written as its label, not as the key pressed."""
        self.assertTrue(self.df.Decision.isin(["Synchronous", "NotSynchronous"]).all())

    def test_confidence_lies_on_the_scale(self):
        """Ratings stay within the scale written next to them."""
        rated = self.df[self.df.RatingProvided.astype(bool)]
        self.assertGreater(len(rated), 0)
        self.assertTrue((rated.Confidence >= rated.ConfidenceLow).all())
        self.assertTrue((rated.Confidence <= rated.ConfidenceHigh).all())
        self.assertTrue(rated.ConfidenceUnit.between(0, 1).all())

    def test_realized_delays_match_the_requested_ones(self):
        """With onsets on target, the physical delay is the requested one.

        Each tone is scheduled the latency bias early, so the delay measured
        against the stamped R-wave is the bias short of the request, and the
        corrected value, which the engine sees, adds it back.
        """
        bias = self.params["latencyBias"] * 1000.0
        self.assertEqual(bias, 50.0)
        delivered = self.df[self.df.nDelivered > 0]
        error = (delivered.RealizedCorrected - delivered.RequestedDelay).abs()
        self.assertTrue((error < 5.0).all(), error.tolist())
        np.testing.assert_allclose(
            delivered.RealizedDelay, delivered.RequestedDelay - bias, atol=1e-6
        )
        # The 130 ms physical floor and the 600 ms top candidate.
        self.assertTrue(delivered.RequestedDelay.between(130, 600).all())

    def test_the_posterior_summary_is_written(self):
        """MuMean is present and finite on every row."""
        self.assertTrue(np.isfinite(self.df.MuMean).all())
        self.assertTrue(np.isfinite(self.df.SigmaMean).all())

    def test_tones_and_beats_files_match_the_rows(self):
        """One tones row per beat a tone was tried on, one beats row per beat."""
        tones = pd.read_csv(self.paths.path("tones"))
        beats = pd.read_csv(self.paths.path("beats"))
        # The row counts the train it kept, which is the last attempt.
        last = tones.Attempt == tones.groupby("Trial").Attempt.transform("max")
        self.assertEqual(
            int(last.sum()), int((self.df.nDelivered + self.df.nSkipped).sum())
        )
        # Beats after the last train belong to no trial.
        filed = beats[beats.Trial.notna()]
        self.assertEqual(len(filed), int(self.df.nBeatsSeen.sum()))
        # The beats polled between trains are kept, not thrown away.
        self.assertGreater(int((beats.status == "between").sum()), 0)
        for column in ("Trial", "index", "r_time", "target", "onset", "realized"):
            self.assertIn(column, tones.columns)
        played = tones[~tones.skipped.astype(bool)]
        np.testing.assert_allclose(played.onset, played.target, atol=1e-9)

    def test_posterior_file_has_one_grid_per_trial(self):
        """The .npy stacks the posterior after each trial."""
        posterior = np.load(self.paths.path("posterior", ext="npy"))
        engine = self.params["engine"]
        self.assertEqual(posterior.shape, (len(self.df), *engine.shape))
        np.testing.assert_allclose(posterior.reshape(len(self.df), -1).sum(1), 1.0)

    def test_engine_state_is_saved(self):
        """The engine JSON loads and holds one history entry per decision."""
        state = json.loads(Path(self.paths.path("engine", ext="json")).read_text())
        self.assertEqual(len(state["history"]), int(self.df.DecisionProvided.sum()))
        self.assertEqual(self.df.nTrials.iloc[-1], len(state["history"]))

    def test_manifest_names_the_task_and_axis(self):
        """manifest.json records the task, the axis and the clock."""
        manifest = json.loads(
            (Path(self.paths.directory) / "manifest.json").read_text()
        )
        self.assertEqual(manifest["task"], "HSD")
        self.assertEqual(manifest["axis"], "absolute")
        self.assertEqual(manifest["config"]["axis"], "absolute")
        self.assertEqual(manifest["config"]["maxTrials"], N_TRIALS)
        self.assertEqual(manifest["clock"], "time.perf_counter")
        self.assertEqual(manifest["seed"], SEED)
        self.assertEqual(manifest["tone_player"], {"backend": "silent test player"})

    def test_every_event_fires(self):
        """Each HSD event fires once per trial that reached it."""
        n = len(self.df)
        for event in EVENTS:
            self.assertGreater(self.counts[event], 0, event)
        for event in ("trialStart", "trialStop", "trainStart", "trainStop"):
            self.assertEqual(self.counts[event], n, event)
        self.assertEqual(self.counts["confidenceStart"], self.counts["confidenceStop"])

    def test_the_parameters_pickle_is_written(self):
        """The pickle exists and leaves out the live objects."""
        import pickle

        with open(self.paths.path("parameters", ext="pickle"), "rb") as handle:
            saved = pickle.load(handle)
        for key in ("win", "engine", "beatSource", "tonePlayer", "clock"):
            self.assertNotIn(key, saved)
        self.assertEqual(saved["axis"], "absolute")


class TestPhaseSession(unittest.TestCase):
    """A short session on the phase axis."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        observer = Observer(mu=0.3, sigma=0.1, floor=0.05, peak=0.95)
        cls.params, cls.df = run_session(
            cls.tmp,
            axis="phase",
            observer=observer,
            n_trials=4,
            min_trials=2,
            period=0.6,
            n_breaking=0,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_delays_are_fractions_of_the_period(self):
        """Requested and realized delays lie strictly between 0 and 1."""
        self.assertGreaterEqual(len(self.df), 2)
        self.assertTrue((self.df.Axis == "phase").all())
        for column in ("RequestedDelay", "RealizedDelay", "RealizedCorrected"):
            values = self.df[column]
            self.assertTrue(((values > 0) & (values < 1)).all(), column)
        self.assertTrue(
            (self.df.RequestedDelay <= self.params["maxPeriodFraction"]).all()
        )
        np.testing.assert_allclose(self.df.PeriodMean, 0.6, atol=1e-9)

    def test_manifest_records_the_phase_axis(self):
        """The axis reaches the manifest."""
        manifest = json.loads(
            (Path(self.params["paths"].directory) / "manifest.json").read_text()
        )
        self.assertEqual(manifest["axis"], "phase")


class SlowRater(HSDAutopilot):
    """Takes three seconds over every confidence rating."""

    def rate(self, *args, **kwargs):
        time.sleep(3.0)
        return super().rate(*args, **kwargs)


class TestBeatsBetweenTrains(unittest.TestCase):
    """A rating gap between trains loses no beat and no RR interval."""

    def test_a_rating_gap_keeps_the_rr_and_the_beats(self):
        """After a 3 s gap, the next train's first beat has an RR of one period."""
        tmp = tempfile.mkdtemp()
        try:
            params, df = run_session(
                tmp,
                n_trials=2,
                min_trials=2,
                period=0.6,
                n_breaking=0,
                autopilot=SlowRater,
            )
            beats = pd.read_csv(params["paths"].path("beats"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        second = beats[beats.Trial == 1]
        between = second[second.status == "between"]
        # Three seconds at 0.6 s a beat.
        self.assertGreaterEqual(len(between), 4)
        np.testing.assert_allclose(between.rr, 0.6, atol=1e-6)
        first = second[second.status != "between"].iloc[0]
        self.assertAlmostEqual(first.rr, 0.6, places=6)
        # Every beat is there once: r_times are unique and evenly spaced.
        r_times = np.sort(beats.r_time.to_numpy())
        np.testing.assert_allclose(np.diff(r_times), 0.6, atol=1e-6)


class TestStoppingRule(unittest.TestCase):
    """The session stops on convergence, after minTrials and before maxTrials."""

    def test_a_sharp_observer_converges_early(self):
        """With a generous ciWidth the row count lies strictly between the two."""
        tmp = tempfile.mkdtemp()
        try:
            params, df = run_session(
                tmp,
                observer=Observer(mu=250.0, sigma=40.0, floor=0.02, peak=0.98),
                n_trials=CONVERGE_MAX,
                min_trials=CONVERGE_MIN,
                period=0.6,
                n_breaking=0,
                ciWidth=CONVERGE_WIDTH,
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertGreater(len(df), CONVERGE_MIN)
        self.assertLess(len(df), CONVERGE_MAX)
        width = df.MuCIHigh - df.MuCILow
        self.assertLessEqual(width.iloc[-1], CONVERGE_WIDTH)
        # Not converged on any earlier row past minTrials, or it would have
        # stopped there.
        first = CONVERGE_MIN - 1
        earlier = width.iloc[first:-1]
        self.assertTrue((earlier > CONVERGE_WIDTH).all())


class Flatline:
    """A beat source that never reports a beat or a period."""

    period = None

    def start(self):
        pass

    def stop(self):
        pass

    def poll(self):
        return []


class TestNoBeats(unittest.TestCase):
    """A source that has lost the heart stops the session, which still saves."""

    def test_three_empty_trials_raise_and_save(self):
        """After MAX_EMPTY_TRIALS trials with no tone, run() raises."""
        tmp = tempfile.mkdtemp()
        saved_wait = hsd.PERIOD_WAIT
        hsd.PERIOD_WAIT = 0.1
        try:
            params = getParameters(
                participant="FLAT",
                session="1",
                setup="test",
                axis="phase",
                nTrials=6,
                fullscr=False,
                nBreaking=0,
                resultPath=tmp,
                seed=SEED,
                beat_source=Flatline(),
                tone_player=SilentPlayer(time.perf_counter),
                config=TaskConfig(minTrials=1),
                clock=time.perf_counter,
            )
            params["autopilot"] = HSDAutopilot(
                params["rng"], Observer(mu=0.3, sigma=0.1, floor=0.05, peak=0.95)
            )
            try:
                with self.assertRaisesRegex(RuntimeError, "delivered no tone"):
                    hsd.run(params, confidenceRating=True, runTutorial=False)
            finally:
                params["win"].close()
            paths = params["paths"]
            df = pd.read_csv(paths.path("final"))
            self.assertEqual(len(df), hsd.MAX_EMPTY_TRIALS)
            self.assertTrue((df.nDelivered == 0).all())
            self.assertTrue((df.AbortReason == "no_period").all())
            self.assertFalse(df.DecisionProvided.any())
            posterior = np.load(paths.path("posterior", ext="npy"))
            self.assertEqual(posterior.shape[0], hsd.MAX_EMPTY_TRIALS)
            state = json.loads(Path(paths.path("engine", ext="json")).read_text())
            self.assertEqual(state["history"], [])
            self.assertTrue(Path(paths.path("parameters", ext="pickle")).exists())
        finally:
            hsd.PERIOD_WAIT = saved_wait
            shutil.rmtree(tmp, ignore_errors=True)


def scripted_result(
    delay, axis, n_delivered, aborted=False, reason=None, period=0.9, realized=None
):
    """A TrainResult as the scheduler would return it."""
    tones = []
    for i in range(n_delivered):
        r_time = 10.0 + i * period
        offset = realized if realized is not None else delay
        offset_s = offset / 1000.0 if axis == "absolute" else offset * period
        tones.append(
            ToneRecord(
                index=i,
                r_time=r_time,
                period=period,
                target=r_time + offset_s,
                onset=r_time + offset_s,
                realized=offset_s,
            )
        )
    result = TrainResult(
        delay=delay,
        axis=axis,
        tones=tones,
        n_delivered=n_delivered,
        aborted=aborted,
        abort_reason=reason if aborted else None,
        end_reason=reason if aborted else "complete",
        started=9.0,
        ended=20.0,
        beats_seen=[
            {"r_time": 9.5, "period": period, "rr": period, "seen": 9.6},
            {"r_time": 9.5 + period, "period": period, "rr": period, "seen": 10.0},
        ],
    )
    if n_delivered:
        value = realized if realized is not None else delay
        result.realized_mean = value / 1000.0 if axis == "absolute" else value
        result.realized_corrected = value
    return result


class ScriptedScheduler:
    """Returns prepared trains, in order, and records what was asked."""

    def __init__(self, results):
        self.results = list(results)
        self.asked = []
        self.marker = None
        self.on_frame = None

    def observe(self, beats):
        return []

    def take_between(self):
        return []

    def run(self, delay, axis, min_delay_s, max_fraction=0.75, **kwargs):
        self.asked.append(delay)
        result = self.results.pop(0)
        result.delay = delay
        return result


class TestRefusedTrains(unittest.TestCase):
    """What a trial does with a train the scheduler stopped or refused."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.sessions = {}
        for axis in ("absolute", "phase"):
            params = getParameters(
                participant="REFUSED",
                session=axis,
                setup="test",
                axis=axis,
                nTrials=10,
                fullscr=False,
                nBreaking=0,
                resultPath=cls.tmp,
                seed=SEED,
                beat_source=VirtualHeart(time.perf_counter, period=0.9),
                tone_player=SilentPlayer(time.perf_counter),
                config=TaskConfig(minTrials=1),
                clock=time.perf_counter,
            )
            params["autopilot"] = HSDAutopilot(
                params["rng"], Observer(mu=250.0, sigma=80.0, floor=0.05, peak=0.95)
            )
            params["beatSource"].start()
            cls.sessions[axis] = params

    @classmethod
    def tearDownClass(cls):
        for params in cls.sessions.values():
            params["win"].close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_trial(self, axis, results):
        params = self.sessions[axis]
        scheduler = ScriptedScheduler(results)
        params["scheduler"] = scheduler
        params["tone_rows"].clear()
        n_history = len(params["engine"].history)
        outcome = hsd.trial(params, 0, confidenceRating=True)
        return params, scheduler, outcome, len(params["engine"].history) - n_history

    def test_a_ceiling_after_tones_keeps_the_partial_train(self):
        """Tones already heard are the stimulus: no second train is played."""
        partial = scripted_result(
            200.0, "absolute", n_delivered=2, aborted=True, reason="ceiling"
        )
        params, scheduler, outcome, updates = self.run_trial("absolute", [partial])
        self.assertEqual(len(scheduler.asked), 1)
        self.assertEqual(outcome.quality["nTrains"], 1)
        self.assertEqual(outcome.nDelivered, 2)
        self.assertTrue(outcome.aborted)
        self.assertTrue(outcome.respProvided)
        self.assertEqual(updates, 1)
        self.assertEqual({row["Attempt"] for row in params["tone_rows"]}, {0})

    def test_a_ceiling_before_any_tone_draws_once_more(self):
        """Nothing heard: one new delay, under the period the train saw."""
        refused = scripted_result(
            600.0,
            "absolute",
            n_delivered=0,
            aborted=True,
            reason="ceiling",
            period=0.5,
        )
        complete = scripted_result(200.0, "absolute", n_delivered=5, period=0.5)
        params, scheduler, outcome, updates = self.run_trial(
            "absolute", [refused, complete]
        )
        self.assertEqual(len(scheduler.asked), 2)
        low, high = params["config"].bounds(0.5)
        self.assertLessEqual(scheduler.asked[1], high)
        self.assertGreaterEqual(scheduler.asked[1], low)
        self.assertEqual(outcome.quality["nTrains"], 2)
        self.assertEqual(outcome.nDelivered, 5)
        self.assertEqual(updates, 1)

    def test_a_phase_floor_refusal_draws_once_more(self):
        """A floor refusal on the phase axis is drawn again like a ceiling."""
        refused = scripted_result(
            0.1, "phase", n_delivered=0, aborted=True, reason="floor"
        )
        complete = scripted_result(0.3, "phase", n_delivered=5)
        params, scheduler, outcome, updates = self.run_trial(
            "phase", [refused, complete]
        )
        self.assertEqual(len(scheduler.asked), 2)
        self.assertEqual(outcome.quality["nTrains"], 2)
        self.assertEqual(updates, 1)
        self.assertEqual({row["Attempt"] for row in params["tone_rows"]}, {1})


class Stub:
    def draw(self):
        pass


class TestTutorial(unittest.TestCase):
    """runTutorial=True shows three instruction screens and three practice trials."""

    def test_the_tutorial_runs_before_the_task(self):
        """Practice trials run through trial() and leave the engine untouched."""
        steps = []

        def fake_text(parameters, message, pos=(0.0, 0.0), **kwargs):
            return Stub()

        def fake_hold(win, duration, *stims):
            steps.append("show")
            return duration

        def fake_wait(parameters):
            steps.append("wait")

        real_trial = hsd.trial
        practice = []

        def counted_trial(parameters, nTrial, **kwargs):
            if kwargs.get("practice"):
                practice.append(kwargs.get("confidenceRating"))
            return real_trial(parameters, nTrial, **kwargs)

        saved = (hsd.text, hsd.hold, hsd.waitInput, hsd.trial)
        hsd.text, hsd.hold, hsd.waitInput, hsd.trial = (
            fake_text,
            fake_hold,
            fake_wait,
            counted_trial,
        )
        tmp = tempfile.mkdtemp()
        try:
            params, df = run_session(
                tmp,
                n_trials=1,
                min_trials=1,
                period=0.6,
                run_tutorial=True,
                n_breaking=0,
            )
        finally:
            hsd.text, hsd.hold, hsd.waitInput, hsd.trial = saved
            shutil.rmtree(tmp, ignore_errors=True)

        # Three tutorial screens and the start screen each wait once.
        self.assertEqual(steps.count("wait"), 4)
        self.assertEqual(practice, [True, True, True])
        self.assertEqual(len(df), 1)
        self.assertEqual(len(params["posteriors"]), 1)
        self.assertEqual(len(params["engine"].history), 1)


class TestSetup(unittest.TestCase):
    """getParameters refuses what cannot run, before it writes anything."""

    def test_a_behavioral_launch_without_a_recorder_leaves_nothing_behind(self):
        """The device check runs before the run directory and the log exist."""
        tmp = tempfile.mkdtemp()
        try:
            with self.assertRaisesRegex(ValueError, "recorder=LSLRecorder"):
                getParameters(setup="behavioral", resultPath=tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_ntrials_below_mintrials_is_refused(self):
        """nTrials is named in the error, not hidden in a config check."""
        with self.assertRaisesRegex(ValueError, "nTrials=2"):
            getParameters(setup="test", nTrials=2, config=TaskConfig(minTrials=5))

    def test_a_player_without_describe_is_still_described(self):
        """The shared tone player has no describe(); the manifest reads its fields."""
        from cardioception.HSD.parameters import _describe_player

        class Player:
            fs = 48000.0
            device = 3

        self.assertEqual(
            _describe_player(Player()),
            {"class": "Player", "fs": 48000.0, "device": 3, "latency_class": None},
        )


if __name__ == "__main__":
    unittest.main()
