"""One command for a live run of the Phase Adjustment Task, recorded to XDF.

Usage, from the repository root (hub on, electrodes on)::

    .venv\\Scripts\\python.exe bench\\pat_live_launch.py --participant P01 --session 1

1. Starts the hub bridge, ``plux-lsl\\plux_lsl.py``, with plux-lsl's own
   Python 3.13 venv, and waits for its ``PLUX`` stream.
2. Opens the ECG stream and sets the task up (window, sound, the ``PAT``
   marker stream), then starts ``LabRecorderCLI.exe`` recording ``PLUX`` and
   ``PAT`` to ``bench\\data\\pat_live_<participant>_<session>_<stamp>.xdf``,
   and waits for it to connect.
3. Runs the task in this process (PsychoPy wants the main thread).
4. However the task ends (done, Esc, Ctrl+C, an error), closes the task,
   stops the recorder and then the bridge, and prints the XDF path and the
   task's result folder.

The process handling is ``pat_dryrun_launch.py``'s: the bridge and the
recorder run in their own process groups, so Ctrl+C reaches only the task,
and everything is in a job object that is closed when this script exits.
"""

import argparse
import datetime
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pat_dryrun_launch as launch
from pat_dryrun_launch import (
    BRIDGE_PYTHON,
    BRIDGE_SCRIPT,
    DATA_DIR,
    LABRECORDER,
    PLUX_DIR,
    Stop,
    kill_children_on_exit,
    split,
    stop_by_eof,
    stop_recorder,
    tail,
    wait_for_stream,
)

pylsl = launch.pylsl

#: Seconds to wait for LabRecorderCLI to open the task's marker stream.
RECORDER_CONNECT = 20.0


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--participant", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--channel", default="ECG1", help="ECG channel (default ECG1)")
    ap.add_argument("--stream", default="PLUX", help="LSL stream (default PLUX)")
    ap.add_argument("--mode", default="relative", choices=["relative", "absolute"])
    ap.add_argument("--practice", type=int, default=2, help="default 2")
    ap.add_argument("--trials", type=int, default=6, help="default 6")
    ap.add_argument("--windowed", action="store_true", help="not full screen")
    ap.add_argument("--screen", type=int, default=0, help="screen number")
    ap.add_argument("--no-tutorial", action="store_true")
    ap.add_argument("--language", default="english", choices=["english", "danish"])
    ap.add_argument("--out", default=str(DATA_DIR), help="folder for the XDF")
    ap.add_argument(
        "--no-bridge",
        action="store_true",
        help="use a PLUX stream that is already online instead of starting one",
    )
    ap.add_argument(
        "--bridge-cmd",
        help="command to run instead of the hub bridge (testing without a hub); "
        "it must publish the stream and stop when its stdin closes",
    )
    ap.add_argument("--recorder", default=str(LABRECORDER), help="LabRecorderCLI.exe")
    ap.add_argument("--bridge-timeout", type=float, default=60.0)
    return ap.parse_args(argv)


def start_bridge(args, log_path: Path) -> subprocess.Popen:
    if args.bridge_cmd:
        cmd = split(args.bridge_cmd)
    else:
        cmd = [str(BRIDGE_PYTHON), str(BRIDGE_SCRIPT), "--stop-on-eof"]
    print(f"Starting the hub bridge (log {log_path.name}) ...", flush=True)
    with open(log_path, "w") as log:
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(Path(cmd[1]).parent if len(cmd) > 1 else PLUX_DIR),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env=dict(os.environ, PYTHONUNBUFFERED="1"),
        )


def watch(procs, logs, done: threading.Event) -> None:
    """Say so in the console if the bridge or the recorder stops mid-task."""
    while not done.wait(1.0):
        for name, proc in list(procs.items()):
            if proc.poll() is not None:
                print(
                    f"\nWARNING: {name} stopped during the task; the recording is "
                    f"incomplete. Last lines of its log:\n{tail(logs[name])}",
                    flush=True,
                )
                del procs[name]


def main(argv=None) -> int:
    args = parse_args(argv)
    if not kill_children_on_exit():
        print(
            "Note: could not set up the job object; child processes are still "
            "stopped on the way out, but not if this window is killed."
        )

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    xdf = out_dir / f"pat_live_{args.participant}_{args.session}_{stamp}.xdf"
    bridge_log = xdf.with_suffix(".bridge.log")
    recorder_log = xdf.with_suffix(".labrecorder.log")

    if not Path(args.recorder).exists():
        print(f"No LabRecorderCLI at {args.recorder}")
        return 1
    if not args.no_bridge:
        if not args.bridge_cmd and not BRIDGE_PYTHON.exists():
            print(f"No plux-lsl venv at {BRIDGE_PYTHON}")
            return 1
        if pylsl.resolve_byprop("name", args.stream, timeout=1.0):
            print(
                f"A {args.stream} stream is already online (physio app or another "
                "bridge?). Stop it, or use --no-bridge to record from it."
            )
            return 1
    if pylsl.resolve_byprop("name", "PAT", timeout=0.5):
        print("A PAT marker stream is already online; is another task running?")
        return 1

    bridge: Optional[subprocess.Popen] = None
    recorder: Optional[subprocess.Popen] = None
    lsl_recorder = None
    parameters = None
    done = threading.Event()
    running = False
    code = 1
    # Ctrl+C only stops the waiting here; once the task runs it raises
    # KeyboardInterrupt in the task, and the clean-up below still runs.
    signal.signal(signal.SIGINT, Stop.handler)
    try:
        if not args.no_bridge:
            bridge = start_bridge(args, bridge_log)
            if not wait_for_stream(args.stream, args.bridge_timeout, bridge):
                if not Stop.requested:
                    print(
                        f"No {args.stream} stream from the bridge. Is the hub on "
                        "and paired? Last lines of its log:"
                    )
                    print(tail(bridge_log))
                return 1
            print(f"{args.stream} stream online.", flush=True)
        if Stop.requested:
            return 1
        signal.signal(signal.SIGINT, signal.default_int_handler)

        from cardioception.devices import LSLRecorder
        from cardioception.PAT.parameters import getParameters
        from cardioception.PAT.task import run

        # The task opens its own PAT marker stream, so none here.
        lsl_recorder = LSLRecorder(
            name=args.stream, channel=args.channel, marker_stream=None
        )
        parameters = getParameters(
            participant=args.participant,
            session=args.session,
            recorder=lsl_recorder,
            mode=args.mode,
            nTrials=args.trials,
            nPractice=args.practice,
            fullscr=not args.windowed,
            screenNb=args.screen,
            language=args.language,
        )
        outlet = parameters.get("outlet")
        if outlet is None or not pylsl.resolve_byprop("name", "PAT", timeout=10.0):
            print("The task did not open its PAT marker stream.")
            return 1

        with open(recorder_log, "w") as log:
            recorder = subprocess.Popen(
                [str(args.recorder), str(xdf), f"name='{args.stream}'", "name='PAT'"],
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        print(f"Recording to {xdf}", flush=True)
        if not outlet.wait_for_consumers(RECORDER_CONNECT):
            print("LabRecorderCLI did not connect. Last lines of its log:")
            print(tail(recorder_log))
            return 1
        time.sleep(1.0)  # let it open the ECG inlet too

        procs = {"LabRecorderCLI": recorder}
        logs = {"LabRecorderCLI": recorder_log, "The hub bridge": bridge_log}
        if bridge is not None:
            procs["The hub bridge"] = bridge
        threading.Thread(target=watch, args=(procs, logs, done), daemon=True).start()

        running = True
        run(parameters, runTutorial=not args.no_tutorial, confidenceRating=True)
        code = 0
    except KeyboardInterrupt:
        print("\nStopped by Ctrl+C.", flush=True)
    except Exception as err:
        if running:
            import traceback

            traceback.print_exc()
            print(f"\nThe task stopped with an error: {err!r}", flush=True)
        else:
            print(f"\nCannot start the task: {err}", flush=True)
    finally:
        done.set()
        # Ignore further Ctrl+C: the clean-up must finish.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        steps = []
        if parameters is not None:
            steps += [parameters["win"].close, parameters["engine"].close]
        if lsl_recorder is not None:
            steps.append(lsl_recorder.close)
        steps += [
            lambda: stop_recorder(recorder),
            lambda: stop_by_eof(bridge, "The hub bridge", 10.0),
        ]
        for step in steps:
            try:
                step()
            except Exception as err:  # keep going: the next one must still stop
                print(f"Clean-up: {err!r}")

    if parameters is not None:
        print(f"\nTask results: {parameters['resultPath']}")
    if recorder is not None:
        if xdf.exists():
            print(f"Saved {xdf}")
            print(
                "Report: .venv\\Scripts\\python.exe bench\\pat_dryrun_report.py "
                f"{xdf} --markers PAT --channel {args.channel}"
            )
        else:
            print(f"No XDF was written. LabRecorderCLI log:\n{tail(recorder_log)}")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
