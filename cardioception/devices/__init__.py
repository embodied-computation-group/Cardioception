# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Recording backends.

The tasks currently program directly against whatever object sits at
``parameters["oxiTask"]``, using ten undeclared members of it. This package is
the beginning of an explicit interface, so that a device other than the Nonin
pulse oximeter can be used without editing the task, and so that a session can
be replayed without any hardware at all.

``ReplayRecorder`` is the first backend and exists to make the tasks testable.
It presents the same surface the tasks already use, so nothing in the task code
has to change to accept it.
"""

from .replay import ReplayRecorder

__all__ = ["ReplayRecorder"]
