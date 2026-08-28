# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Where a session's files go, and what they are called.

The old layout was ``data/<participant><session>`` with no separator, created
under a bare ``os.path.exists`` check, and only two of the seven output files
carried the session label at all. Re-running a participant silently overwrote
the previous run, which has cost real data in longitudinal studies.

Here the run timestamp makes the directory unique, so overwriting is not
possible, and every filename carries participant, session and run, so a file
still identifies itself after being copied out of its directory.
"""

import datetime
import json
import os
from typing import Optional


class SessionPaths:
    """Build the output directory and the paths inside it.

    Parameters
    ----------
    root :
        Directory holding all participants, usually ``<cwd>/data``.
    participant, session :
        Identifiers. Kept separate rather than concatenated: ``("P0", "1001")``
        and ``("P01", "001")`` used to land in the same directory.
    run_id :
        Defaults to the local start time as ``YYYYMMDD-HHMMSS``.
    overwrite :
        Allow a directory that already holds results. Off by default.

    """

    def __init__(
        self,
        root: str,
        participant: str,
        session: str,
        run_id: Optional[str] = None,
        overwrite: bool = False,
    ):
        self.participant = str(participant)
        self.session = str(session)
        self.run_id = run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.directory = os.path.join(
            root,
            f"sub-{self.participant}",
            f"ses-{self.session}",
            f"run-{self.run_id}",
        )
        if os.path.isdir(self.directory) and not overwrite:
            existing = [f for f in os.listdir(self.directory) if f.endswith(".txt")]
            if existing:
                raise FileExistsError(
                    f"{self.directory} already holds results ({len(existing)} files). "
                    "Pass overwrite=True to write here anyway."
                )
        os.makedirs(self.directory, exist_ok=True)

    @property
    def prefix(self) -> str:
        return f"sub-{self.participant}_ses-{self.session}_run-{self.run_id}"

    def path(self, kind: str, ext: str = "txt") -> str:
        """Path for one output, e.g. ``path("final")`` or ``path("ppg-3")``."""
        return os.path.join(self.directory, f"{self.prefix}_{kind}.{ext}")

    def write_manifest(self, **fields) -> str:
        """Record what this session is, at the start rather than the end.

        The parameters pickle is written when the task finishes, so an aborted
        session left no record of its own settings.
        """
        target = os.path.join(self.directory, "manifest.json")
        payload = {
            "participant": self.participant,
            "session": self.session,
            "run_id": self.run_id,
            **fields,
        }
        with open(target, "w") as handle:
            json.dump(payload, handle, indent=2, default=str)
        return target
