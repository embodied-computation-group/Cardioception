---
myst:
  html_meta:
    description: "The four Cardioception tasks side by side: Heart Rate Discrimination, Heartbeat Counting, Heartbeat Synchrony Discrimination and the Phase Adjustment Task, with what each measures, what it needs and how to analyze it."
    keywords: "cardioception tasks, heart rate discrimination, heartbeat counting, heartbeat synchrony discrimination, phase adjustment task, cardiac interoception"
---

# The tasks

Cardioception runs four tasks: two established, the Heart Rate Discrimination
task (HRD) and the Heartbeat Counting task (HBC), and two in beta, the
Heartbeat Synchrony Discrimination task (HSD) and the Phase Adjustment Task
(PAT). Tasks in beta are close to feature complete and are still being
rigorously validated. Two more, the Whitehead method and the method of constant
stimuli, are coming. Each task has a page that says what it measures and how to
run it; this page sets them side by side.

| Task | [HRD](hrd/index.md) | [HBC](hbc.md) | [HSD](hsd/index.md) | [PAT](pat.md) | [Whitehead](whitehead.md) | [Constant stimuli](constant-stimuli.md) |
|---|---|---|---|---|---|---|
| Measure | Bias (threshold) and precision (slope) of judgements of one's own heart rate, with confidence | Reported against recorded heartbeats over fixed windows, with confidence | Where in the cardiac cycle the heartbeat is felt (`mu`), how sharply (`sigma`), and how strongly, with confidence | Consistency of the chosen tone delay or phase across trials, with confidence | Discrimination of synchronous from delayed tones {cite:p}`1977:whitehead` | Proportion of tones judged simultaneous at each delay {cite:p}`1993:brener` |
| Reference | {cite:t}`2022:legrand` | {cite:t}`1981:schandry`, {cite:t}`1978:dale` | {cite:t}`1993:brener` | {cite:t}`2021:plans`, {cite:t}`2026:hodgetts` | {cite:t}`1977:whitehead` | {cite:t}`1993:brener` |
| Adaptive | Yes: a Psi staircase sets the tone rate | No | Yes: Bayesian placement of the tone delay | No: the participant adjusts the delay | No | No |
| Hardware | Pulse oximeter, or ECG or PPG over LSL; headphones; mouse or keyboard | Pulse oximeter, or ECG or PPG over LSL; keyboard | ECG over LSL; sound card; keyboard | ECG over LSL; sound card; mouse wheel; a tactor for the control task |  |  |
| Trials and minutes | 120 trials, about 20 minutes plus the tutorial | 6 counting windows, about 4 minutes | 15 to 60 trials; 60 took 7 minutes | 28 trials and 8 practice, about 30 minutes |  |  |
| Status | Established | Established | Beta | Beta | Coming soon | Coming soon |

Every task writes to the same layout,
`data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/` under the current
folder or under `resultPath`. The timestamp makes each run's directory unique,
every file name carries participant, session and run, and `manifest.json`
records the settings before the first trial. The trial table is always
`*_final.txt`.

## Strengths and limitations

Each task answers a different question, and each has costs.

**The HRD.** It separates the bias of heart rate judgements from their
precision, includes a within-person exteroceptive comparison, adapts the
stimulus with a staircase, and runs on a pulse oximeter. Hierarchical models
with normative priors are available for its data. It measures judgements of
heart rate, which combine beliefs about one's heart rate with whatever is
sensed in the listening window. It does not show whether or when a person feels
individual heartbeats; see
[what you may conclude](hrd/theory.md#what-you-may-conclude-from-the-hrd). A
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
Bluetooth ECG, which widens `sigma`. Read the [design page](hsd/design.md)
before using it.

**The PAT.** It connects to the phase adjustment literature and classifies
participants against chance with a fixed number of trials. It cannot separate
where the sensation lies from how precise it is, and a participant can be
consistent through a habit of search rather than a sensation; the
[HSD design page](hsd/design.md#relation-to-the-phase-adjustment-task) compares
the two. This port is in beta, and its timing differs from the hardware
original.


## Theory

Author: Micah G. Allen

Before you analyze an HRD dataset, you need to be clear about what the task can
measure. Cardiac interoception is often described as the ability to perceive
one's heartbeat accurately. That description sounds straightforward until we
ask what an experimental score actually identifies.

We developed the Heart Rate Discrimination task to estimate three distinguishable
features of cardiac judgement: perceptual bias, perceptual precision, and the
relationship between confidence and performance. Together they describe a
person's beliefs about their heart rate under particular task conditions. This
is a narrower claim than measuring a general interoceptive ability.

This page explains that position and the evidence behind it. The practical
tutorials build on these distinctions.
The HRD half of that argument, from why the HRD measures cardiac beliefs
onwards, is on the [HRD theory page](hrd/theory.md).

## Cardiac interoception as a measurement problem

Interoception encompasses the processes by which the nervous system senses,
interprets, and regulates the internal state of the body. Cardiac interoception
is one part of that larger system. It has been studied extensively because the
heartbeat is continuous, discrete, and easy to record, and because bodily
signals are thought to contribute to emotion, cognition, and the sense of self
{cite:p}`2022:legrand,2022:garfinkel`.

The experimental difficulty is that a heartbeat is an endogenous stimulus. In
most laboratory studies we can record it, but we cannot set its intensity and
timing as freely as we would set the contrast of a visual stimulus. A participant's
response may therefore reflect several sources of information at once, including
afferent cardiac signals, prior knowledge of heart rate, attention, decision
strategy, and the current physiological context. A task score does not separate
these sources simply because it is compared with an objective recording.

This problem is clearest in the two task families that have dominated the
cardiac interoception literature. Brener and Ring provide a detailed review
{cite:p}`2016:brener`.

### What heartbeat counting can establish

In the heartbeat counting task {cite:p}`1981:schandry,1978:dale`, participants
report how many heartbeats they experienced during a fixed interval. The reported
count is compared with the recorded count to produce an accuracy score. The task
is brief and simple to administer, which helps explain its very large literature.

A plausible estimate of resting heart rate can produce a good counting score
without reliable detection of individual heartbeats. Several results show how
strongly prior knowledge contributes:

- In patients with cardiac pacemakers, actual rates of 61, 76, and 109 BPM
  produced reported rates of 52, 54, and 59 BPM. The reports changed very little
  as the heart rate changed {cite:p}`1999:windmann`.
- Counting scores tend to improve when participants lie down. In one study,
  reported rates were similar when supine and standing, at 50 and 48 BPM, while
  recorded rates differed substantially, at 70 and 86 BPM. The score improved
  because the recorded rate moved closer to the participant's estimate
  {cite:p}`2016:brener`.
- Heart-rate feedback can improve later counting scores even when the feedback
  is unrelated to the participant's own heart. This changes knowledge of heart
  rate without demonstrating increased cardiac sensitivity {cite:p}`2016:brener`.

The scoring rule adds further ambiguity. Systematic undercounting has a large
influence on the score, and sensitivity cannot be separated from response bias
{cite:p}`1996:ring,2018:zamariola,2020:desmedt`. A high counting score is therefore
insufficient evidence that the participant detected their heartbeats. It may
reflect sensation, knowledge, or a favourable combination of the two. The large
literature built with the task remains informative within that constraint
{cite:p}`2022:ferentzi`.

### What fixed-delay synchrony tasks can establish

The other common approach is a two-alternative heartbeat synchrony task
{cite:p}`1977:whitehead`. Tones or flashes are presented at two delays from the
ECG R-wave, and participants judge which sequence is simultaneous with their
heartbeat. Successful performance requires access to cardiac timing, which is a
clear advantage over counting.

The usual implementation assumes that heartbeat sensations occur at similar
latencies across people. Multi-interval studies show substantial individual
variation, with preferred intervals distributed across approximately R+100 to
R+400 ms {cite:p}`2016:brener`. Consider a participant whose heartbeat sensation
occurs at R+256 ms. Tones at R+128 and R+384 ms are equally distant from that
sensation, so the participant may treat both as equally synchronous. Their poor
discrimination would be compatible with a clearly perceived heartbeat at a
latency the task did not sample.

Fixed-delay tasks consequently risk false negatives. Only about one quarter of
participants meet the conventional detector criterion in common versions of the
task, and performance improves when stimulus delays better accommodate individual
cardiac timing {cite:p}`2016:brener`. A failure to discriminate two chosen delays
does not uniquely identify an absence of heartbeat sensation.

### Why the traditional tasks disagree

Heartbeat counting and fixed-delay synchrony tasks are often placed under the
same heading of interoceptive accuracy. If they measured the same ability, their
scores should show a reasonably stable association. In practice, correlations
are generally weak or absent {cite:p}`2016:brener`.

This disagreement is informative. Counting is vulnerable to good performance
based on prior knowledge, while a fixed-delay task can miss participants whose
sensation occurs at an unexpected latency. Combining both under a single label
does not resolve either measurement problem.

## A dimensional framework

Garfinkel and colleagues proposed a useful distinction among three aspects of
interoception {cite:p}`2015:garfinkel`:

| Dimension | Intended construct | Typical assessment |
|---|---|---|
| Interoceptive accuracy | Detection of internal events | Objective task performance |
| Interoceptive sensibility | Attention to and beliefs about internal states | Self-report questionnaires |
| Interoceptive awareness | Insight into one's own task performance | Confidence-based metacognitive measures |

The framework prevents us from treating task performance, questionnaire scores,
and metacognition as versions of the same variable. That was an important advance,
and later work has extended the framework across bodily systems and additional
dimensions {cite:p}`2022:garfinkel`.

The label attached to a task does not establish its construct validity. Calling
heartbeat counting and fixed-delay synchrony measures "interoceptive accuracy"
still leaves their opposite biases and weak correspondence unexplained. Murphy
makes the broader point that progress now depends on better measurement and a
more careful account of individual differences, including state dependence and
the context in which a person uses bodily information {cite:p}`2023:murphy`.

We retain the dimensional view. For the HRD, we define each quantity from the
behaviour that identifies it and avoid treating accuracy as a general-purpose
label.

## A stronger measure of heartbeat timing

The method of constant stimuli offers an instructive comparison. It presents
signals at several delays spanning the cardiac cycle, commonly from R+0 to
R+500 ms, and asks whether each signal was simultaneous with a heartbeat
sensation {cite:p}`1993:brener`.

Sampling several delays allows the participant's data to reveal two quantities.
The preferred delay locates the heartbeat sensation within the cardiac cycle.
The spread of preferred delays measures the temporal precision of detection.
This design addresses the main ambiguity of fixed-delay tasks and shows good
agreement with related multi-interval procedures {cite:p}`2016:brener`.

Its practical demands are substantial. A standard session takes about 35 minutes,
and implementations can take considerably longer once familiarization is included
{cite:p}`2016:brener,2022:legrand`. The task also requires precise synchronization
of cardiac and external events. Participants must attend to both streams and make
a temporal judgement, which adds demands beyond sensing the heartbeat itself.

For studies concerned specifically with the timing and reliability of afferent
heartbeat sensations, this remains an important design. The HRD addresses a
different question.

```{toctree}
---
hidden:
---
Heart Rate Discrimination task <hrd/index.md>
Heartbeat Counting task <hbc.md>
Phase Adjustment Task <pat.md>
Heartbeat Synchrony Discrimination task <hsd/index.md>
Whitehead method <whitehead.md>
Method of constant stimuli <constant-stimuli.md>
```
