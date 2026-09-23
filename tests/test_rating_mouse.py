# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The mouse confidence rating must not warp the cursor on every frame.

On macOS every cursor warp suppresses hardware mouse events for 0.25 s, so a
loop that warps per frame never sees movement or clicks (issue #103). These
tests drive ``confidenceRatingTask`` with a scripted mouse and a fake PsychoPy,
so they run without a display and without PsychoPy installed.
"""

import sys
import types
from typing import List, Sequence, Tuple

import numpy as np
import pytest


class FakeClock:
    """A clock that advances by a fixed step on every read."""

    def __init__(self, step: float = 0.1):
        self.step = step
        self.t = -step

    def getTime(self) -> float:
        self.t += self.step
        return self.t

    def reset(self) -> None:
        self.t = -self.step


class FakeMarker:
    size = (0.0, 0.0)
    color = "white"


class FakeSlider:
    def __init__(self, **kwargs):
        self.marker = FakeMarker()
        self.markerPos = 0.0

    def draw(self) -> None:
        pass


class FakeTextStim:
    def __init__(self, *args, **kwargs):
        self.color = kwargs.get("color", "white")

    def draw(self) -> None:
        pass


class FakeWindow:
    def __init__(self):
        self.mouseVisible = True
        self.flips = 0

    def flip(self) -> None:
        self.flips += 1


class ScriptedMouse:
    """Replays cursor positions and button states frame by frame."""

    def __init__(
        self,
        positions: Sequence[Tuple[float, float]],
        pressed: Sequence[bool],
    ):
        self.positions = list(positions)
        self.pressed = list(pressed)
        self.frame = 0
        self.setPos_calls: List[Tuple[float, float]] = []
        self.clickResets = 0

    def _clamp(self, i: int, n: int) -> int:
        return min(i, n - 1)

    def getPos(self) -> np.ndarray:
        pos = self.positions[self._clamp(self.frame, len(self.positions))]
        return np.array(pos, dtype=float)

    def getPressed(self, getTime: bool = False):
        left = int(self.pressed[self._clamp(self.frame, len(self.pressed))])
        self.frame += 1
        buttons = [left, 0, 0]
        return (buttons, [0.0, 0.0, 0.0]) if getTime else buttons

    def setPos(self, newPos) -> None:
        self.setPos_calls.append((float(newPos[0]), float(newPos[1])))

    def clickReset(self, buttons=(0, 1, 2)) -> None:
        self.clickResets += 1


@pytest.fixture
def fake_psychopy(monkeypatch):
    core = types.ModuleType("psychopy.core")
    core.Clock = FakeClock  # type: ignore[attr-defined]
    core.wait = lambda t: None  # type: ignore[attr-defined]
    visual = types.ModuleType("psychopy.visual")
    visual.Slider = FakeSlider  # type: ignore[attr-defined]
    visual.TextStim = FakeTextStim  # type: ignore[attr-defined]
    psychopy = types.ModuleType("psychopy")
    psychopy.core = core  # type: ignore[attr-defined]
    psychopy.visual = visual  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psychopy", psychopy)
    monkeypatch.setitem(sys.modules, "psychopy.core", core)
    monkeypatch.setitem(sys.modules, "psychopy.visual", visual)
    return psychopy


def make_parameters(mouse: ScriptedMouse) -> dict:
    return {
        "device": "mouse",
        "win": FakeWindow(),
        "myMouse": mouse,
        "textSize": 0.04,
        "texts": {
            "Confidence": "How confident?",
            "VASlabels": ["a", "b"],
            "tooLate": "!",
        },
        "minRatingTime": 0.5,
        "maxRatingTime": 5.0,
    }


def test_cursor_is_warped_once_when_it_stays_on_screen(fake_psychopy):
    from cardioception.HRD.task import confidenceRatingTask

    # Drift right across the slider for 12 frames (1.2 s), then click.
    positions = [(-0.3 + 0.05 * i, 0.2) for i in range(12)] + [(0.3, 0.2)]
    pressed = [False] * 12 + [True]
    mouse = ScriptedMouse(positions, pressed)
    parameters = make_parameters(mouse)

    confidence, confidenceRT, provided, _ = confidenceRatingTask(parameters)

    assert provided is True
    assert confidence == pytest.approx(50 + (0.3 / 0.5) * 50)
    assert confidenceRT is not None and confidenceRT > parameters["minRatingTime"]
    # One warp to the random start position, and none after that.
    assert len(mouse.setPos_calls) == 1
    x0, y0 = mouse.setPos_calls[0]
    assert -0.25 <= x0 <= 0.25 and y0 == 0.2


def test_marker_is_clamped_without_moving_the_cursor(fake_psychopy):
    from cardioception.HRD.task import confidenceRatingTask

    # Past the end of the slider but still on screen: clamp the marker only.
    positions = [(0.65, 0.25)] * 8
    pressed = [False] * 7 + [True]
    mouse = ScriptedMouse(positions, pressed)

    confidence, _, provided, _ = confidenceRatingTask(make_parameters(mouse))

    assert provided is True
    assert confidence == 100
    assert len(mouse.setPos_calls) == 1


def test_cursor_is_brought_back_from_the_screen_edge(fake_psychopy):
    from cardioception.HRD.task import confidenceRatingTask

    # Two frames far to the right, where a second monitor would begin.
    positions = [(0.0, 0.2)] * 6 + [(0.95, 0.2), (0.95, 0.2), (0.4, 0.2)]
    pressed = [False] * 8 + [True]
    mouse = ScriptedMouse(positions, pressed)

    _, _, provided, _ = confidenceRatingTask(make_parameters(mouse))

    assert provided is True
    edge_warps = mouse.setPos_calls[1:]
    assert len(edge_warps) == 2
    assert all(call == (0.5, 0.2) for call in edge_warps)


def test_early_click_is_ignored(fake_psychopy):
    from cardioception.HRD.task import confidenceRatingTask

    # Click on the first frames (before minRatingTime), then release, then
    # click again after 1 s.
    positions = [(0.0, 0.2)] * 12
    pressed = [True, True, True] + [False] * 8 + [True]
    mouse = ScriptedMouse(positions, pressed)
    parameters = make_parameters(mouse)

    _, confidenceRT, provided, _ = confidenceRatingTask(parameters)

    assert provided is True
    assert confidenceRT > parameters["minRatingTime"]
    assert mouse.frame == 12


def test_timeout_returns_no_rating(fake_psychopy):
    from cardioception.HRD.task import confidenceRatingTask

    mouse = ScriptedMouse([(0.0, 0.2)] * 100, [False] * 100)
    parameters = make_parameters(mouse)
    parameters["maxRatingTime"] = 1.0

    confidence, confidenceRT, provided, _ = confidenceRatingTask(parameters)

    assert provided is False
    assert confidence is None
    assert confidenceRT is None
    assert len(mouse.setPos_calls) == 1
