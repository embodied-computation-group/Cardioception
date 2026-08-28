# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""The trigger callbacks, which used to be documented but never called.

Every reference in the Heartbeat Counting task was a bare expression statement,
``parameters["triggers"]["trialStart"]``, which looks the callable up and throws
it away. Anyone following the documentation to drive a parallel port or an LSL
marker stream got no triggers and no error. The Heart Rate Discrimination task
documented the same dictionary and never created it, so following its
documentation raised ``KeyError``.
"""

import unittest

from cardioception._triggers import EVENTS, default_triggers, fire, validate


class TestTriggerRegistry(unittest.TestCase):
    def test_every_documented_event_is_present_and_unset_by_default(self):
        triggers = default_triggers()
        self.assertEqual(set(triggers), set(EVENTS))
        self.assertTrue(all(v is None for v in triggers.values()))

    def test_a_registered_callback_is_actually_called(self):
        """The whole point. A bare lookup would leave this list empty."""
        seen = []
        params = {"triggers": validate({"trialStart": lambda: seen.append("start")})}
        fire(params, "trialStart")
        self.assertEqual(seen, ["start"])

    def test_firing_an_unset_event_is_a_no_op(self):
        params = {"triggers": default_triggers()}
        fire(params, "trialStop")  # must not raise

    def test_firing_without_a_triggers_key_is_a_no_op(self):
        fire({}, "trialStart")  # must not raise

    def test_a_non_callable_fails_at_setup_not_at_trial_eighty(self):
        with self.assertRaises(TypeError):
            validate({"trialStart": 1})

    def test_a_misspelled_event_fails_at_setup(self):
        """Silently accepting this is how a trigger goes missing unnoticed."""
        with self.assertRaises(ValueError) as ctx:
            validate({"trialStarted": lambda: None})
        self.assertIn("trialStarted", str(ctx.exception))

    def test_a_partial_mapping_is_filled_in(self):
        triggers = validate({"trialStart": lambda: None})
        self.assertEqual(set(triggers), set(EVENTS))
        self.assertIsNone(triggers["trialStop"])


class TestNoBareLookupsRemain(unittest.TestCase):
    def test_no_statement_in_the_package_evaluates_a_value_and_discards_it(self):
        """A regression guard against the original defect returning.

        flake8 does not report pointless statements, so nothing else in the
        toolchain would catch a bare lookup reappearing. Walking the AST rather
        than grepping means a docstring that quotes the bad pattern, as
        ``_triggers`` does, cannot trip it.
        """
        import ast
        from pathlib import Path

        import cardioception

        root = Path(cardioception.__file__).parent
        offenders = []
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Expr):
                    continue
                # A bare expression is only meaningful as a docstring or a call.
                if isinstance(node.value, (ast.Constant, ast.Call, ast.Await)):
                    continue
                offenders.append(
                    f"{path.name}:{node.lineno}: " f"{ast.dump(node.value)[:60]}"
                )
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
