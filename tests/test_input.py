# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Mouse input must be edge triggered, not level triggered."""

import unittest

from cardioception.HRD.task import accept_press

LEFT = [1, 0, 0]
RIGHT = [0, 0, 1]
NONE = [0, 0, 0]


class TestAcceptPress(unittest.TestCase):
    def test_a_press_after_a_release_is_accepted(self):
        buttons, armed = accept_press(NONE, False)
        self.assertEqual(buttons, NONE)
        self.assertTrue(armed)
        buttons, armed = accept_press(LEFT, armed)
        self.assertEqual(buttons, LEFT)

    def test_a_button_already_down_is_ignored_until_released(self):
        """The defect: a hold spanning a trial boundary answered the next trial."""
        armed = False
        for _ in range(50):
            buttons, armed = accept_press(LEFT, armed)
            self.assertEqual(buttons, NONE, "a held button was read as a press")
        buttons, armed = accept_press(NONE, armed)
        self.assertTrue(armed)
        buttons, armed = accept_press(LEFT, armed)
        self.assertEqual(buttons, LEFT)

    def test_a_press_starting_armed_is_accepted_immediately(self):
        buttons, _ = accept_press(RIGHT, True)
        self.assertEqual(buttons, RIGHT)

    def test_holding_after_an_accepted_press_stays_accepted(self):
        """Within one response window a hold should not flicker off."""
        buttons, armed = accept_press(LEFT, True)
        self.assertEqual(buttons, LEFT)
        buttons, armed = accept_press(LEFT, armed)
        self.assertEqual(buttons, LEFT)

    def test_release_always_arms(self):
        for start in (True, False):
            _, armed = accept_press(NONE, start)
            self.assertTrue(armed)


class HeldMouse:
    """A mouse whose left button is down for the first ``held`` polls."""

    def __init__(self, held=10):
        self.held, self.polls = held, 0

    def getPressed(self, getTime=False):
        self.polls += 1
        state = LEFT if self.polls <= self.held else NONE
        return (state, [0.0, 0.0, 0.0]) if getTime else state

    def clickReset(self):
        pass


class TestHeldMouseIsIgnored(unittest.TestCase):
    def test_the_hold_is_swallowed_and_the_next_press_is_not(self):
        mouse = HeldMouse(held=5)
        armed = not any(mouse.getPressed())
        self.assertFalse(armed, "fixture should start with the button down")

        accepted = []
        for _ in range(10):
            buttons, armed = accept_press(mouse.getPressed(), armed)
            accepted.append(any(buttons))
        self.assertFalse(any(accepted), "held button produced a response")

        # A genuine press once the button has come back up.
        buttons, armed = accept_press(LEFT, armed)
        self.assertEqual(buttons, LEFT)


if __name__ == "__main__":
    unittest.main()
