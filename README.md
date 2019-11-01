<img src= "images/LabLogov2.jpg" width="100">

# Cardioception
Cardioception Python Package - Measuring Interoception with Psychopy. This package implements two measures of cardiac interoception (cardioception): 1) the classical 'heartbeat counting task' by developed by Rainer Schandry[^fn1][^fn2], and 2) a novel "Heartrate Discrimination Task" implementing an adaptive psychophysical measure for measuring cardioception. See *Tasks* below for more details of each individual method. Currently the toolbox natively supports the [Nonin 3012LP Xpod USB pulse oximeter](https://www.nonin.com/products/xpod/) together with [Nonin 8000SM 'soft-clip' fingertip sensors](https://www.nonin.com/products/8000s/). These devices are fairly cheap and readily availble, however in time the intention is to more generally support more sensors and modalities (e.g., ECG).  

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

## Heart Beats Counting
To run the Heart Rate Discrimination Task, run:
`pyton [path]/cardioception/HeartBeatCounting/run.py`
Where `path` is the path to your install folder.

This module implements the classic "heartbeat counting task" (HBT) originally developed by

## Heart Rate Discrimination
To run the Heart Rate Discrimination Task, run:
`pyton [path]/cardioception/HeartRateDiscrimination/run.py`
Where `path` is the path to your install folder.

# Analyses


The `Analyses` folder contains notebooks detailing analysis steps for each tasks.

#References

[^fn1]: Dale, A., & Anderson, D. (1978). Information Variables in Voluntary Control and Classical Conditioning of Heart Rate: Field Dependence and Heart-Rate Perception. Perceptual and Motor Skills, 47(1), 79–85. https://doi.org/10.2466/pms.1978.47.1.79

[^fn2]: Schandry, R. (1981). Heart Beat Perception and Emotional Experience. Psychophysiology, 18(4), 483–488. https://doi.org/10.1111/j.1469-8986.1981.tb02486.x
