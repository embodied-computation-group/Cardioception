# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import shutil
import tempfile
import unittest
from unittest import TestCase

import pytest

from cardioception.HBC.parameters import getParameters
from cardioception.HBC.task import run


class TestHBC(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_parameters(self):
        """Test get_parameters function"""
        # Get parameters
        parameters = getParameters(setup="test", resultPath=self.tmp)
        parameters["win"].close()

    @pytest.mark.blocking
    def test_run(self):
        """A whole session, with a person pressing space at each screen.

        HBC has no autopilot yet: its instruction screens call event.waitKeys,
        and its counting window blocks inside oxiTask.read(). Until the
        recorder interface lands this cannot run unattended.
        """
        # Get parameters
        parameters = getParameters(
            setup="test", taskVersion="test", resultPath=self.tmp
        )

        run(parameters)

        parameters["win"].close()


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)


class TestSetupIsValidated(unittest.TestCase):
    """An unknown `setup` must fail before the window opens.

    It used to fall through the if/elif chain and return a parameters
    dictionary with no `oxiTask` in it, so the session died inside `trial()`
    on a KeyError -- after the window had opened, in front of the participant,
    and naming a key rather than the typo that caused it. HRD has raised here
    since the audit; HBC did not.
    """

    def test_an_unknown_setup_raises_and_says_what_is_valid(self):
        with pytest.raises(ValueError, match="behavioral"):
            getParameters(setup="behavioural")  # the British spelling

    def test_the_error_names_the_value_it_was_given(self):
        with pytest.raises(ValueError, match="nonsense"):
            getParameters(setup="nonsense")
