# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Design values are settable from the caller's script, and recorded.

The trial- and run-level functions should not carry design values of their own.
These were literals inside getParameters, so changing one meant editing the
package or patching the parameters dictionary afterwards — where the change was
invisible to anyone reading the results.
"""

import json
import shutil
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

from cardioception.HRD.config import TaskConfig
from cardioception.HRD.parameters import getParameters

SETTABLE = [f.name for f in fields(TaskConfig)]


class TestTaskConfig(unittest.TestCase):
    def test_the_defaults_are_what_the_task_used_before(self):
        c = TaskConfig()
        self.assertEqual(c.respMax, 5.0)
        self.assertEqual(c.minRatingTime, 0.5)
        self.assertEqual(c.maxRatingTime, 5.0)
        self.assertEqual(c.nFeedback, 5)
        self.assertEqual(c.nConfidence, 8)
        self.assertEqual(c.isi, (0.25, 0.25))
        self.assertEqual(c.startKey, "space")
        self.assertEqual(c.response_keys, {"More": "up", "Less": "down"})
        self.assertEqual(c.HRcutOff, (40.0, 120.0))
        self.assertEqual(c.textSize, 0.04)
        self.assertEqual(c.listeningDuration, 5.0)

    def test_allowed_keys_follow_the_response_mapping(self):
        c = TaskConfig(response_keys={"More": "right", "Less": "left"})
        self.assertEqual(c.allowedKeys, ["right", "left"])

    def test_every_factor_reaches_the_parameters_dictionary(self):
        parameters = {}
        TaskConfig().apply(parameters)
        for name in SETTABLE:
            self.assertIn(name, parameters, name)

    def test_a_config_cannot_be_edited_after_the_session_starts(self):
        with self.assertRaises(Exception):
            TaskConfig().respMax = 99


class TestConfigReachesTheSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, **kwargs):
        return getParameters(
            participant="CONFIG",
            session="1",
            setup="test",
            nTrials=2,
            exteroception=False,
            resultPath=self.tmp,
            **kwargs
        )

    def test_a_changed_factor_takes_effect(self):
        parameters = self.build(config=TaskConfig(respMax=9, HRcutOff=(30.0, 200.0)))
        parameters["win"].close()
        self.assertEqual(parameters["respMax"], 9)
        self.assertEqual(parameters["HRcutOff"], (30.0, 200.0))

    def test_a_changed_factor_is_recorded_with_the_data(self):
        """A patched parameters dictionary left no trace in the output."""
        parameters = self.build(config=TaskConfig(respMax=9, nFeedback=1))
        parameters["win"].close()
        manifest = json.loads(
            (Path(parameters["paths"].directory) / "manifest.json").read_text()
        )
        self.assertEqual(manifest["config"]["respMax"], 9)
        self.assertEqual(manifest["config"]["nFeedback"], 1)

    def test_the_staircase_bounds_come_from_the_config(self):
        """The range of stimuli a participant can be shown is a design choice."""
        parameters = self.build(config=TaskConfig(intensRange=(-20.0, 20.0)))
        parameters["win"].close()
        grid = parameters["stairCase"]["Intero"]._psi.x
        self.assertEqual((grid.min(), grid.max()), (-20.0, 20.0))

    def test_an_unconfigured_session_is_unchanged(self):
        parameters = self.build()
        parameters["win"].close()
        self.assertEqual(parameters["respMax"], 5.0)
        self.assertEqual(parameters["allowedKeys"], ["up", "down"])


if __name__ == "__main__":
    unittest.main()
