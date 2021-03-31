# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import shutil
import unittest
from unittest import TestCase

from psychopy import prefs

prefs.hardware["audioLib"] = ["pygame"]

from cardioception.HBC.parameters import getParameters
from cardioception.HBC.task import run


class TestHBC(TestCase):
    def test_parameters(self):
        """Test get_parameters function"""
        # Get parameters
        parameters = getParameters(setup="test")
        parameters["win"].close()
        shutil.rmtree(parameters["resultPath"])

    def test_run(self):
        """Test run function"""
        # Get parameters
        parameters = getParameters(setup="test", taskVersion="test")

        run(parameters)

        parameters["win"].close()
        shutil.rmtree(parameters["resultPath"])


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
