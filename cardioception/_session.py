# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Session helpers shared by the tasks that run trial by trial in a window.

Waiting for the participant to continue, recording while the screen keeps
redrawing, showing an instruction screen, and collecting a confidence rating.
These began in ``HRD/task.py``. They live here so the Heart Rate
Discrimination task (``cardioception.HRD``) and the Heartbeat Synchrony
Discrimination task (``cardioception.HSD``) use the same code, and
``HRD/task.py`` imports them back under their original names.

Some of them read parameter keys that the HRD session defines, most notably
``parameters["oxiTask"]`` for the recorder. Each docstring says which, so a
second task knows what its parameters dictionary has to provide.
"""

import time
from typing import Callable, Optional, Tuple

from ._log import get_logger
from ._present import accept_press, hold
from ._screens import text

logger = get_logger()


def waitInput(parameters: dict):
    """Wait for participant input before continue.

    Reads ``parameters["device"]``, ``"win"``, ``"startKey"`` (keyboard) or
    ``"myMouse"`` (mouse), and ``"autopilot"`` when set. With
    ``parameters["continuousRecording"]`` true it also drains
    ``parameters["oxiTask"]``, the HRD recorder key, while it waits.
    """

    from psychopy import core, event

    # A synthetic participant advances at once. Whatever was drawn before this
    # call has already been drawn and flipped, so the screen is still exercised.
    if parameters.get("autopilot") is not None:
        parameters["autopilot"].advance()
        return

    # A break is the longest the task ever waits, and it does not flip, so the
    # per-frame hook does not reach here. Undrained, the driver buffer holds
    # about 10.9 seconds -- 4096 bytes at 5 bytes a packet and 75 Hz -- and a
    # participant resting for longer loses whatever overflows.
    drain = (
        parameters["oxiTask"].readInWaiting
        if parameters.get("continuousRecording")
        else None
    )

    if parameters["device"] == "keyboard":
        # Without this, a key pressed earlier is still buffered and dismisses
        # this screen before it is read.
        event.clearEvents(eventType="keyboard")
        while True:
            if drain is not None:
                drain()
            keys = event.getKeys()
            if "escape" in keys:
                logger.warning("User abort")
                parameters["win"].close()
                core.quit()
            elif parameters["startKey"] in keys:
                break
    elif parameters["device"] == "mouse":
        mouse = parameters["myMouse"]
        mouse.clickReset()
        # clickReset resets click times, not button state, so a button still
        # held from the previous screen reads as a fresh press. Wait for a
        # release, then for a press.
        armed = not any(mouse.getPressed())
        while True:
            if drain is not None:
                drain()
            buttons, armed = accept_press(mouse.getPressed(), armed)
            if any(buttons):
                break
            keys = event.getKeys()
            if "escape" in keys:
                logger.warning("User abort")
                parameters["win"].close()
                core.quit()


def drain_for(parameters: dict, duration: float, *stims) -> None:
    """Record for ``duration`` seconds while the window keeps redrawing.

    What `Oximeter.read(duration=...)` does, without blocking: it busy-waits
    inside systole for the whole window, so the screen freezes, PsychoPy
    records no frame intervals, and a keypress cannot be seen until it ends.

    Escape is honoured here too. The listening window is the longest stretch
    of a trial in which the participant is asked to do nothing, so it is where
    an experimenter is most likely to want to stop.

    The recorder is read from ``parameters["oxiTask"]``, the key the HRD
    session uses for it.
    """
    from psychopy import core, event

    recorder = parameters["oxiTask"]
    clock = core.Clock()
    while clock.getTime() < duration:
        recorder.readInWaiting()
        for stim in stims:
            stim.draw()
        parameters["win"].flip()
        if "escape" in event.getKeys(keyList=["escape"]):
            logger.warning("User abort")
            parameters["win"].close()
            core.quit()


def show_screen(
    parameters: dict,
    screen,
    prompt=None,
    *,
    text_fn: Optional[Callable] = None,
    hold_fn: Optional[Callable] = None,
    wait_fn: Optional[Callable] = None,
) -> list:
    """Draw one instruction screen and, unless told otherwise, wait.

    Returns the stimuli it built, so a caller that keeps the screen up can
    redraw the same objects rather than constructing them again.

    ``text_fn``, ``hold_fn`` and ``wait_fn`` default to :func:`text`,
    :func:`hold` and :func:`waitInput`. A task module passes its own bindings
    of those names, so a test that stubs them on that module reaches this
    screen too. ``screen`` is a :class:`cardioception._screens.Screen`; its
    text keys are looked up in ``parameters["texts"]`` and its image, if any,
    in ``parameters``.
    """
    text_fn = text if text_fn is None else text_fn
    hold_fn = hold if hold_fn is None else hold_fn
    wait_fn = waitInput if wait_fn is None else wait_fn

    stims = [
        text_fn(parameters, parameters["texts"][key], pos=pos)
        for key, pos in screen.texts
    ]
    if screen.image:
        image = parameters[screen.image]
        stims = [image] + stims if screen.image_first else stims + [image]
    if screen.prompt and prompt is not None:
        stims.append(prompt)

    hold_fn(parameters["win"], screen.seconds, *stims)
    if screen.wait:
        wait_fn(parameters)
    return stims


def confidence_rating(
    parameters: dict,
) -> Tuple[Optional[float], Optional[float], bool, Optional[float]]:
    """Confidence rating scale, using keyboard or mouse inputs.

    Parameters
    ----------
    parameters : dict
        Parameters dictionary. Reads ``"device"``, ``"win"``, ``"texts"``
        (``Confidence`` and ``tooLate``), ``"confidenceScale"``,
        ``"minRatingTime"``, ``"maxRatingTime"``, ``"textSize"``, ``"rng"``,
        ``"myMouse"`` (mouse) and ``"autopilot"`` when set. With
        ``"continuousRecording"`` true it also drains ``parameters["oxiTask"]``,
        the HRD recorder key, while the scale is up.

    Returns
    -------
    confidence, confidenceRT, ratingProvided, ratingEndTrigger

    """

    from ._rating import keyboard_rating, mouse_rating

    logger.info("...starting confidence rating.")

    # Both rating loops flip for themselves rather than through hold(), so the
    # window's per-frame hook does not reach either of them.
    rating_drain = (
        parameters["oxiTask"].readInWaiting
        if parameters.get("continuousRecording")
        else None
    )

    # Initialise default values
    confidence, confidenceRT = None, None

    pilot = parameters.get("autopilot")
    if pilot is not None:
        # The rating widget itself is covered by its own tests; here we only
        # need a value of the right shape so the session can run unattended.
        answer = pilot.rate(
            *parameters["confidenceScale"].bounds,
            min_time=parameters["minRatingTime"],
            max_wait=parameters["maxRatingTime"],
        )
        if answer is None:
            return None, None, False, time.time()
        confidence, confidenceRT = answer
        return confidence, confidenceRT, True, time.time()

    if parameters["device"] == "keyboard":
        message = text(parameters, parameters["texts"]["Confidence"], pos=(0, 0.2))

        # Arrow keys move the marker, the down key confirms. This was a
        # visual.RatingScale until PsychoPy 2026 moved that class into the
        # psychopy-legacy plugin, where constructing one raises
        # PluginRequiredError. Slider is the supported replacement and is what
        # the mouse branch below already used, so both devices now show the
        # same widget.
        scale = parameters["confidenceScale"]
        confidence, confidenceRT, ratingProvided = keyboard_rating(
            on_frame=rating_drain,
            win=parameters["win"],
            message=message,
            low=scale.low,
            high=scale.high,
            labels=scale.labels,
            granularity=scale.granularity,
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            label_height=parameters["textSize"] * 0.6,
            rng=parameters["rng"],
        )
        if ratingProvided and confidenceRT is not None:
            logger.info(
                f"... Confidence level: {confidence}"
                + f" with response time {round(confidenceRT, 2)} seconds"
            )

    elif parameters["device"] == "mouse":
        # The cursor drives the marker; see mouse_rating for why it is warped
        # once and not on every frame (issue #103).
        message = text(parameters, parameters["texts"]["Confidence"], pos=(0, 0.2))
        confidence, confidenceRT, ratingProvided = mouse_rating(
            win=parameters["win"],
            mouse=parameters["myMouse"],
            message=message,
            scale=parameters["confidenceScale"],
            min_time=parameters["minRatingTime"],
            max_time=parameters["maxRatingTime"],
            label_height=0.1 * 0.6,
            rng=parameters["rng"],
            on_frame=rating_drain,
        )
        if ratingProvided and confidenceRT is not None:
            logger.info(
                f"... Confidence level: {confidence}"
                + f" with response time {round(confidenceRT, 2)} seconds"
            )
        else:
            # Text feedback if no rating provided
            message = text(
                parameters,
                parameters["texts"]["tooLate"],
                pos=(0.0, -0.2),
                color="red",
            )
            hold(parameters["win"], 0.5, message)
    ratingEndTrigger = time.time()
    parameters["win"].flip()

    return confidence, confidenceRT, ratingProvided, ratingEndTrigger
