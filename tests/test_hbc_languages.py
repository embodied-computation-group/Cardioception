# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The Heartbeat Counting texts, in YAML, and the language they are chosen by.

Nothing here opens a window or plays a sound. Where ``getParameters`` has to
run, PsychoPy is replaced by stand-ins and the recorder by a stub.
"""

import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import pytest
import yaml

from cardioception.HBC import languages
from cardioception.HBC.languages import REQUIRED_KEYS, available, get_texts

SNAPSHOT = json.loads(
    (Path(__file__).parent / "data" / "hbc_language_snapshot.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture
def tmp():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_every_language_survived_the_move_to_yaml():
    """Against a snapshot of the code being replaced.

    The English entry is the inline dictionary ``HBC/parameters.py`` held, with
    the "Guess" and "Certain" labels its default scale carried. The German
    entry is the function 0.7.2 carried. Both were taken before the Python
    was deleted.
    """
    assert sorted(SNAPSHOT) == ["english", "german"]
    for language, expected in SNAPSHOT.items():
        assert get_texts(language) == expected, language


def test_the_two_languages_are_there():
    assert available() == ["english", "german"]


def test_an_unknown_language_fails_and_names_the_others():
    with pytest.raises(ValueError) as raised:
        get_texts("klingon")
    assert "['english', 'german']" in str(raised.value)


@pytest.mark.parametrize("language", ["english", "german"])
def test_every_required_key_is_defined(language):
    assert set(get_texts(language)) == set(REQUIRED_KEYS)


@pytest.mark.parametrize("language", ["english", "german"])
def test_no_text_varies_by_device(language):
    """The HBC has one response device, so nothing should need a variant."""
    path = Path(languages.TEXTS_DIR, f"{language}.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "variants" not in document


def test_the_german_rating_labels():
    assert get_texts("german")["labelsRating"] == ["Geraten", "Sicher"]


# --- through getParameters, without a window ---------------------------------


class _StubRecorder:
    def setup(self):
        return self

    def read(self, duration):
        return self

    def describe(self):
        return {"device": "stub"}


@pytest.fixture
def no_psychopy(monkeypatch):
    """Stand-ins for the PsychoPy objects getParameters creates."""

    def image(**kwargs):
        return types.SimpleNamespace(size=np.array([1.0, 1.0]))

    sound = types.ModuleType("psychopy.sound")
    sound.Sound = lambda *args, **kwargs: object()  # type: ignore[attr-defined]
    visual = types.ModuleType("psychopy.visual")
    visual.Window = lambda **kwargs: types.SimpleNamespace()  # type: ignore
    visual.ImageStim = image  # type: ignore[attr-defined]
    psychopy = types.ModuleType("psychopy")
    psychopy.sound = sound  # type: ignore[attr-defined]
    psychopy.visual = visual  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psychopy", psychopy)
    monkeypatch.setitem(sys.modules, "psychopy.sound", sound)
    monkeypatch.setitem(sys.modules, "psychopy.visual", visual)
    yield
    # Release the session log, so the run directory can be removed on Windows.
    from cardioception._log import start_session_log

    start_session_log(None)


def _parameters(tmp, **kwargs):
    from cardioception.HBC.parameters import getParameters

    return getParameters(
        setup="test", resultPath=tmp, recorder=_StubRecorder(), **kwargs
    )


def _manifest(parameters):
    path = Path(parameters["paths"].directory, "manifest.json")
    return json.loads(path.read_text())


def test_english_is_the_default(tmp, no_psychopy):
    parameters = _parameters(tmp)
    assert parameters["language"] == "english"
    assert parameters["texts"] == SNAPSHOT["english"]
    assert parameters["labelsRating"] == ["Guess", "Certain"]
    assert _manifest(parameters)["language"] == "english"


def test_german_participants_see_german_labels(tmp, no_psychopy):
    parameters = _parameters(tmp, language="german")
    assert parameters["language"] == "german"
    assert parameters["texts"] == SNAPSHOT["german"]
    assert parameters["labelsRating"] == ["Geraten", "Sicher"]
    assert list(parameters["confidenceScale"].labels) == ["Geraten", "Sicher"]
    assert _manifest(parameters)["language"] == "german"


def test_a_scale_passed_in_keeps_its_own_labels(tmp, no_psychopy):
    from cardioception.scales import DISCRETE_1_7

    scale = DISCRETE_1_7.with_labels(["low", "high"])
    parameters = _parameters(tmp, language="german", confidenceScale=scale)
    assert parameters["labelsRating"] == ["low", "high"]


def test_an_unknown_language_fails_before_anything_is_created(tmp, monkeypatch):
    """No run directory, and PsychoPy is never reached."""
    monkeypatch.setitem(sys.modules, "psychopy", None)
    from cardioception.HBC.parameters import getParameters

    with pytest.raises(ValueError, match="klingon"):
        getParameters(setup="test", resultPath=tmp, language="klingon")
    assert list(Path(tmp).glob("**/run-*")) == []
