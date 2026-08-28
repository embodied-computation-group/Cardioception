# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

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
