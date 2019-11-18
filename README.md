<img src= "images/LabLogo.jpg" width="200">

# Cardioception

The Cardioception Python Package - Measuring Interoception with Psychopy - implements two measures of cardiac interoception (cardioception):
1. the classical *heartbeat counting task* developed by Rainer Schandry<sup>1,2</sup>
2. a novel "Heartrate Discrimination Task" implementing an adaptive psychophysical measure for measuring cardioception.

See *Tasks* below for more details of each individual method.

Currently the toolbox natively supports the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). These devices are fairly cheap and readily available, however in time the intention is to support more sensors and modalities (e.g., ECG).  

# Installation

Download the repository as zip archive and extract the files.

Using a terminal, go to the folder and run:
`python setup.py install`

The **Nonin pulse oximeter** will be automatically launched from the device port specified in the `parameters.py` file of each project. The following lines might be adapted depending on your local configuration.

```python
# Open seral port for Oximeter
parameters['serial'] = serial.Serial('COM4',
                                     baudrate=9600,
                                     timeout=1/75,
                                     stopbits=1,
                                     parity=serial.PARITY_NONE)
```
Where `COM4` refers to the USB port to open.

# Tasks

By default, the results will be saved in the `Results` folder contained in each task folder. This can be modified by changing the value of the `path` entry of the parameters dictionary.

## Heart Beat Counting

<img src= "images/HeartBeatCounting.png">

<br>

To run the Heart Beat Counting Task, run: <br>
`pyton [path]/cardioception/HeartBeatCounting/run.py` <br>
Where `path` is the path to your install folder.

**Task Description**

This module implements a general version of the classic 1978 "heartbeat counting task" (HCT)<sup>1,2</sup> (AKA the 'Schandry task'), in which participants attend to and count their heartbeats in intervals of various length. Afterwards the participant indicates the number of counted heartbeats and an "interoceptive accuracy" (iACC) score is computed to represent their accuracy. In the original version<sup>1</sup>, the task begins with a resting period of 60 seconds and followed by three estimation session (25, 35 and 45 seconds) interleaved with resting periods of 30 seconds.

This package by default implements both the classic task, and an alternative version used in recent publications<sup>3-5</sup> by the Garfinkel lab at Sussex University. In the alternate version, participants first complete a 30s training trial followed by 6 experimental trials of different time-windows (25, 30, 35, 40, 45 and 50s) in a randomized order, without resting periods. Either version can be set as default parameters by the setting the 'task_version' flag to 'Schandry' or 'Garfinkel'. The trial length, the condition ('Rest', 'Count', 'Training') and the randomization can be fully customized in the parameters dictionary.

**The instructions are the following:**

>Without manually checking can you silently count each heartbeat you feel in your body from the time you hear the first tone to when you hear the second tone.

**The accuracy score is calculated using the following equation:**

<img src="http://latex.codecogs.com/gif.latex?Score=\frac{\left | N_{real} - N_{counted} \right |}{\frac{N_{real} + N_{reported}}{2}}" align="center"/>

After each counting response, the participant is prompted to rate their subjective confidence (from 0 to 100), used to calculate "interoceptive awareness", i.e. the relationship of confidence and accuracy. Total task runtime using Garfinkel task settings is approximately **4 minutes**.

## Heart Rate Discrimination

This task implements an adaptive psychophysical procedure for estimating participant ability to discriminate their own heart-rate. On each trial, participants attend to their heartbeat sensations for five seconds and estimate their average heartrate. Immediately following this period, a cardiac feedback stimulus of 5 tones (440 Hz) is played at a particular BPM frequency. The frequency is determined as their estimate average BPM plus or minus an absolute 'alpha' value. This value is the relative difference in frequency between their true heartrate and the feedback stimulus, and is estimated across trials using an adaptive procedure.

Note that currently, the task implements a 1 up 2 down adaptive staircasing, using a logarithmic stepsize function. Using the parameters object, you can set various settings such as step criterion and size, trial numbers, and a boolean flag to collect confidence ratings or not. Future versions will implement a Bayesian Adaptive Procedure to more efficiently estimate psychometric parameters such as slope and threshold.

To run the Heart Rate Discrimination Task, run:
`python [path]/cardioception/HeartRateDiscrimination/run.py`
Where `path` is the path to your install folder.

# Analyses
The [Analyses](../cardioception/Analyses/Analyses.ipynd) folder contains notebooks detailing analysis steps for each tasks. These implement basic data quality checks, summary statistics, and the estimation and plotting of HRD psychometric functions.

# References

1. Dale, A., & Anderson, D. (1978). Information Variables in Voluntary Control and Classical Conditioning of Heart Rate: Field Dependence and Heart-Rate Perception. Perceptual and Motor Skills, 47(1), 79–85. https://doi.org/10.2466/pms.1978.47.1.79

2. Schandry, R. (1981). Heart Beat Perception and Emotional Experience. Psychophysiology, 18(4), 483–488. https://doi.org/10.1111/j.1469-8986.1981.tb02486.x

3. Leganes-Fonteneau, M., Cheang, Y., Lam, Y., Garfinkel, S., & Duka, T. (2019). Interoceptive awareness is associated with acute alcohol-induced changes in subjective effects. Pharmacology Biochemistry and Behavior, 181, 69–76. https://doi.org/10.1016/j.pbb.2019.03.007

4. Rae, C., Ahmad, A., Larsson, D., Silva, M., van Praag, C. G., Garfinkel, S., & Critchley, H. (2019). Impact of cardiac interoception cues on voluntary decisions to make or withhold action in an intentional inhibition task.

5. Rae, C. L., Larsson, D. E., Garfinkel, S. N., & Critchley, H. D. (2019). Dimensions of interoception predict premonitory urges and tic severity in Tourette syndrome. Psychiatry research, 271, 469-475.

# Credit
Some icons used in the Figures or presented during the tasks were downloaded from **Flaticon** [www.flaticon.com](www.flaticon.com).
