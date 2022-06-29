The Heart Rate Discrimination task
==================================

Staircases
----------

If you run the task in behavioral mode, the **Nonin pulse oximeter** will be read from the port provided. These components might be adapted depending on your local configuration.

Two staircasing procedure are implemented and can be controlled through the `staircase` parameters in the logging screen:

#### 1. nUp/nDown

This procedure uses a classical adaptive nUp/nDown thresholding procedure (Cornsweet et al., 1976) to estimate the sensitivity and bias of cardiac beliefs. To do so, the staircase adjusts the absolute difference between the frequency of an auditory feedback stimulus and the estimated heart-rate during the interoceptive 'listening' interval (i.e., absolute $\Delta$-BPM). Feedback tones on each trial are thus presented at a frequency faster or slower than the true heart-rate, according to the absolute $\Delta$-BPM parameter. (i.e., 'Faster' or 'Slower' condition). Staircase responses are coded according to their accuracy relative to the ground truth heart-rate, e.g. when the participant correctly discriminates whether a feedback tone is faster or slower than their true heartrate. This procedure converges on the minimum difference between the tones and their heartrate a participant can reliably discriminate, according to the stepping rule parameter. A default 1-down 2-up procedure is used, converging at ~71% accuracy at the limit. Depending on how the `parameters.py` file is set, 2 or more randomly interleaved staircases can be presented at low versus high starting values. This procedure is optimal for estimating the accuracy of interoceptive belief in a simple, reasonably robust algorithm, but should not be used for estimate interoceptive precision (i.e., slope).

#### 2. Psi

This procedure uses Kontsevich and Tyler's (1999) psi-method to estimate the point of subjective equality for faster versus slower cardiac feedback stimuli, based on a cumulative Gaussian psychometric function. Here, tones are presented at the relative $\Delta$-BPM (i.e., which can be more or less than the true heartrate), and this stimulus intensity value is adjusted according to the psi-method, between a minimum and maximum range of $\Delta$-BPM = [-40 40]. The staircase is 'response coded', such that the psychometric function converges on the point of subjective equality between faster and slower stimuli. In this case, the estimated threshold can be treated as an objective measure of subjective cardiac bias, and the slope as a measure of interoceptive uncertainty or precision. Nuisance parameters (i.e., guess rate and lapse rate) are fixed at values corresponding to a standard 1-alternative forced choice paradigm.
