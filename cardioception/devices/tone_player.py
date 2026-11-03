# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Tones and vibration bursts at scheduled times, with their reported onsets.

:class:`TonePlayer` drives PsychPortAudio (``psychtoolbox.audio``) directly:
one stereo output at latency class 1 that runs for the whole session, the
tone on the left channel and a vibration burst (for a tactor) on the right.
Times in and out are on the LSL clock. PsychToolbox is imported only when a
player is made, so this module imports without it.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .beat_source import Clock, default_clock

#: Sound kinds :class:`TonePlayer` can play.
KINDS = ("tone", "vibration")


def make_tone(
    freq: float, duration: float, ramp: float, volume: float, fs: float
) -> np.ndarray:
    """A sine burst with raised-cosine ramps, mono float32.

    The tone (1000 Hz) and the vibration burst (50 Hz) are both made with it.
    ``ramp`` is shortened to half the burst if it is longer.
    """
    n = max(int(round(duration * fs)), 1)
    x = volume * np.sin(2 * np.pi * freq * np.arange(n) / fs)
    r = min(int(round(ramp * fs)), n // 2)
    if r > 0:
        window = 0.5 * (1 - np.cos(np.pi * np.arange(r) / r))
        x[:r] *= window
        x[-r:] *= window[::-1]
    return x.astype(np.float32)


#: The former private name, kept for callers that used it.
_burst = make_tone


def ptb_minus_clock(clock: Clock, n: int = 50) -> float:
    """Offset of PsychToolbox's ``GetSecs`` from ``clock``, median of ``n`` readings.

    Each reading takes ``clock`` either side of ``GetSecs`` and uses the
    midpoint, so the cost of the calls does not bias the offset.
    """
    import psychtoolbox as ptb

    offsets = []
    for _ in range(n):
        a = clock()
        g = ptb.GetSecs()
        b = clock()
        offsets.append(g - (a + b) / 2)
    return float(np.median(offsets))


class _Track:
    """One PsychPortAudio slave: a queue of starts of one sound."""

    def __init__(self, slave: Any, duration: float):
        self.slave = slave
        self.duration = duration
        self.queue: List[Tuple[float, int]] = []  # (when on GetSecs, handle)
        self.active: Optional[Tuple[float, int]] = None
        self.onset = 0.0
        self.started_at = 0.0


class TonePlayer:
    """Tones and vibration bursts at scheduled times, through PsychPortAudio.

    One stereo output at latency class 1, kept running for the whole session
    (a master stream with two slaves), so starts are sample-accurate and the
    Windows audio endpoint never has to wake up. The tone plays on the left
    channel, the vibration burst on the right one, so the exteroceptive task
    can drive a tactor through an amplifier from the same jack. Tone and
    vibration can overlap in time.

    :meth:`schedule` and :meth:`poll_onsets` take and return times on
    ``clock`` (the LSL clock by default); the offset to ``GetSecs`` is
    measured once at start.

    Parameters
    ----------
    freq, duration, ramp, volume :
        The tone: Hz, seconds, seconds of raised-cosine ramp at each end,
        amplitude 0 to 1.
    vib_freq, vib_duration, vib_volume :
        The vibration burst, likewise (same ramp).
    device :
        PsychPortAudio output device index; the system default if omitted.
    clock :
        The clock of ``when`` and of the reported onsets.
    """

    def __init__(
        self,
        freq: float = 1000.0,
        duration: float = 0.03,
        ramp: float = 0.005,
        volume: float = 0.5,
        vib_freq: float = 50.0,
        vib_duration: float = 0.05,
        vib_volume: float = 1.0,
        device: Optional[int] = None,
        clock: Optional[Clock] = None,
    ):
        for name, value in (("volume", volume), ("vib_volume", vib_volume)):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} should be between 0 and 1, got {value}")
        import psychtoolbox as ptb
        from psychtoolbox import audio

        audio.verbosity(1)
        self._ptb = ptb
        self.clock = clock or default_clock()
        self.offset = ptb_minus_clock(self.clock)
        # Mode 1 + 8: playback, as a master that slaves mix into.
        self.master = audio.Stream(
            device_id=[] if device is None else device,
            mode=1 + 8,
            latency_class=1,
            freq=[],
            channels=2,
        )
        self.master.run_mode = 1
        status = self.master.status
        self.fs = float(status["SampleRate"])
        self.device = int(status["OutDeviceIndex"])
        # Run forever, from now; slaves are mixed in when started.
        self.master.start(repetitions=0, when=0, wait_for_start=1)
        tone = make_tone(freq, duration, ramp, volume, self.fs)
        vib = make_tone(vib_freq, vib_duration, ramp, vib_volume, self.fs)
        self._tracks: Dict[str, _Track] = {}
        for kind, left, right, dur in (
            ("tone", tone, np.zeros_like(tone), duration),
            ("vibration", np.zeros_like(vib), vib, vib_duration),
        ):
            slave = audio.Slave(self.master.handle, mode=1, channels=2)
            slave.fill_buffer(np.column_stack([left, right]))
            self._tracks[kind] = _Track(slave, dur)
        self._next_handle = 0
        self._done: List[Tuple[int, float]] = []
        self._closed = False
        # Let the endpoint settle before the first real start.
        time.sleep(0.2)

    @property
    def busy(self) -> bool:
        """True while any scheduled sound has not yet reported its onset.

        That is, while one is waiting or playing, or has finished but not
        yet been returned by :meth:`poll_onsets`. Does not advance anything:
        keep calling :meth:`poll_onsets` until it is False.
        """
        if self._done:
            return True
        return any(t.active is not None or t.queue for t in self._tracks.values())

    def schedule(self, when: float, kind: str = "tone") -> int:
        """Play ``kind`` at ``when`` (clock seconds). Returns a handle.

        The onset is reported by :meth:`poll_onsets` under that handle. Sounds
        of one kind play one after the other in time order; a sound whose
        time has passed by the time its turn comes plays at once (and its
        onset says so).
        """
        if kind not in self._tracks:
            raise ValueError(f"kind should be one of {KINDS}, got {kind!r}")
        handle = self._next_handle
        self._next_handle += 1
        track = self._tracks[kind]
        track.queue.append((when + self.offset, handle))
        track.queue.sort()
        self._advance(track)
        return handle

    def poll_onsets(self) -> List[Tuple[int, float]]:
        """``(handle, onset)`` of the sounds that have finished since the last call.

        ``onset`` is when PsychPortAudio says the first sample reached the
        output, on ``clock``; NaN if it gave none (e.g. stopped before it
        started).
        """
        for track in self._tracks.values():
            self._advance(track)
        done, self._done = self._done, []
        return done

    def _advance(self, track: _Track) -> None:
        """Finish the playing sound if it is over, then start the next one."""
        now = self._ptb.GetSecs()
        if track.active is not None:
            when, handle = track.active
            status = track.slave.status
            # Until this sound starts, StartTime can still hold the last one's.
            if status["StartTime"] > when - 0.05:
                track.onset = status["StartTime"]
            # State 1 is waiting for ``when``, 2 playing, 0 stopped. Right
            # after a start the state can still read 0, hence the time check.
            finished = status["State"] == 0 and now > max(when, track.started_at)
            if finished or now > when + track.duration + 1.0:
                start_time = track.slave.stop()[0]
                if not track.onset and start_time > when - 0.05:
                    track.onset = start_time
                onset = track.onset - self.offset if track.onset else math.nan
                self._done.append((handle, onset))
                track.active = None
        if track.active is None and track.queue:
            when, handle = track.queue.pop(0)
            track.onset = 0.0
            track.started_at = now
            track.slave.start(repetitions=1, when=when, wait_for_start=0)
            track.active = (when, handle)

    def stop_all(self) -> None:
        """Stop everything playing or waiting. Their onsets are still reported.

        A sound that had started keeps its onset, the others report NaN.
        """
        now = self._ptb.GetSecs()
        for track in self._tracks.values():
            if track.active is not None:
                when, handle = track.active
                status = track.slave.status
                start_time = track.slave.stop()[0]
                onset = 0.0
                for candidate in (status["StartTime"], start_time):
                    if when - 0.05 < candidate <= now:
                        onset = candidate
                self._done.append((handle, onset - self.offset if onset else math.nan))
                track.active = None
            self._done.extend((handle, math.nan) for _, handle in track.queue)
            track.queue = []

    def close(self) -> None:
        """Stop and release the audio device."""
        if self._closed:
            return
        self._closed = True
        try:
            self.stop_all()
        except Exception:
            pass
        # Slaves first: closing the master closes them under their feet.
        for track in self._tracks.values():
            track.slave.close()
        try:
            self.master.stop()
        except Exception:
            pass
        self.master.close()
