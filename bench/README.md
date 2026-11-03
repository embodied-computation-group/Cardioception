# Bench scripts

Measurements on the stimulation PC. Run everything from the repository root with
the project venv (`.venv\Scripts\python.exe`, Python 3.11). Recordings go to
`bench\data\`, which git ignores.

## PAT-ECG dry run

Checks the timing loop of the PAT-ECG port before there is a task around it: ECG
from the PLUX hub over LSL, R peaks found online, a 1000 Hz tone (30 ms, 5 ms
ramps) played at a phase of each cardiac cycle, and everything recorded to one
XDF so the true R-to-tone timing can be read offline. The phase sweeps on its own
through 0, 45, ... 315 degrees, 8 beats each, so nobody has to touch anything.

### Running it

Hub on, chest ECG on (channel `ECG2`), speakers on. Close the physio app first:
the launcher starts its own hub bridge.

```
.venv\Scripts\python.exe bench\pat_dryrun_launch.py --seconds 180
```

It starts the hub bridge (`plux-lsl\plux_lsl.py`, with plux-lsl's own Python 3.13
venv), waits for the `PLUX` stream, starts `bench\pat_dryrun.py`, records `PLUX`
and `PATdryrun` with LabRecorderCLI, and at the end stops everything and prints
the path of `bench\data\pat_dryrun_<stamp>.xdf`. Ctrl+C stops early and still
saves the file. The bridge and recorder logs are written next to it.

Every 3 s it prints a status line:

```
   21 s  beats   26  HR  83.1  phase 270  tones real  21 pred   1 skip   1  lag  26.6 ms  onset-target  +0.00 ms
```

`lag` is how long after the R-peak sample was stamped the beat was known,
`onset-target` how far the last tone's reported onset was from its target
(positive is late). `NO SIGNAL` at the end of the line means the stream has
stopped delivering samples.

Options: `--phase-step-beats 4` for a faster sweep; `--volume 0.3`;
`--audio-device <index>` (PsychPortAudio index, default the system output).
`--no-bridge` uses a `PLUX` stream that is already online.

### Reading the report

```
.venv\Scripts\python.exe bench\pat_dryrun_report.py bench\data\pat_dryrun_<stamp>.xdf
```

It finds the R peaks offline in the whole recording (the reference) and prints:

- **Detection lag**: commit time minus R time, split into the detector's own part
  (about 17 ms on the test files) and transport (pulling the chunk from LSL).
- **Online vs offline R peaks**: sensitivity, positive predictive value and timing
  error at 50 ms tolerance.
- **Tones**: onset minus target, then, per anchor, the true phase (from the
  nearest preceding offline R peak to the reported onset, as a fraction of that
  cycle) against the intended phase, and a table of tones per phase and anchor.
  Anchor `real` means the tone was timed from the beat just detected; `predicted`
  means that was too late (small phases), so it was timed one anticipated period
  later. Expect the predicted tones to scatter more: the true cycle differs from
  the 3-beat average.

The figure `<name>_report.png` next to the XDF shows true vs intended phase,
the onset error histogram, and the detection lag over time.

The report also works on any XDF with a `PLUX` ECG and no markers, e.g. a
Cardioception session: it then replays the online detector over the recording and
compares it with the offline one.

What the numbers do not include: LSL timestamps are taken when samples reach the
bridge on the PC, 20 to 40 ms after the hub sampled them (`plux-lsl\latency_bench.py`).
True R peaks were that much earlier, so true phases are later than shown.
`--bridge-lag 0.03` corrects for a fixed 30 ms. Likewise the onset is
PsychPortAudio's estimate of when the first sample reaches the DAC, not when sound
leaves the speaker; `bench\audio_onset.py` checks that with the microphone.

### Audio path

`pat_dryrun.py` uses `psychtoolbox.audio` (PsychPortAudio) directly, not PsychoPy's
`sound.Sound`: one stream, latency class 1, engine kept running (run mode 1),
warmed up with silence at start, started with `when=` on the `GetSecs` clock and
the onset read from the stream's `StartTime`. On this PC:

- reported onset minus target, 120 tones at 50 to 800 ms lead: median 0.00 ms,
  95th percentile of |error| about 1 ms, max 2.5 ms;
- with 10 ms or less of lead, starts were 2 to 13 ms late, hence the 0.05 s
  minimum lead;
- without the warm-up, the first tone after opening the stream was 0.4 to 0.8 s
  late;
- latency class 3 reported onsets up to 65 ms off, and its sound came out about
  70 ms later than class 1 without PTB noticing. Do not use it here.

PsychoPy's PTB backend reaches the same engine, but on PsychoPy 2026.2 the backend
name must be lower case (`audioLib = ['ptb']`; `'PTB'` raises
`ModuleNotFoundError`), `audioLatencyMode` is ignored, and it applies its own
ramps unless `hamming=False`. Going direct keeps the latency class, the ramps and
the onset readout explicit.

`GetSecs` and `pylsl.local_clock` share the QueryPerformanceCounter origin (offset
a few microseconds). The dry run still measures the offset at start and records
it as a `clock` marker.

### Marker stream

`PATdryrun` (type `Markers`, source id `pat-dryrun`), one JSON object per sample,
as in `.context/pat-ecg/dryrun-contract.md`: `clock`, `beat`, `tone_scheduled`,
`tone_onset`. One addition: `beat` also carries `commit_sample_time`, the
timestamp of the sample the detector committed on, so the lag can be split into
detector and transport.
