# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""What the shared stimulus constructors pass through to PsychoPy."""

import unittest
from unittest import mock

from cardioception._screens import fixation, text

PARAMETERS = {"win": "WINDOW", "textSize": 0.04}


def captured(fn, *args, **kwargs):
    """Call fn with visual.TextStim/GratingStim stubbed, returning the kwargs."""
    with mock.patch("psychopy.visual.TextStim") as stim, mock.patch(
        "psychopy.visual.GratingStim"
    ) as grating:
        fn(*args, **kwargs)
    call = stim.call_args or grating.call_args
    return call.args, call.kwargs


class TestText(unittest.TestCase):
    def test_the_plain_shape(self):
        args, kwargs = captured(text, PARAMETERS, "hello")
        self.assertEqual(args, ("WINDOW",))
        self.assertEqual(kwargs["text"], "hello")
        self.assertEqual(kwargs["height"], 0.04)
        self.assertEqual(kwargs["pos"], (0.0, 0.0))

    def test_a_colour_is_passed_only_when_given(self):
        """Nine of the 64 sites set one, and PsychoPy's default is not None."""
        _, plain = captured(text, PARAMETERS, "hello")
        self.assertNotIn("color", plain)
        _, red = captured(text, PARAMETERS, "hello", color="red")
        self.assertEqual(red["color"], "red")

    def test_position_and_height_override(self):
        _, kwargs = captured(text, PARAMETERS, "hi", pos=(0.0, 0.2), height=0.1)
        self.assertEqual(kwargs["pos"], (0.0, 0.2))
        self.assertEqual(kwargs["height"], 0.1)

    def test_unknown_keywords_reach_psychopy(self):
        _, kwargs = captured(text, PARAMETERS, "hi", wrapWidth=0.9)
        self.assertEqual(kwargs["wrapWidth"], 0.9)

    def test_the_fixation_cross(self):
        _, kwargs = captured(fixation, PARAMETERS)
        self.assertEqual(kwargs["mask"], "cross")
        self.assertEqual(kwargs["size"], 0.1)
        self.assertEqual(kwargs["sf"], 0)
        self.assertEqual(kwargs["win"], "WINDOW")


if __name__ == "__main__":
    unittest.main()
