# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Keep tests that need a human out of an unattended run.

Two of the inherited tests call ``run()`` directly. That opens a window and
blocks in ``event.waitKeys``, so a plain ``pytest tests/`` hangs on an
instruction screen until someone presses space, and escape does not abort it.
They are skipped unless asked for by name.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-blocking",
        action="store_true",
        default=False,
        help="also run tests that open a window and wait for a keypress",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "blocking: needs a person at the keyboard to finish"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-blocking"):
        return
    skip = pytest.mark.skip(reason="needs a keypress; pass --run-blocking to include")
    for item in items:
        if "blocking" in item.keywords:
            item.add_marker(skip)
