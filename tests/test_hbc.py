# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import shutil
import unittest
from unittest import TestCase

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
