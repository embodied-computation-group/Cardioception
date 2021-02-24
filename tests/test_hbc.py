# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

# Running short blocks of the task for testing.
# Shoult not be used for data acquisition

import unittest
from unittest import TestCase

from cardioception.HBC.parameters import getParameters


class TestHBC(TestCase):
    def test_parameters(self):

        # Get parameters
        parameters = getParameters(setup="test")
        parameters["win"].close()


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
