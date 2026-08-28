# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Session output paths, and the overwrite guard."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cardioception.output import SessionPaths


class TestSessionPaths(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_participant_and_session_cannot_collide(self):
        """("P0", "1001") and ("P01", "001") used to share a directory."""
        a = SessionPaths(self.root, "P0", "1001", run_id="r")
        b = SessionPaths(self.root, "P01", "001", run_id="r")
        self.assertNotEqual(a.directory, b.directory)

    def test_two_runs_of_the_same_session_are_separate(self):
        a = SessionPaths(self.root, "P1", "01", run_id="20260101-090000")
        b = SessionPaths(self.root, "P1", "01", run_id="20260101-100000")
        self.assertNotEqual(a.directory, b.directory)

    def test_every_filename_carries_participant_session_and_run(self):
        """So a file still identifies itself once copied out of its folder."""
        paths = SessionPaths(self.root, "P1", "01", run_id="r")
        name = Path(paths.path("final")).name
        for part in ("sub-P1", "ses-01", "run-r", "final"):
            self.assertIn(part, name)

    def test_writing_over_existing_results_is_refused(self):
        paths = SessionPaths(self.root, "P1", "01", run_id="r")
        Path(paths.path("final")).write_text("x")
        with self.assertRaises(FileExistsError):
            SessionPaths(self.root, "P1", "01", run_id="r")

    def test_overwrite_is_possible_when_asked_for(self):
        paths = SessionPaths(self.root, "P1", "01", run_id="r")
        Path(paths.path("final")).write_text("x")
        SessionPaths(self.root, "P1", "01", run_id="r", overwrite=True)

    def test_an_empty_directory_is_not_treated_as_occupied(self):
        paths = SessionPaths(self.root, "P1", "01", run_id="r")
        SessionPaths(self.root, "P1", "01", run_id="r")
        self.assertTrue(Path(paths.directory).is_dir())

    def test_a_run_id_is_generated_when_not_given(self):
        paths = SessionPaths(self.root, "P1", "01")
        self.assertRegex(paths.run_id, r"^\d{8}-\d{6}$")

    def test_the_manifest_is_written_at_the_start(self):
        paths = SessionPaths(self.root, "P1", "01", run_id="r")
        target = paths.write_manifest(seed=42, device="mouse")
        payload = json.loads(Path(target).read_text())
        self.assertEqual(payload["participant"], "P1")
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["run_id"], "r")


if __name__ == "__main__":
    unittest.main()
