# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""An oximeter whose per-sample cost does not grow with the recording.

`systole.recording.Oximeter.add_paquet` rescans the whole peaks list on every
sample to recover a value that depends only on the last two peaks::

    if sum(self.peaks) >= 2:
        self.instant_rr.append(
            (np.diff(np.where(self.peaks)[0])[-1] / self.sfreq) * 1000
        )

Both `sum` and `np.where` are O(N), so a session costs O(N^2) and the
per-sample time climbs with it -- measured at 0.06 ms over 10 s of recording
and 2.28 ms over 800 s. At 60 Hz the task must absorb 1.25 samples per frame,
so past roughly nine minutes the oximeter alone eats a frame budget and the
task starts dropping frames. That is the whole reason whole-session recording
looks impossible on this hardware; it is a cache, not a limitation.

Counting peaks and remembering where the last two were makes it O(1), which is
what this subclass does. The arithmetic is unchanged: the same inputs produce
the same `instant_rr`, which `tests/test_continuous.py` checks sample by
sample against stock systole.
"""

import time
from typing import List, Optional

import numpy as np
from systole.recording import Oximeter


class ContinuousOximeter(Oximeter):
    """`Oximeter` with an O(1) `add_paquet`, and a clock on every packet.

    Attributes
    ----------
    wall_times : list of float
        `time.time()` when each packet was added. `Oximeter.times` counts
        samples (`len(self.times) / self.sfreq`), so a dropped sample shortens
        the timeline instead of leaving a hole and the loss cannot be found
        afterwards. These are what make a gap visible.
    """

    #: `Oximeter` assigns these without annotating them, so their type cannot
    #: be inferred through a subclass. Declaring them is typing only and
    #: leaves the runtime untouched; the element types are systole's to say.
    times: list
    diff: list

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reset_peak_cache()

    def _reset_peak_cache(self) -> None:
        """Forget where the peaks were. Must follow anything clearing `peaks`."""
        self.wall_times: List[float] = []
        self._n_peaks: int = 0
        self._last_peak: Optional[int] = None
        self._previous_peak: Optional[int] = None

    def reset(self, *args, **kwargs):
        """Restart the recording, and the cache that describes it.

        `setup()` calls this, and the task calls `setup()` at every break, so
        the cache would otherwise describe peaks that no longer exist.
        """
        out = super().reset(*args, **kwargs)
        self._reset_peak_cache()
        return out

    def add_paquet(self, value: int, window: float = 1.0):
        """One sample, in time that does not depend on how many came before.

        A transcription of `Oximeter.add_paquet` with the two scans replaced by
        counters. Everything else -- the threshold window, the differential,
        the 0.2 s refractory check -- is left exactly as it was, including its
        quirks, so that this stays a performance change and nothing else.
        """
        self.recording.append(value)
        self.peaks.append(0)
        self.wall_times.append(time.time())

        if self.channels is not None:
            for ch in self.channels:
                self.channels[ch].append(0)

        if not self.times:
            self.times = [0]
        else:
            self.times.append(len(self.times) / self.sfreq)

        window_n = int(window * self.sfreq)
        recent = self.recording[-window_n:]
        self.threshold.append(float(np.mean(recent) + np.std(recent)))

        if not self.diff:
            self.diff = [0]
        else:
            self.diff.append(self.recording[-1] - self.recording[-2])

            if value > self.threshold[-1]:
                if (self.diff[-1] <= 0) & (self.diff[-2] > 0):
                    if not any(self.peaks[-15:]):
                        self.peaks[-1] = 1
                        # The only bookkeeping this class adds.
                        self._previous_peak = self._last_peak
                        self._last_peak = len(self.peaks) - 1
                        self._n_peaks += 1

        # Was: sum(self.peaks) >= 2, then np.diff(np.where(self.peaks)[0])[-1].
        # The interval between the last two peaks is all either expression
        # ever recovered.
        if self._n_peaks >= 2:
            samples = self._last_peak - self._previous_peak  # type: ignore[operator]
            self.instant_rr.append((samples / self.sfreq) * 1000)
        else:
            self.instant_rr.append(float("nan"))

        return self
