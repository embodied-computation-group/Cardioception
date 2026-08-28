"""Phase 6 hardware validation: 10 interoceptive and 10 exteroceptive trials.

Run from the repository root with the PsychoPy venv:

    <venv>/python.exe hardware_check.py [COM3] [mouse|keyboard] [on|off]

The third argument is continuous recording. Run it once `on` and once `off` to
compare dropped frames: the 2026-08-28 validation logged 191 dropped frames
with it on and has no control, so whether the per-frame drain costs anything
is still unknown. Frame budget was the original objection in issue #95, so it
is the number worth having.

What this is set up to exercise, beyond an ordinary session:

- `continuousRecording=True`, which is the whole point. The recorder is a
  `ContinuousOximeter`, drained on every frame the task holds a screen for.
- `nBreaking=10`, so a break falls at trial 10 rather than at the end. The
  break no longer resets the recorder, and that resync is the riskiest new
  behaviour: without the reset there is no `reset_input_buffer()` to fall
  back on if draining fails to keep up.
- The tutorial is skipped to keep the session short. It exercises the same
  drain path, so nothing here is unique to it.
"""

import sys

from cardioception.HRD.config import TaskConfig
from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run

port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
device = sys.argv[2] if len(sys.argv) > 2 else "mouse"
continuous = (sys.argv[3] if len(sys.argv) > 3 else "on").lower() != "off"

print(f"Port {port}, device {device}, continuous recording {'on' if continuous else 'off'}.")
print("20 trials, 10 per modality, break at trial 10.")

parameters = getParameters(
    participant="HW",
    session="phase6" if continuous else "control",
    serialPort=port,
    setup="behavioral",
    device=device,
    language="english",
    exteroception=True,   # alternates modality, so nTrials=20 is 10 of each
    nTrials=20,
    catchTrials=0.0,
    nBreaking=10,         # a break at trial 10, mid-session, on purpose
    config=TaskConfig(continuousRecording=continuous),
)

run_dir = parameters["paths"].directory
print(f"Writing to {run_dir}")

try:
    run(parameters, confidenceRating=True, runTutorial=False)
finally:
    parameters["win"].close()

print()
print("Session finished. Now check it with:")
print(f'  python -m cardioception.validate "{run_dir}"')
