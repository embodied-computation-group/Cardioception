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

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


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


@dataclass(frozen=True)
class Screen:
    """One instruction screen.

    The tutorials were a dozen near-identical blocks of "build the text, build
    the prompt, hold, wait". Written as a table the sequence is visible: what
    participants are told, in what order, and which screens a given session
    skips. Changing that is then a one-line edit rather than a code change.

    Parameters
    ----------
    texts :
        ``(key, position)`` pairs, looked up in ``parameters["texts"]`` and
        drawn in the order given.
    image :
        A key in ``parameters`` holding an image stimulus, e.g.
        ``"handSchema"``.
    image_first :
        Draw the image before the text. Only matters where the two overlap,
        and is set to preserve the original draw order rather than to change
        anything.
    prompt :
        Draw the "press space to continue" line at the bottom.
    seconds :
        Minimum time on screen before input is accepted.
    wait :
        Wait for the participant afterwards. ``False`` where the screen leads
        straight into something else, such as the finger-number question.
    requires :
        Skip this screen unless the named text key holds something. The Danish
        children's version leaves ``pulseTutorial2`` empty to drop that screen.

    """

    texts: Sequence[Tuple[str, Tuple[float, float]]]
    image: Optional[str] = None
    image_first: bool = False
    prompt: bool = True
    seconds: float = 1.0
    wait: bool = True
    requires: Optional[str] = None
    extero_only: bool = False

    def skipped(self, parameters: dict) -> bool:
        if self.extero_only and not parameters["ExteroCondition"]:
            return True
        return bool(self.requires) and not parameters["texts"].get(self.requires)


@dataclass(frozen=True)
class Practice:
    """A block of practice trials: a short run of the real thing.

    A tutorial is not a slideshow. It is the experiment in miniature, with
    helper text between the phases, and each phase differs in what the
    participant is asked to do — judge with feedback, then judge and rate
    without it. Those differences were literals inside ``tutorial()``.

    Parameters
    ----------
    modality :
        ``"Intero"`` or ``"Extero"``.
    count :
        Name of the parameter holding the number of trials, so the length of a
        practice block is set where every other design value is set.
    feedback :
        Tell the participant whether they were right.
    rating :
        Ask for a confidence rating.
    intensities :
        Magnitudes the stimulus difference is drawn from, in BPM. The sign is
        drawn separately, so ``(20.0,)`` means plus or minus 20. Practice does
        not use the staircase: these are fixed, and deliberately easier than
        the task will become. The numeric type carries through to the ``Alpha``
        column, so it is used as written rather than coerced.
    setup_recording :
        Reset the recording before the block.

    """

    modality: str
    count: str
    feedback: bool = False
    rating: bool = False
    intensities: Tuple[float, ...] = (20.0,)
    setup_recording: bool = True
    extero_only: bool = False

    def skipped(self, parameters: dict) -> bool:
        return self.extero_only and not parameters["ExteroCondition"]


@dataclass(frozen=True)
class AskFingerNumber:
    """Which finger the pulse oximeter is on. Interactive, so it stands alone."""

    screen: Screen

    def skipped(self, parameters: dict) -> bool:
        return False
