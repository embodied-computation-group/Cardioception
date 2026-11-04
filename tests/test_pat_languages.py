# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The Phase Adjustment Task texts, in YAML, and the language they are chosen by.

Nothing here opens a window or plays a sound.
"""

import itertools
import json
from pathlib import Path

import pytest
import yaml

from cardioception.PAT import languages
from cardioception.PAT.languages import REQUIRED_KEYS, available, get_texts

SNAPSHOT = json.loads(
    (Path(__file__).parent / "data" / "pat_language_snapshot.json").read_text(
        encoding="utf-8"
    )
)

LANGUAGES = ("english", "danish")
DEVICES = ("keyboard", "mouse")
COMBINATIONS = list(itertools.product(LANGUAGES, DEVICES, (False, True), (True, False)))


def _key(language, device, extero, dial, low, high) -> str:
    return (
        f"{language}|{device}|extero={str(extero).lower()}|"
        f"dial={str(dial).lower()}|{low}-{high}"
    )


def test_every_text_survived_the_move_to_yaml():
    """Against a snapshot of the functions being replaced.

    ``english`` and ``danish`` in ``PAT/languages.py`` took the device, the
    exteroceptive task, the ends of the confidence scale and whether the dial
    is shown. The snapshot holds what they returned for every device,
    exteroception and dial, on two scales, and was taken before the Python
    was deleted.
    """
    assert len(SNAPSHOT) == 32
    seen = set()
    for language, device, extero, dial in COMBINATIONS:
        for low, high in ((1, 10), (0, 100)):
            key = _key(language, device, extero, dial, low, high)
            texts = get_texts(
                language,
                device=device,
                extero=extero,
                low=low,
                high=high,
                showDial=dial,
            )
            assert texts == SNAPSHOT[key], key
            seen.add(key)
    assert seen == set(SNAPSHOT)


def test_the_two_languages_are_there():
    assert available() == ["danish", "english"]


def test_an_unknown_language_fails_and_names_the_others():
    with pytest.raises(ValueError) as raised:
        get_texts("klingon")
    assert "['danish', 'english']" in str(raised.value)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_required_key_is_defined(language):
    """The helper keys of the dial page are used up and not returned."""
    texts = get_texts(language)
    assert set(texts) == set(REQUIRED_KEYS) - {"dialPage", "noDialPage"}


@pytest.mark.parametrize("language, device, extero, dial", COMBINATIONS)
def test_texts(language, device, extero, dial):
    texts = get_texts(language, device=device, extero=extero, showDial=dial)
    assert len(texts["instructions"]) == 7
    flat = " ".join(
        " ".join(v) if isinstance(v, list) else str(v) for v in texts.values()
    )
    assert "—" not in flat and "–" not in flat  # no em or en dashes
    assert "{" not in flat.replace("{done}", "").replace("{total}", "")
    assert "10" in texts["instructions"][5]
    assert ("vibration" in flat) is extero
    # The wheel is named, and the beeps never change speed
    assert "scroll" in texts["instructions"][1]
    assert any(word in texts["instructions"][0] for word in ("never", "aldrig"))


def test_the_dial_is_described_only_when_shown():
    with_dial = " ".join(get_texts("english", showDial=True)["instructions"])
    without = " ".join(get_texts("english", showDial=False)["instructions"])
    assert "pointer" in with_dial and "pointer" not in without


def test_the_scale_ends_are_filled_in_and_nothing_else():
    texts = get_texts("english", low=0, high=100)
    assert "from 0 (not at all) to 100 (extremely)" in texts["instructions"][5]
    # Filled in on every frame by the task, so left as they are
    assert texts["tutorialProgress"] == "Rolled {done} of {total}. Then press SPACE."
    assert "from 0.5 (" in get_texts("english", low=0.5)["instructions"][5]


@pytest.mark.parametrize("language", LANGUAGES)
def test_variants_are_by_device_or_exteroception(language):
    """Only the axes the loader knows, and the rating help alone by device."""
    path = Path(languages.TEXTS_DIR, f"{language}.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    axes = {key: v["axis"] for key, v in document["variants"].items()}
    assert set(axes.values()) == {"device", "exteroception"}
    assert [k for k, axis in axes.items() if axis == "device"] == ["ratingHelp"]
    pages = document["variants"]["instructions"]["values"]
    for value in pages.values():
        assert value.count(languages.DIAL_PAGE) == 1
