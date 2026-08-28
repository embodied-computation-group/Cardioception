# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Presentation and input helpers shared by both tasks."""


def accept_press(buttons, armed: bool):
    """Filter a level-triggered mouse state down to a press edge.

    ``Mouse.getPressed`` reports the button's current level and ``clickReset``
    resets click times, not state, so a button still held from an earlier screen
    reads as a fresh press. Returns ``(buttons, armed)``, where a button that
    has not been released since arming reports nothing.
    """
    if not any(buttons):
        return [0, 0, 0], True
    if not armed:
        return [0, 0, 0], False
    return list(buttons), True


def hold(win, duration: float, *stims) -> float:
    """Keep ``stims`` on screen for ``duration`` seconds, flipping every frame.

    Replaces ``core.wait``, which blocks without flipping, so the window stops
    redrawing and no frame intervals are recorded. Durations are unchanged.

    Stimuli must be passed in and are redrawn every frame: PsychoPy clears the
    back buffer on flip, so flipping without drawing blanks the screen.

    Returns the time held, quantised up to the next frame boundary.
    """
    from psychopy import core

    clock = core.Clock()
    while clock.getTime() < duration:
        for stim in stims:
            stim.draw()
        win.flip()
    return clock.getTime()
