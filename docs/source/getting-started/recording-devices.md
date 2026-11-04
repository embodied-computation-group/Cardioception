---
myst:
  html_meta:
    description: "The recording devices Cardioception supports: the Nonin USB pulse oximeter, any ECG or PPG device over Lab Streaming Layer, and custom recorders."
    keywords: "cardioception recording device, Nonin pulse oximeter, ECG, PPG, Lab Streaming Layer, LSL, LabRecorder, PLUX"
---

# Recording devices

The default setup uses the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/), which plugs into the stimulus PC over USB and needs no extra code. Any ECG or PPG device that streams over [Lab Streaming Layer](https://labstreaminglayer.org/) also works, through `cardioception.devices.LSLRecorder`, and other devices can be added by supplying a recorder object to `getParameters`.

Both the Heartbeat Counting task (HBC) and the Heart Rate Discrimination task (HRD) need a physiological recording device during the task, either to estimate the heart rate or to count the number of heartbeats in a given time window. Cardioception natively supports:

* The [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/)
* Any ECG or PPG device that streams over [Lab Streaming Layer](https://labstreaminglayer.org/) (LSL), through `cardioception.devices.LSLRecorder`

The Heartbeat Synchrony Discrimination task (HSD), in beta, times each tone from the R-wave, so it needs an ECG over LSL; see [Running the HSD](../tasks/hsd/running.md).

To check the pulse oximeter before collecting data, see [step 5 of the installation](installation.md#5-check-the-recording-device).

## ECG or PPG over LSL

Install the optional dependency with `pip install cardioception-toolbox[lsl]`. Start the device's own streaming program, then name the stream and the channel holding the heart signal:

```python
from cardioception.devices import LSLRecorder
from cardioception.HRD.parameters import getParameters

recorder = LSLRecorder(name="PLUX", channel="ECG2", signal_type="ecg")
parameters = getParameters(..., recorder=recorder)
```

`channel` is an index or a label from the stream's channel metadata. With `signal_type="ecg"` the beats come from systole's `ecg_peaks` (sleepecg detector), each moved to the R peak, at the stream's own rate, and the tutorial skips the pulse oximeter and finger instructions. The heart rate is then computed from the beats exactly as for the oximeter.

The trigger codes the task writes are also sent to an LSL marker stream, `Cardioception` by default (`marker_stream=` to rename, `None` to turn off), labelled by name (`TRIAL_START`, `LISTENING_START`, ...). Record that stream and the device's with [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder) to get the physiology and the task events on one clock. Cardioception's own signal files are written as before, with each sample's LSL timestamp added.

### A PLUX hub

`plux_lsl.py`, from the [`plux-lsl`](https://github.com/embodied-computation-group/plux-lsl) repository, streams the hub over LSL under the name `PLUX`, which is the wrapper's default. Start it with `python plux_lsl.py --ports 1` before the task.

The PLUX hub with a chest ECG lead, streamed to LSL as `PLUX` by the hub bridge (`plux_lsl.py`). The label of the ECG channel is not the same on every hub (the bridge has given `ECG1` on one and `ECG2` on another), so check it in the stream before the session. Start the bridge before the task. Electrodes as in {cite:t}`2026:hodgetts`: right clavicle, lowest left rib, reference on the left clavicle or hip. With the PLUX lead set, upright R-waves came from black on the lowest left rib and red on the right clavicle; swap them if the trace is inverted.

## Other devices

Other devices can be added by writing a recorder and passing it in:

```python
parameters = getParameters(..., recorder=MyRecorder())
```

This bypasses `setup` entirely, so nothing touches a serial port. The recorder has to provide a real-time estimate of cardiac frequency during the trial, because that is what sets the tone frequency: a device that only records for later analysis cannot drive the HRD on its own. See `cardioception.devices.ReplayRecorder` for a worked example, which is also what the test suite runs against.
