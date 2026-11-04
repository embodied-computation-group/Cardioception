"""Measure audio onset timing on the stimulation PC.

Three measurements for a beat-locked auditory task:

1. Clock relation between ``psychtoolbox.GetSecs()`` and ``pylsl.local_clock()``.
2. Scheduled playback accuracy with PsychPortAudio, used directly and through
   PsychoPy's ``sound.Sound`` (PTB backend).
3. Physical loopback through the laptop speaker and microphone, as a rough check
   that the onset PsychPortAudio reports is real.

The script makes sound. Run it from the repository root with the project venv::

    .venv\\Scripts\\python.exe bench\\audio_onset.py

Use ``--no-loopback`` to skip the microphone check and ``--save-recording`` to
keep the loopback recording as a ``.npz`` file for inspection.
"""

import argparse
import time

import numpy as np
import psychtoolbox as ptb
import pylsl
from psychtoolbox import audio

FS = 48000
TONE_HZ = 1000.0
TONE_SECS = 0.030
RAMP_SECS = 0.005


# ---------------------------------------------------------------- helpers


def table(title, rows, header=None):
    """Print a small left-aligned table."""
    print(f"\n{title}")
    print("-" * len(title))
    all_rows = ([header] if header else []) + rows
    widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(all_rows[0]))]
    for k, row in enumerate(all_rows):
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
        if header and k == 0:
            print("  ".join("-" * w for w in widths))


def ms(x, nd=3):
    return f"{1000 * x:.{nd}f} ms"


def us(x):
    return f"{1e6 * x:.1f} us"


def summary(err):
    err = np.asarray(err)
    return {
        "n": len(err),
        "median": np.median(err),
        "p95": np.percentile(np.abs(err), 95),
        "max": np.max(np.abs(err)),
        "sd": np.std(err, ddof=1) if len(err) > 1 else np.nan,
    }


def make_tone(fs=FS, channels=2):
    """1000 Hz, 30 ms tone with 5 ms raised-cosine on and off ramps."""
    n = int(round(TONE_SECS * fs))
    t = np.arange(n) / fs
    y = 0.5 * np.sin(2 * np.pi * TONE_HZ * t)
    nr = int(round(RAMP_SECS * fs))
    ramp = 0.5 * (1 - np.cos(np.pi * np.arange(nr) / nr))
    y[:nr] *= ramp
    y[-nr:] *= ramp[::-1]
    return np.tile(y[:, None], (1, channels)).astype(np.float32)


def make_click(fs=FS, channels=2):
    """Sharp-onset 3 kHz burst (4 ms) for loopback onset detection."""
    n = int(round(0.004 * fs))
    t = np.arange(n) / fs
    y = 0.8 * np.sin(2 * np.pi * 3000.0 * t)
    nr = int(round(0.001 * fs))
    y[-nr:] *= np.linspace(1, 0, nr)
    return np.tile(y[:, None], (1, channels)).astype(np.float32)


def open_stream(classes=(3, 1), **kwargs):
    """Open a PsychPortAudio stream, trying latency classes in order."""
    errors = {}
    for cls in classes:
        try:
            return audio.Stream(latency_class=cls, **kwargs), cls, errors
        except Exception as err:  # PTB raises plain Exception
            errors[cls] = str(err).splitlines()[0] if str(err) else repr(err)
    raise RuntimeError(f"could not open stream: {errors}")


def wait_until(t):
    """Sleep until GetSecs() reaches t (coarse sleep, then spin)."""
    while True:
        dt = t - ptb.GetSecs()
        if dt <= 0:
            return
        time.sleep(dt - 0.002 if dt > 0.003 else 0)


# ---------------------------------------------------- 1. clock relation


def clock_relation(n=200):
    """Sample GetSecs, local_clock and perf_counter back to back."""
    lsl_off, perf_off, rtt = [], [], []
    for _ in range(n):
        g0 = ptb.GetSecs()
        lsl = pylsl.local_clock()
        perf = time.perf_counter()
        g1 = ptb.GetSecs()
        mid = 0.5 * (g0 + g1)
        lsl_off.append(lsl - mid)
        perf_off.append(perf - mid)
        rtt.append(g1 - g0)
        time.sleep(0.002)
    lsl_off, perf_off, rtt = map(np.asarray, (lsl_off, perf_off, rtt))

    rows = []
    for name, off in (
        ("local_clock - GetSecs", lsl_off),
        ("perf_counter - GetSecs", perf_off),
    ):
        rows.append(
            [
                name,
                f"{np.median(off):+.6f} s",
                us(np.percentile(off, 95) - np.percentile(off, 5)),
                us(off.max() - off.min()),
            ]
        )
    table(
        f"1. Clock relation ({n} samples, 2 ms apart, GetSecs = {ptb.GetSecs():.1f} s)",
        rows,
        header=["pair", "median offset", "p5-p95 spread", "range"],
    )
    print(f"median duration of the GetSecs bracket: {us(np.median(rtt))}")
    same = abs(np.median(lsl_off)) < 1e-3 and (lsl_off.max() - lsl_off.min()) < 2e-4
    if same:
        print(
            "Verdict: SAME clock. local_clock and GetSecs share the "
            "QueryPerformanceCounter origin (offset near zero and stable). LSL "
            "timestamps can be used directly as PTB `when` times, no conversion needed."
        )
    else:
        print(
            "Verdict: DIFFERENT origin. Convert with when = lsl_time - median_offset "
            f"({np.median(lsl_off):+.6f} s), and re-measure it every session."
        )
    return {"lsl_offset": float(np.median(lsl_off)), "same": same}


# --------------------------------------------- 2. scheduled playback (PTB)


def run_schedule(start_fn, status_fn, n, lead, settle=0.06):
    """Schedule n playbacks at GetSecs()+lead; return requested and reported."""
    req, rep, xruns = [], [], []
    for _ in range(n):
        when = ptb.GetSecs() + lead
        start_fn(when)
        wait_until(when + TONE_SECS + settle)
        st = status_fn()
        req.append(when)
        rep.append(st["StartTime"])
        xruns.append(st.get("XRuns", 0))
        time.sleep(0.02)
    return np.asarray(req), np.asarray(rep), int(max(xruns) if xruns else 0)


def measure_config(stream, run_mode, n, lead):
    """Warm up, read predicted latency, then schedule n tones."""
    stream.run_mode = run_mode
    stream.start(when=ptb.GetSecs() + 0.2)  # warm-up
    wait_until(ptb.GetSecs() + 0.4)
    when = ptb.GetSecs() + 0.1
    stream.start(when=when)
    wait_until(when + 0.01)
    predicted = stream.status["PredictedLatency"]
    wait_until(when + 0.1)
    req, rep, xr = run_schedule(
        lambda w: stream.start(when=w), lambda: stream.status, n, lead
    )
    return summary(rep - req), xr, predicted


def schedule_ptb(n=50, lead=0.1):
    """Requested vs reported onset for latency class 3 (low latency) and 1."""
    configs, results, sweeps, notes = [], {}, {}, []
    dev = None
    for want in (3, 1):
        try:
            stream, cls, errors = open_stream(
                classes=(want,), mode=1, freq=FS, channels=2
            )
        except RuntimeError as err:
            notes.append(f"latency class {want} refused: {err}")
            continue
        st = stream.status
        out_index = int(st["OutDeviceIndex"])
        dev = [d for d in audio.get_devices() if int(d["DeviceIndex"]) == out_index][0]
        stream.fill_buffer(make_tone())
        # run_mode 0 (default) stops the engine after each sound; run_mode 1 keeps
        # it running between sounds, as a beat-locked task would.
        for run_mode in (0, 1) if cls == 3 else (1,):
            key = f"class {cls}, run_mode {run_mode}"
            configs.append(key)
            results[key] = measure_config(stream, run_mode, n, lead)
        sweeps[cls] = []
        for lead_i in (0.002, 0.005, 0.010, 0.020, 0.050):
            r, p_, _ = run_schedule(
                lambda w: stream.start(when=w), lambda: stream.status, 20, lead_i
            )
            sweeps[cls].append(p_ - r)
        stream.close()

    def cell(key, what):
        s, xr, pred = results[key]
        extra = {"xruns": xr, "pred": ms(pred)}
        return extra[what] if what in extra else us(s[what])

    table(
        f"2a. PsychPortAudio direct: reported StartTime - requested when "
        f"(n={n}, lead {ms(lead, 0)})",
        [
            [label] + [cell(k, what) for k in configs]
            for label, what in (
                ("median error", "median"),
                ("p95 |error|", "p95"),
                ("max |error|", "max"),
                ("predicted output latency", "pred"),
                ("xruns", "xruns"),
            )
        ],
        header=[""] + configs,
    )
    if dev is not None:
        print(
            f"device: {dev['HostAudioAPIName']}: {dev['DeviceName']}, 48000 Hz, "
            f"device low output latency {ms(dev['LowOutputLatency'])}"
        )
    for note in notes:
        print(f"note: {note}")

    leads = (2, 5, 10, 20, 50)
    rows = []
    for i, lead_ms in enumerate(leads):
        row = [f"{lead_ms} ms"]
        for cls in sweeps:
            e = sweeps[cls][i]
            row += [us(np.median(e)), f"{np.mean(e > 0.5e-3):.0%}"]
        rows.append(row)
    header = ["lead"]
    for cls in sweeps:
        header += [f"class {cls} median", f"class {cls} late>0.5ms"]
    table(
        "2b. Lead sweep, run_mode 1 (20 each): schedule at GetSecs()+lead", rows, header
    )
    return results, configs


# ------------------------------------------ 2c. PsychoPy sound.Sound (PTB)


def schedule_psychopy(n=50, lead=0.1):
    from psychopy import logging, prefs

    logging.console.setLevel(logging.ERROR)
    prefs.hardware["audioLib"] = ["PTB"]
    prefs.hardware["audioLatencyMode"] = 3
    from psychopy import sound
    from psychopy.hardware.speaker import SpeakerDevice

    notes = []
    try:
        sound.Sound.resolveBackend()
    except Exception as err:
        notes.append(
            f"audioLib=['PTB'] rejected ({type(err).__name__}: backend keys are "
            "lower case); used ['ptb']"
        )
        prefs.hardware["audioLib"] = ["ptb"]
    notes.append(
        "prefs.hardware['audioLatencyMode'] is a legacy pref in this PsychoPy and is "
        "ignored; the latency class was passed as SpeakerDevice(latencyClass=...)"
    )

    speaker, cls = None, None
    for c in (3, 1):
        try:
            speaker = SpeakerDevice(latencyClass=c)
            cls = c
            break
        except Exception as err:
            notes.append(
                f"SpeakerDevice(latencyClass={c}) failed: {str(err).splitlines()[0]}"
            )
    if speaker is None:
        print("\n2c. PsychoPy sound.Sound: could not open a speaker, skipped")
        for note in notes:
            print(f"note: {note}")
        return None

    fs = int(speaker.sampleRateHz)
    snd = sound.Sound(
        make_tone(fs, int(speaker.channels)),
        sampleRate=fs,
        hamming=False,
        speaker=speaker,
        autoLog=False,
    )
    detail = snd.statusDetailed
    has_onset = isinstance(detail, dict) and "StartTime" in detail

    def start(w):
        snd.stop(log=False)
        snd.play(when=w, log=False)

    rows = [
        ["device", speaker.name],
        ["latency class", cls],
        [
            "onset API",
            (
                "snd.statusDetailed['StartTime'] (PTB slave status)"
                if has_onset
                else "none"
            ),
        ],
    ]
    result = {"cls": cls, "has_onset": has_onset, "err": None}
    if has_onset:
        start(ptb.GetSecs() + 0.2)  # warm-up
        wait_until(ptb.GetSecs() + 0.4)
        req, rep, xr = run_schedule(start, lambda: snd.statusDetailed, n, lead)
        valid = rep > 0
        s = summary(rep[valid] - req[valid])
        result["err"] = s
        rows += [
            [
                "master predicted latency",
                ms(speaker.stream.status["PredictedLatency"]),
            ],
            ["n valid / lead", f"{s['n']}/{n} / {ms(lead, 0)}"],
            ["median error", us(s["median"])],
            ["p95 |error|", us(s["p95"])],
            ["max |error|", us(s["max"])],
            ["xruns", xr],
        ]
    table(
        "2c. PsychoPy sound.Sound (PTB backend): reported StartTime - requested when",
        rows,
    )
    for note in notes:
        print(f"note: {note}")
    if not has_onset:
        print(
            "PsychoPy's Sound does not expose a reported onset for this backend; the "
            "task would have no per-tone timestamp from it."
        )
    try:
        snd.stop(log=False)
        speaker.close()
    except Exception:
        pass
    return result


# ---------------------------------------------------- 3. physical loopback


def find_input_device(out_index):
    devs = audio.get_devices()
    out = [d for d in devs if int(d["DeviceIndex"]) == out_index][0]
    cands = [
        d
        for d in devs
        if d["NrInputChannels"] > 0
        and d["HostAudioAPIName"] == out["HostAudioAPIName"]
        and "loopback" not in d["DeviceName"].lower()
    ]
    return cands[0] if cands else None


def detect_onsets(x, fs, t_capture0, sched, baseline_secs):
    """Envelope threshold onset per scheduled click; returns onsets and SNRs."""
    x = x - np.convolve(x, np.ones(48) / 48, mode="same")  # crude high-pass
    k = max(1, int(0.0003 * fs))
    env = np.convolve(np.abs(x), np.ones(k) / k, mode="same")
    nb = int(baseline_secs * fs)
    noise = np.percentile(env[:nb], 99.5)
    onsets, snrs = [], []
    for t in sched:
        i0 = int((t - 0.010 - t_capture0) * fs)
        i1 = int((t + 0.200 - t_capture0) * fs)
        if i0 < 0 or i1 > len(env):
            onsets.append(np.nan)
            snrs.append(0.0)
            continue
        seg = env[i0:i1]
        peak = seg.max()
        snr = peak / noise if noise > 0 else np.inf
        snrs.append(snr)
        if snr < 4:
            onsets.append(np.nan)
            continue
        thr = noise + 0.2 * (peak - noise)
        idx = int(np.argmax(seg > thr))
        onsets.append(t_capture0 + (i0 + idx) / fs)
    return np.asarray(onsets), np.asarray(snrs), noise


def loopback(out_class, n=20, interval=0.4, save=None, lead=0.1):
    try:
        out, out_cls, _ = open_stream(classes=(out_class,), mode=1, freq=FS, channels=2)
    except RuntimeError as err:
        print(f"\n3. Loopback: output class {out_class} unavailable ({err}), skipped")
        return None
    out_index = int(out.status["OutDeviceIndex"])
    indev = find_input_device(out_index)
    if indev is None:
        print("\n3. Loopback: no microphone on the same host API, skipped")
        out.close()
        return None
    try:
        mic, in_cls, _ = open_stream(
            # Shared mode on purpose: in exclusive mode (class 2/3) this Realtek SST
            # mic delivers about 1.8x more samples than wall-clock time, so its
            # recording cannot be mapped to GetSecs.
            classes=(1,),
            device_id=int(indev["DeviceIndex"]),
            mode=2,
            freq=FS,
            channels=int(min(2, indev["NrInputChannels"])),
        )
    except RuntimeError as err:
        print(f"\n3. Loopback: microphone unavailable ({err}), skipped")
        out.close()
        return None

    out.fill_buffer(make_click())
    out.run_mode = 1
    baseline = 0.8
    total = baseline + n * interval + 1.0
    mic.get_audio_data(total + 2.0)  # allocate the capture buffer
    mic.start(0, 0, 1)
    t0 = ptb.GetSecs() + baseline + 0.2
    sched = t0 + interval * np.arange(n)
    reported = []
    for t in sched:
        wait_until(t - lead)
        out.start(when=t)
        wait_until(t + 0.05)
        reported.append(out.status["StartTime"])
    wait_until(sched[-1] + 0.4)
    wall = ptb.GetSecs() - mic.status["CaptureStartTime"]
    mic.stop()
    cap0 = mic.status["CaptureStartTime"]
    data, _, overflow, cstart = mic.get_audio_data()
    if not cap0:
        cap0 = cstart
    out.close()
    mic.close()

    data = np.asarray(data, dtype=float)
    x = data.mean(axis=1) if data.ndim == 2 else data
    base_secs = max(0.1, min(baseline, sched[0] - cap0 - 0.05))
    onsets, snrs, noise = detect_onsets(x, FS, cap0, sched, base_secs)
    reported = np.asarray(reported)
    if save:
        np.savez(save, x=x, fs=FS, capture_start=cap0, sched=sched, reported=reported)

    ok = np.isfinite(onsets)
    rows = [
        ["input device", f"{indev['HostAudioAPIName']}: {indev['DeviceName']}"],
        ["latency class out / in", f"{out_cls} / {in_cls}"],
        [
            "recorded / wall clock",
            f"{len(x) / FS:.2f} s / {wall:.2f} s, overflow={overflow}",
        ],
        ["clicks detected", f"{ok.sum()}/{n} (median SNR {np.median(snrs):.0f}x)"],
    ]
    title = f"3. Physical loopback, output class {out_cls} (speaker, air, laptop mic)"
    if abs(len(x) / FS - wall) > 0.05 * wall or overflow:
        table(title, rows)
        print("Recording length does not match wall-clock time; loopback invalid.")
        return None
    if ok.sum() >= max(5, n // 2):
        d = onsets[ok] - sched[ok]
        rd = onsets[ok] - reported[ok]
        rows += [
            ["recorded - scheduled, median", ms(np.median(d), 2)],
            ["recorded - scheduled, SD", ms(np.std(d, ddof=1), 2)],
            ["recorded - scheduled, range", f"{ms(d.min(), 2)} .. {ms(d.max(), 2)}"],
            ["recorded - reported, median", ms(np.median(rd), 2)],
        ]
        table(title, rows)
        print(
            "This delay includes the microphone input path (driver buffering, any mic "
            "DSP, and the accuracy of PTB's CaptureStartTime) and acoustic travel, so it "
            "is an upper bound on the true output latency, not a measurement of it. The "
            "SD is the useful number: small means onsets are locked to the schedule."
        )
        return {
            "cls": out_cls,
            "median": float(np.median(d)),
            "sd": float(np.std(d, ddof=1)),
            "rep_median": float(np.median(rd)),
        }
    table(title, rows)
    print(
        "Too few clicks detected above the noise floor (room too noisy, speaker muted, "
        "or mic unavailable). Loopback skipped; no onset estimate."
    )
    return None


# ------------------------------------------------------------------ main


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-loopback", action="store_true", help="skip the mic check")
    ap.add_argument(
        "--save-recording", default=None, help="path prefix for loopback .npz files"
    )
    args = ap.parse_args()

    audio.verbosity(1)
    print(
        f"psychtoolbox {ptb.__version__}, pylsl {pylsl.__version__}, "
        f"{audio.get_version_info()['version']}"
    )
    clock = clock_relation()
    direct, configs = schedule_ptb()
    pp = schedule_psychopy()
    lbs = []
    if not args.no_loopback:
        for c in (3, 1):
            save = (
                f"{args.save_recording}_class{c}.npz" if args.save_recording else None
            )
            lbs.append(loopback(c, save=save))

    print("\nSummary")
    print("-------")
    print(f"clocks same origin: {clock['same']} (offset {clock['lsl_offset']:+.6f} s)")
    for key in configs:
        e = direct[key][0]
        print(
            f"PTB direct {key}: median error {us(e['median'])}, "
            f"max {us(e['max'])}, predicted latency {ms(direct[key][2])}"
        )
    if pp and pp["err"]:
        print(
            f"PsychoPy Sound: class {pp['cls']}, median error "
            f"{us(pp['err']['median'])}, max {us(pp['err']['max'])}"
        )
    for lb in lbs:
        if lb:
            print(
                f"loopback class {lb['cls']}: recorded - scheduled "
                f"{ms(lb['median'], 2)} +/- {ms(lb['sd'], 2)} SD, recorded - reported "
                f"{ms(lb['rep_median'], 2)} (upper bounds)"
            )


if __name__ == "__main__":
    main()
