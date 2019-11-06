# -*- coding: utf-8 -*-
"""
Created on Tue Nov  5 13:42:45 2019

@author: au646069
"""
import serial
import time
from ect.recording import Oximeter
from psychopy.sound import Sound
import matplotlib.pyplot as plt
import numpy as np

ser = serial.Serial('COM4')

# Open seral port for Oximeter
oxi = Oximeter(serial=ser, sfreq=75, add_channels=3).setup()

systole = Sound('C', secs=0.1)
diastole1 = Sound('C', secs=0.1)
diastole2 = Sound('E', secs=0.1)

systoleTime1, systoleTime2 = None, None
tstart = time.time()
while time.time() - tstart < 10:

    # Check if there are new data to read
    while oxi.serial.inWaiting() >= 5:

        # Convert bytes into list of int
        paquet = list(oxi.serial.read(5))
        if oxi.check(paquet):  # Check data validity
            oxi.add_paquet(paquet[2])  # Add the new data point

        # Track the note status
        oxi.channels['Channel_0'][-1] = systole.status
        oxi.channels['Channel_1'][-1] = diastole1.status
        oxi.channels['Channel_2'][-1] = diastole2.status

        if oxi.peaks[-1] == 1:
            systole.play()
            systole = Sound('C', secs=0.1)
            systoleTime1 = time.time()
            systoleTime2 = time.time()

        if systoleTime1 is not None:
            if time.time() - systoleTime1 >= 0.3:
                diastole1.play()
                diastole1 = Sound('E', secs=0.1)
                systoleTime1 = None

        if systoleTime2 is not None:
            if time.time() - systoleTime2 >= 0.5:
                diastole2.play()
                diastole2 = Sound('G', secs=0.1)
                systoleTime2 = None
