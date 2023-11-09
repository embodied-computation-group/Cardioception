# Measuring cardiac interoception

Cardiac interoception has been largely investigated using the heartbeat counting task (also known as the heartbeat tracking task) that was formally introduced more than 40 years ago {cite:p}`1981:schandry`. This task comes with several variants that can concern task instruction, experimental design or the scores derived to measure cardiac interoceptive accuracy and metacognition. Here, we describe the heartbeat counting task together with the heart rate discrimination task, that was recently proposed {cite:p}`2022:legrand` and is also implemented in [cardioception](https://github.com/LegrandNico/Cardioception).

## The Heart Beat Counting task

In the classic "heartbeat counting task" {cite:p}`1981:schandry,1978:dale` participants attend to their heartbeats in intervals of various lengths and are asked to count the number of heartbeats they can effectively feel during this period. An accuracy score is then derived by comparing the reported number of heartbeats and the true number of heartbeats. In the original version {cite:p}`1981:schandry`, the task started with a resting period of 60 seconds and consisted of three estimation sessions (25, 35, and 45 seconds) interleaved with resting periods of 30 seconds.

![hbc](https://raw.githubusercontent.com/LegrandNico/Cardioception/master/docs/source/images/HeartBeatCounting.png)

By default, [Cardioception](https://github.com/LegrandNico/Cardioception) implements the version used in recent publications {cite:p}`2013:hart` in which a training trial of 20 seconds is proposed, after which the 6 experimental trials of different time windows (25, 30, 35,40, 45 and 50s) occurred in a randomized order. The trial length, the condition (`'Rest'`, `'Count'`, `'Training'`), and the randomization can be controlled in the parameters dictionary. This behaviour can be controlled using the `"taskVersion"` parameter.

### Instructions

The instructions are the following:

```text
Without manually checking can you silently count each heartbeat you feel in your body from the time you hear the first tone to when you hear the second tone?
```

### Score

Many variants of the *interoceptive accuracy* score have been proposed, here we implemented and use the one that we considered to be the more widely used, following the formula proposed by Hart et al. {cite:p}`2013:hart` as follows:

```{math}
   Accuracy = 1-\frac{\left | N_{real} - N_{reported} \right |}{\frac{N_{real} + N_{reported}}{2}}
```

After each counting response, the participant is prompted to rate their subjective confidence (from 0 to 100), used to calculate "interoceptive awareness", i.e. the relationship between confidence and accuracy. Total task runtime using default settings is approximately **4 minutes**.

## The Heart Rate Discrimination task

The **Heart Rate Discrimination Task** {cite:p}`2022:legrand` implements an adaptive psychophysical measure of cardiac interoception where participants have to estimate the frequency of their heart rate by comparing it to tones that can be faster or slower. By manipulating the difference between the true heart rate and the presented tone using different staircase procedures, the bias (threshold) and precision (slope) of the psychometric function can be estimated either online or offline, together with metacognitive efficiency.

![hrd](https://raw.githubusercontent.com/LegrandNico/Cardioception/master/docs/source/images/HeartRateDiscrimination.png)

### Staircases

If you run the task in behavioural mode, the **Nonin pulse oximeter** will be read from the port provided. These components might be adapted depending on your local configuration.

Two staircase procedures are implemented and can be controlled through the `stairType` parameters in the parameters dictionary:

#### 1. nUp/nDown

This procedure uses a classical adaptive nUp/nDown thresholding procedure {cite:p}`1962:cornsweet` to estimate the sensitivity and bias of cardiac beliefs. To do so, the staircase adjusts the absolute difference between the frequency of an auditory feedback stimulus and the estimated heart rate during the interoceptive 'listening' interval (i.e., absolute $\Delta$-BPM). Feedback tones on each trial are thus presented at a frequency faster or slower than the true heart rate, according to the absolute $\Delta$-BPM parameter. (i.e., 'Faster' or 'Slower' condition). Staircase responses are coded according to their accuracy relative to the ground truth heart rate, e.g. when the participant correctly discriminates whether a feedback tone is faster or slower than their true heart rate. This procedure converges on the minimum difference between the tones and the heart rate a participant can reliably discriminate, according to the stepping rule parameter. A default 1-down 2-up procedure is used, converging at ~71% accuracy at the limit. Depending on how the `parameters.py` file is set, 2 or more randomly interleaved staircases can be presented at low versus high starting values. This procedure is optimal for estimating the accuracy of interoceptive belief in a simple, reasonably robust algorithm, but should not be used for estimating interoceptive precision (i.e., slope).

#### 2. Psi

This procedure uses Kontsevich and Tyler's {cite:p}`1999:kontsevich` psi-method to estimate the point of subjective equality for faster versus slower cardiac feedback stimuli, based on a cumulative Gaussian psychometric function. Here, tones are presented at the relative $\Delta$-BPM (i.e., which can be more or less than the true heart rate), and this stimulus intensity value is adjusted according to the psi-method, between a minimum and maximum range of $\Delta$-BPM = [-40 40]. The staircase is 'response coded', such that the psychometric function converges on the point of subjective equality between faster and slower stimuli. In this case, the estimated threshold can be treated as an objective measure of subjective cardiac bias, and the slope as a measure of interoceptive uncertainty or precision. Nuisance parameters (i.e., guess and lapse rates) are fixed at values corresponding to a standard 1-alternative forced choice paradigm.

## Discussion

The validity and reliability of the heartbeat counting task (HBC, also called heartbeat tracking task) as a measure of cardiac interoceptive accuracy has been discussed during the last years and it is acknowledged that the scores derived from this task are difficult to interpret concerning interoceptive abilities {cite:p}`2022:ferentzi`. It has been documented that the HBC task is poorly related to actual heartbeat detection {cite:p}`2020:desmedt`, is confounded by fundamental mathematical issues {cite:p}`2018:zamariola`, is unable to distinguish subjective from physiological confounds {cite:p}`1996:ring`, is unable to distinguish true interoceptors from non-interoceptors, and most crucially cannot, by design, distinguish cardiac accuracy (hit rate) from response bias. Furthermore, the task is also ill-suited to the estimation of metacognition variables, as there are extremely few trials and no overall control of accuracy (see {cite:p}`2014:fleming` for details on how metacognition should be measured).

Based on these observations, we considered that *cardiac interoceptive accuracy* is a too multifaceted concept and too confounded by other psychological factors to be measured precisely in the lab without directly manipulating the cardiac signal (i.e. changing and/or systematically observing different cardiac frequencies). It is indeed not possible to know if a participant is correct when reporting heartbeat counts because he/she has good interoceptive accuracy, or because he/she is simply lucky to have prior cardiac beliefs that are aligned with the physiological signal, at least for the time of the experience.

With the heart rate discrimination task (HRD), we proposed to change the focus and the way we measure cardioception. Suppose cardiac interoceptive accuracy cannot be precisely estimated because it is confounded by cardiac beliefs. In that case, we can however measure these beliefs in a very precise and rigorous manner using methods from psychophysics. In addition to that, because we test decisions from the participant many times (the recommended number of trials in the HRD task is 40 per condition minimum), we can estimate metacognitive efficiency more robustly using *meta-d'* {cite:p}`2014:fleming`.
