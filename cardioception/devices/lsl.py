# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Read the heart from a Lab Streaming Layer stream instead of a serial port.

Any device with an LSL outlet can drive the tasks this way: an ECG amplifier,
a biosignalsplux hub, a PPG sensor. The device's own software owns the
hardware and publishes the stream; Cardioception is one more consumer of it,
so the same signal can be recorded by LabRecorder alongside everything else
in the session.

The trigger codes the tasks write into ``Channel_0`` are also pushed, as they
happen, to an LSL marker stream. A recorder that saves both streams then holds
the physiology and the task events on one clock, which the per-trial text
files cannot provide.

Requires ``pylsl`` (``pip install cardioception-toolbox[lsl]``).
"""

import logging
import time
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ._beats import detect_beats

logger = logging.getLogger("cardioception")

#: Signal types the beat detector knows how to read.
SIGNAL_TYPES = ("ecg", "ppg")

#: Seconds of signal searched for a beat by ``waitBeat``.
BEAT_SEARCH_WINDOW = 3.0

#: Seconds ``waitBeat`` waits for a beat before giving up and returning, so a
#: lost signal delays a trial instead of hanging it.
BEAT_TIMEOUT = 5.0

#: Most samples one ``pull_chunk`` call returns; ``_pull`` repeats it until
#: the inlet is empty.
PULL_CHUNK = 1024


class _MarkerChannel(list):
    """A trigger channel that also sends what is written to it.

    The tasks mark an event with ``channels["Channel_0"][-1] = code``. Sending
    from the assignment keeps that idiom, so neither task has to know where
    its markers end up.
    """

    def __init__(self, outlet=None):
        super().__init__()
        self._outlet = outlet

    def __setitem__(self, index, value):
        super().__setitem__(index, value)
        if self._outlet is not None and not isinstance(index, slice) and value:
            # The enum name where there is one, so the marker stream reads
            # without the task's code table.
            label = getattr(value, "name", None) or str(int(value))
            self._outlet.push_sample([label])


class LSLRecorder:
    """Record ECG or PPG from an LSL stream, with the surface of ``Oximeter``.

    Parameters
    ----------
    name :
        Name of the stream to read, e.g. ``"PLUX"``. Either this or
        ``stream_type`` is required.
    stream_type :
        Type of the stream to read, e.g. ``"ECG"``, when the name is not
        known in advance.
    channel :
        The channel holding the heart signal: an index, or a label from the
        stream's ``channels`` metadata, e.g. ``"ECG2"``.
    signal_type :
        ``"ecg"`` or ``"ppg"``. Chooses the beat detector, and whether the
        tutorial asks for a pulse oximeter on the finger.
    add_channels :
        Number of auxiliary channels, for trigger codes.
    marker_stream :
        Name of the LSL marker stream the trigger codes are sent to. ``None``
        sends nothing.
    timeout :
        Seconds to look for the stream before giving up.

    Attributes
    ----------
    lsl_times : list of float
        The LSL timestamp of each sample, on the clock LabRecorder writes.
    wall_times : list of float
        The same moments as ``time.time()``, to align with the results file.

    """

    def __init__(
        self,
        name: Optional[str] = None,
        stream_type: Optional[str] = None,
        channel: Union[int, str] = 0,
        signal_type: str = "ecg",
        add_channels: int = 1,
        marker_stream: Optional[str] = "Cardioception",
        timeout: float = 10.0,
    ):
        import pylsl

        if signal_type not in SIGNAL_TYPES:
            raise ValueError(
                f"signal_type should be one of {SIGNAL_TYPES}, got {signal_type!r}"
            )
        if name is None and stream_type is None:
            raise ValueError("Give the stream's name or its type.")

        self._pylsl = pylsl
        self.signal_type = signal_type
        self.n_channels = add_channels
        self.info = self._resolve(name, stream_type, timeout)
        self.name = self.info.name()
        self.sfreq = self.info.nominal_srate()
        if self.sfreq <= 0:
            raise ValueError(
                f"LSL stream {self.name!r} has an irregular rate, and the beat "
                "detectors need a fixed one."
            )
        self.channel_labels = self._channel_labels()
        self.channel = self._channel_index(channel)
        self.channel_label = self.channel_labels[self.channel]

        self.inlet = pylsl.StreamInlet(
            self.info,
            max_buflen=60,
            processing_flags=pylsl.proc_clocksync | pylsl.proc_dejitter,
        )
        self.inlet.open_stream(timeout=timeout)

        self.outlet = None
        if marker_stream is not None:
            marker_info = pylsl.StreamInfo(
                marker_stream,
                "Markers",
                1,
                pylsl.IRREGULAR_RATE,
                pylsl.cf_string,
                f"cardioception-{marker_stream}",
            )
            self.outlet = pylsl.StreamOutlet(marker_info)

        # LSL timestamps are seconds on local_clock(); this offset turns them
        # into epoch seconds, matching the times in the results file.
        self._epoch_offset = time.time() - pylsl.local_clock()
        self.reset()
        logger.info(
            f"LSL recorder: {self.name!r} channel {self.channel_label!r} "
            f"({self.signal_type.upper()}, {self.sfreq:g} Hz)"
        )

    # -- finding the stream ----------------------------------------------

    def _resolve(self, name, stream_type, timeout):
        prop, value = ("name", name) if name is not None else ("type", stream_type)
        found = self._pylsl.resolve_byprop(prop, value, timeout=timeout)
        if not found:
            visible = [
                f"{s.name()} ({s.type()})"
                for s in self._pylsl.resolve_streams(wait_time=1.0)
            ]
            raise RuntimeError(
                f"No LSL stream with {prop} {value!r} found in {timeout:g} s. "
                f"Streams visible: {', '.join(visible) or 'none'}. Is the "
                "device's streaming program running?"
            )
        if len(found) > 1:
            logger.warning(
                f"{len(found)} LSL streams with {prop} {value!r}; using the first."
            )
        return found[0]

    def _channel_labels(self) -> List[str]:
        """Labels from the stream metadata, or the indices where there are none.

        ``resolve_byprop`` returns only the header, so the full description
        comes from an inlet.
        """
        full = self._pylsl.StreamInlet(self.info).info(timeout=5.0)
        labels = []
        ch = full.desc().child("channels").child("channel")
        while not ch.empty():
            labels.append(ch.child_value("label"))
            ch = ch.next_sibling()
        if len(labels) != self.info.channel_count():
            labels = [str(i) for i in range(self.info.channel_count())]
        return labels

    def _channel_index(self, channel: Union[int, str]) -> int:
        labels = self.channel_labels
        if isinstance(channel, str):
            if channel not in labels:
                raise ValueError(
                    f"No channel {channel!r} in LSL stream {self.name!r}. "
                    f"Channels: {', '.join(labels)}"
                )
            return labels.index(channel)
        if not 0 <= channel < len(labels):
            raise ValueError(
                f"Channel {channel} out of range: {self.name!r} has "
                f"{len(labels)} channels."
            )
        return channel

    # -- the surface the tasks use ---------------------------------------

    def reset(self) -> "LSLRecorder":
        """Empty the buffers, keeping the connection."""
        self.recording: List[float] = []
        self.peaks: List[int] = []
        self.instant_rr: List[float] = []
        self.times: List[float] = []
        self.lsl_times: List[float] = []
        self.wall_times: List[float] = []
        self.channels: Dict[str, List[int]] = {
            f"Channel_{i}": _MarkerChannel(self.outlet if i == 0 else None)
            for i in range(self.n_channels)
        }
        return self

    def setup(self, read_duration: float = 1.0) -> "LSLRecorder":
        """Start a new recording, as ``Oximeter.setup`` does.

        Drops what the inlet holds, so the recording starts now, then reads
        ``read_duration`` seconds and fails if nothing arrived. The stream is
        still recorded in full by anything else consuming it.
        """
        self.reset()
        self.inlet.flush()
        self.read(duration=read_duration)
        if read_duration > 0 and not self.recording:
            raise RuntimeError(
                f"No samples from LSL stream {self.name!r} in {read_duration:g} s. "
                "Is the device streaming?"
            )
        return self

    def read(self, duration: float = 1.0) -> "LSLRecorder":
        """Record for ``duration`` seconds."""
        start = time.time()
        while time.time() - start < duration:
            self._pull(timeout=min(0.05, duration))
        return self

    def readInWaiting(self, stop: bool = False) -> None:
        """Append everything that has arrived since the last read, without waiting.

        The recording then ends at the newest sample, so a trigger written to
        ``channels["Channel_0"][-1]`` straight after marks the present.
        """
        self._pull(timeout=0.0)

    def waitBeat(self) -> "LSLRecorder":
        """Read until a beat arrives that was not there when this was called.

        Gives up after :data:`BEAT_TIMEOUT` seconds. A lost signal then delays
        the trial rather than hanging the session.
        """
        start = time.time()
        known = len(self.recording)
        window = int(BEAT_SEARCH_WINDOW * self.sfreq)
        while time.time() - start < BEAT_TIMEOUT:
            self._pull(timeout=0.05)
            if len(self.recording) < window:
                continue
            offset = len(self.recording) - window
            _, peaks = detect_beats(
                self.recording[-window:], self.sfreq, self.signal_type, self.sfreq
            )
            beats = offset + np.flatnonzero(peaks)
            if beats.size and beats[-1] >= known:
                self.peaks[int(beats[-1])] = 1
                return self
        logger.warning(f"No beat in {BEAT_TIMEOUT:g} s from LSL stream {self.name!r}")
        return self

    def save(self, fname: str) -> None:
        """Write the recording, with beats found over the whole of it."""
        n = len(self.recording)
        if n > 2 * self.sfreq:
            _, peaks = detect_beats(
                self.recording, self.sfreq, self.signal_type, self.sfreq
            )
            self.peaks = peaks.astype(int).tolist()
            beats = np.flatnonzero(peaks)
            rr = np.full(n, np.nan)
            rr[beats[1:]] = np.diff(beats) / self.sfreq * 1000
            self.instant_rr = rr.tolist()
        columns = {
            "signal": self.recording,
            "peaks": self.peaks,
            "instant_rr": (
                self.instant_rr if len(self.instant_rr) == n else [np.nan] * n
            ),
            "time": self.times,
            "lsl_time": self.lsl_times,
            "wall_time": self.wall_times,
        }
        columns.update(self.channels)
        pd.DataFrame(columns).to_csv(fname, index=False)

    def close(self) -> None:
        self.inlet.close_stream()
        self.outlet = None

    def describe(self) -> Dict[str, Union[str, float]]:
        """What the recording is reading, for the session manifest."""
        return {
            "recorder": "lsl",
            "stream": self.name,
            "channel": self.channel_label,
            "signal_type": self.signal_type,
            "sfreq": self.sfreq,
        }

    # -- helpers ---------------------------------------------------------

    def _pull(self, timeout: float) -> None:
        """Append everything the inlet holds, waiting ``timeout`` for the first.

        One ``pull_chunk`` returns at most ``PULL_CHUNK`` samples, about a
        second at 1000 Hz, so after a longer gap it is repeated until the
        inlet is empty. Otherwise a trigger written after ``readInWaiting``
        would land on a sample from the start of the gap.
        """
        while True:
            samples, stamps = self.inlet.pull_chunk(
                timeout=timeout, max_samples=PULL_CHUNK
            )
            if not stamps:
                return
            start = len(self.recording)
            self.recording.extend(float(s[self.channel]) for s in samples)
            self.peaks.extend([0] * len(stamps))
            self.instant_rr.extend([np.nan] * len(stamps))
            self.times.extend((start + i) / self.sfreq for i in range(len(stamps)))
            self.lsl_times.extend(stamps)
            self.wall_times.extend(t + self._epoch_offset for t in stamps)
            for channel in self.channels.values():
                channel.extend([0] * len(stamps))
            if len(stamps) < PULL_CHUNK:
                return
            timeout = 0.0
