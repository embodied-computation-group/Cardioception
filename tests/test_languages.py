# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The YAML texts must say exactly what the Python functions used to say."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cardioception.HRD import languages
from cardioception.HRD.languages import REQUIRED_KEYS, available, get_texts

SNAPSHOT = json.loads(
    (Path(__file__).parent / "data" / "language_snapshot.json").read_text(
        encoding="utf-8"
    )
)


class TestLanguages(unittest.TestCase):
    def test_every_language_survived_the_move_to_yaml(self):
        """All 16 combinations, against a snapshot of the code being replaced.

        Taken before the Python functions were deleted, so a mistranslation or
        an encoding fault in the Danish or French strings shows up here.
        """
        self.assertEqual(len(SNAPSHOT), 16)
        for combination, expected in SNAPSHOT.items():
            language, device, exteroception = combination.split("|")
            with self.subTest(combination):
                self.assertEqual(
                    get_texts(language, device, exteroception == "True"), expected
                )

    def test_the_four_languages_are_all_there(self):
        self.assertEqual(
            available(), ["danish", "danish_children", "english", "french"]
        )

    def test_an_unknown_language_fails_at_setup(self):
        """It used to leave parameters["texts"] unset and fail mid-session."""
        with self.assertRaises(ValueError) as raised:
            get_texts("swedish", "mouse", True)
        self.assertIn("Available:", str(raised.exception))

    def test_a_language_missing_a_key_fails_at_setup(self):
        """The failure this replaces was a KeyError at whatever trial needed it."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        source = Path(languages.TEXTS_DIR, "english.yaml").read_text(encoding="utf-8")
        Path(tmp, "broken.yaml").write_text(
            source.replace("  tooLate:", "  tooLateTypo:"), encoding="utf-8"
        )

        original = languages.TEXTS_DIR
        languages.TEXTS_DIR = tmp
        self.addCleanup(setattr, languages, "TEXTS_DIR", original)

        with self.assertRaises(ValueError) as raised:
            get_texts("broken", "mouse", True)
        self.assertIn("tooLate", str(raised.exception))

    def test_the_required_keys_match_what_english_defines(self):
        self.assertEqual(set(get_texts("english", "mouse", True)), set(REQUIRED_KEYS))

    def test_the_exteroceptive_tutorial_screens_are_absent_without_the_condition(self):
        """They were omitted, not reworded, and that has to stay true."""
        without = get_texts("english", "mouse", False)
        self.assertNotIn("Tutorial3bis", without)
        self.assertNotIn("Tutorial3ter", without)


if __name__ == "__main__":
    unittest.main()
