---
myst:
  html_meta:
    description: "Running the Heart Rate Discrimination task in Cardioception: the Psi staircase and its settings."
    keywords: "heart rate discrimination, HRD, Psi staircase, psychophysics, cardioception, PsychoPy"
---

# Running the HRD

The general steps for a session, a script and the wrappers are on [Running a session](../../getting-started/running-a-session.md).

## Staircase procedures

### Psi

The only staircase. This uses Kontsevich and Tyler's {cite:p}`1999:kontsevich` psi-method to estimate the point of subjective equality for faster versus slower cardiac feedback, based on a cumulative Gaussian psychometric function. Tones are presented at the relative $\Delta$-BPM and this stimulus intensity is adjusted between $\Delta$-BPM = [-50.5 50.5]. The staircase is response-coded, so the function converges on the point of subjective equality between faster and slower stimuli. The threshold is then an estimate of subjective cardiac bias, and the slope an estimate of interoceptive precision. Nuisance parameters (guess and lapse rate) are fixed at values corresponding to a standard 1-alternative forced choice paradigm.

```{important}
Psi converges on the participant's point of subjective equality, their bias, not on a target level of accuracy. That is what the task is designed to measure, but it has consequences for any measure scored against the true heart rate. See the [metacognition tutorial](tutorials/metacognition.md).
```

The nUp/nDown staircase was removed in 1.0.0: `stairType="updown"` now raises. The [changelog](../../reference/changelog.md) explains why.
