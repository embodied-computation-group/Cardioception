# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Participant-facing text of the Phase Adjustment Task.

The instructions follow Hodgetts et al. (2026): move the beeps with the dial
until they fall on the heartbeat, explore freely, press space when they match,
then rate confidence from 1 (not at all) to 10 (extremely). Sit still, breathe
normally, do not tense the muscles, and attend to one place in the body. In the
exteroceptive task a vibration on the hand takes the place of the heartbeat.

The first live run showed that "turn the dial" was not enough: participants
need to hear that the beeps never change speed, that the wheel shifts each beep
within the beat, and which wheel that is.

The strings live in ``texts/<language>.yaml`` beside this module, in the
format of the HRD's (:mod:`cardioception.HRD.languages`), and are loaded and
checked by the same code, :mod:`cardioception._texts`. Three rules are the
PAT's own:

- **Device and exteroception** are ``variants``, as for the HRD: the rating
  help names the wheel or the mouse (axis ``device``), and every text that
  names the heartbeat names the vibration in the exteroceptive task (axis
  ``exteroception``).
- **The ends of the confidence scale** are written ``{low}`` and ``{high}``
  and replaced by the ends of the session's scale, as ``f"{end:g}"``. Only
  those two names are replaced, by plain substitution rather than
  ``str.format``, so other braces are left alone: ``tutorialProgress`` keeps
  its ``{done}`` and ``{total}`` for the task to fill in on every frame.
- **The dial page.** The ``instructions`` page that reads ``{dial}`` is
  replaced by ``dialPage`` when the dial is shown and by ``noDialPage`` when
  it is not. Neither key is in the returned dictionary.

The two languages were converted from the Python functions that held them
string for string, and ``tests/data/pat_language_snapshot.json`` holds what
those functions returned for every device, exteroception, dial and scale, so
the conversion is checked.

To add a language, copy ``texts/english.yaml``, translate the values, and pass
its filename stem as ``language``. Keys and placeholders are not translated.
"""

import os
from typing import Any, Dict, List

from .. import _texts

TEXTS_DIR = os.path.join(os.path.dirname(__file__), "texts")

#: Every key a language must define. Checked at load, so a language that is
#: missing one fails at launch rather than at the screen that needed it.
REQUIRED_KEYS = frozenset(
    {
        "Confidence",
        "VASlabels",
        "dialPage",
        "done",
        "instructions",
        "noDialPage",
        "ratingHelp",
        "textBreaks",
        "textNext",
        "textNextTrial",
        "textPracticeStart",
        "textTaskStart",
        "tooLate",
        "tutorialEarlier",
        "tutorialEnd",
        "tutorialFree",
        "tutorialIntro",
        "tutorialLater",
        "tutorialListen",
        "tutorialProgress",
        "tutorialReady",
        "waitingFirstTone",
    }
)

#: The instructions page replaced by the dial page, or by the page without it.
DIAL_PAGE = "{dial}"


def available() -> List[str]:
    """Languages that can be passed as ``language``."""
    return _texts.available(TEXTS_DIR)


def _fill(value: Any, low: str, high: str) -> Any:
    """Put the scale ends in place of ``{low}`` and ``{high}``, and nothing else."""
    if isinstance(value, list):
        return [_fill(v, low, high) for v in value]
    if isinstance(value, str):
        return value.replace("{low}", low).replace("{high}", high)
    return value


def get_texts(
    language: str,
    device: str = "keyboard",
    extero: bool = False,
    low: float = 1,
    high: float = 10,
    showDial: bool = True,
) -> Dict[str, Any]:
    """Every string this session will show the participant.

    Parameters
    ----------
    language :
        A filename stem in ``texts/``. :func:`available` lists them.
    device :
        The confidence rating device, ``"keyboard"`` (the wheel) or
        ``"mouse"``.
    extero :
        If ``True``, the texts of the exteroceptive task (vibration instead of
        heartbeat).
    low, high :
        Ends of the confidence scale, named in the instructions.
    showDial :
        If ``True``, the instructions describe the dial on the screen.

    Raises
    ------
    ValueError
        If the language does not exist, or its file is missing a key. Both are
        raised at setup, before any window opens.

    """
    texts = _texts.get_texts(
        language,
        texts_dir=TEXTS_DIR,
        required=REQUIRED_KEYS,
        device=device,
        exteroception=extero,
    )
    texts = {k: _fill(v, f"{low:g}", f"{high:g}") for k, v in texts.items()}
    dial = texts.pop("dialPage")
    no_dial = texts.pop("noDialPage")
    page = dial if showDial else no_dial
    texts["instructions"] = [
        page if text == DIAL_PAGE else text for text in texts["instructions"]
    ]
    return texts
