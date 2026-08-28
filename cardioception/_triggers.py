# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Event callbacks fired at trial boundaries, for parallel port or LSL markers.

Registered as {event: callable} in ``parameters["triggers"]``. ``validate``
rejects unknown events and non-callables at setup rather than mid-session.
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
