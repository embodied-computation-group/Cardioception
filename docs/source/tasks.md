---
myst:
  html_meta:
    description: "The four Cardioception tasks side by side: Heart Rate Discrimination, Heartbeat Counting, Heartbeat Synchrony Discrimination and the Phase Adjustment Task, with what each measures, what it needs and how to analyze it."
    keywords: "cardioception tasks, heart rate discrimination, heartbeat counting, heartbeat synchrony discrimination, phase adjustment task, cardiac interoception"
---

# The tasks

Cardioception runs four tasks: two established, the Heart Rate Discrimination
task (HRD) and the Heartbeat Counting task (HBC), and two experimental, the
Heartbeat Synchrony Discrimination task (HSD) and the Phase Adjustment Task
(PAT). This page puts them side by side.

| Task | HRD | HBC | HSD | PAT |
|---|---|---|---|---|
| Measure | Bias (threshold) and precision (slope) of judgements of one's own heart rate, with confidence | Reported against recorded heartbeats over fixed windows, with confidence | Where in the cardiac cycle the heartbeat is felt (`mu`), how sharply (`sigma`), and how strongly, with confidence | Consistency of the chosen tone delay or phase across trials, with confidence |
| Adaptive | Yes: a Psi staircase sets the tone rate | No | Yes: Bayesian placement of the tone delay | No: the participant adjusts the delay |
| Hardware | Pulse oximeter, or ECG or PPG over LSL; headphones; mouse or keyboard | Pulse oximeter, or ECG or PPG over LSL; keyboard | ECG over LSL; sound card; keyboard | ECG over LSL; sound card; mouse wheel; a tactor for the control task |
| Trials and minutes | 120 trials, about 20 minutes plus the tutorial | 6 counting windows, about 4 minutes | 15 to 60 trials; 60 took 7 minutes | 28 trials and 8 practice, about 30 minutes |
| Status | Established | Established | [Experimental](hsd_design.md) | [Experimental](pat.md) |

Every task writes to the same layout,
`data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/` under the current
folder or under `resultPath`. The timestamp makes each run's directory unique,
every file name carries participant, session and run, and `manifest.json`
records the settings before the first trial. The trial table is always
`*_final.txt`.

## Heart Rate Discrimination task

**What it measures.** The HRD {cite:p}`2022:legrand` estimates the bias and the
precision of a person's judgements of their own heart rate, as the threshold
and slope of a psychometric function, and with confidence ratings their
metacognition. It indexes the accuracy and precision of beliefs about one's
heart rate; the [theory page](measuring.md) sets out what it can establish.

**Procedure.** On each trial the participant attends to their heartbeat for
five seconds while the pulse is recorded. They then hear tones at their
measured heart rate plus or minus a difference, judge whether the tones were
faster or slower than their heart, and rate their confidence. By default half
the trials are an exteroceptive control, in which the reference is a tone
sequence rather than the heart.

**Stimulus and response.** Tones whose rate differs from the heart rate by
`Alpha` ΔBPM. Faster or slower with the mouse buttons or the arrow keys;
confidence on a 0 to 100 slider with the mouse or ten steps with the keyboard.

**Adaptive.** A Psi staircase {cite:p}`1999:kontsevich` per condition chooses
`Alpha` on each trial.

**Hardware.** The Nonin pulse oximeter by default, or any ECG or PPG device
streaming over Lab Streaming Layer (LSL) through `LSLRecorder`.

**Output.** `*_final.txt`, one row per trial: `Modality` (`Intero` or
`Extero`), `Alpha`, `Decision` (`More` or `Less`), `ResponseCorrect`,
`Confidence`, `listenBPM` and the staircase's own `EstimatedThreshold` and
`EstimatedSlope`. The pulse recordings are saved next to it.

**Length.** 120 trials by default, 60 per condition. The four example sessions
in the documentation ran in 20 to 22 minutes, not counting the tutorial.

**Analysis.** Fit the trials with the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception)
{cite:p}`2026:courtin`; the [tutorials](tutorials/index.md) walk through it.
`EstimatedThreshold` and `EstimatedSlope` are a sanity check, not a dependent
variable.

## Heartbeat Counting task

**What it measures.** The HBC {cite:p}`1978:dale,1981:schandry` compares the
number of heartbeats a person reports with the number recorded. It is usually
taken to index interoceptive accuracy.

**Procedure.** The participant attends to their heartbeat during windows of
fixed length, signalled by a sound at the start and the end, and types the
number of beats they counted. They then rate their confidence. The default
version (`taskVersion="Garfinkel"`) runs six counting windows of 25, 30, 35,
40, 45 and 50 seconds in random order; `taskVersion="Schandry"` runs three
windows of 25, 35 and 45 seconds after a minute of rest, separated by 30 second
rests.

**Stimulus and response.** No stimulus beyond the start and stop sounds. The
count is typed, and confidence rated, on the keyboard.

**Adaptive.** No.

**Hardware.** The same as the HRD: the pulse oximeter, or ECG or PPG over LSL.

**Output.** `*_final.txt`, one row per window: `nTrial`, `Condition`,
`Duration`, `Reported`, `Confidence`, plus one pulse recording per window
(`*_ppg-<n>`), from which the true count comes.

**Length.** About 4 minutes with the default settings.

**Analysis.** The accuracy score of {cite:t}`2013:hart`, given in the
[user guide](user_guide.md#the-tasks) and computed by the HBC report notebook.

## Heartbeat Synchrony Discrimination task

**What it measures.** The HSD is an adaptive Bayesian version of the heartbeat
detection task {cite:p}`1993:brener`. It estimates where in the cardiac cycle
the heartbeat is felt (`mu`, in ms after the R-wave), how sharply (`sigma`),
and how much more often the participant answers "synchronous" there than away
from it, which is the sensitivity measure.

**Procedure.** Each trial plays five tones, each a chosen delay after an R-wave
detected online in the ECG. The participant answers whether the tones were
synchronous with their heartbeat and rates their confidence. The next delay is
placed where it is most informative about `mu` and `sigma`, and the session
stops once `mu` is known to within 100 ms, after at least 15 trials, or at 60.

**Stimulus and response.** Delays from 130 to 600 ms after the R-wave, or a
fraction of the interbeat interval (`axis="phase"`). UP for synchronous, DOWN
for not; confidence in ten steps.

**Adaptive.** Yes: the delay is chosen by expected information gain.

**Hardware.** An ECG over LSL, since every tone is timed from the R-wave
(a pulse oximeter cannot drive it), and a sound card driven through
PsychPortAudio. Record the ECG with LabRecorder: the task keeps no copy.

**Output.** `*_final.txt`: `RequestedDelay`, `RealizedCorrected` (the delay as
played, which is the stimulus to analyze), `Decision`, `Confidence`, and the
posterior after each trial (`MuMean`, `MuCILow`, `MuCIHigh`, `SigmaMean`,
`DetectionBF`). Also `*_tones.txt`, `*_beats.txt` and `*_engine.json`.

**Length.** Three practice trials, then 15 to 60 trials. The one hardware dry
run reached the 60 trial maximum in 7 minutes.

**Status.** Experimental: run on hardware once, not validated, with a
provisional stopping rule. See the [design page](hsd_design.md) and the
[user guide](user_guide.md#heartbeat-synchrony-discrimination).

**Analysis.** The online posterior is a monitoring aid. No offline model has
been published yet: the Hierarchical Interoception toolbox covers the HRD so
far. Fit any later model to the trial history, `RealizedCorrected` against
`Decision`, which `*_engine.json` also holds.

## Phase Adjustment Task

**What it measures.** The PAT {cite:p}`2021:plans` measures how consistently a
person places a tone at the same point of their cardiac cycle. Cardioception
follows the ECG version of {cite:t}`2026:hodgetts`, where choices more
consistent than chance index interoceptive accuracy.

**Procedure.** The participant hears one tone per heartbeat and turns a dial
that moves the tone earlier or later after each R-wave until tone and heartbeat
feel simultaneous, then presses space and rates their confidence. The dial
starts at one of four phases, so a remembered position does not help.

**Stimulus and response.** A 1000 Hz tone on every beat, at a phase of the
anticipated heart period (`mode="relative"`, the default) or a delay in ms
(`mode="absolute"`). The mouse wheel turns the dial; confidence from 1 to 10.

**Adaptive.** No. The participant sets the delay.

**Hardware.** An ECG over LSL, a sound card, and a mouse wheel. The
exteroceptive control (`extero=True`) needs no ECG but a vibrotactile
transducer on the right audio channel.

**Output.** `*_final.txt`: `ChosenPhaseDeg`, `ChosenDelayMs`,
`AnticipatedPeriodMs`, `ObservedPeriodMs`, `TrialStatus`, `Confidence`; and
`*_tones.txt`, one row per tone.

**Length.** 8 practice and 28 main trials, about 30 minutes in the PAT-ECG
study; the exteroceptive control, with the same trial counts, about 10.

**Status.** Experimental. It detects the R-wave in software rather than in
hardware, which changes the timing; see the [PAT page](pat.md).

**Analysis.** `cardioception.PAT.scoring.consistency_grid` scores the eight
consistency measures of Hodgetts et al., each against a Monte Carlo chance
threshold. See [scoring](pat.md#scoring).

## Strengths and limitations

Each task answers a different question, and each has costs. This section sets
them side by side; which one fits depends on the question you are asking.

**The HRD.** It separates the bias of heart rate judgements from their
precision, includes a within-person exteroceptive comparison, adapts the
stimulus with a staircase, and runs on a pulse oximeter. Hierarchical models
with normative priors are available for its data. It measures judgements of
heart rate, which combine beliefs about one's heart rate with whatever is
sensed in the listening window. It does not show whether or when a person feels
individual heartbeats; see
[what you may conclude](measuring.md#what-you-may-conclude-from-the-hrd). A
full session takes about 20 minutes plus the tutorial.

**The HBC.** It is short, needs only a pulse oximeter, and connects directly to
a large literature, which is why the package keeps it. A plausible estimate of
heart rate can produce a good counting score without detecting any beats
{cite:p}`1999:windmann,2016:brener`, and counting scores are unrelated to
heartbeat detection {cite:p}`2018:ring`, so a score is hard to read as
sensitivity on its own.

**The HSD.** It estimates where in the cardiac cycle a person feels the
heartbeat and how sharply. It keeps the multi-interval logic of the method of
constant stimuli, which takes about 35 minutes {cite:p}`2016:brener`, and
spends the trials where they are informative. It is in beta: not yet
validated, unable to probe delays below 130 ms, and sensitive to jitter in a
Bluetooth ECG, which widens `sigma`. Read the [design page](hsd_design.md)
before using it.

**The PAT.** It connects to the phase adjustment literature and classifies
participants against chance with a fixed number of trials. It cannot separate
where the sensation lies from how precise it is, and a participant can be
consistent through a habit of search rather than a sensation; the
[HSD design page](hsd_design.md#relation-to-the-phase-adjustment-task) compares
the two. This port is in beta, and its timing differs from the hardware
original.
