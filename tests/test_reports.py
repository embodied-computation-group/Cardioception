# Author: Nicolas Legrand <nicolas.legrand@cas.au.dk>

import os
import unittest
from unittest import TestCase

import cardioception
from cardioception.reports import report


class TestHRD(TestCase):
    def test_report(self):
        """Test parameters function"""

        #####
        # HRD
        #####
        hrd_resultsPath = os.path.join(
            os.path.dirname(cardioception.__file__), "notebooks", "data", "HRD"
        )

        hrd_reportPath = os.path.join(
            os.path.dirname(cardioception.__file__), "notebooks", "data", "HRD"
        )
        report(resultPath=hrd_resultsPath, reportPath=hrd_reportPath)

        os.remove(os.path.join(hrd_reportPath, "HRD_report.html"))

        #####
        # HBC
        #####
        hbc_resultsPath = os.path.join(
            os.path.dirname(cardioception.__file__), "notebooks", "data", "HBC"
        )

        hbc_reportPath = os.path.join(
            os.path.dirname(cardioception.__file__), "notebooks", "data", "HBC"
        )
        report(resultPath=hbc_resultsPath, reportPath=hbc_reportPath, task="HBC")

        os.remove(os.path.join(hbc_reportPath, "HBC_report.html"))


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
