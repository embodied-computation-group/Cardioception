"""Read a PAT-ECG dry run back from its XDF: how late were the beats and the tones?

Usage, from the repository root::

    .venv\\Scripts\\python.exe bench\\pat_dryrun_report.py bench\\data\\pat_dryrun_<stamp>.xdf

The R peaks found offline in the whole recording
(:func:`cardioception.devices._beats.detect_beats`) are the reference. Against
them the report gives:

- detection lag, from each ``beat`` marker's ``commit_time`` minus its
  ``r_time``: how long after the R-peak sample was stamped the task knew of
  the beat;
- online versus offline R timing, matched within ``--tolerance``;
- for each tone, the interval from the nearest preceding offline R peak to the
  onset PsychPortAudio reported, as a phase of the cycle it fell in, against
  the phase intended, split by anchor (``real`` or ``predicted``);
- the onset error, reported onset minus target.

A figure is saved next to the XDF as ``<name>_report.png``.

The same works on a live run of the task (``bench/pat_live_launch.py``): its
marker stream is ``PAT`` (``--markers PAT``, also picked up on its own when
there is no ``PATdryrun``). Its beat markers carry no ``commit_time``, so the
marker's timestamp is used; only tones (not vibrations) are scored; marker
kinds the report does not use (``trial_start``, ``dial``, ``press``, ...) are
counted and otherwise skipped. The task aims each tone ``latencyBias`` (0.05 s)
before the phase on the dial, to make up for delays the timestamps cannot see;
``--bridge-lag 0.05`` puts the report on the same footing.

A file without markers (any recording with a ``PLUX`` ECG) gets
the detector part only: the online detector is replayed over the recorded
signal, and its lag is then the detector's own, without transport.

All times are LSL timestamps of when samples reached the hub bridge on the
PC, which is 20 to 40 ms after the hub sampled them. True R peaks were that
much earlier than their timestamps, so true phases are later than shown by
that amount; ``--bridge-lag 0.03`` moves the offline R peaks back to correct
for it.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

#: Samples per chunk when the online detector is replayed over a file, as the
#: hub bridge sends them.
REPLAY_CHUNK = 10


def find_stream(streams: List[dict], name: str) -> Optional[dict]:
    for stream in streams:
        if stream["info"]["name"][0] == name:
            return stream
    return None


def arrival_timeline(stamps: np.ndarray, sfreq: float, block: float = 5.0):
    """Sample times that follow the arrival timestamps, smoothed over ``block`` s.

    pyxdf's dejitter fits one straight line through a stream's timestamps,
    which assumes the device clock runs at a constant rate against the PC.
    The PLUX hub's does not: on a 26 min recording the arrival times wandered
    from 90 ms before to 150 ms after that line, and the pulse transit time
    to the Nonin (a separate device) stayed constant on the arrival timeline
    but drifted by 110 ms on the straight one. The online detector stamps
    beats on the arrival timeline too, so the offline R peaks are put there:
    the straight line, plus the median of the raw timestamps' departure from
    it in each ``block``, interpolated between blocks.
    """
    stamps = np.asarray(stamps, dtype=float)
    n = np.arange(len(stamps), dtype=float)
    t0 = stamps[0]
    slope, intercept = np.polyfit(n, stamps - t0, 1)
    line = t0 + intercept + slope * n
    resid = stamps - line
    size = max(int(block * sfreq), 1)
    starts = np.arange(0, len(stamps), size)
    centres = np.minimum(starts + size / 2, len(stamps) - 1)
    medians = [np.median(resid[i:][:size]) for i in starts]
    return line + np.interp(n, centres, medians)


def channel_labels(stream: dict) -> List[str]:
    try:
        channels = stream["info"]["desc"][0]["channels"][0]["channel"]
        return [c["label"][0] for c in channels]
    except (KeyError, IndexError, TypeError):
        n = int(stream["info"]["channel_count"][0])
        return [str(i) for i in range(n)]


def pct(x, q) -> float:
    return float(np.percentile(x, q)) if len(x) else float("nan")


def wrap180(deg):
    return (np.asarray(deg, dtype=float) + 180.0) % 360.0 - 180.0


def circ_mean(deg) -> float:
    rad = np.deg2rad(np.asarray(deg, dtype=float))
    return float(np.rad2deg(np.angle(np.mean(np.exp(1j * rad)))) % 360.0)


def replay_online(signal, times, sfreq) -> Dict[str, np.ndarray]:
    """Run the online detector over a recording, chunk by chunk."""
    from cardioception.devices._online_beats import OnlineRDetector

    detector = OnlineRDetector(sfreq=sfreq)
    r_time, commit_time = [], []
    for start in range(0, len(signal), REPLAY_CHUNK):
        stop = start + REPLAY_CHUNK
        for beat in detector.process(signal[start:stop], times[start:stop]):
            r_time.append(beat.r_time)
            commit_time.append(times[beat.commit_index])
    return {"r_time": np.asarray(r_time), "commit_time": np.asarray(commit_time)}


def match(online: np.ndarray, offline: np.ndarray, tolerance: float) -> dict:
    """Pair each online R with the nearest offline R within ``tolerance``."""
    if not len(online) or not len(offline):
        return {"tp": 0, "sens": np.nan, "ppv": np.nan, "err": np.array([])}
    # Only the stretch the online detector covered can be held against it.
    ref = offline[(offline >= online[0] - tolerance) & (offline <= online[-1] + 1.0)]
    idx = np.clip(np.searchsorted(ref, online), 1, len(ref) - 1)
    nearest = np.where(
        np.abs(online - ref[idx - 1]) <= np.abs(online - ref[idx]),
        ref[idx - 1],
        ref[idx],
    )
    err = online - nearest
    hit = np.abs(err) <= tolerance
    tp = len(np.unique(nearest[hit]))
    return {
        "tp": tp,
        "n_ref": len(ref),
        "sens": tp / len(ref),
        "ppv": hit.sum() / len(online),
        "err": err[hit],
    }


def tone_table(markers: List[dict], r_peaks: np.ndarray) -> List[dict]:
    """One row per reported onset, with the true phase from the offline R peaks."""
    scheduled = {
        m.get("target"): m for m in markers if m.get("kind") == "tone_scheduled"
    }
    rows = []
    for m in markers:
        if m.get("kind") != "tone_onset" or m.get("sound", "tone") != "tone":
            continue
        if m.get("onset") is None or m.get("phase_deg") is None:
            continue
        sched = scheduled.get(m["target"], {})
        onset = m["onset"]
        i = np.searchsorted(r_peaks, onset) - 1
        if i < 0 or i + 1 >= len(r_peaks):
            continue
        prev_r, next_r = r_peaks[i], r_peaks[i + 1]
        true_phase = 360.0 * (onset - prev_r) / (next_r - prev_r)
        rows.append(
            {
                "anchor": m.get("anchor") or sched.get("anchor", "unknown"),
                "phase_deg": float(m["phase_deg"]),
                "target": m["target"],
                "onset": onset,
                "onset_error": onset - m["target"],
                "r_to_onset": onset - prev_r,
                "cycle": next_r - prev_r,
                "true_phase": true_phase,
                "phase_error": float(wrap180(true_phase - m["phase_deg"])),
                # The phase error as time, in the cycle the tone fell in.
                "time_error": float(wrap180(true_phase - m["phase_deg"]))
                / 360.0
                * (next_r - prev_r),
                "period": sched.get("period", np.nan),
            }
        )
    return rows


def describe(label: str, values_ms, unit: str = "ms") -> str:
    v = np.asarray(values_ms, dtype=float)
    if not v.size:
        return f"{label}: none"
    return (
        f"{label}: n {v.size}, median {np.median(v):+.1f} {unit}, "
        f"95th percentile {pct(v, 95):+.1f}, max {v.max():+.1f}"
    )


def report(args: argparse.Namespace) -> int:
    import pyxdf

    from cardioception.devices._beats import detect_beats

    path = Path(args.xdf)
    # Raw timestamps: see arrival_timeline for why not pyxdf's dejitter.
    streams, _ = pyxdf.load_xdf(str(path), dejitter_timestamps=args.linear_timestamps)
    plux = find_stream(streams, args.stream)
    if plux is None:
        names = ", ".join(s["info"]["name"][0] for s in streams)
        sys.exit(f"No {args.stream!r} stream in {path.name}. Streams: {names}")
    labels = channel_labels(plux)
    if args.channel not in labels:
        sys.exit(f"No channel {args.channel!r} in {args.stream!r}: {labels}")
    sfreq = float(plux["info"]["nominal_srate"][0])
    times = np.asarray(plux["time_stamps"], dtype=float)
    if not args.linear_timestamps:
        times = arrival_timeline(times, sfreq)
    data = np.asarray(plux["time_series"])
    signal = data[:, labels.index(args.channel)].astype(float)
    print(
        f"{path.name}: {args.stream} {args.channel}, {len(times)} samples, "
        f"{(times[-1] - times[0]):.0f} s at {sfreq:g} Hz"
    )
    if "nSeq" in labels:
        nseq = data[:, labels.index("nSeq")].astype(np.int64)
        steps = np.diff(nseq)
        print(
            f"Hub samples dropped: {int((steps - 1)[steps > 1].sum())} "
            f"in {int((steps > 1).sum())} gaps"
        )

    _, peaks = detect_beats(signal, sfreq, "ecg", int(round(sfreq)))
    idx = np.flatnonzero(peaks)
    r_offline = times[np.clip(idx, 0, len(times) - 1)] - args.bridge_lag
    rr = np.diff(r_offline)
    print(
        f"Offline R peaks: {len(r_offline)}, median HR " f"{60 / np.median(rr):.1f} bpm"
        if len(rr)
        else "Offline R peaks: none"
    )

    markers: List[dict] = []
    marker_stream = find_stream(streams, args.markers)
    if marker_stream is None and args.markers == "PATdryrun":
        marker_stream = find_stream(streams, "PAT")
    if marker_stream is not None:
        name = marker_stream["info"]["name"][0]
        for sample, stamp in zip(
            marker_stream["time_series"], marker_stream["time_stamps"]
        ):
            try:
                marker = json.loads(sample[0])
            except (ValueError, TypeError):
                continue
            if isinstance(marker, dict) and "kind" in marker:
                marker["_stamp"] = float(stamp)
                markers.append(marker)
        kinds: Dict[str, int] = {}
        for marker in markers:
            kinds[marker["kind"]] = kinds.get(marker["kind"], 0) + 1
        print(
            f"Markers ({name}): "
            + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))
        )
    beats = [m for m in markers if m.get("kind") == "beat"]
    clock = [m for m in markers if m.get("kind") == "clock"]
    if clock:
        print(f"PTB minus LSL clock: {clock[0]['ptb_minus_lsl'] * 1e6:+.1f} us")

    if beats:
        source = "online, from the beat markers"
        r_online = np.array([b["r_time"] for b in beats])
        # The task's beat markers have no commit_time: they are pushed, and
        # stamped, when the beat is known.
        commit = np.array([b.get("commit_time", b["_stamp"]) for b in beats])
        sample_commit = np.array(
            [b.get("commit_sample_time", np.nan) for b in beats], dtype=float
        )
    else:
        source = "online detector replayed over the file (no transport)"
        replay = replay_online(signal, times, sfreq)
        r_online, commit = replay["r_time"], replay["commit_time"]
        sample_commit = commit.copy()
    lag = (commit - r_online) * 1000
    print(f"\nDetection lag ({source})")
    print("  " + describe("commit minus R", lag))
    if beats and np.isfinite(sample_commit).any():
        print(
            "  "
            + describe(
                "of which detector (commit sample minus R)",
                (sample_commit - r_online) * 1000,
            )
        )
        print(
            "  "
            + describe(
                "of which transport (commit minus commit sample)",
                (commit - sample_commit) * 1000,
            )
        )

    # The online R times carry no bridge-lag correction; compare like with like.
    m = match(r_online, r_offline + args.bridge_lag, args.tolerance)
    print(f"\nOnline vs offline R peaks (tolerance {args.tolerance * 1000:.0f} ms)")
    print(f"  sensitivity {m['sens']:.3f}, positive predictive value {m['ppv']:.3f}")
    err = np.abs(m["err"]) * 1000
    if err.size:
        print(
            f"  |online minus offline|: median {np.median(err):.1f} ms, 95th "
            f"percentile {pct(err, 95):.1f} ms, max {err.max():.1f} ms"
        )

    rows = tone_table(markers, r_offline)
    n_sched = sum(1 for x in markers if x.get("kind") == "tone_scheduled")
    n_onset = sum(1 for x in markers if x.get("kind") == "tone_onset")
    if n_sched:
        print(
            f"\nTones: {n_sched} scheduled, {n_onset} onsets reported, "
            f"{len(rows)} placed between two offline R peaks"
        )
        onset_err = np.array([r["onset_error"] for r in rows]) * 1000
        if onset_err.size:
            print(
                f"  onset minus target: median {np.median(onset_err):+.2f} ms, "
                f"95th percentile of |error| {pct(np.abs(onset_err), 95):.2f} ms, "
                f"max |error| {np.abs(onset_err).max():.2f} ms"
            )
        for anchor in ("real", "predicted"):
            sub = [r for r in rows if r["anchor"] == anchor]
            if not sub:
                continue
            perr = np.array([r["phase_error"] for r in sub])
            terr = np.array([r["time_error"] for r in sub]) * 1000
            print(
                f"  anchor {anchor}: n {len(sub)}, true minus intended phase "
                f"median {np.median(perr):+.1f} deg, 95th percentile of |error| "
                f"{pct(np.abs(perr), 95):.1f} deg; as time, median "
                f"{np.median(terr):+.1f} ms, 95th percentile of |error| "
                f"{pct(np.abs(terr), 95):.1f} ms"
            )
        print("\n  phase   real  pred   true phase (circular mean)   R-to-onset median")
        for phase in sorted({r["phase_deg"] for r in rows}):
            sub = [r for r in rows if r["phase_deg"] == phase]
            n_real = sum(r["anchor"] == "real" for r in sub)
            n_pred = sum(r["anchor"] == "predicted" for r in sub)
            interval = np.median([r["r_to_onset"] for r in sub]) * 1000
            print(
                f"  {phase:5.0f}  {n_real:5d} {n_pred:5d}   "
                f"{circ_mean([r['true_phase'] for r in sub]):22.1f}   "
                f"{interval:14.0f} ms"
            )
    elif marker_stream is None:
        print(f"\nNo {args.markers!r} stream: detector comparison only.")

    out = Path(args.out) if args.out else path.with_name(path.stem + "_report.png")
    figure(out, path.name, rows, r_online, lag, sample_commit, beats)
    print(f"\nFigure: {out}")
    return 0


def figure(out, title, rows, r_online, lag, sample_commit, beats) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"real": "#2a78d6", "predicted": "#eb6834", "unknown": "#52514e"}
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#8a8984",
            "axes.labelcolor": "#0b0b0b",
            "xtick.color": "#52514e",
            "ytick.color": "#52514e",
            "font.size": 9,
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    fig.suptitle(title, fontsize=10)

    ax = axes[0]
    if rows:
        rng = np.random.default_rng(0)
        for anchor in ("real", "predicted", "unknown"):
            sub = [r for r in rows if r["anchor"] == anchor]
            if not sub:
                continue
            x = np.array([r["phase_deg"] for r in sub])
            # Shown on the side of the intended phase it is nearest, so 350
            # against 0 reads as 10 degrees early, not 350 late.
            y = x + np.array([r["phase_error"] for r in sub])
            ax.scatter(
                x + rng.uniform(-6, 6, x.size),
                y,
                s=14,
                color=colors[anchor],
                alpha=0.7,
                linewidths=0,
                label=f"{anchor} (n {len(sub)})",
            )
        ax.plot([-20, 335], [-20, 335], color="#8a8984", lw=1, zorder=0)
        ax.set_xticks(range(0, 360, 45))
        ax.legend(frameon=False, loc="upper left")
    else:
        ax.text(0.5, 0.5, "no tones in this file", ha="center", transform=ax.transAxes)
    ax.set_xlabel("intended phase (deg)")
    ax.set_ylabel("true phase from offline R (deg)")
    ax.set_title("True vs intended phase", loc="left")
    ax.grid(color="#e6e5e0", lw=0.6)

    ax = axes[1]
    err = np.array([r["onset_error"] for r in rows]) * 1000
    if err.size:
        ax.hist(err, bins=40, color=colors["real"], edgecolor="white", linewidth=0.5)
        ax.axvline(0, color="#8a8984", lw=1)
    else:
        ax.text(0.5, 0.5, "no tones in this file", ha="center", transform=ax.transAxes)
    ax.set_xlabel("reported onset minus target (ms)")
    ax.set_ylabel("tones")
    ax.set_title("Onset error", loc="left")
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)

    ax = axes[2]
    if len(r_online):
        t = r_online - r_online[0]
        label = "commit minus R" if beats else "detector replay"
        ax.plot(t, lag, ".", ms=4, color=colors["real"], label=label)
        detector = (sample_commit - r_online) * 1000
        if beats and np.isfinite(detector).any():
            ax.plot(
                t, detector, ".", ms=4, color=colors["predicted"], label="detector part"
            )
        ax.legend(frameon=False, loc="upper right")
    ax.set_xlabel("time from first beat (s)")
    ax.set_ylabel("lag (ms)")
    ax.set_title("Detection lag", loc="left")
    ax.grid(color="#e6e5e0", lw=0.6)

    fig.savefig(out, dpi=130)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("xdf", help="the recording")
    ap.add_argument("--stream", default="PLUX")
    ap.add_argument("--channel", default="ECG2")
    ap.add_argument("--markers", default="PATdryrun")
    ap.add_argument(
        "--tolerance",
        type=float,
        default=0.05,
        help="online and offline R match within this, in s (default 0.05)",
    )
    ap.add_argument(
        "--bridge-lag",
        type=float,
        default=0.0,
        help="seconds the bridge timestamps trail the hub; shifts R peaks back",
    )
    ap.add_argument(
        "--linear-timestamps",
        action="store_true",
        help="use pyxdf's straight-line dejitter for the ECG timestamps, as "
        "before 2026-11-03 (wrong on long recordings)",
    )
    ap.add_argument("--out", help="figure path (default next to the XDF)")
    return report(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
