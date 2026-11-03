"""Dry run of the PAT-ECG timing loop: ECG in over LSL, a tone out at a phase.

Reads the ``PLUX`` stream, finds R peaks as the samples arrive, and plays a
1000 Hz tone at a chosen phase of each cardiac cycle. The phase sweeps through
0, 45, ... 315 degrees on its own, so no dial is needed. Everything the loop
decides is pushed to the ``PATdryrun`` marker stream (one JSON object per
sample, see ``.context/pat-ecg/dryrun-contract.md``), so a recording of the
ECG and the markers holds the true R-to-tone timing for
``pat_dryrun_report.py`` to read.

Run it through ``pat_dryrun_launch.py``, which also starts the hub bridge and
the recorder. On its own, with a ``PLUX`` stream already online::

    .venv\\Scripts\\python.exe bench\\pat_dryrun.py --seconds 180

Scheduling, on each beat the detector commits: ``target = r_time + phase *
period``, ``period`` being the mean of the last 3 RR intervals. If the target
is less than ``--audio-lead`` seconds (0.05) away it is too late for that cycle, and
the tone goes one period later instead (anchor ``predicted`` rather than
``real``). A tone is skipped if another was due less than 0.3 s before it.

Audio goes through ``psychtoolbox.audio`` directly: one stream at latency
class 1 with the engine kept running (run mode 1), started with ``when=`` on
the ``GetSecs`` clock for each tone, and the onset read back from the
stream's ``StartTime``. On the stim PC, starts with 20 ms or more of lead were
reported within about 1 ms of the request; with 10 ms or less they were 7 to
13 ms late, hence the 0.05 s lead. Latency class 3 reported onsets up to 65 ms
off and its sound came out about 70 ms later without PTB noticing, so it is
not used (see ``bench/README.md``).
"""

import argparse
import json
import sys
import threading
import time
from collections import deque
from typing import Deque, List, Optional, Tuple

import numpy as np

from cardioception.devices._online_beats import Beat, OnlineRDetector
from cardioception.devices.lsl import PULL_CHUNK, LSLRecorder

MARKER_STREAM = "PATdryrun"
MARKER_SOURCE = "pat-dryrun"

TONE_HZ = 1000.0
TONE_SECS = 0.030
RAMP_SECS = 0.005

#: Phases swept through, in degrees.
PHASES = tuple(range(0, 360, 45))

#: A tone is skipped if another was due less than this many seconds before.
MIN_TONE_GAP = 0.3

#: Seconds between status lines.
STATUS_EVERY = 3.0

#: Seconds without a sample before the status line says so.
STALL_WARN = 2.0


def make_tone(fs: float, volume: float) -> np.ndarray:
    """1000 Hz, 30 ms, with 5 ms raised-cosine ramps, as stereo float32."""
    n = int(round(TONE_SECS * fs))
    r = int(round(RAMP_SECS * fs))
    tone = volume * np.sin(2 * np.pi * TONE_HZ * np.arange(n) / fs)
    ramp = 0.5 * (1 - np.cos(np.pi * np.arange(r) / r))
    tone[:r] *= ramp
    tone[-r:] *= ramp[::-1]
    return np.column_stack([tone, tone]).astype(np.float32)


def ptb_minus_lsl(n: int = 50) -> float:
    """Offset of ``GetSecs`` from ``local_clock``, median of ``n`` readings.

    Each reading takes ``local_clock`` either side of ``GetSecs`` and uses the
    midpoint, so the cost of the calls does not bias the offset.
    """
    import psychtoolbox as ptb
    import pylsl

    offsets = []
    for _ in range(n):
        a = pylsl.local_clock()
        g = ptb.GetSecs()
        b = pylsl.local_clock()
        offsets.append(g - (a + b) / 2)
    return float(np.median(offsets))


class TonePlayer:
    """One PsychPortAudio stream, started at a scheduled time for each tone.

    Tones are queued with their target on the ``GetSecs`` clock. ``poll``
    starts the next one when the stream is free, and returns the tones that
    have finished with the onset PsychPortAudio reports (when the first
    sample reaches the DAC, by its estimate). ``poll`` reads ``StartTime``
    while the tone plays and stops the stream once it has finished, before
    the next start.
    """

    def __init__(self, device: Optional[int], latency_class: int, volume: float):
        import psychtoolbox as ptb
        from psychtoolbox import audio

        audio.verbosity(1)
        self._ptb = ptb
        self.stream = audio.Stream(
            device_id=[] if device is None else device,
            mode=1,
            latency_class=latency_class,
            freq=[],
            channels=2,
        )
        # Keep the audio engine running between tones: restarting it for each
        # one costs the first milliseconds of a scheduled start.
        self.stream.run_mode = 1
        status = self.stream.status
        self.fs = float(status["SampleRate"])
        self.device = int(status["OutDeviceIndex"])
        self.warm_up()
        self.stream.fill_buffer(make_tone(self.fs, volume))
        self.queue: Deque[Tuple[float, dict]] = deque()
        self._active: Optional[Tuple[float, dict]] = None
        self._onset = 0.0
        self._started_at = 0.0

    def warm_up(self) -> None:
        """Play 0.1 s of silence, so the engine is running before the first tone.

        The first start after opening wakes the Windows audio endpoint, and on
        the stim PC that took 0.4 to 0.8 s: the first tone of a run came out
        that late. With run mode 1 the engine keeps running after this.
        """
        self.stream.fill_buffer(np.zeros((int(0.1 * self.fs), 2), dtype=np.float32))
        self.stream.start(repetitions=1, when=0, wait_for_start=1)
        deadline = self._ptb.GetSecs() + 3.0
        while self.stream.status["State"] != 0 and self._ptb.GetSecs() < deadline:
            time.sleep(0.005)
        self.stream.stop()

    @property
    def busy(self) -> bool:
        return self._active is not None or bool(self.queue)

    def schedule(self, when: float, payload: dict) -> None:
        self.queue.append((when, payload))

    def poll(self) -> List[Tuple[dict, float]]:
        """Advance the queue; return ``(payload, onset)`` for finished tones."""
        done = []
        now = self._ptb.GetSecs()
        if self._active is not None:
            when, payload = self._active
            status = self.stream.status
            # Until this tone starts, StartTime can still hold the last one's.
            if status["StartTime"] > when - 0.05:
                self._onset = status["StartTime"]
            # State 1 is waiting for ``when``, 2 playing, 0 stopped. Right
            # after ``start`` the state can still read 0, hence the time check.
            finished = status["State"] == 0 and now > max(when, self._started_at)
            if finished or now > when + TONE_SECS + 1.0:
                start_time = self.stream.stop()[0]
                if not self._onset and start_time > when - 0.05:
                    self._onset = start_time
                onset = self._onset
                done.append((payload, onset if onset > 0 else float("nan")))
                self._active = None
        if self._active is None and self.queue:
            when, payload = self.queue.popleft()
            self._onset = 0.0
            self._started_at = now
            self.stream.start(repetitions=1, when=when, wait_for_start=0)
            self._active = (when, payload)
        return done

    def close(self) -> None:
        try:
            self.stream.stop()
        except Exception:
            pass
        self.stream.close()


class DryRun:
    """The loop: pull, detect, schedule, play, mark."""

    def __init__(self, args: argparse.Namespace):
        import pylsl

        self.args = args
        self.pylsl = pylsl
        print(f"Looking for LSL stream {args.stream!r} ...", flush=True)
        self.rec = LSLRecorder(
            name=args.stream,
            channel=args.channel,
            signal_type="ecg",
            marker_stream=None,
            timeout=args.timeout,
        )
        print(
            f"Reading {self.rec.name!r} channel {self.rec.channel_label!r} "
            f"at {self.rec.sfreq:g} Hz",
            flush=True,
        )
        info = pylsl.StreamInfo(
            MARKER_STREAM,
            "Markers",
            1,
            pylsl.IRREGULAR_RATE,
            pylsl.cf_string,
            MARKER_SOURCE,
        )
        self.outlet = pylsl.StreamOutlet(info)
        self.player = TonePlayer(args.audio_device, args.latency_class, args.volume)
        print(
            f"Audio: PsychPortAudio device {self.player.device}, "
            f"{self.player.fs:g} Hz, latency class {args.latency_class}",
            flush=True,
        )
        self.detector = OnlineRDetector(sfreq=self.rec.sfreq)
        self.n_fed = 0
        self.n_beats = 0
        self.last_target: Optional[float] = None
        self.counts = {"real": 0, "predicted": 0, "skipped": 0, "onsets": 0}
        self.last_lag: Optional[float] = None
        self.last_error: Optional[float] = None
        self.errors: List[float] = []
        self.lags: List[float] = []
        self.offset = 0.0
        self.stop_requested = False

    def push(self, payload: dict, stamp: float) -> None:
        self.outlet.push_sample([json.dumps(payload)], stamp)

    def phase(self) -> int:
        step = max(self.args.phase_step_beats, 1)
        return PHASES[(self.n_beats // step) % len(PHASES)]

    # -- setup ---------------------------------------------------------

    def wait_for_recorder(self) -> None:
        if self.args.wait_for_recorder <= 0:
            return
        print("Waiting for the recorder to open the marker stream ...", flush=True)
        if not self.outlet.wait_for_consumers(self.args.wait_for_recorder):
            print("No recorder connected; continuing without one.", flush=True)
        else:
            # Let the recorder open the PLUX inlet too before the first marker.
            time.sleep(1.0)

    def measure_clock(self) -> None:
        self.offset = ptb_minus_lsl()
        self.push({"kind": "clock", "ptb_minus_lsl": self.offset}, 0.0)
        print(f"PTB minus LSL clock: {self.offset * 1e6:+.1f} us", flush=True)

    # -- per beat --------------------------------------------------------

    def on_beat(self, beat: Beat, commit_time: float, commit_sample_time: float):
        period = self.detector.anticipated_period
        self.push(
            {
                "kind": "beat",
                "r_time": beat.r_time,
                "commit_time": commit_time,
                "rr": beat.rr,
                "period": period,
                # Not in the contract: when the committing sample was stamped,
                # so the lag splits into detector and transport.
                "commit_sample_time": commit_sample_time,
            },
            commit_time,
        )
        self.lags.append(commit_time - beat.r_time)
        self.last_lag = commit_time - beat.r_time
        phase_deg = self.phase()
        self.n_beats += 1
        if period is None:
            return
        now = self.pylsl.local_clock()
        target = beat.r_time + phase_deg / 360.0 * period
        anchor = "real"
        if target - now <= self.args.audio_lead:
            target += period
            anchor = "predicted"
        lead = target - now
        if lead <= self.args.audio_lead or (
            self.last_target is not None and target - self.last_target < MIN_TONE_GAP
        ):
            self.counts["skipped"] += 1
            return
        self.last_target = target
        self.counts[anchor] += 1
        self.push(
            {
                "kind": "tone_scheduled",
                "r_time": beat.r_time,
                "period": period,
                "phase_deg": phase_deg,
                "target": target,
                "anchor": anchor,
                "lead": lead,
            },
            now,
        )
        self.player.schedule(
            target + self.offset, {"target": target, "phase_deg": phase_deg}
        )

    def on_onsets(self, finished: List[Tuple[dict, float]]) -> None:
        for payload, onset_ptb in finished:
            target = payload["target"]
            if not np.isfinite(onset_ptb):
                # PsychPortAudio gave no start time; say so rather than guess.
                print(f"No onset reported for the tone due at {target:.3f}")
                self.push(
                    {
                        "kind": "tone_onset",
                        "target": target,
                        "onset": None,
                        "phase_deg": payload["phase_deg"],
                    },
                    0.0,
                )
                continue
            onset = onset_ptb - self.offset
            self.push(
                {
                    "kind": "tone_onset",
                    "target": target,
                    "onset": onset,
                    "phase_deg": payload["phase_deg"],
                },
                onset,
            )
            self.counts["onsets"] += 1
            self.last_error = onset - target
            self.errors.append(self.last_error)

    # -- the loop --------------------------------------------------------

    def status(self, elapsed: float, stalled: float) -> str:
        period = self.detector.anticipated_period
        hr = f"{60 / period:5.1f}" if period else "  -  "
        lag = f"{self.last_lag * 1000:5.1f}" if self.last_lag is not None else "  -  "
        err = (
            f"{self.last_error * 1000:+6.2f}"
            if self.last_error is not None
            else "   -  "
        )
        line = (
            f"{elapsed:5.0f} s  beats {self.n_beats:4d}  HR {hr}  "
            f"phase {self.phase():3d}  tones real {self.counts['real']:3d} "
            f"pred {self.counts['predicted']:3d} skip {self.counts['skipped']:3d}  "
            f"lag {lag} ms  onset-target {err} ms"
        )
        if stalled > STALL_WARN:
            line += f"  NO SIGNAL for {stalled:.0f} s"
        return line

    def run(self) -> int:
        self.wait_for_recorder()
        self.measure_clock()
        inlet = self.rec.inlet
        inlet.flush()
        ch = self.rec.channel
        start = time.perf_counter()
        last_sample = start
        next_status = start + STATUS_EVERY
        print(
            f"Running for {self.args.seconds:g} s; phase changes every "
            f"{self.args.phase_step_beats} beats. Ctrl+C to stop.",
            flush=True,
        )
        while not self.stop_requested:
            now_pc = time.perf_counter()
            if now_pc - start >= self.args.seconds:
                break
            samples, stamps = inlet.pull_chunk(timeout=0.002, max_samples=PULL_CHUNK)
            if stamps:
                last_sample = now_pc
                x = np.asarray(samples, dtype=float)[:, ch]
                beats = self.detector.process(x, stamps)
                commit_time = self.pylsl.local_clock()
                for beat in beats:
                    i = beat.commit_index - self.n_fed
                    sample_time = stamps[min(max(i, 0), len(stamps) - 1)]
                    self.on_beat(beat, commit_time, sample_time)
                self.n_fed += len(stamps)
            self.on_onsets(self.player.poll())
            if now_pc >= next_status:
                print(self.status(now_pc - start, now_pc - last_sample), flush=True)
                next_status += STATUS_EVERY
        # Let a tone already scheduled play and report.
        deadline = time.perf_counter() + 2.0
        while self.player.busy and time.perf_counter() < deadline:
            self.on_onsets(self.player.poll())
            time.sleep(0.002)
        return 0

    def summary(self) -> str:
        lines = [
            f"Beats {self.n_beats}, tones real {self.counts['real']}, predicted "
            f"{self.counts['predicted']}, skipped {self.counts['skipped']}, "
            f"onsets reported {self.counts['onsets']}."
        ]
        if self.lags:
            lag = np.asarray(self.lags) * 1000
            lines.append(
                f"Detection lag (commit minus R): median {np.median(lag):.1f} ms, "
                f"95th percentile {np.percentile(lag, 95):.1f} ms."
            )
        if self.errors:
            err = np.asarray(self.errors) * 1000
            lines.append(
                f"Onset minus target: median {np.median(err):+.2f} ms, 95th "
                f"percentile of |error| {np.percentile(np.abs(err), 95):.2f} ms."
            )
        return "\n".join(lines)

    def close(self) -> None:
        self.player.close()
        self.rec.close()


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--seconds", type=float, default=180.0, help="default 180")
    ap.add_argument(
        "--phase-step-beats",
        type=int,
        default=8,
        help="beats per phase before moving 45 degrees on (default 8)",
    )
    ap.add_argument("--stream", default="PLUX", help="LSL stream name (default PLUX)")
    ap.add_argument("--channel", default="ECG2", help="ECG channel label")
    ap.add_argument(
        "--audio-lead",
        type=float,
        default=0.05,
        help="least time between scheduling and target, in s (default 0.05)",
    )
    ap.add_argument(
        "--audio-device",
        type=int,
        default=None,
        help="PsychPortAudio device index (default: system default output)",
    )
    ap.add_argument(
        "--latency-class",
        type=int,
        default=1,
        help="PsychPortAudio latency class (default 1, see bench/README.md)",
    )
    ap.add_argument("--volume", type=float, default=0.5, help="0 to 1 (default 0.5)")
    ap.add_argument("--timeout", type=float, default=15.0, help="stream search, s")
    ap.add_argument(
        "--wait-for-recorder",
        type=float,
        default=0.0,
        help="seconds to wait for a recorder to open the marker stream",
    )
    ap.add_argument(
        "--stop-on-eof",
        action="store_true",
        help="also stop when stdin closes (used by pat_dryrun_launch.py)",
    )
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run = DryRun(args)
    if args.stop_on_eof:

        def wait_for_eof():
            sys.stdin.read()
            run.stop_requested = True

        threading.Thread(target=wait_for_eof, daemon=True).start()
    code = 0
    try:
        code = run.run()
    except KeyboardInterrupt:
        print("\nStopped by Ctrl+C.", flush=True)
        try:
            deadline = time.perf_counter() + 2.0
            while run.player.busy and time.perf_counter() < deadline:
                run.on_onsets(run.player.poll())
                time.sleep(0.002)
        except KeyboardInterrupt:
            pass
    finally:
        print(run.summary(), flush=True)
        run.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
