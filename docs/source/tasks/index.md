---
myst:
  html_meta:
    description: "The four Cardioception tasks side by side: Heart Rate Discrimination, Heartbeat Counting, the Phase Adjustment Task and Heartbeat Synchrony Discrimination, with what each measures, what it needs and how to analyze it."
    keywords: "cardioception tasks, heart rate discrimination, heartbeat counting, heartbeat synchrony discrimination, phase adjustment task, cardiac interoception"
---

# The tasks

Cardioception runs four tasks: two established, the Heart Rate Discrimination
task (HRD) and the Heartbeat Counting task (HBC), and two in beta, the Phase
Adjustment Task (PAT) and the Heartbeat Synchrony Discrimination task (HSD).
Tasks in beta are close to feature complete and are still being rigorously
validated. Two more, the Whitehead method and the method of constant
stimuli, are coming. Each task has a page that says what it measures and how to
run it; this page sets them side by side.

| Task | [HRD](hrd/index.md) | [HBC](hbc.md) | [PAT](pat.md) | [HSD](hsd/index.md) | [Whitehead](whitehead.md) | [Constant stimuli](constant-stimuli.md) |
|---|---|---|---|---|---|---|
| Measure | Bias (threshold) and precision (slope) of judgements of one's own heart rate, with confidence | Heartbeats reported against heartbeats recorded over fixed windows, with confidence | Consistency of the chosen tone delay or phase across trials, with confidence | Where in the cardiac cycle the heartbeat is felt (`mu`), how sharply (`sigma`), and how strongly, with confidence | Discrimination of synchronous from delayed tones {cite:p}`1977:whitehead` | Proportion of tones judged simultaneous at each delay {cite:p}`1993:brener` |
| Reference | {cite:t}`2022:legrand` | {cite:t}`1981:schandry`, {cite:t}`1978:dale` | {cite:t}`2021:plans`, {cite:t}`2026:hodgetts` | {cite:t}`1993:brener` | {cite:t}`1977:whitehead` | {cite:t}`1993:brener` |
| Adaptive | Yes: a Psi staircase sets the tone rate | No | No: the participant adjusts the delay | Yes: Bayesian placement of the tone delay | No | No |
| Hardware | Pulse oximeter, or ECG or PPG over LSL; headphones; mouse or keyboard | Pulse oximeter, or ECG or PPG over LSL; keyboard | ECG over LSL; sound card; mouse wheel; a tactor for the control task | ECG over LSL; sound card; keyboard |  |  |
| Trials and minutes | 120 trials, about 20 minutes plus the tutorial | 6 counting windows, about 4 minutes | 28 trials and 8 practice, about 30 minutes | 15 to 60 trials; 60 took 7 minutes |  |  |
| Status | Established | Established | Beta | Beta | Coming soon | Coming soon |

Every task writes to the same run directory layout, with the trial table in
`*_final.txt`; [Running a session](../getting-started/running-a-session.md#where-the-data-goes)
describes it.

## Strengths and limitations

Each task answers a different question, and each has costs.

**The HRD.** It separates the bias of heart rate judgements from their
precision, includes a within-person exteroceptive comparison, adapts the
stimulus with a staircase, and runs on a pulse oximeter. Hierarchical models
with normative priors are available for its data. It measures judgements of
heart rate, which combine beliefs about one's heart rate with whatever is
sensed in the listening window. It does not show whether or when a person feels
individual heartbeats; see
[what you may conclude](theory.md#what-you-may-conclude-from-the-hrd). A
full session takes about 20 minutes plus the tutorial.

**The HBC.** It is short, needs only a pulse oximeter, and connects directly to
a large literature, which is why the package keeps it. A plausible estimate of
heart rate can produce a good counting score without detecting any beats
{cite:p}`1999:windmann,2016:brener`, and counting scores are unrelated to
heartbeat detection {cite:p}`2018:ring`, so a score is hard to read as
sensitivity on its own.

**The PAT.** It connects to the phase adjustment literature and classifies
participants against chance with a fixed number of trials. It cannot separate
where the sensation lies from how precise it is, and a participant can be
consistent through a habit of search rather than a sensation;
[the PAT and the HSD](#the-pat-and-the-hsd) sets the two side by side. This port is in beta, and its timing differs from the hardware
original.

**The HSD.** It estimates where in the cardiac cycle a person feels the
heartbeat and how sharply. It keeps the multi-interval logic of the method of
constant stimuli, which takes about 35 minutes {cite:p}`2016:brener`, and
spends the trials where they are informative. It is in beta: not yet
validated, unable to probe delays below 130 ms, and sensitive to jitter in a
Bluetooth ECG, which widens `sigma`. Read the [design page](hsd/design.md)
before using it.

## The PAT and the HSD

Both tasks time a tone from the R-wave, on a delay in milliseconds or a phase
of the cardiac cycle, and both ask for a confidence rating. They differ in the
psychophysical method.

| | PAT | HSD |
|---|---|---|
| Method | Adjustment: the participant turns a dial until the tones feel synchronous, then presses space | Constant stimuli made adaptive: the procedure sets the delay, the participant answers yes or no |
| Who samples the delays | The participant, freely, for as long as they like (about 1 minute per trial, 28 trials in 30 minutes) | The algorithm, by expected information gain; a trial is five beats plus a response |
| Measure | Circular consistency of the chosen delays across trials (mean resultant length), tested against a Monte Carlo null | Posterior over the location, width, floor and peak of a response envelope; credible intervals; posterior evidence that the envelope rises at all |
| Width of the sensation | Not separable from consistency | An explicit parameter, `sigma` |
| Lapses and bias | Not modelled; confidence weighting offered instead | Floor and peak parameters absorb lapses, and are marginalized out |
| Stopping | Fixed 28 trials, justified by simulation (15 to 20 enough for classification) | Credible-interval width on `mu`, with a maximum |
