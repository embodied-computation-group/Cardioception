# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Participant-facing text, loaded from ``texts/*.yaml``.

This was 484 lines of Python holding the same 31 strings four times over. To
add a language you copied a function and translated inside it; to fix a typo
you edited Python. Nothing checked that the four functions agreed on which keys
they defined, so a language missing a key raised ``KeyError`` at whatever trial
first needed that screen — with a participant in the chair.

The strings now live in one YAML file per language, and :func:`get_texts`
validates the whole set against :data:`REQUIRED_KEYS` when the session starts.
A missing or misspelled key is an error at launch.

To add a language, copy ``texts/english.yaml``, translate the values, and pass
its filename stem as ``language``. Keys are not translated.
"""

import os
from typing import AbstractSet, Any, Dict, List, Optional

import yaml

TEXTS_DIR = os.path.join(os.path.dirname(__file__), "texts")

#: Every key a language must define. Checked at load, so a language that is
#: missing one fails at launch rather than at the screen that needed it.
REQUIRED_KEYS = frozenset(
    {
        "Confidence",
        "Decision",
        "Tutorial1",
        "Tutorial2",
        "Tutorial3_icon",
        "Tutorial3_responses",
        "Tutorial3bis",
        "Tutorial3ter",
        "Tutorial4",
        "Tutorial5",
        "Tutorial6",
        "VASlabels",
        "checkOximeter",
        "correctResponse",
        "done",
        "faster",
        "incorrectResponse",
        "pulseTutorial1",
        "pulseTutorial2",
        "pulseTutorial3",
        "pulseTutorial4",
        "responseText",
        "slower",
        "stayStill",
        "textBreaks",
        "textHeartListening",
        "textNext",
        "textTaskStart",
        "textToneListening",
        "textWaitTrigger",
        "tooLate",
    }
)


def available(texts_dir: Optional[str] = None) -> List[str]:
    """Languages that can be passed as ``language``.

    ``texts_dir`` defaults to :data:`TEXTS_DIR`, read when this is called.
    Another task passes its own directory.
    """
    if texts_dir is None:
        texts_dir = TEXTS_DIR
    if not os.path.isdir(texts_dir):
        return []
    return sorted(
        f[: -len(".yaml")] for f in os.listdir(texts_dir) if f.endswith(".yaml")
    )


def _resolve(key: str, variant: Dict[str, Any], device: str, exteroception: bool):
    """Pick one value from a key that depends on how the session is configured."""
    axis, values = variant["axis"], variant["values"]
    if axis == "device":
        selector = device
    elif axis == "exteroception":
        selector = str(exteroception).lower()
    elif axis == "device+exteroception":
        selector = f"{device}/{str(exteroception).lower()}"
    else:
        raise ValueError(f"{key}: unknown variant axis {axis!r}")

    if selector not in values:
        raise ValueError(f"{key}: no text for {selector!r}. Defined: {sorted(values)}.")
    return values[selector]


def get_texts(
    language: str,
    device: str,
    exteroception: bool,
    texts_dir: Optional[str] = None,
    required: Optional[AbstractSet[str]] = None,
) -> Dict[str, Any]:
    """Every string this session will show the participant.

    Parameters
    ----------
    language :
        A filename stem in ``texts/``. :func:`available` lists them.
    device :
        ``"keyboard"`` or ``"mouse"``. Selects the wording of the response
        instructions, which name the actual keys or buttons.
    exteroception :
        Whether the session includes the exteroceptive condition, which changes
        what the tutorial says is coming.
    texts_dir :
        The directory holding the language files. Defaults to
        :data:`TEXTS_DIR`, read when this is called. Another task passes its
        own directory.
    required :
        The keys every language must define. Defaults to
        :data:`REQUIRED_KEYS`, read when this is called.

    Raises
    ------
    ValueError
        If the language does not exist, or its file is missing a key. Both are
        raised here, at setup, rather than at the screen that needed the text.

    """
    if texts_dir is None:
        texts_dir = TEXTS_DIR
    if required is None:
        required = REQUIRED_KEYS

    path = os.path.join(texts_dir, f"{language}.yaml")
    if not os.path.isfile(path):
        raise ValueError(
            f"No texts for language {language!r}. "
            f"Available: {available(texts_dir)}. "
            f"Add {language}.yaml to {texts_dir} to define it."
        )

    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    plain = document.get("texts") or {}
    variants = document.get("variants") or {}

    # Completeness is checked against the file, not against what this session
    # resolves to, so a language missing a key fails at launch whatever the
    # session was configured to do.
    missing = set(required) - (set(plain) | set(variants))
    if missing:
        raise ValueError(
            f"{path} is missing {sorted(missing)}. Every language must define "
            f"all {len(required)} keys; see "
            f"{os.path.join(texts_dir, 'english.yaml')}."
        )

    texts: Dict[str, Any] = dict(plain)
    for key, variant in variants.items():
        value = _resolve(key, variant, device, exteroception)
        # A null means the key does not apply here. The exteroceptive tutorial
        # screens are simply absent from a session that has no such condition.
        if value is not None:
            texts[key] = value
    return texts


def _shim(language: str):
    """Keep the old per-language function importable.

    These were public through ``cardioception.HRD``. ``setup`` never affected
    the result — verified across all four languages, both devices and both
    exteroception settings — and is accepted only so existing calls still work.
    """

    def loader(device: str, setup: str = "behavioral", exteroception: bool = True):
        return get_texts(language, device, exteroception)

    loader.__name__ = language
    loader.__doc__ = (
        f"Deprecated. Texts for {language}; use "
        f"get_texts({language!r}, device, exteroception)."
    )
    return loader


english = _shim("english")
danish = _shim("danish")
danish_children = _shim("danish_children")
french = _shim("french")
german = _shim("german")
