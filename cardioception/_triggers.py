# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Event callbacks fired at trial boundaries, for parallel port or LSL markers.

Registered as {event: callable} in ``parameters["triggers"]``. ``validate``
rejects unknown events and non-callables at setup rather than mid-session.

:data:`EVENTS` are the Heart Rate Discrimination task's events. A task with a
different trial structure passes its own tuple as ``events``.
"""

from typing import Any, Dict, Optional, Sequence

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


def default_triggers(events: Sequence[str] = EVENTS) -> Dict[str, Optional[Any]]:
    """A dictionary with every event in ``events`` present and unset."""
    return {name: None for name in events}


def validate(
    triggers: Optional[Dict[str, Any]], events: Sequence[str] = EVENTS
) -> Dict[str, Optional[Any]]:
    """Check a user-supplied trigger mapping before the task starts.

    ``events`` is the task's list of event names; anything outside it is
    rejected, and any it names that ``triggers`` leaves out is filled in unset.
    """
    if triggers is None:
        return default_triggers(events)
    unknown = set(triggers) - set(events)
    if unknown:
        raise ValueError(
            f"unknown trigger event(s): {sorted(unknown)}. "
            f"Valid events are {list(events)}"
        )
    for name, callback in triggers.items():
        if callback is not None and not callable(callback):
            raise TypeError(
                f"triggers[{name!r}] should be callable or None, "
                f"got {type(callback).__name__}"
            )
    merged = default_triggers(events)
    merged.update(triggers)
    return merged


def fire(parameters: dict, event: str) -> None:
    """Run the callback registered for ``event``, if there is one."""
    callback = (parameters.get("triggers") or {}).get(event)
    if callback is not None:
        callback()
