# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

# Check that every translation provides the same texts as the English version.
# These tests only build dictionaries of strings: no window, sound or oximeter.

import itertools
import unittest
from unittest import TestCase

from cardioception.HBC import languages as hbc_languages
from cardioception.HRD import languages as hrd_languages

HRD_LANGUAGES = ["danish", "danish_children", "french", "german"]
HBC_LANGUAGES = ["german"]


def _structure(texts):
    """Return the keys, value types and nested keys of a texts dictionary."""
    return {
        key: (type(value), sorted(value) if isinstance(value, dict) else None)
        for key, value in texts.items()
    }


class TestLanguages(TestCase):
    def test_hrd_languages(self):
        """Every HRD language returns the same keys as English."""
        for device, exteroception in itertools.product(
            ["keyboard", "mouse"], [True, False]
        ):
            kwargs = dict(
                device=device, setup="behavioral", exteroception=exteroception
            )
            reference = _structure(hrd_languages.english(**kwargs))
            for language in HRD_LANGUAGES:
                with self.subTest(
                    language=language, device=device, exteroception=exteroception
                ):
                    texts = getattr(hrd_languages, language)(**kwargs)
                    self.assertEqual(_structure(texts), reference)
                    self.assertEqual(len(texts["VASlabels"]), 2)

    def test_hrd_german_response_keys(self):
        """The German response mapping matches the English one."""
        keyboard = hrd_languages.german("keyboard", "behavioral", True)
        self.assertIn(
            "NACH OBEN) oder langsamer (Taste NACH UNTEN",
            keyboard["Tutorial3_responses"],
        )
        self.assertIn("NACH UNTEN für langsamer", keyboard["responseText"])
        mouse = hrd_languages.german("mouse", "behavioral", True)
        self.assertIn(
            "(RECHTE Maustaste) oder langsamer (LINKE Maustaste)", mouse["Tutorial3ter"]
        )
        self.assertIn("LINKE Maustaste für langsamer", mouse["responseText"])

    def test_hrd_german_rating_hint(self):
        """The German confidence instruction names the device in use."""
        keyboard = hrd_languages.german("keyboard", "behavioral", True)
        self.assertNotIn("Maus", keyboard["Tutorial4"])
        self.assertIn("Pfeiltasten", keyboard["Tutorial4"])
        mouse = hrd_languages.german("mouse", "behavioral", True)
        self.assertIn("Maus", mouse["Tutorial4"])

    def test_hbc_languages(self):
        """Every HBC language returns the same keys as English."""
        reference = _structure(hbc_languages.english())
        self.assertEqual(len(hbc_languages.english()["labelsRating"]), 2)
        for language in HBC_LANGUAGES:
            with self.subTest(language=language):
                texts = getattr(hbc_languages, language)()
                self.assertEqual(_structure(texts), reference)
                self.assertEqual(len(texts["labelsRating"]), 2)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
