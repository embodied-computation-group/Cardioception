# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Stimulus constructors shared by both tasks.

The two task modules built 64 `visual.TextStim` objects, each spelling out the
same window and the same text height across five lines. That is 369 lines
saying almost nothing, and it hid the differences that matter: nine of the 64
pass a colour, and not always the same one.

Construction stays where it was. These are shorter spellings of the same call,
not a change to when a stimulus is made — building one inside a loop that used
to be built outside it is not timing-neutral.
"""

from typing import Optional, Tuple


def text(
    parameters: dict,
    message: str,
    pos: Tuple[float, float] = (0.0, 0.0),
    color: Optional[str] = None,
    height: Optional[float] = None,
    **kwargs,
):
    """A line of text on the task window.

    Parameters
    ----------
    parameters :
        The task parameters, read for the window and the default text height.
    message :
        What to show.
    pos :
        Centre of the text, in height units.
    color :
        Left to PsychoPy's default (white) when not given. Used for the red
        warnings and the green feedback.
    height :
        Overrides ``parameters["textSize"]``.

    """
    from psychopy import visual

    if color is not None:
        kwargs["color"] = color
    return visual.TextStim(
        parameters["win"],
        height=parameters["textSize"] if height is None else height,
        pos=pos,
        text=message,
        **kwargs,
    )


def fixation(parameters, size: float = 0.1, pos=(0, 0)):
    """The fixation cross shown between trials."""
    from psychopy import visual

    return visual.GratingStim(
        win=parameters["win"], mask="cross", size=size, pos=pos, sf=0
    )
