# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Keep tests that need a human, or make a sound, out of an unattended run.

Two of the inherited tests call ``run()`` directly. That opens a window and
blocks in ``event.waitKeys``, so a plain ``pytest tests/`` hangs on an
instruction screen until someone presses space, and escape does not abort it.
They are marked ``blocking`` and skipped unless ``--run-blocking`` is given.

Tests marked ``audio`` play through the sound card with PsychToolbox, which
bypasses the system volume. They are skipped unless ``--run-audio`` is given.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-blocking",
        action="store_true",
        default=False,
        help="also run tests that open a window and wait for a keypress",
    )
    parser.addoption(
        "--run-audio",
        action="store_true",
        default=False,
        help="also run tests that play through the sound card",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "blocking: needs a person at the keyboard to finish"
    )
    config.addinivalue_line(
        "markers", "audio: plays through the sound card, at the card's own volume"
    )


def pytest_collection_modifyitems(config, items):
    skips = {
        "blocking": pytest.mark.skip(
            reason="needs a keypress; pass --run-blocking to include"
        ),
        "audio": pytest.mark.skip(reason="plays sound; pass --run-audio to include"),
    }
    for marker, skip in skips.items():
        if config.getoption(f"--run-{marker}"):
            continue
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)
