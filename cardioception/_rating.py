# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Keyboard-driven confidence rating, shared by both tasks.

Both tasks used ``visual.RatingScale`` for the keyboard confidence rating. From
PsychoPy 2026 that class lives in the ``psychopy-legacy`` plugin, and
constructing one without the plugin raises ``PluginRequiredError`` rather than
warning, so it had to go.

``visual.Slider`` is the supported replacement, and the HRD mouse branch already
used it. Putting the keyboard version here means both tasks and both input
devices now present the same widget, rather than a Slider for one and a
differently drawn scale for the other.

The arrow keys move the marker and the accept key confirms, which is what
``RatingScale`` did with ``acceptKeys="down"``.
"""

from typing import List, Optional, Sequence, Tuple

import numpy as np


def keyboard_rating(
    win,
    message,
    low: int,
    high: int,
    labels: Sequence[str],
    marker_start: Optional[int] = None,
    min_time: float = 0.0,
    max_time: Optional[float] = None,
    accept_keys: Sequence[str] = ("down",),
    granularity: float = 1,
    label_height: float = 0.06,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[Optional[float], Optional[float], bool]:
    """Collect a confidence rating using the arrow keys.

    Parameters
    ----------
    win :
        The PsychoPy window to draw into.
    message :
        A stimulus drawn above the slider on every frame, usually the prompt.
    low, high :
        Ends of the confidence scale, inclusive.
    labels :
        Text for the two ends, e.g. ``["Guess", "Certain"]``.
    marker_start :
        Where the marker begins. Randomised over the scale when omitted, which
        is what the previous implementation did: a fixed start would bias the
        ratings of participants who accept without moving.
    min_time :
        Accept keys are ignored before this many seconds have passed, so a
        participant cannot confirm the starting value reflexively.
    max_time :
        Give up after this many seconds and return no rating. ``None`` waits
        indefinitely, which is what the Heartbeat Counting task does.
    accept_keys :
        Keys that confirm the current value.
    granularity :
        Step size, and how far one arrow keypress moves the marker.
    label_height :
        Text height for the end labels.
    rng :
        The session generator, so the randomised starting position is
        reproducible. Falls back to a fresh generator when omitted.

    Returns
    -------
    confidence :
        The rating, or ``None`` if the participant did not respond in time.
    confidenceRT :
        Seconds from the first frame to the accepting keypress, or ``None``.
    ratingProvided :
        Whether a rating was given.

    """
    from psychopy import core, event, visual

    from ._present import hold

    if marker_start is None:
        # The starting position biases the rating, so the draw has to come from
        # the seeded session generator to be reproducible and recoverable.
        draw = rng if rng is not None else np.random.default_rng()
        marker_start = float(draw.choice(np.arange(low, high, granularity)))

    slider = visual.Slider(
        win=win,
        name="slider",
        pos=(0, -0.2),
        size=(0.7, 0.1),
        labels=list(labels),
        granularity=granularity,
        ticks=(low, high),
        style="rating",
        color="LightGray",
        flip=False,
        labelHeight=label_height,
    )
    slider.marker.size = (0.03, 0.03)
    slider.markerPos = marker_start

    confidence: Optional[float] = None
    confidenceRT: Optional[float] = None
    ratingProvided = False

    # Drop anything typed before the scale appeared, or a keypress left over
    # from the decision would be read as a rating.
    event.clearEvents(eventType="keyboard")
    clock = core.Clock()

    watched: List[str] = ["left", "right"] + list(accept_keys)

    while True:
        elapsed = clock.getTime()

        for key in event.getKeys(keyList=watched):
            if key == "left":
                slider.markerPos = max(low, slider.markerPos - granularity)
            elif key == "right":
                slider.markerPos = min(high, slider.markerPos + granularity)
            elif key in accept_keys and elapsed > min_time:
                confidence, confidenceRT, ratingProvided = (
                    slider.markerPos,
                    clock.getTime(),
                    True,
                )

        if ratingProvided:
            # Confirm visibly before moving on, as the mouse branch does.
            slider.marker.color = "green"
            hold(win, 0.2, slider, message)
            break

        if max_time is not None and elapsed > max_time:
            break

        slider.draw()
        message.draw()
        win.flip()

    return confidence, confidenceRT, ratingProvided
