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

The loader itself started here and was later moved to
:mod:`cardioception._texts`, once the Heartbeat Synchrony and Heartbeat
Counting tasks kept their texts the same way. This module now only names the
HRD's directory and keys, and keeps the HRD's signatures and the deprecated
per-language functions.
"""

import os
from typing import AbstractSet, Any, Dict, List, Optional

from .. import _texts

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
    """
    return _texts.available(TEXTS_DIR if texts_dir is None else texts_dir)


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
        :data:`TEXTS_DIR`, read when this is called.
    required :
        The keys every language must define. Defaults to
        :data:`REQUIRED_KEYS`, read when this is called.

    Raises
    ------
    ValueError
        If the language does not exist, or its file is missing a key. Both are
        raised here, at setup, rather than at the screen that needed the text.

    """
    # The module attributes are read here, at call time, not bound as default
    # arguments, so that a caller (or a test) that reassigns TEXTS_DIR is heard.
    return _texts.get_texts(
        language,
        texts_dir=TEXTS_DIR if texts_dir is None else texts_dir,
        required=REQUIRED_KEYS if required is None else required,
        device=device,
        exteroception=exteroception,
    )


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
