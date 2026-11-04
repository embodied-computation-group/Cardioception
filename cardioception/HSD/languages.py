# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Participant-facing text of the Heartbeat Synchrony Discrimination task.

The strings live in ``texts/<language>.yaml`` beside this module, in the same
format as the HRD's (:mod:`cardioception.HRD.languages`), and are loaded and
checked by the same code. Only the directory and the required keys differ.

English is the only language so far. To add one, copy ``texts/english.yaml``,
translate the values, and pass its filename stem as ``language``.
"""

import os
from typing import Any, Dict, List

from cardioception.HRD import languages as _shared

TEXTS_DIR = os.path.join(os.path.dirname(__file__), "texts")

#: Every key a language must define. Checked at load, so a language that is
#: missing one fails at launch rather than at the screen that needed it.
REQUIRED_KEYS = frozenset(
    {
        "Confidence",
        "Decision",
        "Tutorial1",
        "Tutorial2",
        "Tutorial3",
        "VASlabels",
        "done",
        "responseText",
        "textBreaks",
        "textNext",
        "textTaskStart",
        "tooLate",
        "trainPrompt",
    }
)


def available() -> List[str]:
    """Languages that can be passed as ``language``."""
    return _shared.available(TEXTS_DIR)


def get_texts(language: str, device: str) -> Dict[str, Any]:
    """Every string this session will show the participant.

    Parameters
    ----------
    language :
        A filename stem in ``texts/``. :func:`available` lists them.
    device :
        Selects the wording of the instructions that name keys. Only
        ``"keyboard"`` is written so far.

    Raises
    ------
    ValueError
        If the language does not exist, or its file is missing a key.

    """
    return _shared.get_texts(
        language,
        device,
        exteroception=False,
        texts_dir=TEXTS_DIR,
        required=REQUIRED_KEYS,
    )
