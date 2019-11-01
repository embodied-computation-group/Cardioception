# Cardioception
Cardioception Python Package - Measuring interoceptive performance with Psychopy

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

## Heart Rate Discrimination
To run the Heart Rate Discrimination Task, run:
`pyton [path]/cardioception/HeartRateDiscrimination/run.py`
Where `path` is the path to your install folder.

# Analyses

The `Analyses` folder contains notebooks detailing analysis steps for each tasks.
