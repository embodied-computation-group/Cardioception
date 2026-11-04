# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Participant-facing text of the Heartbeat Counting task.

The strings live in ``texts/<language>.yaml`` beside this module, in the same
format as the HRD's (:mod:`cardioception.HRD.languages`), and are loaded and
checked by the same code, :mod:`cardioception._texts`. Only the directory and
the required keys differ. None of the HBC's strings depends on the response
device, so a file has ``texts`` and no ``variants``.

0.7.2 added German as a Python function beside the English one. The two were
converted to YAML string for string, and ``tests/data/hbc_language_snapshot.json``
holds what they said, so the conversion is checked.

To add a language, copy ``texts/english.yaml``, translate the values, and pass
its filename stem as ``language``. Keys are not translated.
"""

import os
from typing import Any, Dict, List

from .. import _texts

TEXTS_DIR = os.path.join(os.path.dirname(__file__), "texts")

#: Every key a language must define. Checked at load, so a language that is
#: missing one fails at launch rather than at the screen that needed it.
#: ``Training`` is not shown by the task at present but every language has
#: always defined it, and ``labelsRating`` holds the two end labels of the
#: confidence scale.
REQUIRED_KEYS = frozenset(
    {
        "Count",
        "Rest",
        "Training",
        "Tutorial1",
        "Tutorial2",
        "Tutorial3",
        "Tutorial4",
        "Tutorial5",
        "Tutorial6",
        "Tutorial7",
        "Tutorial8",
        "Tutorial9",
        "confidence",
        "labelsRating",
        "nCount",
    }
)


def available() -> List[str]:
    """Languages that can be passed as ``language``."""
    return _texts.available(TEXTS_DIR)


def get_texts(language: str) -> Dict[str, Any]:
    """Every string this session will show the participant.

    Parameters
    ----------
    language :
        A filename stem in ``texts/``. :func:`available` lists them.

    Raises
    ------
    ValueError
        If the language does not exist, or its file is missing a key. Both are
        raised at setup, before any window opens.

    """
    return _texts.get_texts(language, texts_dir=TEXTS_DIR, required=REQUIRED_KEYS)
