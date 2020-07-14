# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 14:17:46 2020

@author: stimuser
"""

from psychopy import visual, event

win = visual.Window(monitor='testMonitor', fullscr=False)
mouse = event.Mouse(visible=False, newPos=(0, 0), win=win)
mouse.setPos((0, -.4))
mouse.clickReset()

slider = visual.Slider(
    win=win, name='slider', size=(8.0, 0.5), pos=(0, -0.4),
    labels=['low', 'high'], granularity=0.1, ticks=(1, 100),
    style=('rating',), color='LightGray', font='HelveticaBold', flip=False,
    labelHeight=.5)

while not slider.rating:
    # Mouse position
    newPos = mouse.getPos()
    p = newPos[0]/5
    slider.markerPos = 50 + (p*50)
    slider.draw()
    win.flip()
print(slider.getRating(), slider.getRT())
win.close()
