# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The PsychoPy side of the Phase Adjustment Task, without hardware.

A fake engine stands in for :class:`cardioception.PAT.engine.PhaseEngine`
(the interface in the task contract) and a fake PsychoPy replays key presses
and wheel turns, so these tests need no ECG, no sound card and no display.
One test opens a small real window, and is skipped where that is impossible.
"""

import math
import os
import sys
import time
import types
from typing import Callable, List, Optional

import numpy as np
import pandas as pd
import pytest

from cardioception.PAT.languages import danish, english
from cardioception.PAT.parameters import getParameters, startPhaseSequence
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
        self.ended = 0
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

    def stop_tones(self) -> None:
        self.active = False
        self.stops += 1

    def end_trial(self) -> dict:
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
    """Half a notch per wheel read, so every second frame moves the dial."""

    def __init__(self, *args, **kwargs):
        self.wheel = 0.5
        self.pressed = False
        self.x = 0.0

    def getWheelRel(self) -> np.ndarray:
        return np.array([0.0, self.wheel])

    def getPressed(self):
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
    return keyboard


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
    assert parameters["confScale"] == [1, 10]
    assert parameters["labelsRating"] == ["Not at all", "Extremely"]
    assert parameters["results_df"].empty and parameters["tones"] == []
    assert isinstance(parameters["win"], FakeWindow)
    assert parameters["win"].kwargs["fullscr"] is False
    assert parameters["win"].mouseVisible is False

    danish_parameters = make_parameters(tmp_path / "da", language="danish")
    assert danish_parameters["labelsRating"] == ["Slet ikke", "Ekstremt"]


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
        {"confScale": (10, 1)},
    ],
)
def test_parameters_reject_bad_input(fake_psychopy, tmp_path, kwargs):
    with pytest.raises(ValueError):
        make_parameters(tmp_path, **kwargs)


def test_parameters_need_a_recorder(fake_psychopy, tmp_path):
    with pytest.raises(ValueError, match="recorder"):
        getParameters(resultPath=str(tmp_path))


def test_parameters_refuse_to_overwrite_a_run(fake_psychopy, tmp_path):
    (tmp_path / "final.txt").write_text("Trial\n1\n")
    with pytest.raises(ValueError, match="already holds"):
        make_parameters(tmp_path)


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


#########
# Texts #
#########


@pytest.mark.parametrize("language", [english, danish])
@pytest.mark.parametrize("extero", [False, True])
@pytest.mark.parametrize("device", ["keyboard", "mouse"])
def test_texts(language, extero, device):
    texts = language(device=device, extero=extero)
    assert set(texts) == set(english(device=device, extero=extero))
    assert len(texts["instructions"]) == 7
    assert (
        len(language(device=device, extero=extero, showDial=False)["instructions"]) == 7
    )
    flat = " ".join(
        " ".join(v) if isinstance(v, list) else str(v) for v in texts.values()
    )
    assert "—" not in flat and "–" not in flat  # no em or en dashes
    assert "10" in texts["instructions"][5]
    vibration = "vibration" in flat
    assert vibration is extero
    # The wheel is named, and the beeps never change speed
    assert "scroll" in texts["instructions"][1]
    assert any(word in texts["instructions"][0] for word in ("never", "aldrig"))


def test_texts_describe_the_dial_only_when_shown():
    with_dial = " ".join(english(showDial=True)["instructions"])
    without = " ".join(english(showDial=False)["instructions"])
    assert "pointer" in with_dial and "pointer" not in without


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

    final = read(tmp_path / "final.txt")
    assert list(final.columns) == FINAL_COLUMNS
    assert len(final) == 1
    assert final.loc[0, "Block"] == "practice"
    assert final.loc[0, "StartPhaseDeg"] == 90
    assert bool(final.loc[0, "Extero"]) is False

    trial(parameters, 2, "practice", 180.0)
    assert len(read(tmp_path / "final.txt")) == 2  # saved after every trial

    tones = read(tmp_path / "tones.txt")
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
    assert not os.path.exists(tmp_path / "tones.txt")  # nothing saved


def test_run_saves_everything(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nTrials=12, nPractice=2)
    fake_psychopy.policy = space_after_polls(engine, parameters=parameters)

    run(parameters, runTutorial=True, confidenceRating=True)

    assert parameters["aborted"] is False
    # Tutorial, then 2 practice and 12 main trials, numbered across blocks
    assert [s[0] for s in engine.started] == [TUTORIAL_TRIAL] + list(range(1, 15))
    final = read(tmp_path / "final.txt")
    assert list(final["Trial"]) == list(range(1, 15))
    assert list(final["Block"]) == ["practice"] * 2 + ["main"] * 12
    assert list(final["StartPhaseDeg"]) == (
        parameters["startPhasePractice"] + parameters["startPhaseMain"]
    )
    assert final["Confidence"].between(1, 10).all()

    tones = read(tmp_path / "tones.txt")
    assert TUTORIAL_TRIAL not in set(tones["Trial"])  # the tutorial is not saved
    assert set(tones["Trial"]) == set(range(1, 15))
    assert (
        tones.groupby("Trial")["Block"].first() == final.set_index("Trial")["Block"]
    ).all()

    saved = read(tmp_path / "parameters.txt").set_index("Parameter")["Value"]
    assert saved["mode"] == '"relative"'
    assert saved["nTrials"] == "12"
    assert "engine" not in saved.index and "win" not in saved.index


def test_run_without_rating(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    fake_psychopy.policy = space_after_polls(engine)

    run(parameters, runTutorial=False, confidenceRating=False)

    final = read(tmp_path / "final.txt")
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
    assert engine.stops >= 3  # the tones of the aborted trial were stopped
    final = read(tmp_path / "final.txt")
    assert list(final["Trial"]) == [1, 2]
    assert not engine.closed  # left to the caller


def test_escape_in_the_rating_keeps_the_trial(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, nPractice=0)
    normal = space_after_polls(engine)

    def policy(keyList):
        if engine.ended == 1 and keyList == ["escape"]:
            return ["escape"]  # while the first rating is on screen
        return normal(keyList)

    fake_psychopy.policy = policy
    run(parameters, runTutorial=False)

    assert parameters["aborted"] is True
    final = read(tmp_path / "final.txt")
    assert len(final) == 1 and final["Confidence"].isna().all()


def test_escape_before_any_trial_writes_no_results(fake_psychopy, tmp_path):
    parameters = make_parameters(tmp_path)
    fake_psychopy.policy = lambda keyList: ["escape"]

    run(parameters)

    assert parameters["aborted"] is True
    assert not os.path.exists(tmp_path / "final.txt")
    # So the same session can be started again
    make_parameters(tmp_path)


def test_mouse_rating(fake_psychopy, tmp_path):
    engine = FakeEngine()
    parameters = make_parameters(tmp_path, engine=engine, device="mouse")
    fake_psychopy.policy = space_after_polls(engine)
    parameters["myMouse"].pressed = True
    parameters["myMouse"].x = 0.35  # right end of the slider

    row = trial(parameters, 1, "main", 0.0)

    assert row["Confidence"] == 10
    assert row["ConfidenceRT"] > parameters["minRatingTime"]


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

    tones = read(tmp_path / "tones.txt")
    assert set(tones["Kind"]) == {"tone", "vibration"}
    assert set(tones.loc[tones["Kind"] == "vibration", "Anchor"]) == {"virtual"}
    assert tones["Onset"].notna().all()
    assert list(read(tmp_path / "final.txt").columns) == FINAL_COLUMNS


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
    from cardioception.PAT._rating import wheel_rating

    win = FakeWindow()
    fake_psychopy.policy = lambda keyList: ["space"] if keyList else []
    confidence, _, provided = wheel_rating(
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
    waitInput(parameters)

    assert len(calls) == 6  # only space moved on
    assert engine.nudges == []
    assert engine.idlePolls == 6  # beats are still detected on text screens


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
