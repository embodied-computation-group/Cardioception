"""One command for the PAT-ECG dry run: hub bridge, recorder, task loop.

Usage, from the repository root (hub on, electrodes on)::

    .venv\\Scripts\\python.exe bench\\pat_dryrun_launch.py --seconds 180

1. Starts the hub bridge, ``plux-lsl\\plux_lsl.py``, with plux-lsl's own
   Python 3.13 venv (PLUX's API has no 3.11 build), and waits for its ``PLUX``
   stream.
2. Starts ``bench\\pat_dryrun.py`` in this console, and once its ``PATdryrun``
   marker stream is up, ``LabRecorderCLI.exe`` recording ``PLUX`` and
   ``PATdryrun`` to ``bench\\data\\pat_dryrun_<stamp>.xdf``. The dry run waits
   for the recorder before its first marker.
3. When the dry run ends (after ``--seconds``, or Ctrl+C), stops the recorder,
   then the bridge, and prints the path of the XDF.

Options it does not know are passed on to ``pat_dryrun.py`` (e.g.
``--volume 0.3``). The logs of the bridge and the recorder are written next
to the XDF. Every process it starts is in a Windows job object that is closed
when this script exits, however it exits, so nothing is left running.
"""

import argparse
import ctypes
import datetime
import os
import shlex
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import List, Optional

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
PLUX_DIR = REPO.parent / "plux-lsl"
BRIDGE_PYTHON = PLUX_DIR / ".venv" / "Scripts" / "python.exe"
BRIDGE_SCRIPT = PLUX_DIR / "plux_lsl.py"
LABRECORDER = PLUX_DIR / "LabRecorder" / "LabRecorderCLI.exe"
DATA_DIR = BENCH / "data"

# liblsl errors only, as in plux-lsl; set before pylsl loads, inherited by all.
if (PLUX_DIR / "lsl_api.cfg").exists():
    os.environ.setdefault("LSLAPICFG", str(PLUX_DIR / "lsl_api.cfg"))

import pylsl  # noqa: E402

# -- no orphans --------------------------------------------------------------


class _IoCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_ulonglong)
        for name in ("read_ops", "write_ops", "other_ops", "read", "write", "other")
    ]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


_JOB = None


def kill_children_on_exit() -> bool:
    """Put this process in a job that kills everything in it when it exits.

    Processes started afterwards join the job too, and so do their own
    children. That matters here: a venv's ``python.exe`` is a launcher that
    starts the real interpreter as a child, which killing the launcher alone
    would leave running.
    """
    global _JOB
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return False
    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
    ok = kernel32.SetInformationJobObject(
        wintypes.HANDLE(job),
        9,  # JobObjectExtendedLimitInformation
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ) and kernel32.AssignProcessToJobObject(
        wintypes.HANDLE(job), wintypes.HANDLE(kernel32.GetCurrentProcess())
    )
    if ok:
        _JOB = job  # kept open until this process exits
    return bool(ok)


# -- the parts -----------------------------------------------------------------


class Stop:
    """Ctrl+C reaches every process in the console. The dry run handles its
    own; here it only stops the waiting, and the clean-up still runs."""

    requested = False

    @classmethod
    def handler(cls, *_):
        if not cls.requested:
            print("\nCtrl+C: stopping ...", flush=True)
        cls.requested = True


def tail(path: Path, n: int = 15) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join("    " + ln for ln in lines[-n:])


def wait_for_stream(name: str, timeout: float, proc: subprocess.Popen) -> bool:
    """Wait until ``name`` is visible, while ``proc`` is alive."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not Stop.requested:
        if pylsl.resolve_byprop("name", name, timeout=0.5):
            return True
        if proc.poll() is not None:
            return False
    return False


def stop_by_eof(proc: Optional[subprocess.Popen], name: str, timeout: float):
    """Close its stdin (``--stop-on-eof``) and wait; kill if it hangs."""
    if proc is None:
        return
    try:
        if proc.stdin is not None:
            proc.stdin.close()
        proc.wait(timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        print(f"{name} did not stop in {timeout:g} s; killing it.", flush=True)
        proc.kill()
        proc.wait(timeout=5)


def stop_recorder(proc: Optional[subprocess.Popen]) -> None:
    """As plux-lsl's recorder.py: let the last chunks in, then Enter."""
    if proc is None or proc.poll() is not None:
        return
    time.sleep(1.5)
    try:
        proc.communicate(b"\n", timeout=20)
    except subprocess.TimeoutExpired:
        print("LabRecorderCLI did not finish in 20 s; killing it.", flush=True)
        proc.kill()
        proc.wait(timeout=5)


def split(cmd: str) -> List[str]:
    return [t.strip('"') for t in shlex.split(cmd, posix=False)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--seconds", type=float, default=180.0, help="default 180")
    ap.add_argument("--phase-step-beats", type=int, default=8, help="default 8")
    ap.add_argument("--out", default=str(DATA_DIR), help="folder for the XDF")
    ap.add_argument(
        "--no-bridge",
        action="store_true",
        help="use a PLUX stream that is already online instead of starting one",
    )
    ap.add_argument(
        "--bridge-cmd",
        help="command to run instead of the hub bridge (testing without a hub); "
        "it must publish PLUX and stop when its stdin closes",
    )
    ap.add_argument("--recorder", default=str(LABRECORDER), help="LabRecorderCLI.exe")
    ap.add_argument("--bridge-timeout", type=float, default=60.0)
    args, passthrough = ap.parse_known_args(argv)

    if not kill_children_on_exit():
        print(
            "Note: could not set up the job object; child processes are still "
            "stopped on the way out, but not if this window is killed."
        )

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    xdf = out_dir / f"pat_dryrun_{stamp}.xdf"
    bridge_log = xdf.with_suffix(".bridge.log")
    recorder_log = xdf.with_suffix(".labrecorder.log")

    if not Path(args.recorder).exists():
        print(f"No LabRecorderCLI at {args.recorder}")
        return 1
    if not args.no_bridge and pylsl.resolve_byprop("name", "PLUX", timeout=1.0):
        print(
            "A PLUX stream is already online (physio app or another bridge?). "
            "Stop it, or use --no-bridge to record from it."
        )
        return 1
    if pylsl.resolve_byprop("name", "PATdryrun", timeout=0.5):
        print("A PATdryrun stream is already online; is another dry run running?")
        return 1

    import signal

    signal.signal(signal.SIGINT, Stop.handler)
    bridge = dryrun = recorder = None
    group = subprocess.CREATE_NEW_PROCESS_GROUP  # keeps Ctrl+C away from them
    code = 1
    try:
        if not args.no_bridge:
            if args.bridge_cmd:
                cmd = split(args.bridge_cmd)
            else:
                if not BRIDGE_PYTHON.exists():
                    print(f"No plux-lsl venv at {BRIDGE_PYTHON}")
                    return 1
                cmd = [str(BRIDGE_PYTHON), str(BRIDGE_SCRIPT), "--stop-on-eof"]
            print(f"Starting the hub bridge (log {bridge_log.name}) ...", flush=True)
            with open(bridge_log, "w") as log:
                bridge = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=str(Path(cmd[1]).parent if len(cmd) > 1 else PLUX_DIR),
                    creationflags=group,
                    env=dict(os.environ, PYTHONUNBUFFERED="1"),
                )
            if not wait_for_stream("PLUX", args.bridge_timeout, bridge):
                if not Stop.requested:
                    print(
                        "No PLUX stream from the bridge. Is the hub on and "
                        "paired? Last lines of its log:"
                    )
                    print(tail(bridge_log))
                return 1
            print("PLUX stream online.", flush=True)

        dryrun = subprocess.Popen(
            [
                sys.executable,
                str(BENCH / "pat_dryrun.py"),
                "--seconds",
                str(args.seconds),
                "--phase-step-beats",
                str(args.phase_step_beats),
                "--wait-for-recorder",
                "30",
                "--stop-on-eof",
                *passthrough,
            ],
            stdin=subprocess.PIPE,
            cwd=str(REPO),
        )
        if not wait_for_stream("PATdryrun", 60.0, dryrun):
            if not Stop.requested:
                print("pat_dryrun.py did not start its marker stream.")
            return 1

        with open(recorder_log, "w") as log:
            recorder = subprocess.Popen(
                [str(args.recorder), str(xdf), "name='PLUX'", "name='PATdryrun'"],
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=group,
            )
        print(f"Recording to {xdf}", flush=True)

        failed = False
        while dryrun.poll() is None:
            if bridge is not None and bridge.poll() is not None:
                print("The hub bridge stopped. Last lines of its log:")
                print(tail(bridge_log))
                failed = True
                break
            if recorder.poll() is not None:
                print("LabRecorderCLI stopped. Last lines of its log:")
                print(tail(recorder_log))
                failed = True
                break
            time.sleep(0.2)
        stop_by_eof(dryrun, "pat_dryrun.py", 15.0)
        code = 1 if failed else (dryrun.returncode or 0)
    finally:
        # Each stop runs even if Ctrl+C comes again.
        for step in (
            lambda: stop_by_eof(dryrun, "pat_dryrun.py", 15.0),
            lambda: stop_recorder(recorder),
            lambda: stop_by_eof(bridge, "The hub bridge", 10.0),
        ):
            try:
                step()
            except Exception as err:  # keep going: the next one must still stop
                print(f"Clean-up: {err}")

    if recorder is None:
        return code or 1
    if xdf.exists():
        print(f"\nSaved {xdf}")
        print(f"Report: .venv\\Scripts\\python.exe bench\\pat_dryrun_report.py {xdf}")
        return code
    print(f"\nNo XDF was written. LabRecorderCLI log:\n{tail(recorder_log)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
