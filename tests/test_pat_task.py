# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The PsychoPy side of the Phase Adjustment Task, without hardware.

A fake engine stands in for :class:`cardioception.PAT.engine.PhaseEngine`
(the interface in the task contract) and a fake PsychoPy replays key presses
and wheel turns, so these tests need no ECG, no sound card and no display.
One test opens a small real window, and is skipped where that is impossible.
"""

import json
import math
import os
import sys
import time
import types
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np
import pandas as pd
import pytest

from cardioception._log import start_session_log
from cardioception._present import on_every_frame
from cardioception.output import SessionPaths
from cardioception.PAT import parameters as pat_parameters
from cardioception.PAT._autopilot import PATAutopilot
from cardioception.PAT.parameters import EVENTS, getParameters, startPhaseSequence
from cardioception.PAT.task import (
    FINAL_COLUMNS,
    TONE_COLUMNS,
    TUTORIAL_TRIAL,
    _clock,
    run,
    trial,
    tutorial,
)

#: Every stimulus drawn, in order, by the fake PsychoPy below
DRAWN: List["FakeStim"] = []
#: The text of every text drawn, as it read when drawn
TEXTS: List[str] = []

##############
# Fake engine #
##############


class FakeEngine:
    """Plays a 'tone' every third poll, at a fixed 1 s period.

    Tones are timed on the task's clock and play at once, so the task sees the
    first beep of a trial on the third poll.
    """

    def __init__(self, period: float = 1.0):
        self.period = period
        self._tones: List[dict] = []
        self._phase = 0.0
        self.active = False
        self.trial: Optional[int] = None
        self.block = ""
        self.polls = 0
        self.started: List[tuple] = []
        self.nudges: List[float] = []
        self.stops = 0
        self.stopReasons: List[str] = []
        self.ended = 0
        self.waits = 0
        self.closed = False
        self.marks: List[tuple] = []
        self.clock = _clock()
        self.t = self.clock()
        self.nudgePolls: List[int] = []
        self.idlePolls = 0
        self.idleDuringTrial = 0

    def start_trial(self, trial: int, start_phase_deg: float, block: str = "") -> None:
        self.trial, self.block = trial, block
        self._phase = float(start_phase_deg) % 360
        self.started.append((trial, start_phase_deg, block))
        self.active = True
        self.polls = 0

    def nudge(self, notches: float, gain_deg: float, gain_ms: float) -> None:
        self._phase = (self._phase + notches * gain_deg) % 360
        self.nudges.append(notches)
        self.nudgePolls.append(self.polls)

    @property
    def phase_deg(self) -> float:
        return self._phase

    @property
    def delay_ms(self) -> float:
        return self._phase / 360 * self.period * 1000

    def poll(self) -> None:
        if not self.active:
            return
        self.polls += 1
        self.t = self.clock()
        if self.polls % 3 == 0:
            self._tones.append(
                {
                    "Trial": self.trial,
                    "RTime": self.t,
                    "PeriodS": self.period,
                    "PhaseDeg": self._phase,
                    "DelayMs": self.delay_ms,
                    "Target": self.t,
                    "Anchor": "real" if self.polls % 2 else "predicted",
                    "Onset": self.t + 0.001,
                    "Kind": "tone",
                }
            )

    def idle_poll(self) -> None:
        self.idlePolls += 1
        if self.active:
            self.idleDuringTrial += 1

    def stop_tones(self, reason: str = "press") -> None:
        self.active = False
        self.stops += 1
        self.stopReasons.append(reason)

    def end_trial(self, on_wait=None) -> dict:
        if on_wait is not None:
            self.waits += 1
            on_wait()  # one frame of the wait for the next R-wave
        self.ended += 1
        mine = [t for t in self._tones if t["Trial"] == self.trial]
        # Leaves out PressTime and TrialDuration: the task fills them in
        return {
            "Trial": self.trial,
            "ChosenPhaseDeg": self._phase,
            "ChosenDelayMs": self.delay_ms,
            "AnticipatedPeriodMs": self.period * 1000,
            "ObservedPeriodMs": math.nan,
            "LastRTime": self.t,
            "nTonesReal": sum(t["Anchor"] == "real" for t in mine),
            "nTonesPredicted": sum(t["Anchor"] == "predicted" for t in mine),
            "nTonesSkipped": 0,
        }

    @property
    def tones(self) -> List[dict]:
        return self._tones

    def mark(self, kind: str, stamp: float = 0.0, **fields) -> None:
        self.marks.append((kind, fields))

    def close(self) -> None:
        self.closed = True


###############
# Fake PsychoPy #
###############


class FakeClock:
    def __init__(self, step: float = 0.1):
        self.step = step
        self.t = -step

    def getTime(self) -> float:
        self.t += self.step
        return self.t


class FakeStim:
    """Records how it looked each time it was drawn."""

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.text = kwargs.get("text")
        self.color = kwargs.get("color", "white")
        self.fillColor = kwargs.get("fillColor")
        self.pos = kwargs.get("pos", (0, 0))
        self.ori = 0.0
        self.history: List[tuple] = []

    def draw(self) -> None:
        self.history.append((self.ori, self.fillColor, tuple(self.pos)))
        DRAWN.append(self)
        if self.text:
            TEXTS.append(self.text)


class FakeRect(FakeStim):
    """The dial's pointer: the only Rect the task draws."""

    instances: List["FakeRect"] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        FakeRect.instances.append(self)


class FakeMarker:
    size = (0.0, 0.0)
    color = "white"


class FakeSlider(FakeStim):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.marker = FakeMarker()
        self.markerPos = 0


class FakeWindow:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.mouseVisible = True
        self.flips = 0
        self.closed = False

    def flip(self) -> None:
        self.flips += 1

    def close(self) -> None:
        self.closed = True


class FakeMouse:
    """Half a notch per wheel read, so every second frame moves the dial.

    ``buttons``, when set, scripts the left button one read at a time; past
    its end the button stays as ``pressed`` says.
    """

    def __init__(self, *args, **kwargs):
        self.wheel = 0.5
        self.pressed = False
        self.buttons: List[bool] = []
        self.x = 0.0

    def getWheelRel(self) -> np.ndarray:
        return np.array([0.0, self.wheel])

    def getPressed(self):
        if self.buttons:
            return [int(self.buttons.pop(0)), 0, 0]
        return [int(self.pressed), 0, 0]

    def getPos(self) -> np.ndarray:
        return np.array([self.x, 0.2])

    def setPos(self, pos) -> None:
        pass

    def clickReset(self) -> None:
        pass


class FakeKeyboard:
    """Answers getKeys from a policy: (keyList) -> keys."""

    def __init__(self):
        self.policy: Callable[[Optional[list]], List[str]] = lambda keyList: (
            ["space"] if keyList and "space" in keyList else []
        )

    def getKeys(self, keyList=None, **kwargs) -> List[str]:
        return self.policy(keyList)

    def clearEvents(self, eventType=None) -> None:
        pass


@pytest.fixture
def fake_psychopy(monkeypatch):
    DRAWN.clear()
    TEXTS.clear()
    FakeRect.instances.clear()
    keyboard = FakeKeyboard()
    core = types.ModuleType("psychopy.core")
    core.Clock = FakeClock  # type: ignore[attr-defined]
    core.wait = lambda t: None  # type: ignore[attr-defined]
    event = types.ModuleType("psychopy.event")
    event.getKeys = keyboard.getKeys  # type: ignore[attr-defined]
    event.clearEvents = keyboard.clearEvents  # type: ignore[attr-defined]
    event.Mouse = FakeMouse  # type: ignore[attr-defined]
    visual = types.ModuleType("psychopy.visual")
    visual.Window = FakeWindow  # type: ignore[attr-defined]
    visual.TextStim = FakeStim  # type: ignore[attr-defined]
    visual.GratingStim = FakeStim  # type: ignore[attr-defined]
    visual.Slider = FakeSlider  # type: ignore[attr-defined]
    visual.Circle = FakeStim  # type: ignore[attr-defined]
    visual.Rect = FakeRect  # type: ignore[attr-defined]
    psychopy = types.ModuleType("psychopy")
    for name, module in (("core", core), ("event", event), ("visual", visual)):
        setattr(psychopy, name, module)
        monkeypatch.setitem(sys.modules, f"psychopy.{name}", module)
    monkeypatch.setitem(sys.modules, "psychopy", psychopy)
    yield keyboard
    # Release the session log, so the run directory can be removed on Windows.
    start_session_log(None)


def make_parameters(tmp_path, engine=None, **kwargs) -> dict:
    kwargs.setdefault("nTrials", 4)
    kwargs.setdefault("nPractice", 2)
    parameters = getParameters(
        participant="test",
        resultPath=str(tmp_path),
        engine=engine or FakeEngine(),
        fullscr=False,
        **kwargs,
    )
    parameters["minTrialTime"] = 0.0
    return parameters


TUTORIAL_STAGES = ("tutorialListen", "tutorialLater", "tutorialEarlier", "tutorialFree")


def lastStage(parameters: dict) -> Optional[str]:
    """The key of the tutorial stage drawn last, footers aside."""
    keys = {parameters["texts"][k]: k for k in TUTORIAL_STAGES}
    for text in reversed(TEXTS):
        if text in keys:
            return keys[text]
    return None


def space_after_polls(engine: FakeEngine, n: int = 7, parameters=None):
    """Space ends a trial after n engine polls; every wait passes at once.

    With `parameters`, the wheel rolls towards the participant while the
    tutorial asks for it, and away otherwise.
    """

    def policy(keyList):
        if parameters is not None:
            earlier = lastStage(parameters) == "tutorialEarlier"
            parameters["myMouse"].wheel = -0.5 if earlier else 0.5
        if not keyList or "space" not in keyList:
            return []
        if "left" in keyList and engine.active and engine.polls < n:
            return []  # inside a trial, not yet
        return ["space"]

    return policy


def read(path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


#######################
# Start phase sequence #
#######################


def test_start_phase_sequence_is_blocks_of_permutations():
    seq = startPhaseSequence(44, rng=np.random.default_rng(1))
    assert len(seq) == 44
    for block in np.reshape(seq, (11, 4)):
        assert sorted(block) == [0, 90, 180, 270]
    # No immediate repeat, within or across blocks
    assert all(a != b for a, b in zip(seq[:-1], seq[1:]))


def test_start_phase_sequence_edge_cases():
    assert startPhaseSequence(0) == []
    assert len(startPhaseSequence(6)) == 6  # cut inside the second block
    assert startPhaseSequence(5, phases=(90,)) == [90] * 5  # cannot avoid repeats
    a = startPhaseSequence(28, rng=np.random.default_rng(7))
    b = startPhaseSequence(28, rng=np.random.default_rng(7))
    assert a == b
    with pytest.raises(ValueError):
        startPhaseSequence(4, phases=())
    with pytest.raises(ValueError):
        startPhaseSequence(-1)


##############
# Parameters #
##############


def test_parameters(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=28, nPractice=8)
    assert parameters["engine"] is engine
    assert parameters["outlet"] is None  # an injected engine brings its own markers
    assert len(parameters["startPhaseMain"]) == 28
    assert len(parameters["startPhasePractice"]) == 8
    scale = parameters["confidenceScale"]
    assert scale.bounds == (1, 10) and scale.kind == "discrete"
    assert list(scale.labels) == ["Not at all", "Extremely"]
    assert parameters["labelsRating"] == ["Not at all", "Extremely"]
    assert parameters["results_df"].empty and parameters["tones"] == []
    assert isinstance(parameters["win"], FakeWindow)
    assert parameters["win"].kwargs["fullscr"] is False
    assert parameters["win"].mouseVisible is False

    danish_parameters = make_parameters(tmp_path / "da", language="danish")
    assert danish_parameters["labelsRating"] == ["Slet ikke", "Ekstremt"]
    assert list(danish_parameters["confidenceScale"].labels) == [
        "Slet ikke",
        "Ekstremt",
    ]


def test_a_scale_passed_in_keeps_its_labels_and_sets_the_instructions(
    fake_psychopy, tmp_path
):
    from cardioception.scales import VAS_0_100

    scale = VAS_0_100.with_labels(["low", "high"])
    parameters = make_parameters(tmp_path, confidenceScale=scale)
    assert parameters["confidenceScale"] is scale
    assert parameters["labelsRating"] == ["low", "high"]
    assert "from 0 (not at all) to 100 (extremely)" in " ".join(
        parameters["texts"]["instructions"]
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "phase"},
        {"language": "german"},
        {"device": "wheel"},
        {"nTrials": 0},
        {"nPractice": -1},
        {"startPhases": (0, 360)},
        {"startPhases": ()},
        {"exteroPeriod": 1000},  # milliseconds, not seconds
        {"exteroPeriod": "regular"},
        {"toneVolume": 2.0},
        {"confidenceScale": (1, 10)},  # a ConfidenceScale, not a tuple
    ],
)
def test_parameters_reject_bad_input(fake_psychopy, tmp_path, kwargs):
    with pytest.raises(ValueError):
        make_parameters(tmp_path, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minToneGap": 0.0},
        {"minToneGap": 0.07},  # less than the 0.03 s tone plus 0.05 s
        {"minToneGap": 0.3, "toneDuration": 0.3},
    ],
)
def test_parameters_reject_a_tone_gap_the_player_cannot_keep(
    fake_psychopy, tmp_path, kwargs
):
    with pytest.raises(ValueError, match="minToneGap"):
        make_parameters(tmp_path, **kwargs)


def test_parameters_accept_the_shortest_tone_gap(fake_psychopy, tmp_path):
    parameters = make_parameters(tmp_path, minToneGap=0.08, toneDuration=0.03)
    assert parameters["minToneGap"] == 0.08


def test_parameters_need_a_recorder(fake_psychopy, tmp_path):
    with pytest.raises(ValueError, match="recorder"):
        getParameters(resultPath=str(tmp_path))


def test_parameters_refuse_to_overwrite_a_run(fake_psychopy, tmp_path, monkeypatch):
    """A run directory that already holds results is not written into."""
    monkeypatch.setattr(
        pat_parameters,
        "SessionPaths",
        lambda **kwargs: SessionPaths(run_id="fixed", **kwargs),
    )
    first = make_parameters(tmp_path)
    with open(first["paths"].path("final"), "w") as handle:
        handle.write("Trial\n1\n")
    with pytest.raises(FileExistsError, match="already holds"):
        make_parameters(tmp_path)
    again = make_parameters(tmp_path, overwrite=True)
    assert again["paths"].directory == first["paths"].directory


def test_results_go_to_a_run_directory(fake_psychopy, tmp_path):
    """sub-<participant>/ses-<session>/run-<timestamp>, with a manifest."""
    parameters = make_parameters(tmp_path, session="002", seed=11)
    directory = Path(parameters["paths"].directory)
    assert directory.parent == tmp_path / "sub-test" / "ses-002"
    assert directory.name.startswith("run-")
    assert parameters["resultPath"] == str(directory)
    assert Path(parameters["paths"].path("final")).name.startswith(
        "sub-test_ses-002_run-"
    )
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["task"] == "PAT"
    assert manifest["participant"] == "test" and manifest["session"] == "002"
    assert manifest["seed"] == 11
    assert manifest["nTrials"] == 4 and manifest["nPractice"] == 2
    assert manifest["mode"] == "relative" and manifest["extero"] is False
    assert (directory / "session.log").exists()


def test_the_seed_decides_the_start_phases(fake_psychopy, tmp_path):
    a = make_parameters(tmp_path / "a", nTrials=28, nPractice=8, seed=5)
    b = make_parameters(tmp_path / "b", nTrials=28, nPractice=8, seed=5)
    c = make_parameters(tmp_path / "c", nTrials=28, nPractice=8, seed=6)
    assert a["seed"] == 5
    assert a["startPhaseMain"] == b["startPhaseMain"]
    assert a["startPhasePractice"] == b["startPhasePractice"]
    assert a["startPhaseMain"] != c["startPhaseMain"]
    unseeded = make_parameters(tmp_path / "d")
    assert isinstance(unseeded["seed"], int)  # drawn, and recorded


def test_parameters_open_a_real_window(tmp_path):
    """A small real window, where this machine can open one."""
    pytest.importorskip("psychopy.visual")
    try:
        parameters = getParameters(
            resultPath=str(tmp_path), engine=FakeEngine(), fullscr=False
        )
    except Exception as error:  # no display, no OpenGL
        pytest.skip(f"cannot open a PsychoPy window here: {error}")
    try:
        assert parameters["win"].units == "height"
        assert parameters["myMouse"] is not None
    finally:
        parameters["win"].close()


#################
# Trial and run #
#################


def test_trial_writes_a_row_and_saves(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    fake_psychopy.policy = space_after_polls(engine)

    row = trial(parameters, 1, "practice", 90.0)

    assert engine.started == [(1, 90.0, "practice")]
    assert engine.stops == 1 and engine.ended == 1
    assert len(engine.nudges) >= 2  # half a notch per frame adds up
    assert row["nDialMoves"] == len(engine.nudges)
    assert row["ChosenPhaseDeg"] == pytest.approx(90 + 10 * sum(engine.nudges))
    assert 1 <= row["Confidence"] <= 10 and row["ConfidenceRT"] > 0.5
    assert row["PressTime"] > 0 and row["TrialDuration"] >= 0  # task fallback

    final = read(parameters["paths"].path("final"))
    assert list(final.columns) == FINAL_COLUMNS
    assert len(final) == 1
    # The rating, the same rating on 0 to 1, and the scale it was given on
    assert final.loc[0, "ConfidenceUnit"] == pytest.approx(
        (final.loc[0, "Confidence"] - 1) / 9
    )
    assert final.loc[0, "Device"] == "keyboard"
    assert final.loc[0, "ConfidenceScale"] == "discrete"
    assert final.loc[0, "ConfidenceLow"] == 1 and final.loc[0, "ConfidenceHigh"] == 10
    assert final.loc[0, "ConfidenceLevels"] == 10
    assert bool(final.loc[0, "ConfidenceSigned"]) is False
    assert final.loc[0, "Block"] == "practice"
    assert final.loc[0, "StartPhaseDeg"] == 90
    assert bool(final.loc[0, "Extero"]) is False

    trial(parameters, 2, "practice", 180.0)
    assert len(read(parameters["paths"].path("final"))) == 2  # saved after every trial

    tones = read(parameters["paths"].path("tones"))
    assert list(tones.columns) == TONE_COLUMNS
    assert set(tones["Trial"]) == {1, 2}
    assert set(tones["Block"]) == {"practice"}

    kinds = [kind for kind, _ in engine.marks]
    assert kinds == ["confidence", "confidence"]


def pointer_angles(rect: "FakeRect") -> List[float]:
    return [ori for ori, _, _ in rect.history]


@pytest.mark.parametrize(
    "mode, direction, step",
    [("relative", 1, 10.0), ("relative", -1, -10.0), ("absolute", 1, 9.0)],
)
def test_pointer_starts_at_twelve_and_turns_with_the_wheel(
    fake_psychopy, tmp_path, mode, direction, step
):
    engine = FakeEngine()  # period 1 s: 25 ms per notch is 9 degrees
    parameters = make_parameters(
        tmp_path, engine=engine, mode=mode, wheelDirection=direction
    )
    fake_psychopy.policy = space_after_polls(engine, n=12)

    perTrial = []
    for number, startPhase in ((1, 180.0), (2, 90.0)):
        before = len(engine.nudges)
        trial(parameters, number, "main", startPhase)
        perTrial.append(engine.nudges[before:])

    assert len(FakeRect.instances) == 2  # a new dial for every trial
    for rect, nudges in zip(FakeRect.instances, perTrial):
        angles = pointer_angles(rect)
        assert angles[0] == 0  # twelve o'clock, whatever the start phase
        assert nudges and all(np.sign(n) == direction for n in nudges)
        # The last frame drawn shows every notch but those of the press frame
        travel = np.cumsum(nudges) * abs(step)
        assert any(
            angles[-1] == pytest.approx(t % 360) for t in travel[-2:]
        ), "the pointer turns by the same angle as the phase"


def test_pointer_flashes_with_each_beep(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    parameters["flashDuration"] = 10.0  # every frame after a beep is lit
    fake_psychopy.policy = space_after_polls(engine, n=12)

    trial(parameters, 1, "main", 0.0)

    colours = [colour for _, colour, _ in FakeRect.instances[0].history]
    assert "white" in colours


def test_nothing_moves_before_the_first_beep(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    # Space on every frame: it must wait for the first beep (third poll)
    fake_psychopy.policy = lambda keyList: ["space"] if keyList else []

    trial(parameters, 1, "main", 0.0)

    waiting = parameters["texts"]["waitingFirstTone"]
    assert waiting in [stim.text for stim in DRAWN]
    assert engine.polls >= 3
    assert all(polls >= 3 for polls in engine.nudgePolls)


def test_no_dial_when_hidden(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, showDial=False)
    fake_psychopy.policy = space_after_polls(engine)

    row = trial(parameters, 1, "main", 0.0)

    assert FakeRect.instances and not FakeRect.instances[0].history
    assert row["nDialMoves"] > 0  # the wheel still works


def test_tutorial_guides_through_the_wheel(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    fake_psychopy.policy = space_after_polls(engine, n=0, parameters=parameters)
    texts = parameters["texts"]

    tutorial(parameters)

    assert [s[0] for s in engine.started] == [TUTORIAL_TRIAL]
    shown = [stim.text for stim in DRAWN if stim.text]
    order = [
        texts["tutorialListen"],
        texts["tutorialLater"],
        texts["tutorialEarlier"],
        texts["tutorialFree"],
    ]
    firsts = [shown.index(text) for text in order]
    assert firsts == sorted(firsts)
    # No wheel while listening; then at least 3 notches later, then 3 earlier
    listenEnd = engine.nudgePolls[0]
    assert listenEnd >= 3 * parameters["tutorialListenTones"]
    signs = np.sign(engine.nudges)
    firstEarlier = int(np.argmax(signs < 0))
    assert sum(engine.nudges[:firstEarlier]) >= parameters["tutorialNotches"]
    assert sum(n for n in engine.nudges[firstEarlier:] if n < 0) <= -3
    assert texts["textNext"] in shown  # the footer once a step is done
    assert not os.path.exists(parameters["paths"].path("tones"))  # nothing saved


def test_run_saves_everything(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=12, nPractice=2)
    fake_psychopy.policy = space_after_polls(engine, parameters=parameters)

    run(parameters, runTutorial=True, confidenceRating=True)

    assert parameters["aborted"] is False
    # Tutorial, then 2 practice and 12 main trials, numbered across blocks
    assert [s[0] for s in engine.started] == [TUTORIAL_TRIAL] + list(range(1, 15))
    final = read(parameters["paths"].path("final"))
    assert list(final["Trial"]) == list(range(1, 15))
    assert list(final["Block"]) == ["practice"] * 2 + ["main"] * 12
    assert list(final["StartPhaseDeg"]) == (
        parameters["startPhasePractice"] + parameters["startPhaseMain"]
    )
    assert final["Confidence"].between(1, 10).all()

    tones = read(parameters["paths"].path("tones"))
    assert TUTORIAL_TRIAL not in set(tones["Trial"])  # the tutorial is not saved
    assert set(tones["Trial"]) == set(range(1, 15))
    assert (
        tones.groupby("Trial")["Block"].first() == final.set_index("Trial")["Block"]
    ).all()

    saved = read(parameters["paths"].path("parameters")).set_index("Parameter")["Value"]
    assert saved["mode"] == '"relative"'
    assert saved["nTrials"] == "12"
    assert "engine" not in saved.index and "win" not in saved.index


def test_run_without_rating(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    fake_psychopy.policy = space_after_polls(engine)

    run(parameters, runTutorial=False, confidenceRating=False)

    final = read(parameters["paths"].path("final"))
    assert len(final) == 4 and final["Confidence"].isna().all()
    assert engine.marks == []


def test_escape_in_a_trial_keeps_completed_trials(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=6, nPractice=0)
    normal = space_after_polls(engine)

    def policy(keyList):
        if len(engine.started) == 3 and keyList and "left" in keyList:
            return ["escape"]  # during the third trial
        return normal(keyList)

    fake_psychopy.policy = policy
    run(parameters, runTutorial=False)

    assert parameters["aborted"] is True
    # The tones of the aborted trial were stopped, as an abort, not a press
    assert engine.stopReasons == ["press", "press", "abort"]
    final = read(parameters["paths"].path("final"))
    assert list(final["Trial"]) == [1, 2]
    # Its tones are not saved either: no row, no tones
    assert set(read(parameters["paths"].path("tones"))["Trial"]) == {1, 2}
    assert 3 not in parameters["trialBlocks"]
    assert not engine.closed  # left to the caller


class SilentEngine(FakeEngine):
    """An engine whose ECG never gives a beat: no tone ever plays."""

    def poll(self) -> None:
        if self.active:
            self.polls += 1


def test_a_trial_with_no_beats_times_out(fake_psychopy, tmp_path):
    engine = SilentEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=2, nPractice=0)
    parameters["maxTrialTime"] = 0.2
    fake_psychopy.policy = space_after_polls(engine)  # space never works

    run(parameters, runTutorial=False)

    assert parameters["aborted"] is False
    assert engine.stopReasons == ["timeout", "timeout"]
    final = read(parameters["paths"].path("final"))
    assert list(final.columns) == FINAL_COLUMNS
    assert list(final["TrialStatus"]) == ["timeout", "timeout"]
    assert final["ChosenPhaseDeg"].isna().all()
    assert final["ChosenDelayMs"].isna().all()
    # No choice, so no rating was asked
    assert final["Confidence"].isna().all()
    assert engine.marks == []
    assert (final["TrialDuration"] >= 0.2).all()


def test_a_normal_trial_is_ok(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    fake_psychopy.policy = space_after_polls(engine)

    row = trial(parameters, 1, "main", 0.0)

    assert row["TrialStatus"] == "ok"
    assert engine.stopReasons == ["press"]


def test_escape_after_the_press_keeps_the_trial(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    normal = space_after_polls(engine)

    def policy(keyList):
        if keyList == ["escape"] and engine.stops == 1 and engine.ended == 0:
            return ["escape"]  # while waiting for the R-wave after the press
        return normal(keyList)

    fake_psychopy.policy = policy
    run(parameters, runTutorial=False)

    assert parameters["aborted"] is True
    assert engine.waits == 1
    final = read(parameters["paths"].path("final"))
    assert len(final) == 1 and final.loc[0, "TrialStatus"] == "ok"
    # The choice is kept; no rating was asked
    assert np.isfinite(final.loc[0, "ChosenPhaseDeg"])
    assert final["Confidence"].isna().all()
    assert engine.marks == []


def test_the_wait_after_the_press_flips_the_window(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    fake_psychopy.policy = space_after_polls(engine)
    win = parameters["win"]
    original = engine.end_trial
    flips = []

    def end_trial(on_wait=None):
        before = win.flips
        assert on_wait() is False  # one pass of the wait, no Esc
        flips.append(win.flips - before)
        return original()

    engine.end_trial = end_trial  # type: ignore[method-assign]
    trial(parameters, 1, "main", 0.0, confidenceRating=False)

    assert flips == [1]


def test_escape_in_the_rating_keeps_the_trial(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    normal = space_after_polls(engine)

    def policy(keyList):
        if engine.ended == 1 and keyList and "escape" in keyList:
            return ["escape"]  # while the first rating is on screen
        return normal(keyList)

    fake_psychopy.policy = policy
    run(parameters, runTutorial=False)

    assert parameters["aborted"] is True
    final = read(parameters["paths"].path("final"))
    assert len(final) == 1 and final["Confidence"].isna().all()
    assert final["ConfidenceUnit"].isna().all()


def test_escape_before_any_trial_writes_no_results(fake_psychopy, tmp_path):
    parameters = make_parameters(tmp_path)
    fake_psychopy.policy = lambda keyList: ["escape"]

    run(parameters)

    assert parameters["aborted"] is True
    assert not os.path.exists(parameters["paths"].path("final"))
    assert not os.path.exists(parameters["paths"].path("tones"))


def test_mouse_rating(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, device="mouse")
    fake_psychopy.policy = space_after_polls(engine)
    mouse = parameters["myMouse"]
    # Held from before the rating for 10 reads, released, then pressed
    mouse.buttons = [True] * 10 + [False] * 2
    mouse.pressed = True
    mouse.x = 0.5  # right end of the slider

    row = trial(parameters, 1, "main", 0.0)

    assert row["Confidence"] == 10
    # Not on the first read past minRatingTime, while the button was still held
    assert row["ConfidenceRT"] > 1.0
    assert row["Device"] == "mouse" and row["ConfidenceUnit"] == 1.0
    assert engine.idlePolls >= 10  # the engine is polled during the rating


def test_escape_in_the_mouse_rating_keeps_the_trial(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, device="mouse", nPractice=0)
    normal = space_after_polls(engine)

    def policy(keyList):
        if engine.ended == 1 and keyList == ["escape"]:
            return ["escape"]  # while the first rating is on screen
        return normal(keyList)

    fake_psychopy.policy = policy
    run(parameters, runTutorial=False)

    assert parameters["aborted"] is True
    final = read(parameters["paths"].path("final"))
    assert len(final) == 1 and final["Confidence"].isna().all()


#####################################
# With the real engine, no hardware #
#####################################


class FakePlayer:
    """Reports every sound as played on time, once its target has passed."""

    def __init__(self, clock):
        self.clock = clock
        self.pending: dict = {}
        self.played: List[tuple] = []

    def schedule(self, when: float, kind: str = "tone") -> int:
        handle = len(self.played) + len(self.pending) + 1
        self.pending[handle] = (when, kind)
        return handle

    def poll_onsets(self):
        now = self.clock()
        due = [(h, w) for h, (w, _) in self.pending.items() if w <= now]
        for handle, when in due:
            self.played.append((handle, when, self.pending.pop(handle)[1]))
        return due

    def stop_all(self) -> None:
        self.pending.clear()

    def close(self) -> None:
        pass


def test_trial_with_the_real_engine(fake_psychopy, tmp_path):
    """The extero task end to end: virtual beats, vibrations and tones."""
    engine_module = pytest.importorskip("cardioception.PAT.engine")
    pylsl = pytest.importorskip("pylsl")
    clock = pylsl.local_clock

    source = engine_module.VirtualBeatSource(0.6, clock=clock, lead_in=0.1)
    player = FakePlayer(clock)
    engine = engine_module.PhaseEngine(source, player, "relative", clock=clock)
    parameters = make_parameters(tmp_path, engine=engine, extero=True)

    started: dict = {}

    def policy(keyList):
        if not keyList or "space" not in keyList:
            return []
        if "left" in keyList:  # in the trial: wait 2 s, turning the wheel
            t0 = started.setdefault(engine.trial, clock())
            return ["space"] if clock() - t0 > 2.0 else []
        return ["space"]

    fake_psychopy.policy = policy
    row = trial(parameters, 1, "main", 270.0)

    assert row["Extero"] is True and row["StartPhaseDeg"] == 270.0
    assert row["AnticipatedPeriodMs"] == pytest.approx(600)
    assert row["ObservedPeriodMs"] == pytest.approx(600)
    assert row["nTonesReal"] + row["nTonesPredicted"] >= 2
    assert row["nDialMoves"] > 0

    tones = read(parameters["paths"].path("tones"))
    assert set(tones["Kind"]) == {"tone", "vibration"}
    assert set(tones.loc[tones["Kind"] == "vibration", "Anchor"]) == {"virtual"}
    assert tones["Onset"].notna().all()
    final = read(parameters["paths"].path("final"))
    assert list(final.columns) == FINAL_COLUMNS
    assert list(tones.columns) == TONE_COLUMNS
    # The last tone heard joins tones.txt on its index
    assert tones["ToneIndex"].is_unique
    (last,) = tones[tones["ToneIndex"] == final.loc[0, "LastToneIndex"]].itertuples()
    assert last.Kind == "tone" and last.Anchor == final.loc[0, "LastToneAnchor"]
    assert last.RTime == pytest.approx(final.loc[0, "LastToneRTime"])
    assert last.Target <= final.loc[0, "PressTime"]
    # A virtual heart is never late, so the delay heard is the dial's then
    assert final.loc[0, "LastToneDelayMs"] == pytest.approx(last.DelayMs)


class RecordingOutlet:
    """A marker outlet that keeps every marker, decoded."""

    def __init__(self):
        self.markers: List[dict] = []

    def push_sample(self, sample, stamp=0.0) -> None:
        self.markers.append(json.loads(sample[0]))


def test_escape_mid_trial_with_the_real_engine(fake_psychopy, tmp_path):
    """Markers and tone table after Esc in the second trial."""
    engine_module = pytest.importorskip("cardioception.PAT.engine")
    pylsl = pytest.importorskip("pylsl")
    clock = pylsl.local_clock

    source = engine_module.VirtualBeatSource(0.6, clock=clock, lead_in=0.1)
    outlet = RecordingOutlet()
    engine = engine_module.PhaseEngine(
        source, FakePlayer(clock), "relative", clock=clock, outlet=outlet
    )
    parameters = make_parameters(
        tmp_path, engine=engine, extero=True, nTrials=3, nPractice=0
    )
    started: dict = {}

    def policy(keyList):
        if not keyList or "space" not in keyList:
            return []
        if "left" in keyList:  # in a trial: 1.5 s, then space or Esc
            t0 = started.setdefault(engine.trial, clock())
            if clock() - t0 < 1.5:
                return []
            return ["escape"] if engine.trial == 2 else ["space"]
        return ["space"]

    fake_psychopy.policy = policy
    run(parameters, runTutorial=False)

    assert parameters["aborted"] is True
    stops = [
        (m["kind"], m["trial"])
        for m in outlet.markers
        if m["kind"] in ("press", "abort", "timeout")
    ]
    assert stops == [("press", 1), ("abort", 2)]
    ends = [m["Trial"] for m in outlet.markers if m["kind"] == "trial_end"]
    assert ends == [1]
    assert any(t["Trial"] == 2 for t in engine.tones)
    tones = read(parameters["paths"].path("tones"))
    assert set(tones["Trial"]) == {1}
    assert list(read(parameters["paths"].path("final"))["Trial"]) == [1]


##################################
# The wheel in the rating screen #
##################################


@pytest.mark.parametrize("direction, expected", [(1, 10), (-1, 1)])
def test_rating_follows_the_wheel(fake_psychopy, tmp_path, direction, expected):
    from cardioception.PAT.task import confidenceRatingTask

    parameters = make_parameters(tmp_path, wheelDirection=direction)
    parameters["myMouse"].wheel = 3.0  # three notches away per frame
    fake_psychopy.policy = lambda keyList: ["space"] if keyList else []

    confidence, rt, provided = confidenceRatingTask(parameters)

    assert provided and confidence == expected  # clamped to the scale
    assert parameters["win"].mouseVisible is False


def test_wheel_rating_steps_one_per_notch(fake_psychopy):
    from cardioception._rating import keyboard_rating

    win = FakeWindow()
    fake_psychopy.policy = lambda keyList: ["space"] if keyList else []
    confidence, _, provided = keyboard_rating(
        win=win,
        message=FakeStim(),
        low=1,
        high=10,
        labels=["a", "b"],
        marker_start=5,
        min_time=0.5,
        accept_keys=("space",),
        wheel=lambda: 0.5,  # half a notch per frame
    )
    # Accepted on the sixth or seventh frame: three whole notches either way
    assert provided and confidence == 8


def test_text_screens_ignore_the_wheel(fake_psychopy, tmp_path):
    from cardioception.PAT.task import waitInput

    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    parameters["myMouse"].wheel = 5.0
    calls = []

    def policy(keyList):
        calls.append(keyList)
        return ["space"] if len(calls) > 5 else []

    fake_psychopy.policy = policy
    # run() installs the engine's idle poll as the per-frame hook
    on_every_frame(parameters["win"], engine.idle_poll)
    waitInput(parameters, FakeStim(text="a screen"))

    assert len(calls) == 6  # only space moved on
    assert engine.nudges == []
    assert engine.idlePolls == 6  # beats are still detected on text screens
    assert TEXTS.count("a screen") == 6  # and the screen is redrawn


def test_run_removes_the_frame_hook(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    fake_psychopy.policy = space_after_polls(engine)

    run(parameters, runTutorial=False)

    assert getattr(parameters["win"], "_cardioception_frame_hook", None) is None


def test_idle_poll_between_trials_only(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    fake_psychopy.policy = space_after_polls(engine)

    run(parameters, runTutorial=False)

    assert engine.idlePolls > 0
    assert engine.idleDuringTrial == 0  # never while tones are scheduled


def test_idle_poll_during_the_rating(fake_psychopy, tmp_path):
    from cardioception.PAT.task import confidenceRatingTask

    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    fake_psychopy.policy = lambda keyList: ["space"] if keyList else []

    confidenceRatingTask(parameters)

    assert engine.idlePolls >= 5  # one per frame until the rating is accepted


#########################################
# Tutorial: counts each way, and timeout #
#########################################


def scripted_tutorial(parameters: dict, scripts: dict, limit: float = 30.0):
    """Roll the wheel by a script per stage, then press space once it ends.

    The wheel value set on one frame is read on the next, so every step of a
    script is applied before the space press that follows it.
    """
    frames = {key: 0 for key in TUTORIAL_STAGES}
    start = time.perf_counter()

    def policy(keyList):
        if not keyList or "left" not in keyList:
            return ["space"] if keyList and "space" in keyList else []
        assert time.perf_counter() - start < limit, "stuck in the tutorial"
        stage = lastStage(parameters)
        script = scripts.get(stage, [])
        if stage is None:
            return []
        i = frames[stage]
        frames[stage] += 1
        if i < len(script):
            parameters["myMouse"].wheel = script[i]
            return []
        parameters["myMouse"].wheel = 0.0
        return ["space"]

    return policy


def test_tutorial_counts_each_way_not_the_net(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    parameters["tutorialStageTimeout"] = 1e9  # only the counts can open a stage
    later = [1.0] * 5 + [-1.0] * 4  # net +1, but 5 notches away
    earlier = [-1.0] * 3 + [1.0] * 3  # net 0, but 3 notches towards
    fake_psychopy.policy = scripted_tutorial(
        parameters, {"tutorialLater": later, "tutorialEarlier": earlier}
    )

    tutorial(parameters)

    assert engine.nudges == later + earlier
    texts = parameters["texts"]
    for done in range(3):  # at 3 of 3 the page says to press space
        assert texts["tutorialProgress"].format(done=done, total=3) in TEXTS
    assert texts["tutorialReady"] in TEXTS
    # Once ready, rolling back does not take the page back to "Rolled 2 of 3"
    laterReady = TEXTS.index(texts["tutorialReady"])
    stageEarlier = TEXTS.index(texts["tutorialEarlier"])
    between = TEXTS[laterReady:stageEarlier]
    assert not any(t.startswith("Rolled") for t in between)


def test_tutorial_progress_in_danish(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, language="danish")
    parameters["tutorialStageTimeout"] = 1e9
    fake_psychopy.policy = scripted_tutorial(
        parameters, {"tutorialLater": [1.0] * 3, "tutorialEarlier": [-1.0] * 3}
    )

    tutorial(parameters)

    assert "Rullet 1 af 3. Tryk derefter på MELLEMRUM." in TEXTS
    assert parameters["texts"]["tutorialReady"] in TEXTS


def test_tutorial_timeout_lets_space_through(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine)
    parameters["tutorialStageTimeout"] = 0.05
    fake_psychopy.policy = scripted_tutorial(parameters, {})  # no wheel at all

    tutorial(parameters)

    assert engine.nudges == []
    assert [s[0] for s in engine.started] == [TUTORIAL_TRIAL]
    texts = parameters["texts"]
    assert texts["tutorialProgress"].format(done=0, total=3) in TEXTS
    assert texts["tutorialFree"] in TEXTS  # got through both wheel pages


############
# Triggers #
############


def test_triggers_fire_once_per_trial(fake_psychopy, tmp_path):
    counts = {event: 0 for event in EVENTS}

    def counter(event):
        def callback():
            counts[event] += 1

        return callback

    engine = FakeEngine()
    parameters = make_parameters(
        tmp_path,
        engine=engine,
        nPractice=1,
        triggers={event: counter(event) for event in EVENTS},
    )
    fake_psychopy.policy = space_after_polls(engine, parameters=parameters)

    run(parameters, runTutorial=True)

    assert counts == {event: 5 for event in EVENTS}  # 1 practice, 4 main


def test_triggers_without_a_rating(fake_psychopy, tmp_path):
    counts = {event: 0 for event in EVENTS}
    triggers = {e: (lambda e=e: counts.__setitem__(e, counts[e] + 1)) for e in EVENTS}
    engine = FakeEngine()
    parameters = make_parameters(
        tmp_path, engine=engine, nPractice=0, triggers=triggers
    )
    fake_psychopy.policy = space_after_polls(engine)

    run(parameters, runTutorial=False, confidenceRating=False)

    assert counts["trialStart"] == counts["trialStop"] == 4
    assert counts["confidenceStart"] == counts["confidenceStop"] == 0


@pytest.mark.parametrize(
    "triggers, error",
    [({"listeningStart": print}, ValueError), ({"trialStart": 1}, TypeError)],
)
def test_bad_triggers_are_refused(fake_psychopy, tmp_path, triggers, error):
    with pytest.raises(error):
        make_parameters(tmp_path, triggers=triggers)


#############
# Autopilot #
#############


def test_the_autopilot_turns_towards_its_aim_and_presses():
    pilot = PATAutopilot(
        np.random.default_rng(0), target=40.0, spread=0.0, notch_interval=0.1
    )
    pilot.start_trial(1)
    assert pilot.aim == 40.0
    # From 0 degrees, later; one notch per interval at most
    assert pilot.frame(0.0, 0.0, 10.0) == (1, False)
    assert pilot.frame(0.05, 10.0, 10.0) == (0, False)
    assert pilot.frame(0.1, 10.0, 10.0) == (1, False)
    # From 350 degrees the short way is later, through 0
    assert pilot.frame(0.25, 350.0, 10.0)[0] == 1
    # From 60 degrees, earlier
    assert pilot.frame(0.5, 60.0, 10.0)[0] == -1
    # Within half a notch: no turn, and the press once it has settled
    assert pilot.frame(1.0, 44.0, 10.0) == (0, False)
    assert pilot.frame(1.1, 44.0, 10.0) == (0, False)
    assert pilot.frame(1.25, 44.0, 10.0) == (0, True)
    # Tutorial screens: roll the way asked, or only press
    assert pilot.frame(2.0, 44.0, 10.0, roll=-1) == (-1, True)
    assert pilot.frame(3.0, 44.0, 10.0, wheel=False) == (0, True)
    # No phase yet, nothing to aim at
    assert pilot.frame(4.0, math.nan, 10.0) == (0, False)
    assert [e["event"] for e in pilot.log] == ["trial"]


def test_the_autopilot_runs_a_session(fake_psychopy, tmp_path):
    """Tutorial, practice and main trials with nobody at the keyboard."""
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=4, nPractice=2)
    pilot = PATAutopilot(
        parameters["rng"], target=95.0, spread=0.0, notch_interval=0.0, settle=0.0
    )
    parameters["autopilot"] = pilot
    fake_psychopy.policy = lambda keyList: []  # no key is ever pressed

    run(parameters, runTutorial=True)

    assert parameters["aborted"] is False
    assert [s[0] for s in engine.started] == [TUTORIAL_TRIAL] + list(range(1, 7))
    final = read(parameters["paths"].path("final"))
    assert len(final) == 6
    # The dial stops within half a notch of the aim, whatever the start phase
    assert (final["ChosenPhaseDeg"] - 95.0).abs().max() <= 5.0
    assert final["Confidence"].between(1, 10).all()
    assert (final["Confidence"] == final["Confidence"].round()).all()  # on a step
    np.testing.assert_allclose(final["ConfidenceUnit"], (final["Confidence"] - 1) / 9)
    rated = [e for e in pilot.log if e["event"] == "rate"]
    assert len(rated) == 6
    # The tutorial screens rolled the way they asked, three notches each
    assert sum(n > 0 for n in engine.nudges) >= 3
    assert sum(n < 0 for n in engine.nudges) >= 3


def test_the_autopilot_tutorial_on_a_clock_of_another_origin(fake_psychopy, tmp_path):
    """The dial loop reads the engine's clock, not one of its own.

    On Linux without pylsl the task's fallback clock and the beat source's
    (PsychToolbox's epoch-based ``GetSecs``) differ by decades, and a loop
    timing beeps on the wrong one never heard one: the tutorial hung.
    """
    engine = FakeEngine()
    base = engine.clock
    engine.clock = lambda: base() + 1.0e9
    parameters = make_parameters(tmp_path, engine=engine, nTrials=1, nPractice=0)
    parameters["tutorialStageTimeout"] = 5.0
    parameters["autopilot"] = PATAutopilot(
        parameters["rng"], target=95.0, spread=0.0, notch_interval=0.0, settle=0.0
    )

    tutorial(parameters)

    assert engine.ended == 1
    assert sum(n > 0 for n in engine.nudges) >= parameters["tutorialNotches"]
    assert sum(n < 0 for n in engine.nudges) >= parameters["tutorialNotches"]


class SilentEngine(FakeEngine):
    """Polled, but never plays a beep: an ECG that finds no beat."""

    def poll(self) -> None:
        self.polls += 1


def test_a_tutorial_without_beeps_ends_on_its_timeout(fake_psychopy, tmp_path, caplog):
    engine = SilentEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=1, nPractice=0)
    parameters["tutorialStageTimeout"] = 0.2
    parameters["autopilot"] = PATAutopilot(parameters["rng"], target=95.0)

    tutorial(parameters)

    assert engine.ended == 1
    assert engine.stops == 1
    assert engine.nudges == []
    assert "tutorial was skipped" in caplog.text
