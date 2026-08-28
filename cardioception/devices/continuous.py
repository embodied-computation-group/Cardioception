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
import pandas as pd
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
    peaks: list
    instant_rr: list
    recording: list

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

    def read(self, duration: float = 1.0):
        """Record for ``duration`` seconds, keeping what came before.

        `Oximeter.read` calls `self.setup()` when a packet fails its checksum,
        and `setup()` resets: one corrupt packet, on a line where corrupt
        packets are the reason a checksum exists, discards the entire
        recording so far. `readInWaiting` handles the same failure by
        resyncing and keeps the recording, so the asymmetry is not a
        considered decision, and it is unsurvivable once a session's worth of
        signal is at stake.

        This resyncs the way `readInWaiting` does. It reads whole packets and
        drops a byte on a bad one, so the stream realigns within five bytes
        instead of losing everything.
        """
        start = time.time()
        while time.time() - start < duration:
            if self.serial.inWaiting() >= 5:
                paquet = list(self.serial.read(5))
                if self.check(paquet):
                    self.add_paquet(value=self.get_value(paquet))
                else:
                    # One byte, not one packet: the stream is misaligned, and
                    # discarding five would step over the next valid header.
                    self.serial.read(1)
        return self

    def save(self, fname: str):
        """Write the recording out, without the repairs that corrupt it.

        `Oximeter.save` guards against its channel lists having drifted out of
        length with each other::

            if len(self.peaks) != len(self.recording):
                self.peak = [0 * len(self.recording)]

        Three things are wrong in two lines. `self.peak` is a typo for
        `self.peaks`, so the assignment creates a new attribute and the real
        list is untouched. `[0 * len(x)]` is the one-element list `[0]`, not a
        zero-filled list of that length -- `[0] * len(x)` was meant. The same
        `[0 * len(x)]` appears for `instant_rr` and `times`, where there is no
        typo and the result is still `[0]`. So every guard replaces a
        wrong-length list with a length-one list, and `np.array(saveList).T`
        two dozen lines later is handed ragged input.

        These fire only when the lists have drifted, which needs a long
        recording -- exactly the case continuous recording creates. Padding to
        the recording's length is what was intended, and the wall clock goes
        out alongside, since `times` counts samples and cannot show a gap.
        """
        n = len(self.recording)
        if len(self.peaks) != n:
            self.peaks = self._padded(self.peaks, n, 0)
        if len(self.instant_rr) != n:
            self.instant_rr = self._padded(self.instant_rr, n, float("nan"))
        if len(self.times) != n:
            self.times = [i / self.sfreq for i in range(n)]
        if len(self.wall_times) != n:
            self.wall_times = self._padded(self.wall_times, n, float("nan"))
        if self.channels is not None:
            for name, channel in self.channels.items():
                if len(channel) != n:
                    self.channels[name] = self._padded(channel, n, 0)

        columns = {
            "signal": self.recording,
            "peaks": self.peaks,
            "instant_rr": self.instant_rr,
            "time": self.times,
            "wall_time": self.wall_times,
        }
        if self.channels is not None:
            columns.update(self.channels)
        pd.DataFrame(columns).to_csv(fname, index=False)

    @staticmethod
    def _padded(values: list, n: int, fill) -> list:
        """``values`` at exactly length ``n``: truncated, or padded with fill."""
        if len(values) > n:
            return list(values[:n])
        return list(values) + [fill] * (n - len(values))
