# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Session logging.

The tasks narrated themselves with `print`, which goes to a terminal nobody
keeps and carries no timestamps. When a session went wrong there was nothing
left to look at: the results file records what the participant did, not what
the task did.

The same messages now go to a timestamped file in the run directory as well as
to the console, so a failed or aborted session leaves a record of how far it
got and what it was doing.
"""

import logging
import sys
from typing import Optional

LOGGER_NAME = "cardioception"

#: Marks the handlers this module owns, so repeated sessions in one process
#: replace them rather than stacking up duplicate output.
_OWNED = "_cardioception_handler"


def get_logger() -> logging.Logger:
    """The package logger. Configured by :func:`start_session_log`."""
    return logging.getLogger(LOGGER_NAME)


def start_session_log(
    directory: Optional[str], level: int = logging.INFO
) -> Optional[str]:
    """Send this session's messages to the console and to ``directory``.

    Returns the path of the log file, or ``None`` when no directory was given.
    """
    logger = get_logger()
    logger.setLevel(level)
    logger.propagate = False

    for handler in [h for h in logger.handlers if getattr(h, _OWNED, False)]:
        handler.close()
        logger.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(message)s"))
    setattr(console, _OWNED, True)
    logger.addHandler(console)

    if directory is None:
        return None

    path = f"{directory}/session.log"
    to_file = logging.FileHandler(path, encoding="utf-8")
    to_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    setattr(to_file, _OWNED, True)
    logger.addHandler(to_file)
    return path
