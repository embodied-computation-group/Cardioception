# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Check that the pulse oximeter is producing a real signal.

    python -m cardioception.check_device

Run this before collecting data. The obvious check, counting beats, does not
work: with an empty sensor the peak detector still reports beats at a plausible
rate, so a session can look fine and contain nothing at all. Measured on an
empty Nonin 3012LP, a trace spanning a single ADC unit produced ten "beats" in
twenty seconds.

What separates the cases is **signal amplitude**, and amplitude is therefore
tested first. A finger gives a swing of a couple of hundred units; an empty
sensor gives one or two. Only once there is a signal worth detecting beats in
does the spread of the inter-beat intervals say whether detection is reliable.
"""

import argparse
import sys
from typing import List, Optional, Tuple

import numpy as np

#: Below this peak-to-peak swing there is nothing to detect beats in. An empty
#: sensor measures around 1; a finger measures in the hundreds. The gap is wide
#: enough that the exact threshold hardly matters.
MIN_AMPLITUDE = 20.0

#: Plausible human inter-beat intervals, in seconds: 50 to 150 BPM.
IBI_MIN, IBI_MAX = 0.4, 1.2

#: Above this standard deviation the detector is finding beats in noise as well
#: as in the pulse.
MAX_IBI_SD = 0.15


def find_ports() -> List[Tuple[str, str]]:
    """Serial ports the machine can see, as (device, description)."""
    from serial.tools import list_ports

    return [(p.device, p.description) for p in list_ports.comports()]


def describe(recording: np.ndarray, peaks: np.ndarray, sfreq: int = 75) -> dict:
    """Summarise a recording without deciding anything about it."""
    out: dict = {
        "n_samples": int(len(recording)),
        "duration": len(recording) / sfreq if sfreq else float("nan"),
        "amplitude": float("nan"),
        "n_beats": int(np.sum(peaks)),
        "bpm": float("nan"),
        "ibi_mean": float("nan"),
        "ibi_min": float("nan"),
        "ibi_max": float("nan"),
        "ibi_sd": float("nan"),
    }
    if len(recording):
        out["amplitude"] = float(
            np.percentile(recording, 95) - np.percentile(recording, 5)
        )
    idx = np.where(peaks)[0]
    if len(idx) > 2:
        ibi = np.diff(idx) / sfreq
        out.update(
            bpm=float(60 / ibi.mean()),
            ibi_mean=float(ibi.mean()),
            ibi_min=float(ibi.min()),
            ibi_max=float(ibi.max()),
            ibi_sd=float(ibi.std()),
        )
    return out


def verdict(summary: dict) -> Tuple[str, str]:
    """Turn a summary into a verdict and a suggestion.

    Amplitude is checked before anything else. A flat trace can still yield
    beats, so reading the beat count first gets the answer wrong in exactly the
    case that matters most.

    """
    if summary["n_samples"] == 0:
        return ("no data", "The device is connected but sent nothing. Check the cable.")

    if not np.isfinite(summary["amplitude"]) or summary["amplitude"] < MIN_AMPLITUDE:
        return (
            "no finger in the sensor",
            "The trace is flat. Any beats reported here are noise. Put a finger "
            "in the sensor and run this again.",
        )

    if summary["n_beats"] < 3 or not np.isfinite(summary["ibi_sd"]):
        return (
            "signal present but no pulse detected",
            "There is a signal but too few beats to judge it. Check the sensor "
            "is on a fingertip and not too loose.",
        )

    plausible = IBI_MIN <= summary["ibi_min"] and summary["ibi_max"] <= IBI_MAX
    if not plausible or summary["ibi_sd"] > MAX_IBI_SD:
        return (
            "signal present but detection unreliable",
            "The intervals between beats are too scattered to trust. Reseat the "
            "sensor, keep the hand still and below heart level, and try again.",
        )

    return ("clean physiological signal", "Ready to collect data.")


def check(port: Optional[str] = None, duration: int = 20, sfreq: int = 75) -> int:
    """Record briefly and report. Returns a shell exit status."""
    import serial
    from systole.recording import Oximeter

    ports = find_ports()
    if not ports:
        print("No serial ports found.")
        print("  Is the oximeter plugged in? On Windows it appears as a COM port,")
        print("  on macOS and Linux as /dev/tty.usbserial-* or /dev/ttyUSB*.")
        return 2

    if port is None:
        if len(ports) > 1:
            print("More than one serial port found, so pick one with --port:")
            for dev, desc in ports:
                print(f"  {dev}  {desc}")
            return 2
        port = ports[0][0]
        print(f"Using the only serial port found: {port} ({ports[0][1]})")

    print(f"Recording {duration} s from {port}. Keep a finger in the sensor.")
    ser = None
    try:
        ser = serial.Serial(
            port,
            baudrate=9600,
            timeout=1 / sfreq,
            stopbits=1,
            parity=serial.PARITY_NONE,
        )
        oxi = Oximeter(serial=ser, sfreq=sfreq, add_channels=1)
        oxi.setup()
        oxi.read(duration=duration)
    except Exception as exc:  # noqa: BLE001 - the message is the whole point
        print(f"\nCould not read from {port}: {type(exc).__name__}: {exc}")
        print("  Another program may be holding the device. Close it and retry.")
        return 2
    finally:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    s = describe(
        np.asarray(oxi.recording, dtype=float), np.asarray(oxi.peaks), sfreq=sfreq
    )
    state, advice = verdict(s)

    print("")
    print(f"  samples            {s['n_samples']} ({s['duration']:.1f} s)")
    print(
        f"  signal amplitude   {s['amplitude']:.1f}      (needs > {MIN_AMPLITUDE:.0f})"
    )
    print(f"  beats detected     {s['n_beats']}")
    if np.isfinite(s["bpm"]):
        print(f"  heart rate         {s['bpm']:.0f} BPM")
        print(
            f"  beat intervals     {s['ibi_min']:.2f} to {s['ibi_max']:.2f} s, "
            f"sd {s['ibi_sd']:.3f}   (needs sd < {MAX_IBI_SD})"
        )
    print("")
    print(f"  VERDICT: {state}")
    print(f"  {advice}")

    return 0 if state == "clean physiological signal" else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cardioception.check_device",
        description="Check the pulse oximeter is producing a real signal.",
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Serial port. Discovered automatically when there is only one.",
    )
    parser.add_argument(
        "--duration", type=int, default=20, help="Seconds to record (default 20)."
    )
    parser.add_argument(
        "--sfreq", type=int, default=75, help="Sampling frequency (default 75)."
    )
    parser.add_argument(
        "--list", action="store_true", help="List serial ports and exit."
    )
    args = parser.parse_args(argv)

    if args.list:
        ports = find_ports()
        if not ports:
            print("No serial ports found.")
            return 2
        for dev, desc in ports:
            print(f"{dev}  {desc}")
        return 0

    return check(port=args.port, duration=args.duration, sfreq=args.sfreq)


if __name__ == "__main__":
    sys.exit(main())
