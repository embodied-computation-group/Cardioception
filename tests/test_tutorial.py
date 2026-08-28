# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""The tutorial runs through, in the right shape, for every configuration.

Not what it says — that is the language files' business, and pinning the text
here would fail on every typo fix. What matters is that the sequence holds
together: the instruction screens and practice blocks come in the right order,
each block asks for what it is supposed to, and the parts that should be left
out for a given session are left out.

Runs with every drawing call stubbed, so no window opens.
"""

import itertools
import unittest

import cardioception.HRD.task as hrd
from cardioception.HRD.languages import get_texts

LANGUAGES = ["english", "danish", "danish_children", "french"]
DEVICES = ["keyboard", "mouse"]
IMAGES = ["pulseSchema", "handSchema", "heartLogo", "listenLogo"]

N_FEEDBACK, N_CONFIDENCE = 2, 3


class Stub:
    def __init__(self, label=""):
        self.label = label

    def draw(self):
        pass


class Recorder:
    """Records the shape of the presentation, not its wording."""

    def __init__(self):
        self.steps = []

    def text(self, parameters, message, pos=(0.0, 0.0), **kwargs):
        return Stub()

    def hold(self, win, duration, *stims):
        self.steps.append(("show", len(stims)))
        return duration

    def wait_input(self, parameters):
        self.steps.append(("wait",))

    def trial(self, parameters, alpha, modality, **kwargs):
        self.steps.append(
            (
                "trial",
                modality,
                kwargs.get("feedback", False),
                kwargs.get("confidenceRating", False),
            )
        )

    @property
    def trials(self):
        return [s for s in self.steps if s[0] == "trial"]

    @property
    def screens(self):
        return [s for s in self.steps if s[0] == "show"]


class FakeOxi:
    def setup(self):
        return self

    def read(self, duration=None):
        return self

    def readInWaiting(self):
        return self


class FixedChoice:
    def choice(self, options):
        return options[0]


def run_tutorial(language="english", device="mouse", exteroception=True):
    recorder = Recorder()
    parameters = {
        "texts": get_texts(language, device, exteroception),
        "ExteroCondition": exteroception,
        "device": device,
        "win": "WINDOW",
        "oxiTask": FakeOxi(),
        "rng": FixedChoice(),
        "nFeedback": N_FEEDBACK,
        "nConfidence": N_CONFIDENCE,
        "textSize": 0.04,
    }
    for name in IMAGES:
        parameters[name] = Stub(name)

    saved = (hrd.text, hrd.hold, hrd.waitInput, hrd.trial)
    hrd.text, hrd.hold, hrd.waitInput, hrd.trial = (
        recorder.text,
        recorder.hold,
        recorder.wait_input,
        recorder.trial,
    )
    try:
        import psychopy.event as pe

        real = pe.waitKeys
        pe.waitKeys = lambda **kwargs: ["3"]
        try:
            hrd.tutorial(parameters)
        finally:
            pe.waitKeys = real
    finally:
        hrd.text, hrd.hold, hrd.waitInput, hrd.trial = saved
    return recorder, parameters


class TestTutorialRuns(unittest.TestCase):
    def test_it_completes_for_every_language_and_device(self):
        for language, device, exteroception in itertools.product(
            LANGUAGES, DEVICES, [True, False]
        ):
            with self.subTest(f"{language}|{device}|{exteroception}"):
                recorder, _ = run_tutorial(language, device, exteroception)
                self.assertTrue(recorder.screens)
                self.assertTrue(recorder.trials)

    def test_practice_comes_in_the_two_phases_the_task_has(self):
        """Judge with feedback first, then judge and rate without it."""
        recorder, _ = run_tutorial(exteroception=False)
        feedback = [t for t in recorder.trials if t[2]]
        rating = [t for t in recorder.trials if t[3]]
        self.assertEqual(len(feedback), N_FEEDBACK)
        self.assertEqual(len(rating), N_CONFIDENCE)
        # Feedback practice runs before rating practice.
        self.assertLess(
            recorder.trials.index(feedback[0]), recorder.trials.index(rating[0])
        )

    def test_no_practice_trial_gives_feedback_and_asks_for_a_rating(self):
        recorder, _ = run_tutorial()
        for step in recorder.trials:
            self.assertFalse(step[2] and step[3], step)

    def test_the_exteroceptive_condition_gets_its_own_practice(self):
        with_extero, _ = run_tutorial(exteroception=True)
        without, _ = run_tutorial(exteroception=False)

        self.assertTrue(any(t[1] == "Extero" for t in with_extero.trials))
        self.assertFalse(any(t[1] == "Extero" for t in without.trials))
        # And its own instruction screens.
        self.assertGreater(len(with_extero.screens), len(without.screens))

    def test_block_lengths_follow_the_parameters(self):
        """So a study can shorten the tutorial without editing the package."""
        recorder, _ = run_tutorial(exteroception=True)
        self.assertEqual(len(recorder.trials), 2 * (N_FEEDBACK + N_CONFIDENCE))

    def test_the_children_version_skips_a_screen(self):
        adults, _ = run_tutorial(language="danish")
        children, _ = run_tutorial(language="danish_children")
        self.assertEqual(len(children.screens), len(adults.screens) - 1)

    def test_the_finger_the_oximeter_is_on_is_recorded(self):
        _, parameters = run_tutorial()
        self.assertEqual(parameters["nFinger"], "3")

    def test_every_screen_waits_for_the_participant(self):
        """Except the finger question, which waits for a digit instead."""
        recorder, _ = run_tutorial()
        waits = [s for s in recorder.steps if s[0] == "wait"]
        self.assertEqual(len(waits), len(recorder.screens) - 2)


if __name__ == "__main__":
    unittest.main()
