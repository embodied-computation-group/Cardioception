# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Fire the task's event callbacks.

Both ``getParameters`` docstrings promise a ``triggers`` dictionary of callables
run at the trial events, which is the documented way to drive a parallel port,
an LSL marker stream or an amplifier. It never worked. The Heartbeat Counting
task referenced the dictionary at eight points and every one was a bare
expression statement:

    parameters["triggers"]["trialStart"]  # Send trigger or None

which looks up the callable and discards it. The missing ``()`` meant a user who
followed the documentation got no triggers and no error, and an EEG or fMRI
dataset with no event markers, discovered at analysis. flake8 does not report
pointless statements, so continuous integration stayed green. The Heart Rate
Discrimination task documented the same dictionary but never created it, so
following its documentation raised ``KeyError``.

``fire`` calls the callback, and ``validate`` fails at launch rather than at
trial eighty if a caller installs something that is not callable.
"""

from typing import Any, Dict, Optional

EVENTS = (
    "trialStart",
    "trialStop",
    "listeningStart",
    "listeningStop",
    "decisionStart",
    "decisionStop",
    "confidenceStart",
    "confidenceStop",
)


def default_triggers() -> Dict[str, Optional[Any]]:
    """A dictionary with every event present and unset."""
    return {name: None for name in EVENTS}


def validate(triggers: Optional[Dict[str, Any]]) -> Dict[str, Optional[Any]]:
    """Check a user-supplied trigger mapping before the task starts."""
    if triggers is None:
        return default_triggers()
    unknown = set(triggers) - set(EVENTS)
    if unknown:
        raise ValueError(
            f"unknown trigger event(s): {sorted(unknown)}. "
            f"Valid events are {list(EVENTS)}"
        )
    for name, callback in triggers.items():
        if callback is not None and not callable(callback):
            raise TypeError(
                f"triggers[{name!r}] should be callable or None, "
                f"got {type(callback).__name__}"
            )
    merged = default_triggers()
    merged.update(triggers)
    return merged


def fire(parameters: dict, event: str) -> None:
    """Run the callback registered for ``event``, if there is one."""
    callback = (parameters.get("triggers") or {}).get(event)
    if callback is not None:
        callback()
