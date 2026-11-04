"""Stream a Nonin 3012LP pulse oximeter to Lab Streaming Layer.

Usage, from the repository root::

    .venv\\Scripts\\python.exe bench\\nonin_lsl.py              # find the port
    .venv\\Scripts\\python.exe bench\\nonin_lsl.py --port COM4

The oximeter is read as Cardioception reads it (systole's ``Oximeter``, 9600
baud, 75 Hz) and each new PPG sample is pushed, as it arrives, to the LSL
stream ``Nonin`` (type ``PPG``, one float32 channel labelled ``PPG``, 75 Hz).
Samples carry their arrival time; the serial link adds a few milliseconds.

Without ``--port`` each USB serial port is tried in turn: the first on which
``setup()`` and one second of reading give about 75 samples is used.
Ctrl+C stops it, and so does closing stdin with ``--stop-on-eof``.
"""

import argparse
import signal
import sys
import threading
import time
from typing import Optional

SFREQ = 75

#: Fewest samples one second of reading must give for a port to count as the
#: oximeter.
MIN_SAMPLES = 60


def open_oximeter(port: str):
    """Open ``port`` as ``check_device`` does, and run ``setup()``."""
    import serial
    from systole.recording import Oximeter

    ser = serial.Serial(
        port,
        baudrate=9600,
        timeout=1 / SFREQ,
        stopbits=1,
        parity=serial.PARITY_NONE,
    )
    try:
        oxi = Oximeter(serial=ser, sfreq=SFREQ, add_channels=1)
        oxi.setup(read_duration=1.0)
    except BaseException:
        ser.close()
        raise
    return oxi


def find_oximeter():
    """Try each USB serial port; return ``(port, oximeter)`` or ``(None, None)``."""
    from cardioception.check_device import find_ports

    ports = [
        (dev, desc)
        for dev, desc in find_ports()
        if "bluetooth" not in desc.lower() and "usb" in desc.lower()
    ]
    for dev, desc in ports:
        print(f"Trying {dev} ({desc}) ...", flush=True)
        try:
            oxi = open_oximeter(dev)
        except Exception as err:
            print(f"  no: {type(err).__name__}: {err}", flush=True)
            continue
        n = len(oxi.recording)
        if n >= MIN_SAMPLES:
            print(f"  yes: {n} samples in 1 s", flush=True)
            return dev, oxi
        print(f"  no: {n} samples in 1 s", flush=True)
        oxi.serial.close()
    return None, None


def make_outlet(port: str):
    import pylsl

    info = pylsl.StreamInfo("Nonin", "PPG", 1, SFREQ, pylsl.cf_float32, f"nonin-{port}")
    channel = info.desc().append_child("channels").append_child("channel")
    channel.append_child_value("label", "PPG")
    channel.append_child_value("type", "PPG")
    channel.append_child_value("unit", "normalized")
    acq = info.desc().append_child("acquisition")
    acq.append_child_value("device", "Nonin 3012LP")
    acq.append_child_value("port", port)
    return pylsl.StreamOutlet(info, chunk_size=1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--port", help="serial port, e.g. COM4 (default: search)")
    ap.add_argument(
        "--stop-on-eof",
        action="store_true",
        help="also stop when stdin closes (used by pat_live_launch.py)",
    )
    args = ap.parse_args(argv)

    port: Optional[str] = args.port
    if port and port.lower() != "auto":
        print(f"Opening {port} ...", flush=True)
        oxi = open_oximeter(port)
    else:
        port, oxi = find_oximeter()
        if oxi is None:
            print(
                "No Nonin found on the USB serial ports. Is it plugged in, with a "
                "finger in the sensor?"
            )
            return 1
    assert port is not None
    outlet = make_outlet(port)

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if args.stop_on_eof:

        def wait_for_eof():
            sys.stdin.read()
            stop.set()

        threading.Thread(target=wait_for_eof, daemon=True).start()

    print(
        f"Streaming LSL 'Nonin' from {port} at {SFREQ} Hz. Ctrl+C to stop.", flush=True
    )
    sent = len(oxi.recording)  # setup's second is not streamed
    total = 0
    last_total, t_report = 0, time.perf_counter()
    try:
        while not stop.is_set():
            oxi.readInWaiting()
            n = len(oxi.recording)
            for value in oxi.recording[sent:n]:
                outlet.push_sample([float(value)])
            total += n - sent
            sent = n
            # The recording lists grow, and systole sums the peaks list on every
            # sample; keep the last 5 s (it only looks back with negative indices).
            if n > 10 * SFREQ:
                for name in (
                    "recording",
                    "peaks",
                    "instant_rr",
                    "times",
                    "threshold",
                    "diff",
                ):
                    values = getattr(oxi, name, None)
                    if isinstance(values, list):
                        del values[: n - 5 * SFREQ]
                for channel in (oxi.channels or {}).values():
                    del channel[: n - 5 * SFREQ]
                sent = len(oxi.recording)
            now = time.perf_counter()
            if now - t_report >= 5:
                rate = (total - last_total) / (now - t_report)
                print(f"  {port}: {total:>8} samples  {rate:5.1f} Hz", flush=True)
                last_total, t_report = total, now
            time.sleep(0.005)
    finally:
        oxi.serial.close()
    print(f"Stopped: {total} samples.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
