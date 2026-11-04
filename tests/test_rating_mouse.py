# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The mouse confidence rating must not warp the cursor on every frame.

On macOS every cursor warp suppresses hardware mouse events for 0.25 s, so a
loop that warps per frame never sees movement or clicks (issue #103). These
tests drive ``cardioception._session.confidence_rating`` with a scripted mouse
and a fake PsychoPy, so they run without a display, a window or sound.
"""

import sys
import types
from typing import List, Sequence, Tuple

import numpy as np
import pytest

from cardioception.scales import VAS_0_100

TEXTS = {
    "Confidence": "How confident?",
    "VASlabels": ["Guess", "Certain"],
    "tooLate": "Too late",
}

#: The scale ``HRD/parameters.py`` resolves for ``device="mouse"`` when none is
#: given: the 0-100 visual analogue scale, labelled from the language's texts.
MOUSE_SCALE = VAS_0_100.with_labels(TEXTS["VASlabels"])


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
    """Replays cursor positions and button states frame by frame.

    Each ``getPressed`` call polls the next frame, and ``getPos`` reports the
    cursor on the frame polled last. Frame 0 is the poll the rating makes
    before its loop, to arm the button, so loop iteration ``i`` reads frame
    ``i + 1``.
    """

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

    @staticmethod
    def _at(seq: list, i: int):
        return seq[min(max(i, 0), len(seq) - 1)]

    def getPos(self) -> np.ndarray:
        return np.array(self._at(self.positions, self.frame - 1), dtype=float)

    def getPressed(self, getTime: bool = False):
        left = int(self._at(self.pressed, self.frame))
        self.frame += 1
        buttons = [left, 0, 0]
        return (buttons, [0.0, 0.0, 0.0]) if getTime else buttons

    def setPos(self, newPos) -> None:
        self.setPos_calls.append((float(newPos[0]), float(newPos[1])))

    def clickReset(self, buttons=(0, 1, 2)) -> None:
        self.clickResets += 1


@pytest.fixture
def fake_psychopy(monkeypatch):
    # confidence_rating, text() and hold() all import psychopy inside the
    # function, so replacing the modules here is enough to keep PsychoPy out.
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


@pytest.fixture
def rate(fake_psychopy):
    from cardioception._session import confidence_rating

    return confidence_rating


def make_parameters(mouse: ScriptedMouse) -> dict:
    return {
        "device": "mouse",
        "win": FakeWindow(),
        "myMouse": mouse,
        "rng": np.random.default_rng(0),
        "confidenceScale": MOUSE_SCALE,
        "textSize": 0.04,
        "texts": dict(TEXTS),
        "minRatingTime": 0.5,
        "maxRatingTime": 5.0,
    }


def test_hrd_task_reexports_the_shared_rating(fake_psychopy):
    from cardioception._session import confidence_rating
    from cardioception.HRD.task import confidenceRatingTask

    assert confidenceRatingTask is confidence_rating


def test_cursor_is_warped_once_when_it_stays_on_screen(rate):
    # Released when the rating opens, then drift right across the slider for
    # 12 frames (1.2 s) and click.
    positions = [(-0.3 + 0.05 * i, 0.2) for i in range(12)] + [(0.3, 0.2)]
    pressed = [False] * 12 + [True]
    mouse = ScriptedMouse(positions, pressed)
    parameters = make_parameters(mouse)

    confidence, confidenceRT, provided, _ = rate(parameters)

    assert provided is True
    assert confidence == MOUSE_SCALE.from_unit((0.3 / 0.5 + 1) / 2) == 80
    assert confidenceRT is not None and confidenceRT > parameters["minRatingTime"]
    # One warp to the random start position, and none after that.
    assert len(mouse.setPos_calls) == 1
    x0, y0 = mouse.setPos_calls[0]
    assert -0.25 <= x0 <= 0.25 and y0 == 0.2
    assert parameters["win"].mouseVisible is False


def test_marker_is_clamped_without_moving_the_cursor(rate):
    # Past the end of the slider but still on screen: clamp the marker only.
    positions = [(0.65, 0.25)] * 8
    pressed = [False] * 7 + [True]
    mouse = ScriptedMouse(positions, pressed)

    confidence, _, provided, _ = rate(make_parameters(mouse))

    assert provided is True
    assert confidence == MOUSE_SCALE.high
    assert len(mouse.setPos_calls) == 1


def test_cursor_is_brought_back_from_the_screen_edge(rate):
    # Two frames far to the right, where a second monitor would begin.
    positions = [(0.0, 0.2)] * 6 + [(0.95, 0.2), (0.95, 0.2), (0.4, 0.2)]
    pressed = [False] * 8 + [True]
    mouse = ScriptedMouse(positions, pressed)

    confidence, _, provided, _ = rate(make_parameters(mouse))

    assert provided is True
    assert confidence == MOUSE_SCALE.from_unit((0.4 / 0.5 + 1) / 2) == 90
    edge_warps = mouse.setPos_calls[1:]
    assert len(edge_warps) == 2
    assert all(call == (0.5, 0.2) for call in edge_warps)


def test_early_click_is_ignored(rate):
    # Released when the rating opens, so the button is armed. Click on the
    # first loop frames (before minRatingTime), release, then click again
    # after 1 s.
    positions = [(0.0, 0.2)] * 12
    pressed = [False, True, True] + [False] * 8 + [True]
    mouse = ScriptedMouse(positions, pressed)
    parameters = make_parameters(mouse)

    confidence, confidenceRT, provided, _ = rate(parameters)

    assert provided is True
    assert confidence == MOUSE_SCALE.midpoint
    assert confidenceRT > parameters["minRatingTime"]
    assert mouse.frame == 12


def test_timeout_returns_no_rating(rate):
    mouse = ScriptedMouse([(0.0, 0.2)] * 100, [False] * 100)
    parameters = make_parameters(mouse)
    parameters["maxRatingTime"] = 1.0

    confidence, confidenceRT, provided, _ = rate(parameters)

    assert provided is False
    assert confidence is None
    assert confidenceRT is None
    assert len(mouse.setPos_calls) == 1
    # Once when the scale opens and once on timeout.
    assert mouse.clickResets == 2
