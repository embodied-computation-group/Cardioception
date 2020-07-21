The Heart Rate Discrimination task
==================================

Staircases
----------

Two staircasing procedure are implemented and can be controlled through the `staircase` parameters in the logging screen:

#### nUp/nDown

This procedure uses a classical adaptive nUp/nDown thresholding procedure (Cornsweet et al., 1976) to estimate the sensitivity and bias of cardiac beliefs. To do so, the staircase adjusts the absolute difference between the frequency of an auditory feedback stimulus and the estimated heart-rate during the interoceptive 'listening' interval (i.e., absolute $\Delta$-BPM). Feedback tones on each trial are thus presented at a frequency faster or slower than the true heart-rate, according to the absolute $\Delta$-BPM parameter. (i.e., 'Faster' or 'Slower' condition). Staircase responses are coded according to their accuracy relative to the ground truth heart-rate, e.g. when the participant correctly discriminates whether a feedback tone is faster or slower than their true heartrate. This procedure converges in the minimum difference between the tones and their heartrate a participant can reliably discriminate, according to the stepping rule parameter. A default 1-down 2-up procedure is used, converging at 71% accuracy at the limit.

#### Psi

This procedure will vary the intensity of the beats frequency from -40.5 bpm to 40.5 bpm. A correct answer is recorded when the participant responds 'More', and an incorrect answer is recorded when the participant responds 'Less'. An ideal observer should therefore end with a threshold estimated at 0.
