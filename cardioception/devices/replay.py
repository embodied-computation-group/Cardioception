# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""A recorder that replays a pulse signal instead of reading one from hardware.

``systole.serialSim`` already substitutes for the serial *port*, but that is one
layer too low to be useful as a test fixture: the task still runs systole's
frame parser in real time, so a five second listening window really does take
five seconds, and the trace it replays is a single fixed recording that cannot
be steered. A session therefore cannot be run quickly, cannot be given a known
heart rate, and cannot be made to produce the awkward signals that the task's
own error handling exists for.

``ReplayRecorder`` replaces the recorder instead. It presents the same surface
the tasks already use, so it can be dropped into ``parameters["oxiTask"]``
unchanged, and in ``realtime=False`` mode it returns immediately, which turns a
five minute test session into a few seconds.

The signal is synthesised rather than loaded, so a test can ask for an exact
heart rate and assert on what the task computed from it. ``bpm`` may be a single
value or a sequence, and ``artefact_trials`` injects the kind of signal that
should trip the task's ``HRcutOff`` rejection, which no test has ever exercised.
"""

from typing import Dict, List, Optional, Sequence, Union

import numpy as np


class ReplayRecorder:
    """Stand-in for ``systole.recording.Oximeter``.

    Parameters
    ----------
    bpm :
        Heart rate to synthesise, in beats per minute. A sequence is consumed
        one entry per ``read`` call, which lets a test drive the rate over the
        course of a session.
    sfreq :
        Sampling frequency, matching the Nonin default the tasks assume.
    realtime :
        When ``False`` (the default here, unlike real hardware) ``read``
        returns as soon as it has generated the samples, rather than waiting
        for them to arrive.
    add_channels :
        Number of auxiliary channels, for trigger codes.
    rng :
        Generator for the noise, so a seeded session replays identically.
    artefact_every :
        When set, every Nth ``read`` produces a signal with no detectable
        beats, to exercise the task's retry path.

    """

    def __init__(
        self,
        bpm: Union[float, Sequence[float]] = 60.0,
        sfreq: int = 75,
        realtime: bool = False,
        add_channels: int = 1,
        rng: Optional[np.random.Generator] = None,
        artefact_every: Optional[int] = None,
    ):
        self.sfreq = sfreq
        self.realtime = realtime
        self.rng = rng if rng is not None else np.random.default_rng()
        self.artefact_every = artefact_every

        self._bpm_sequence = (
            [float(bpm)] if np.isscalar(bpm) else [float(b) for b in bpm]  # type: ignore[arg-type]
        )
        self._read_count = 0
        self._phase = 0.0

        self.recording: List[float] = []
        self.times: List[float] = []
        self.peaks: List[int] = []
        self.instant_rr: List[float] = []
        self.channels: Dict[str, List[int]] = {
            f"Channel_{i}": [] for i in range(add_channels)
        }
        self.n_saves = 0
        self.saved_paths: List[str] = []
        self._archived_codes: List[int] = []

    # -- the surface the tasks use --------------------------------------

    def setup(self) -> "ReplayRecorder":
        """Clear the buffers, as ``Oximeter.setup`` does.

        The markers written into the auxiliary channel are archived first. The
        real recorder is reset at every break, which discards every trigger
        written since the last one, and a test asking "did all five codes get
        written" would otherwise only ever see the final block's worth.
        """
        self._archived_codes.extend(int(v) for v in self.channels["Channel_0"] if v)
        self.recording, self.times, self.peaks, self.instant_rr = [], [], [], []
        for key in self.channels:
            self.channels[key] = []
        self._phase = 0.0
        return self

    def read(self, duration: float = 1.0) -> "ReplayRecorder":
        """Append ``duration`` seconds of signal."""
        self._read_count += 1
        n = int(round(duration * self.sfreq))
        artefact = (
            self.artefact_every is not None
            and self._read_count % self.artefact_every == 0
        )
        bpm = self._bpm_sequence[min(self._read_count - 1, len(self._bpm_sequence) - 1)]
        signal, peaks = self._synthesise(n, bpm, artefact)
        start = len(self.times) / self.sfreq
        self.recording.extend(signal.tolist())
        self.peaks.extend(peaks.tolist())
        self.times.extend((start + np.arange(n) / self.sfreq).tolist())
        for key in self.channels:
            self.channels[key].extend([0] * n)
        if self.realtime:  # pragma: no cover - only used against real timing
            import time as _time

            _time.sleep(duration)
        return self

    def readInWaiting(self) -> None:
        """Append the handful of samples that would have arrived meanwhile.

        The real recorder appends whatever whole packets are waiting on the
        serial port. Appending a small fixed number here keeps the trigger
        idiom ``channels["Channel_0"][-1] = n`` working, which is what the task
        relies on.
        """
        n = max(int(self.sfreq * 0.02), 1)
        bpm = self._bpm_sequence[min(self._read_count - 1, len(self._bpm_sequence) - 1)]
        signal, peaks = self._synthesise(n, bpm, False)
        start = len(self.times) / self.sfreq
        self.recording.extend(signal.tolist())
        self.peaks.extend(peaks.tolist())
        self.times.extend((start + np.arange(n) / self.sfreq).tolist())
        for key in self.channels:
            self.channels[key].extend([0] * n)

    def save(self, path: str) -> None:
        """Record that a save happened, without writing megabytes in a test."""
        self.n_saves += 1
        self.saved_paths.append(str(path))

    def close(self) -> None:
        pass

    # -- helpers ---------------------------------------------------------

    def _synthesise(self, n: int, bpm: float, artefact: bool):
        """A crude but detectable pulse waveform, plus its peak mask."""
        if artefact:
            # Noise with no periodic component, so peak detection finds nothing
            # usable and the task has to decide what to do about it.
            return self.rng.normal(0, 1, n), np.zeros(n, dtype=int)
        f = bpm / 60.0
        t = self._phase + np.arange(n) / self.sfreq
        self._phase = float(t[-1] + 1 / self.sfreq) if n else self._phase
        # A narrow positive pulse rather than a sinusoid, so a peak detector
        # sees something that looks like a systolic upstroke.
        cycle = (t * f) % 1.0
        signal = np.exp(-((cycle - 0.1) ** 2) / 0.002) * 100
        signal = signal + self.rng.normal(0, 0.5, n)
        peaks = (np.diff(np.floor(t * f), prepend=np.floor(t[0] * f)) > 0).astype(int)
        return signal, peaks

    # -- conveniences for tests ------------------------------------------

    @property
    def trigger_codes(self) -> List[int]:
        """Every marker written, including those cleared by a reset."""
        return self._archived_codes + [int(v) for v in self.channels["Channel_0"] if v]
