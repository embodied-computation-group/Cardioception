# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

import os
import unittest
from unittest import TestCase
import pandas as pd
from pathlib import Path
from cardioception.reports import report, preprocessing


class TestReports(TestCase):
    def test_preprocessing(self):
        """Test the preprocessing function"""
        # load the main result data frame
        results = pd.read_csv(
            "https://raw.githubusercontent.com/embodied-computation-group/Cardioception/master/docs/source/examples/templates/data/HRD/HRD_final.txt"
            )
        preprocessing(results=results)


    def test_report(self):
        """Test the report function"""

        #####
        # HRD
        #####
        hrd_results_path = Path(Path.cwd(), "docs", "source", "examples", "templates", "data", "HRD")
        hrd_report_path = Path.cwd()
        report(result_path=hrd_results_path, report_path=hrd_report_path)
        #os.remove(Path(hrd_report_path, "HRD_report.html"))

        #####
        # HBC
        #####
        hbc_results_path = Path(Path.cwd(), "docs", "source", "examples", "templates", "data", "HBC")
        hbc_report_path = Path.cwd()
        report(result_path=hbc_results_path, report_path=hbc_report_path, task="HBC")
        #os.remove(Path(hbc_report_path, "HBC_report.html"))


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
