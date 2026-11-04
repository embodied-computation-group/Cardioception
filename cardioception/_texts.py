# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Load and check participant-facing text held in YAML, for any task.

Each task keeps one file per language in its own ``texts/`` directory and
names the keys a language must define. This module does the rest: it lists the
languages, reads a file, checks it is complete, and resolves the strings that
depend on how the session is configured. The tasks' own ``languages`` modules
are thin wrappers that pass their directory and key set.

A language file looks like this::

    language: english
    texts:
      done: You have completed the task.
    variants:
      responseText:
        axis: device
        values:
          keyboard: Use the UP and DOWN keys.
          mouse: Use the left and right buttons.

``texts`` holds strings that never change. ``variants`` holds the few that
depend on the session, keyed by an ``axis``: ``device``, ``exteroception`` or
``device+exteroception``. A null value means the key does not apply to that
configuration, and it is left out.
"""

import os
from typing import AbstractSet, Any, Dict, List, Optional

import yaml


def available(texts_dir: str) -> List[str]:
    """The languages defined in ``texts_dir``, one per ``<language>.yaml``."""
    if not os.path.isdir(texts_dir):
        return []
    return sorted(
        f[: -len(".yaml")] for f in os.listdir(texts_dir) if f.endswith(".yaml")
    )


def _resolve(
    key: str,
    variant: Dict[str, Any],
    device: Optional[str],
    exteroception: Optional[bool],
):
    """Pick one value from a key that depends on how the session is configured."""
    axis, values = variant["axis"], variant["values"]
    if axis not in ("device", "exteroception", "device+exteroception"):
        raise ValueError(f"{key}: unknown variant axis {axis!r}")
    # A task that never passes a setting must not have its texts quietly
    # resolved against a guess at it.
    if "device" in axis and device is None:
        raise ValueError(f"{key} varies by device, and no device was given.")
    if "exteroception" in axis and exteroception is None:
        raise ValueError(f"{key} varies by exteroception, and none was given.")

    if axis == "device":
        selector = str(device)
    elif axis == "exteroception":
        selector = str(exteroception).lower()
    else:
        selector = f"{device}/{str(exteroception).lower()}"

    if selector not in values:
        raise ValueError(f"{key}: no text for {selector!r}. Defined: {sorted(values)}.")
    return values[selector]


def get_texts(
    language: str,
    texts_dir: str,
    required: AbstractSet[str],
    device: Optional[str] = None,
    exteroception: Optional[bool] = None,
) -> Dict[str, Any]:
    """Every string a session will show the participant.

    Parameters
    ----------
    language :
        A filename stem in ``texts_dir``. :func:`available` lists them.
    texts_dir :
        The directory holding the language files.
    required :
        The keys every language must define.
    device :
        Selects ``variants`` on the ``device`` axis. A task whose texts never
        vary by device leaves it out.
    exteroception :
        Selects ``variants`` on the ``exteroception`` axis. A task whose texts
        never vary by it leaves it out.

    Raises
    ------
    ValueError
        If the language does not exist, its file is missing a key, or a key
        varies by a setting that was not given. All are raised here, at setup,
        rather than at the screen that needed the text.

    """
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
