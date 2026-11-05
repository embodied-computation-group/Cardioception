---
myst:
  html_meta:
    description: "The recording devices Cardioception supports: the Nonin USB pulse oximeter, any ECG or PPG device over Lab Streaming Layer, and custom recorders."
    keywords: "cardioception recording device, Nonin pulse oximeter, ECG, PPG, Lab Streaming Layer, LSL, LabRecorder, PLUX"
---

# Recording devices

Every task reads the participant's heart while it runs. Which device it can read from depends on the task:

| Task | USB pulse oximeter | ECG or PPG over LSL |
|---|---|---|
| Heart Rate Discrimination | yes | yes |
| Heartbeat Counting | yes | yes |
| Phase Adjustment Task | no | ECG only |
| Heartbeat Synchrony Discrimination | no | ECG only |

The two synchrony tasks time each tone from the R-wave, which a pulse oximeter cannot give them.

The device is chosen when the parameters are built. `setup="behavioral"` with a `serialPort` opens the pulse oximeter; `recorder=` passes any other device and wins over `setup`, so nothing touches a serial port.

## The Nonin pulse oximeter

The oximeter Cardioception supports directly is the [Nonin 3012LP Xpod](https://www.nonin.com/products/xpod/) with [Nonin 8000SM soft-clip fingertip sensors](https://www.nonin.com/products/8000s/). It plugs into the stimulus PC over USB, appears as a serial port, and needs no extra software. It is the only Nonin model the package has been tested with.

```python
parameters = getParameters(..., setup="behavioral", serialPort="COM3")
```

`serialPort` is the port's name: `COM3` or similar on Windows, `/dev/tty.usbserial-*` on macOS, `/dev/ttyUSB*` on Linux. `python -m cardioception.check_device --list` prints the ports it can see.

Check the signal before every session:

```bash
python -m cardioception.check_device
```

It records for twenty seconds and reaches one of five verdicts:

| Verdict | What it means |
|---|---|
| `no data` | The device is connected but sent nothing. Check the cable. |
| `no finger in the sensor` | Amplitude below 20. The trace is flat and any beats reported are noise. |
| `signal present but no pulse detected` | A signal, but fewer than three beats. Check that the sensor is on a fingertip and not too loose. |
| `signal present but detection unreliable` | Real signal, but the intervals between beats are too scattered to trust. Reseat the sensor, keep the hand still and below heart level. |
| `clean physiological signal` | Amplitude in the hundreds, intervals between 0.4 and 1.2 s with little spread. Ready. |

Amplitude is tested first because an empty sensor still yields beats at a plausible rate: an empty Nonin gave 67 BPM from 16 detected beats on a trace spanning a single ADC unit, and only its amplitude of 1.0 gave it away.

`--port COM3` picks a port when several are attached, and `--duration` changes the recording length. The command exits 0 only for a clean signal, so it can gate a startup script.

## ECG or PPG over LSL

Any device that streams over [Lab Streaming Layer](https://labstreaminglayer.org/) works through `cardioception.devices.LSLRecorder`. Install the extra, start the device's own streaming program, then name the stream and the channel holding the heart signal:

```bash
pip install "cardioception-toolbox[lsl]"
```

```python
from cardioception.devices import LSLRecorder

recorder = LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg")
parameters = getParameters(..., recorder=recorder)
```

`channel` is an index or a label from the stream's channel metadata. `signal_type` is `"ecg"` or `"ppg"` and chooses the beat detector: systole's `ecg_peaks` with the sleepecg method for ECG, each beat moved to the R peak, or `ppg_peaks` for PPG. With an ECG the tutorial also skips the finger-sensor instructions. When the stream's name is not known in advance, `stream_type="ECG"` finds it by type instead.

The trigger codes a task writes are also pushed, as they happen, to an LSL marker stream named `Cardioception` by default (`marker_stream=` renames it, `None` turns it off), labelled by event name. Record that stream and the device's with [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder) to get the physiology and the task events on one clock. The signal file a task writes carries each sample's LSL timestamp as well.

The HRD and HBC take the recorder as above. The HSD wrapper names its marker stream `HSD`, and the task builds its beat source and tone player over the recorder. The PAT opens its own `PAT` marker stream, so its recorder is given `marker_stream=None`. The task pages show each call.

For the synchrony tasks, a wired ECG with an LSL path (Biopac, ADInstruments and Brain Products all have one) gives less timing jitter than a Bluetooth hub; the [HSD roadmap](../tasks/hsd/design.md#what-comes-next) has the numbers.

### A PLUX hub

The ECG setup used to develop the synchrony tasks is a PLUX hub with a chest lead, streamed to LSL by the bridge in the [plux-lsl](https://github.com/embodied-computation-group/plux-lsl) repository (Apache 2.0). Start it before the task:

```bash
python plux_lsl.py --ports 1
```

It publishes the stream as `PLUX`, which is the wrappers' default. The ECG channel's label is not the same on every hub (`ECG1` on one, `ECG2` on another), so read it from the stream before the session; the PAT and HSD wrappers have no default for it and will not start without one.

Electrodes follow {cite:t}`2026:hodgetts`: right clavicle, lowest left rib, reference on the left clavicle or hip. With the PLUX lead set, upright R-waves came from black on the lowest left rib and red on the right clavicle; swap them if the trace is inverted.

## Running without a device

The HRD and the HBC accept `setup="test"`, which replays a recorded pulse through the same code path as the oximeter and opens a windowed rather than full-screen display. No hardware is needed, which makes it the way to try a task or check an installation.

The HSD accepts `setup="test"` only when a `beat_source` and a `tone_player` are passed in place of the ECG and the sound card; the PAT has no `setup` argument and takes the same two objects. The [PAT page](../tasks/pat.md#running-without-a-participant) shows a headless run with a simulated participant.

## Other devices

Any other device can be added by writing a recorder and passing it in:

```python
parameters = getParameters(..., recorder=MyRecorder())
```

The recorder has to supply a real-time estimate of cardiac frequency during the trial, because that is what sets the tone frequency: a device that only records for later analysis cannot drive the HRD on its own. `cardioception.devices.ReplayRecorder` is a worked example, and is what the test suite runs against.

## Next step

Continue to [Running a session](running-a-session.md) for the wrappers, the output layout, languages and confidence scales.
