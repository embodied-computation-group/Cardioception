# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 14:17:46 2020

@author: stimuser
"""

import time
import numpy as np
import matplotlib.pyplot as plt
from systole.detection import oxi_peaks
from systole.recording import BrainVisionExG
from systole.utils import to_neighbour


sfreq = 200
start = time.time()
final_data3 = []
while time.time() - start < 60:
    recording = BrainVisionExG(ip='10.60.88.162').read(5)
    segment = np.array(recording['PLETH'])
    print(len(segment))
    
    segment = segment[-5*sfreq:]
    signal, peaks = oxi_peaks(segment, sfreq=sfreq)
    #peaks = to_neighbour(signal, peaks, size=100)
    timeidx = np.arange(0, len(signal))/1000
    plt.plot(timeidx, signal)
    plt.plot(timeidx[peaks], signal[peaks], 'ro')
    plt.show()
    
    final_data3.append(recording)


from psychopy.visual.window import Window
from psychopy.visual.slider import Slider

win = Window()
vas = Slider(win,
             ticks=(1, 100),
             labels=('Not at all confident', 'Extremely confident'),
             granularity=1,
             color='white')

while not vas.rating:
    vas.draw()
    win.flip()





ratingScale = visual.Slider(
        win, ticks=(1, 100),
        labels=('Not at all confident', 'Extremely confident'),
        granularity=1, color='white')

while not ratingScale.rating:
    ratingScale.draw()
    win.flip()


00

import json

json = json.dumps(final_data)
f = open("recording.json","w")
f.write(json)
f.close()


# Get actual heart Rate
average_hr = int((60000/np.diff(np.where(peaks)[0])).mean())
print(average_hr)

#from psychopy import event
#
#event.waitKeys()

from psychopy.hardware import keyboard
#from psychopy import core
#
#kb = keyboard.Keyboard(device=)
#
#while True:
#    keys = kb.getKeys(['3', '4'], waitRelease=True)
#    for key in keys:
#        print(key.name, key.rt, key.duration)
import numpy as np
from psychopy import event
from cardioception.HeartRateDiscrimination.fMRI.parameters import getParameters
from cardioception.HeartRateDiscrimination.fMRI.task import run
from psychopy.event import Mouse
from psychopy import visual

parameters = getParameters('test', 1)
ratingScale = visual.Slider(
        parameters['win'], ticks=(1, 100), units=None,
        labels=('Not at all confident', 'Extremely confident'),
        granularity=1, color='white')

while not ratingScale.rating:
    ratingScale.draw()
    win.flip()

kb = keyboard.Keyboard()

# during your trial
while True:
    keys = kb.getKeys(waitRelease=True)
    if keys:
        break
    
    
    
if 'quit' in keys:
    core.quit()
for key in keys:
    print(key.name, key.rt, key.duration)






