---
myst:
  html_meta:
    description: "Heartbeat discrimination: judging whether stimuli at one of two fixed delays after each heartbeat are simultaneous with it. Coming to Cardioception."
    keywords: "heartbeat discrimination, Whitehead, heartbeat detection, heartbeat synchrony, cardiac interoception, cardioception"
---

# Heartbeat discrimination

An implementation of heartbeat discrimination is planned for Cardioception. On each trial, a train of stimuli is presented at one of two fixed delays after each R-wave of the ECG, and the participant judges whether the train was simultaneous with their heartbeat or delayed.

The procedure was introduced by Whitehead and colleagues {cite:p}`1976:whitehead,1977:whitehead`. In the original version a light flashed either 128 or 384 ms after each R-wave over 200 ten-second trials, the participant pressed one of two buttons after each trial, and discrimination was scored with d'. Later laboratories changed most of these parameters: tones replaced the light, the delays moved (for example to 200 and 500 ms), and the number of trials, the stimuli per trial and the scoring rule all varied. There is therefore no single heartbeat discrimination task, and the implementation will document each parameter it uses.

A review of the literature will accompany the implementation. For an introduction to the method and its limitations, see [What fixed-delay synchrony tasks can establish](theory.md#what-fixed-delay-synchrony-tasks-can-establish).
