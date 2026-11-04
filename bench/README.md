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

## Live PAT run

Runs the real task (`cardioception.PAT`) on the hub's ECG and records the ECG
with the task's `PAT` marker stream in one XDF. Hub on, ECG on, physio app
closed:

```
.venv\Scripts\python.exe bench\pat_live_launch.py --participant P01 --session 1
```

It starts the hub bridge, opens the ECG (`--channel`, default `ECG1`), sets the
task up, starts LabRecorderCLI on `PLUX` and `PAT`
(`bench\data\pat_live_<participant>_<session>_<stamp>.xdf`), runs the task in
this window, and on the way out (done, Esc, Ctrl+C or an error) stops the
recorder and the bridge and prints the XDF path and the task's result folder
(`data\<participant><session>\` under the current folder).

Options: `--practice 2` and `--trials 6` (defaults), `--mode relative|absolute`,
`--windowed`, `--screen 1`, `--no-tutorial`, `--language danish`, `--no-bridge`.

The same report reads it:

```
.venv\Scripts\python.exe bench\pat_dryrun_report.py <xdf> --markers PAT --channel ECG1 --bridge-lag 0.05
```

The task aims every tone `latencyBias` (0.05 s) before the dial's phase, to make
up for the delays the timestamps do not show; `--bridge-lag 0.05` scores it on
the same footing. Without it, true phases read about 0.05 s early. The task's
beat markers have no `commit_time`, so the lag is taken from the marker
timestamp; it includes the wait for the next frame, about 8 ms more than in the
dry run.

## Setting up the PLUX bridge on another PC

The launchers above start the hub bridge from the plux-lsl repository. To reproduce it:

1. Clone github.com/embodied-computation-group/plux-lsl next to this repository, so that
   `cannabodies\cardioception-src` and `cannabodies\plux-lsl` are sibling folders.
2. Install Python 3.13, 64-bit, for the current user (it need not be on PATH). PLUX's API has no
   3.11 build, so the bridge has its own venv. From the plux-lsl folder:
   `py -3.13 -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. The PLUX API binaries (`plux.pyd` and the FTDI DLLs) ship in the repository, in `vendor\plux\`
   (with PLUX's `LICENSE` and the source commit in `SOURCE_COMMIT`). Nothing to download.
4. Download LabRecorder 1.18.0 for Windows (github.com/labstreaminglayer/App-LabRecorder,
   releases) and unzip it into `plux-lsl\LabRecorder\`, so that
   `plux-lsl\LabRecorder\LabRecorderCLI.exe` exists.
5. Pair the biosignalsplux hub in Windows Bluetooth settings. `plux_lsl.py` defaults to this lab's
   hub (`DEFAULT_MAC`, 00:07:80:4B:3F:25); for another hub pass `--mac <its MAC>`.
6. Check it: `.venv\Scripts\python.exe plux_lsl.py --list` prints the battery and the sensors
   found, one line per port.

The stream: name `PLUX`, type `Biosignals`, 1000 Hz, int32 raw ADC counts. Channel 0 is `nSeq`
(the hub's sample counter, so dropped samples show as gaps), then one channel per sensor,
labelled by sensor type and hub port: an ECG on port 1 is `ECG1`, on port 2 `ECG2`. Pass the
right one with `--channel` (the dry run defaults to `ECG2`, the live launcher to `ECG1`).

The launchers look for plux-lsl as a sibling folder and there is no single flag to move it. To
use a copy elsewhere, give both parts explicitly (paths without spaces):

```
.venv\Scripts\python.exe bench\pat_dryrun_launch.py ^
  --bridge-cmd "D:\plux-lsl\.venv\Scripts\python.exe D:\plux-lsl\plux_lsl.py --stop-on-eof" ^
  --recorder D:\plux-lsl\LabRecorder\LabRecorderCLI.exe
```

`pat_live_launch.py` takes the same two options. Add `--mac` inside `--bridge-cmd` for
another hub.

The Nonin pulse oximeter has its own bridge in this repository, run with the cardioception venv:
`.venv\Scripts\python.exe bench\nonin_lsl.py --port COM12` (no `--port`: it tries each USB serial
port). It publishes `Nonin` (PPG, 75 Hz); `pat_live_launch.py --nonin [PORT]` starts it and
records it.

## Reports on other marker streams

`pat_dryrun_report.py` reads `PATdryrun` by default and `PAT` on its own. For another task's
marker stream, name it: `--markers HSD`. Kinds it does not know are counted and skipped; the
`beat`, `tone_scheduled` and `tone_onset` it scores must carry the dry run's fields (`r_time`, `target`, `onset`, `phase_deg`).
