#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy3 Experiment Builder (v2020.1.2),
    on July 07, 2020, at 15:15
If you publish work using this script the most relevant publication is:

    Peirce J, Gray JR, Simpson S, MacAskill M, Höchenberger R, Sogo H, Kastman E, Lindeløv JK. (2019) 
        PsychoPy2: Experiments in behavior made easy Behav Res 51: 195. 
        https://doi.org/10.3758/s13428-018-01193-y

"""

from __future__ import absolute_import, division

from psychopy import locale_setup
from psychopy import prefs
from psychopy import sound, gui, visual, core, data, event, logging, clock
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED,
                                STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)

import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import (sin, cos, tan, log, log10, pi, average,
                   sqrt, std, deg2rad, rad2deg, linspace, asarray)
from numpy.random import random, randint, normal, shuffle
import os  # handy system and path functions
import sys  # to get file system encoding

from psychopy.hardware import keyboard



# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_thisDir)

# Store info about the experiment session
psychopyVersion = '2020.1.2'
expName = 'HRD_fMRI'  # from the Builder filename that created this script
expInfo = {'participant': '', 'session': '001'}
dlg = gui.DlgFromDict(dictionary=expInfo, sortKeys=False, title=expName)
if dlg.OK == False:
    core.quit()  # user pressed cancel
expInfo['date'] = data.getDateStr()  # add a simple timestamp
expInfo['expName'] = expName
expInfo['psychopyVersion'] = psychopyVersion

# Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
filename = _thisDir + os.sep + u'data/%s/%s_%s' % (expInfo['participant'], expName, expInfo['date'])

# An ExperimentHandler isn't essential but helps with data saving
thisExp = data.ExperimentHandler(name=expName, version='',
    extraInfo=expInfo, runtimeInfo=None,
    originPath='C:\\Users\\au646069\\github\\Cardioception\\cardioception\\HeartRateDiscrimination\\Bayesian\\HRD_bayesian.py',
    savePickle=True, saveWideText=True,
    dataFileName=filename)
# save a log file for detail verbose info
logFile = logging.LogFile(filename+'.log', level=logging.EXP)
logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

endExpNow = False  # flag for 'escape' or other condition => quit the exp
frameTolerance = 0.001  # how close to onset before 'same' frame

# Start Code - component code to be run before the window creation

# Setup the Window
win = visual.Window(
    size=[1280, 720], fullscr=False, screen=0, 
    winType='pyglet', allowGUI=True, allowStencil=False,
    monitor='testMonitor', color=[0,0,0], colorSpace='rgb',
    blendMode='avg', useFBO=True, 
    units='height')
# store frame rate of monitor if we can measure it
expInfo['frameRate'] = win.getActualFrameRate()
if expInfo['frameRate'] != None:
    frameDur = 1.0 / round(expInfo['frameRate'])
else:
    frameDur = 1.0 / 60.0  # could not measure, so guess

# create a default keyboard (e.g. to check for escape)
defaultKeyboard = keyboard.Keyboard()

# Initialize components for Routine "getTrigger"
getTriggerClock = core.Clock()
key_resp = keyboard.Keyboard()
text_2 = visual.TextStim(win=win, name='text_2',
    text='Please press SPACE when you are ready to start',
    font='Arial',
    pos=(0, 0), height=0.1, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=-1.0);

# Initialize components for Routine "fixCross"
fixCrossClock = core.Clock()
fiCross1 = visual.ShapeStim(
    win=win, name='fiCross1', vertices='cross',
    size=(0.1, 0.1),
    ori=0, pos=(0, 0),
    lineWidth=1, lineColor=[1,1,1], lineColorSpace='rgb',
    fillColor=[1,1,1], fillColorSpace='rgb',
    opacity=1, depth=0.0, interpolate=True)
import pandas as pd
import serial
from systole.recording import findOximeter, Oximeter
from systole detection import oxi_peaks

portNb = findOximeter()
if portNb is None:
    print('Cannot find the Pulse Oximeter automatically, please enter port reference in the GUI')
    core.quit()

port = serial.Serial(portNb)
oxiTask = Oximeter(serial=port, sfreq=75, add_channels=1)
oxiTask.setup().read(duration=1)


signal_df = pd.DataFrame([])

stairCaseIntero = data.PsiHandler(
    nTrials=50,
    intensRange=[-40.5, 40.5], alphaRange=[-40.5, 40.5],
    betaRange=[0.1, 20], intensPrecision=1,
    alphaPrecision=1, betaPrecision=0.1,
    delta=0.05, stepType='lin', expectedMin=0)

stairCaseExtero = data.PsiHandler(
    nTrials=50,
    intensRange=[-40.5, 40.5], alphaRange=[-40.5, 40.5],
    betaRange=[0.1, 20], intensPrecision=1,
    alphaPrecision=1, betaPrecision=0.1,
    delta=0.05, stepType='lin', expectedMin=0)

# Initialize components for Routine "Intero"
InteroClock = core.Clock()
Listen = visual.ImageStim(
    win=win,
    name='Listen', 
    image='Images/heartbeat.png', mask=None,
    ori=0, pos=(0, -0.2), size=(0.18480903, 0.15169271),
    color=[1,1,1], colorSpace='rgb', opacity=1,
    flipHoriz=False, flipVert=False,
    texRes=128, interpolate=True, depth=0.0)
textListen = visual.TextStim(win=win, name='textListen',
    text='Listen to your Heart',
    font='Arial',
    pos=(0, 0.2), height=0.04, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=-1.0);

# Initialize components for Routine "Feedback2_2"
Feedback2_2Clock = core.Clock()
text_7 = visual.TextStim(win=win, name='text_7',
    text='Please stay still during the recording',
    font='Arial',
    pos=(0, 0), height=0.1, wrapWidth=None, ori=0, 
    color='red', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=0.0);

# Initialize components for Routine "Extero"
ExteroClock = core.Clock()
text_3 = visual.TextStim(win=win, name='text_3',
    text='Listen to the tones',
    font='Arial',
    pos=(0, 0.2), height=0.04, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=0.0);
image_2 = visual.ImageStim(
    win=win,
    name='image_2', 
    image='Images/Listen.png', mask=None,
    ori=0, pos=(0, -0.2), size=(0.15, 0.15),
    color=[1,1,1], colorSpace='rgb', opacity=1,
    flipHoriz=False, flipVert=False,
    texRes=128, interpolate=True, depth=-1.0)
sound_2 = sound.Sound('A', secs=-1, stereo=True, hamming=True,
    name='sound_2')
sound_2.setVolume(1)

# Initialize components for Routine "fixCross2"
fixCross2Clock = core.Clock()
fiCross2 = visual.ShapeStim(
    win=win, name='fiCross2', vertices='cross',
    size=(0.1, 0.1),
    ori=0, pos=(0, 0),
    lineWidth=1, lineColor=[1,1,1], lineColorSpace='rgb',
    fillColor=[1,1,1], fillColorSpace='rgb',
    opacity=1, depth=0.0, interpolate=True)

# Initialize components for Routine "Decision"
DecisionClock = core.Clock()
mouse = event.Mouse(win=win)
x, y = [None, None]
mouse.mouseClock = core.Clock()
sound_1 = sound.Sound('A', secs=-1, stereo=True, hamming=True,
    name='sound_1')
sound_1.setVolume(1)
textDecision = visual.TextStim(win=win, name='textDecision',
    text='Do you think the tone frequency was higher or lower than your heart rate?\n\nLower (Left button) - Higher (Right button)',
    font='Arial',
    pos=(0, 0.3), height=0.05, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=-2.0);
image = visual.ImageStim(
    win=win,
    name='image', 
    image='Images/listenResponse.png', mask=None,
    ori=0, pos=(0, -0.2), size=(0.39609375, 0.16111111),
    color=[1,1,1], colorSpace='rgb', opacity=1,
    flipHoriz=False, flipVert=False,
    texRes=128, interpolate=True, depth=-3.0)
text_Less = visual.TextStim(win=win, name='text_Less',
    text='Less',
    font='Arial',
    pos=(-0.2, 0), height=0.1, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=-6.0);
text_More = visual.TextStim(win=win, name='text_More',
    text='More',
    font='Arial',
    pos=(0.2, 0), height=0.1, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=-7.0);

# Initialize components for Routine "RatingScale"
RatingScaleClock = core.Clock()
rating = visual.RatingScale(win=win, name='rating', marker='triangle', size=1.0, pos=[0.0, -0.4], low=0, high=1, precision=100, showValue=False, singleClick=True, disappear=True)

# Initialize components for Routine "Feedback"
FeedbackClock = core.Clock()
text_4 = visual.TextStim(win=win, name='text_4',
    text='Too late',
    font='Arial',
    pos=(0, 0), height=0.1, wrapWidth=None, ori=0, 
    color='red', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=0.0);

# Initialize components for Routine "endScreen"
endScreenClock = core.Clock()
text = visual.TextStim(win=win, name='text',
    text='Thank you for participating\n\nPlease wait for the next instruction',
    font='Arial',
    pos=(0, 0), height=0.1, wrapWidth=None, ori=0, 
    color='white', colorSpace='rgb', opacity=1, 
    languageStyle='LTR',
    depth=0.0);

# Create some handy timers
globalClock = core.Clock()  # to track the time since experiment started
routineTimer = core.CountdownTimer()  # to track time remaining of each (non-slip) routine 

# ------Prepare to start Routine "getTrigger"-------
continueRoutine = True
# update component parameters for each repeat
key_resp.keys = []
key_resp.rt = []
_key_resp_allKeys = []
# keep track of which components have finished
getTriggerComponents = [key_resp, text_2]
for thisComponent in getTriggerComponents:
    thisComponent.tStart = None
    thisComponent.tStop = None
    thisComponent.tStartRefresh = None
    thisComponent.tStopRefresh = None
    if hasattr(thisComponent, 'status'):
        thisComponent.status = NOT_STARTED
# reset timers
t = 0
_timeToFirstFrame = win.getFutureFlipTime(clock="now")
getTriggerClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
frameN = -1

# -------Run Routine "getTrigger"-------
while continueRoutine:
    # get current time
    t = getTriggerClock.getTime()
    tThisFlip = win.getFutureFlipTime(clock=getTriggerClock)
    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
    # update/draw components on each frame
    
    # *key_resp* updates
    waitOnFlip = False
    if key_resp.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
        # keep track of start time/frame for later
        key_resp.frameNStart = frameN  # exact frame index
        key_resp.tStart = t  # local t and not account for scr refresh
        key_resp.tStartRefresh = tThisFlipGlobal  # on global time
        win.timeOnFlip(key_resp, 'tStartRefresh')  # time at next scr refresh
        key_resp.status = STARTED
        # keyboard checking is just starting
        waitOnFlip = True
        win.callOnFlip(key_resp.clock.reset)  # t=0 on next screen flip
        win.callOnFlip(key_resp.clearEvents, eventType='keyboard')  # clear events on next screen flip
    if key_resp.status == STARTED and not waitOnFlip:
        theseKeys = key_resp.getKeys(keyList=['space'], waitRelease=False)
        _key_resp_allKeys.extend(theseKeys)
        if len(_key_resp_allKeys):
            key_resp.keys = _key_resp_allKeys[-1].name  # just the last key pressed
            key_resp.rt = _key_resp_allKeys[-1].rt
            # a response ends the routine
            continueRoutine = False
    
    # *text_2* updates
    if text_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
        # keep track of start time/frame for later
        text_2.frameNStart = frameN  # exact frame index
        text_2.tStart = t  # local t and not account for scr refresh
        text_2.tStartRefresh = tThisFlipGlobal  # on global time
        win.timeOnFlip(text_2, 'tStartRefresh')  # time at next scr refresh
        text_2.setAutoDraw(True)
    
    # check for quit (typically the Esc key)
    if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
        core.quit()
    
    # check if all components have finished
    if not continueRoutine:  # a component has requested a forced-end of Routine
        break
    continueRoutine = False  # will revert to True if at least one component still running
    for thisComponent in getTriggerComponents:
        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
            continueRoutine = True
            break  # at least one component has not yet finished
    
    # refresh the screen
    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
        win.flip()

# -------Ending Routine "getTrigger"-------
for thisComponent in getTriggerComponents:
    if hasattr(thisComponent, "setAutoDraw"):
        thisComponent.setAutoDraw(False)
# check responses
if key_resp.keys in ['', [], None]:  # No response was made
    key_resp.keys = None
thisExp.addData('key_resp.keys',key_resp.keys)
if key_resp.keys != None:  # we had a response
    thisExp.addData('key_resp.rt', key_resp.rt)
thisExp.addData('key_resp.started', key_resp.tStartRefresh)
thisExp.addData('key_resp.stopped', key_resp.tStopRefresh)
thisExp.nextEntry()
thisExp.addData('text_2.started', text_2.tStartRefresh)
thisExp.addData('text_2.stopped', text_2.tStopRefresh)
# the Routine "getTrigger" was not non-slip safe, so reset the non-slip timer
routineTimer.reset()

# set up handler to look after randomisation of conditions etc
trials = data.TrialHandler(nReps=1, method='random', 
    extraInfo=expInfo, originPath=-1,
    trialList=data.importConditions('Conditions.xlsx'),
    seed=None, name='trials')
thisExp.addLoop(trials)  # add the loop to the experiment
thisTrial = trials.trialList[0]  # so we can initialise stimuli with some values
# abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
if thisTrial != None:
    for paramName in thisTrial:
        exec('{} = thisTrial[paramName]'.format(paramName))

for thisTrial in trials:
    currentLoop = trials
    # abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
    if thisTrial != None:
        for paramName in thisTrial:
            exec('{} = thisTrial[paramName]'.format(paramName))
    
    # ------Prepare to start Routine "fixCross"-------
    continueRoutine = True
    # update component parameters for each repeat
    jitter = np.arange(0, 2, .1)
    shuffle(jitter)
    
    if condition == 'Intero':
        nRepsIntero = 5
        nRepsExtero = 0
    elif condition == 'Extero':
        nRepsIntero = 0
        nRepsExtero = 1
    
    oxiTask.readInWaiting()
    
    # keep track of which components have finished
    fixCrossComponents = [fiCross1]
    for thisComponent in fixCrossComponents:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    fixCrossClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
    frameN = -1
    
    # -------Run Routine "fixCross"-------
    while continueRoutine:
        # get current time
        t = fixCrossClock.getTime()
        tThisFlip = win.getFutureFlipTime(clock=fixCrossClock)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *fiCross1* updates
        if fiCross1.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            fiCross1.frameNStart = frameN  # exact frame index
            fiCross1.tStart = t  # local t and not account for scr refresh
            fiCross1.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(fiCross1, 'tStartRefresh')  # time at next scr refresh
            fiCross1.setAutoDraw(True)
        if fiCross1.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > fiCross1.tStartRefresh + jitter[0]-frameTolerance:
                # keep track of stop time/frame for later
                fiCross1.tStop = t  # not accounting for scr refresh
                fiCross1.frameNStop = frameN  # exact frame index
                win.timeOnFlip(fiCross1, 'tStopRefresh')  # time at next scr refresh
                fiCross1.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
            core.quit()
        
        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in fixCrossComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "fixCross"-------
    for thisComponent in fixCrossComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    trials.addData('fiCross1.started', fiCross1.tStartRefresh)
    trials.addData('fiCross1.stopped', fiCross1.tStopRefresh)
    # the Routine "fixCross" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # set up handler to look after randomisation of conditions etc
    trials_2 = data.TrialHandler(nReps=nRepsIntero, method='random', 
        extraInfo=expInfo, originPath=-1,
        trialList=[None],
        seed=None, name='trials_2')
    thisExp.addLoop(trials_2)  # add the loop to the experiment
    thisTrial_2 = trials_2.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisTrial_2.rgb)
    if thisTrial_2 != None:
        for paramName in thisTrial_2:
            exec('{} = thisTrial_2[paramName]'.format(paramName))
    
    for thisTrial_2 in trials_2:
        currentLoop = trials_2
        # abbreviate parameter names if possible (e.g. rgb = thisTrial_2.rgb)
        if thisTrial_2 != None:
            for paramName in thisTrial_2:
                exec('{} = thisTrial_2[paramName]'.format(paramName))
        
        # ------Prepare to start Routine "Intero"-------
        continueRoutine = True
        routineTimer.add(5.000000)
        # update component parameters for each repeat
        oxiTask.readInWaiting()
        oxiTask.channels['Channel_0'][-1] = 1  # Start trigger
        # Read PPG
        oxiTask.read(duration=5.0)
        # keep track of which components have finished
        InteroComponents = [Listen, textListen]
        for thisComponent in InteroComponents:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        InteroClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
        frameN = -1
        
        # -------Run Routine "Intero"-------
        while continueRoutine and routineTimer.getTime() > 0:
            # get current time
            t = InteroClock.getTime()
            tThisFlip = win.getFutureFlipTime(clock=InteroClock)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *Listen* updates
            if Listen.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                Listen.frameNStart = frameN  # exact frame index
                Listen.tStart = t  # local t and not account for scr refresh
                Listen.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(Listen, 'tStartRefresh')  # time at next scr refresh
                Listen.setAutoDraw(True)
            if Listen.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > Listen.tStartRefresh + 5.0-frameTolerance:
                    # keep track of stop time/frame for later
                    Listen.tStop = t  # not accounting for scr refresh
                    Listen.frameNStop = frameN  # exact frame index
                    win.timeOnFlip(Listen, 'tStopRefresh')  # time at next scr refresh
                    Listen.setAutoDraw(False)
            
            # *textListen* updates
            if textListen.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                textListen.frameNStart = frameN  # exact frame index
                textListen.tStart = t  # local t and not account for scr refresh
                textListen.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(textListen, 'tStartRefresh')  # time at next scr refresh
                textListen.setAutoDraw(True)
            if textListen.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > textListen.tStartRefresh + 5.0-frameTolerance:
                    # keep track of stop time/frame for later
                    textListen.tStop = t  # not accounting for scr refresh
                    textListen.frameNStop = frameN  # exact frame index
                    win.timeOnFlip(textListen, 'tStopRefresh')  # time at next scr refresh
                    textListen.setAutoDraw(False)
            
            # check for quit (typically the Esc key)
            if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
                core.quit()
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in InteroComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # -------Ending Routine "Intero"-------
        for thisComponent in InteroComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        trials_2.addData('Listen.started', Listen.tStartRefresh)
        trials_2.addData('Listen.stopped', Listen.tStopRefresh)
        trials_2.addData('textListen.started', textListen.tStartRefresh)
        trials_2.addData('textListen.stopped', textListen.tStopRefresh)
        # Get actual heart Rate
        signal, peaks = oxi_peaks(oxi.recording[-75*6:])
        bpm = 60000/np.diff(np.where(peaks[-5000:])[0])
        
        # Append signal to recording
        signal = np.linspace(0, 1, 5000)
        
        print(trials.thisN)
        
        if (np.any(bpm<30) or np.any(bpm>140)):
            
            average_hr = int(bpm.mean())
        
            trials_2.finished = 1
            nRepsFeedbackBPM = 0
        
            alpha = stairCaseIntero.next()
        
            # Check for extreme HR values, e.g. if HR changes massively from
            # trial to trial.
            if (average_hr + alpha) < 15:
                hr = '15'
            elif (average_hr + alpha) > 199:
                hr = '199'
            else:
                hr = str(int(average_hr + alpha))
        
            file = os.path.join(os.getcwd(), 'sounds', hr + '.wav')
        else:
            nRepsFeedbackBPM = 1
            
            print('WARNING: Noisy signal recording, cannnot estimate heart rate.')
        
            # Set default file is heart rate is not properly recorded
            alpha = 40
            file = os.path.join(os.getcwd(), 'sounds/60.wav')
        
        
        # set up handler to look after randomisation of conditions etc
        trials_6 = data.TrialHandler(nReps=nRepsFeedbackBPM, method='random', 
            extraInfo=expInfo, originPath=-1,
            trialList=[None],
            seed=None, name='trials_6')
        thisExp.addLoop(trials_6)  # add the loop to the experiment
        thisTrial_6 = trials_6.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisTrial_6.rgb)
        if thisTrial_6 != None:
            for paramName in thisTrial_6:
                exec('{} = thisTrial_6[paramName]'.format(paramName))
        
        for thisTrial_6 in trials_6:
            currentLoop = trials_6
            # abbreviate parameter names if possible (e.g. rgb = thisTrial_6.rgb)
            if thisTrial_6 != None:
                for paramName in thisTrial_6:
                    exec('{} = thisTrial_6[paramName]'.format(paramName))
            
            # ------Prepare to start Routine "Feedback2_2"-------
            continueRoutine = True
            routineTimer.add(1.000000)
            # update component parameters for each repeat
            # keep track of which components have finished
            Feedback2_2Components = [text_7]
            for thisComponent in Feedback2_2Components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            Feedback2_2Clock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
            frameN = -1
            
            # -------Run Routine "Feedback2_2"-------
            while continueRoutine and routineTimer.getTime() > 0:
                # get current time
                t = Feedback2_2Clock.getTime()
                tThisFlip = win.getFutureFlipTime(clock=Feedback2_2Clock)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # *text_7* updates
                if text_7.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    text_7.frameNStart = frameN  # exact frame index
                    text_7.tStart = t  # local t and not account for scr refresh
                    text_7.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(text_7, 'tStartRefresh')  # time at next scr refresh
                    text_7.setAutoDraw(True)
                if text_7.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > text_7.tStartRefresh + 1.0-frameTolerance:
                        # keep track of stop time/frame for later
                        text_7.tStop = t  # not accounting for scr refresh
                        text_7.frameNStop = frameN  # exact frame index
                        win.timeOnFlip(text_7, 'tStopRefresh')  # time at next scr refresh
                        text_7.setAutoDraw(False)
                
                # check for quit (typically the Esc key)
                if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
                    core.quit()
                
                # check if all components have finished
                if not continueRoutine:  # a component has requested a forced-end of Routine
                    break
                continueRoutine = False  # will revert to True if at least one component still running
                for thisComponent in Feedback2_2Components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # -------Ending Routine "Feedback2_2"-------
            for thisComponent in Feedback2_2Components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            trials_6.addData('text_7.started', text_7.tStartRefresh)
            trials_6.addData('text_7.stopped', text_7.tStopRefresh)
            thisExp.nextEntry()
            
        # completed nRepsFeedbackBPM repeats of 'trials_6'
        
        thisExp.nextEntry()
        
    # completed nRepsIntero repeats of 'trials_2'
    
    
    # set up handler to look after randomisation of conditions etc
    trials_3 = data.TrialHandler(nReps=nRepsExtero, method='random', 
        extraInfo=expInfo, originPath=-1,
        trialList=[None],
        seed=None, name='trials_3')
    thisExp.addLoop(trials_3)  # add the loop to the experiment
    thisTrial_3 = trials_3.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisTrial_3.rgb)
    if thisTrial_3 != None:
        for paramName in thisTrial_3:
            exec('{} = thisTrial_3[paramName]'.format(paramName))
    
    for thisTrial_3 in trials_3:
        currentLoop = trials_3
        # abbreviate parameter names if possible (e.g. rgb = thisTrial_3.rgb)
        if thisTrial_3 != None:
            for paramName in thisTrial_3:
                exec('{} = thisTrial_3[paramName]'.format(paramName))
        
        # ------Prepare to start Routine "Extero"-------
        continueRoutine = True
        routineTimer.add(5.000000)
        # update component parameters for each repeat
        alpha = stairCaseExtero.next()
        
        # Random selection of HR frequency
        average_hr = np.random.choice(np.arange(40, 100))
        hr = str(int(average_hr + alpha))
        
        file = os.path.join(os.getcwd(), 'sounds', hr + '.wav')
        sound_2.setSound(file, secs=5.0, hamming=True)
        sound_2.setVolume(1, log=False)
        # keep track of which components have finished
        ExteroComponents = [text_3, image_2, sound_2]
        for thisComponent in ExteroComponents:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        ExteroClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
        frameN = -1
        
        # -------Run Routine "Extero"-------
        while continueRoutine and routineTimer.getTime() > 0:
            # get current time
            t = ExteroClock.getTime()
            tThisFlip = win.getFutureFlipTime(clock=ExteroClock)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *text_3* updates
            if text_3.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                text_3.frameNStart = frameN  # exact frame index
                text_3.tStart = t  # local t and not account for scr refresh
                text_3.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(text_3, 'tStartRefresh')  # time at next scr refresh
                text_3.setAutoDraw(True)
            if text_3.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > text_3.tStartRefresh + 5.0-frameTolerance:
                    # keep track of stop time/frame for later
                    text_3.tStop = t  # not accounting for scr refresh
                    text_3.frameNStop = frameN  # exact frame index
                    win.timeOnFlip(text_3, 'tStopRefresh')  # time at next scr refresh
                    text_3.setAutoDraw(False)
            
            # *image_2* updates
            if image_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                image_2.frameNStart = frameN  # exact frame index
                image_2.tStart = t  # local t and not account for scr refresh
                image_2.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(image_2, 'tStartRefresh')  # time at next scr refresh
                image_2.setAutoDraw(True)
            if image_2.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > image_2.tStartRefresh + 5.0-frameTolerance:
                    # keep track of stop time/frame for later
                    image_2.tStop = t  # not accounting for scr refresh
                    image_2.frameNStop = frameN  # exact frame index
                    win.timeOnFlip(image_2, 'tStopRefresh')  # time at next scr refresh
                    image_2.setAutoDraw(False)
            oxiTask.readInWaiting()
            
            # start/stop sound_2
            if sound_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                sound_2.frameNStart = frameN  # exact frame index
                sound_2.tStart = t  # local t and not account for scr refresh
                sound_2.tStartRefresh = tThisFlipGlobal  # on global time
                sound_2.play(when=win)  # sync with win flip
            if sound_2.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > sound_2.tStartRefresh + 5.0-frameTolerance:
                    # keep track of stop time/frame for later
                    sound_2.tStop = t  # not accounting for scr refresh
                    sound_2.frameNStop = frameN  # exact frame index
                    win.timeOnFlip(sound_2, 'tStopRefresh')  # time at next scr refresh
                    sound_2.stop()
            
            # check for quit (typically the Esc key)
            if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
                core.quit()
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in ExteroComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # -------Ending Routine "Extero"-------
        for thisComponent in ExteroComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        trials_3.addData('text_3.started', text_3.tStartRefresh)
        trials_3.addData('text_3.stopped', text_3.tStopRefresh)
        trials_3.addData('image_2.started', image_2.tStartRefresh)
        trials_3.addData('image_2.stopped', image_2.tStopRefresh)
        sound_2.stop()  # ensure sound has stopped at end of routine
        trials_3.addData('sound_2.started', sound_2.tStartRefresh)
        trials_3.addData('sound_2.stopped', sound_2.tStopRefresh)
        thisExp.nextEntry()
        
    # completed nRepsExtero repeats of 'trials_3'
    
    
    # ------Prepare to start Routine "fixCross2"-------
    continueRoutine = True
    # update component parameters for each repeat
    jitter = np.arange(0, 2, .1)
    shuffle(jitter)
    # keep track of which components have finished
    fixCross2Components = [fiCross2]
    for thisComponent in fixCross2Components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    fixCross2Clock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
    frameN = -1
    
    # -------Run Routine "fixCross2"-------
    while continueRoutine:
        # get current time
        t = fixCross2Clock.getTime()
        tThisFlip = win.getFutureFlipTime(clock=fixCross2Clock)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *fiCross2* updates
        if fiCross2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            fiCross2.frameNStart = frameN  # exact frame index
            fiCross2.tStart = t  # local t and not account for scr refresh
            fiCross2.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(fiCross2, 'tStartRefresh')  # time at next scr refresh
            fiCross2.setAutoDraw(True)
        if fiCross2.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > fiCross2.tStartRefresh + jitter[0]-frameTolerance:
                # keep track of stop time/frame for later
                fiCross2.tStop = t  # not accounting for scr refresh
                fiCross2.frameNStop = frameN  # exact frame index
                win.timeOnFlip(fiCross2, 'tStopRefresh')  # time at next scr refresh
                fiCross2.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
            core.quit()
        
        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in fixCross2Components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "fixCross2"-------
    for thisComponent in fixCross2Components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    trials.addData('fiCross2.started', fiCross2.tStartRefresh)
    trials.addData('fiCross2.stopped', fiCross2.tStopRefresh)
    # the Routine "fixCross2" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # ------Prepare to start Routine "Decision"-------
    continueRoutine = True
    routineTimer.add(5.000000)
    # update component parameters for each repeat
    # setup some python lists for storing info about the mouse
    mouse.x = []
    mouse.y = []
    mouse.leftButton = []
    mouse.midButton = []
    mouse.rightButton = []
    mouse.time = []
    gotValidClick = False  # until a click is received
    mouse.mouseClock.reset()
    sound_1.setSound(file, secs=5.0, hamming=True)
    sound_1.setVolume(1, log=False)
    colorLess, colorMore = 'white', 'white'
    estimation = None
    # keep track of which components have finished
    DecisionComponents = [mouse, sound_1, textDecision, image, text_Less, text_More]
    for thisComponent in DecisionComponents:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    DecisionClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
    frameN = -1
    
    # -------Run Routine "Decision"-------
    while continueRoutine and routineTimer.getTime() > 0:
        # get current time
        t = DecisionClock.getTime()
        tThisFlip = win.getFutureFlipTime(clock=DecisionClock)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        # *mouse* updates
        if mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            mouse.frameNStart = frameN  # exact frame index
            mouse.tStart = t  # local t and not account for scr refresh
            mouse.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(mouse, 'tStartRefresh')  # time at next scr refresh
            mouse.status = STARTED
            prevButtonState = mouse.getPressed()  # if button is down already this ISN'T a new click
        if mouse.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > mouse.tStartRefresh + 5.0-frameTolerance:
                # keep track of stop time/frame for later
                mouse.tStop = t  # not accounting for scr refresh
                mouse.frameNStop = frameN  # exact frame index
                win.timeOnFlip(mouse, 'tStopRefresh')  # time at next scr refresh
                mouse.status = FINISHED
        if mouse.status == STARTED:  # only update if started and not finished!
            buttons = mouse.getPressed()
            if buttons != prevButtonState:  # button state changed?
                prevButtonState = buttons
                if sum(buttons) > 0:  # state changed to a new click
                    x, y = mouse.getPos()
                    mouse.x.append(x)
                    mouse.y.append(y)
                    buttons = mouse.getPressed()
                    mouse.leftButton.append(buttons[0])
                    mouse.midButton.append(buttons[1])
                    mouse.rightButton.append(buttons[2])
                    mouse.time.append(mouse.mouseClock.getTime())
        # start/stop sound_1
        if sound_1.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            sound_1.frameNStart = frameN  # exact frame index
            sound_1.tStart = t  # local t and not account for scr refresh
            sound_1.tStartRefresh = tThisFlipGlobal  # on global time
            sound_1.play(when=win)  # sync with win flip
        if sound_1.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > sound_1.tStartRefresh + 5.0-frameTolerance:
                # keep track of stop time/frame for later
                sound_1.tStop = t  # not accounting for scr refresh
                sound_1.frameNStop = frameN  # exact frame index
                win.timeOnFlip(sound_1, 'tStopRefresh')  # time at next scr refresh
                sound_1.stop()
        
        # *textDecision* updates
        if textDecision.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            textDecision.frameNStart = frameN  # exact frame index
            textDecision.tStart = t  # local t and not account for scr refresh
            textDecision.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(textDecision, 'tStartRefresh')  # time at next scr refresh
            textDecision.setAutoDraw(True)
        if textDecision.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > textDecision.tStartRefresh + 5.0-frameTolerance:
                # keep track of stop time/frame for later
                textDecision.tStop = t  # not accounting for scr refresh
                textDecision.frameNStop = frameN  # exact frame index
                win.timeOnFlip(textDecision, 'tStopRefresh')  # time at next scr refresh
                textDecision.setAutoDraw(False)
        
        # *image* updates
        if image.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            image.frameNStart = frameN  # exact frame index
            image.tStart = t  # local t and not account for scr refresh
            image.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(image, 'tStartRefresh')  # time at next scr refresh
            image.setAutoDraw(True)
        if image.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > image.tStartRefresh + 5.0-frameTolerance:
                # keep track of stop time/frame for later
                image.tStop = t  # not accounting for scr refresh
                image.frameNStop = frameN  # exact frame index
                win.timeOnFlip(image, 'tStopRefresh')  # time at next scr refresh
                image.setAutoDraw(False)
        oxiTask.readInWaiting()
        
        
        # *text_Less* updates
        if text_Less.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            text_Less.frameNStart = frameN  # exact frame index
            text_Less.tStart = t  # local t and not account for scr refresh
            text_Less.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(text_Less, 'tStartRefresh')  # time at next scr refresh
            text_Less.setAutoDraw(True)
        if text_Less.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > text_Less.tStartRefresh + 5.0-frameTolerance:
                # keep track of stop time/frame for later
                text_Less.tStop = t  # not accounting for scr refresh
                text_Less.frameNStop = frameN  # exact frame index
                win.timeOnFlip(text_Less, 'tStopRefresh')  # time at next scr refresh
                text_Less.setAutoDraw(False)
        if text_Less.status == STARTED:  # only update if drawing
            text_Less.setColor(colorLess, colorSpace='rgb', log=False)
        
        # *text_More* updates
        if text_More.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            text_More.frameNStart = frameN  # exact frame index
            text_More.tStart = t  # local t and not account for scr refresh
            text_More.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(text_More, 'tStartRefresh')  # time at next scr refresh
            text_More.setAutoDraw(True)
        if text_More.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > text_More.tStartRefresh + 5.0-frameTolerance:
                # keep track of stop time/frame for later
                text_More.tStop = t  # not accounting for scr refresh
                text_More.frameNStop = frameN  # exact frame index
                win.timeOnFlip(text_More, 'tStopRefresh')  # time at next scr refresh
                text_More.setAutoDraw(False)
        if text_More.status == STARTED:  # only update if drawing
            text_More.setColor(colorMore, colorSpace='rgb', log=False)
        if mouse.leftButton == [1]:
            estimation = 'Less'
            colorLess = 'blue'
        elif mouse.rightButton == [1]:
            estimation = 'More'
            colorMore = 'blue'
        
        # check for quit (typically the Esc key)
        if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
            core.quit()
        
        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in DecisionComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "Decision"-------
    for thisComponent in DecisionComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store data for trials (TrialHandler)
    if len(mouse.x): trials.addData('mouse.x', mouse.x[0])
    if len(mouse.y): trials.addData('mouse.y', mouse.y[0])
    if len(mouse.leftButton): trials.addData('mouse.leftButton', mouse.leftButton[0])
    if len(mouse.midButton): trials.addData('mouse.midButton', mouse.midButton[0])
    if len(mouse.rightButton): trials.addData('mouse.rightButton', mouse.rightButton[0])
    if len(mouse.time): trials.addData('mouse.time', mouse.time[0])
    trials.addData('mouse.started', mouse.tStart)
    trials.addData('mouse.stopped', mouse.tStop)
    sound_1.stop()  # ensure sound has stopped at end of routine
    trials.addData('sound_1.started', sound_1.tStartRefresh)
    trials.addData('sound_1.stopped', sound_1.tStopRefresh)
    trials.addData('textDecision.started', textDecision.tStartRefresh)
    trials.addData('textDecision.stopped', textDecision.tStopRefresh)
    trials.addData('image.started', image.tStartRefresh)
    trials.addData('image.stopped', image.tStopRefresh)
    # Is the answer Correct? Update the staircase model
    if estimation is not None:
        if (estimation == 'More') & (alpha > 0):
            stairCaseIntero.addResponse(1)
            accuracy = 1
        elif (estimation == 'Less') & (alpha < 0):
            stairCaseIntero.addResponse(1)
            accuracy = 1
        else:
            stairCaseIntero.addResponse(0)
            accuracy = 0
        nRepsRatingScale = 1
        nRepsFeeback = 0
        correct = ['True' if accuracy==1 else 'False']
        print(f'Initial BPM: {average_hr} - Staircase value: {alpha} - Response: {estimation} ({correct}) - Condition: {condition}')
    else:
        nRepsRatingScale = 0
        nRepsFeeback = 1
        print('No response provided')
    trials.addData('text_Less.started', text_Less.tStartRefresh)
    trials.addData('text_Less.stopped', text_Less.tStopRefresh)
    trials.addData('text_More.started', text_More.tStartRefresh)
    trials.addData('text_More.stopped', text_More.tStopRefresh)
    
    # set up handler to look after randomisation of conditions etc
    trials_5 = data.TrialHandler(nReps=nRepsRatingScale, method='random', 
        extraInfo=expInfo, originPath=-1,
        trialList=[None],
        seed=None, name='trials_5')
    thisExp.addLoop(trials_5)  # add the loop to the experiment
    thisTrial_5 = trials_5.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisTrial_5.rgb)
    if thisTrial_5 != None:
        for paramName in thisTrial_5:
            exec('{} = thisTrial_5[paramName]'.format(paramName))
    
    for thisTrial_5 in trials_5:
        currentLoop = trials_5
        # abbreviate parameter names if possible (e.g. rgb = thisTrial_5.rgb)
        if thisTrial_5 != None:
            for paramName in thisTrial_5:
                exec('{} = thisTrial_5[paramName]'.format(paramName))
        
        # ------Prepare to start Routine "RatingScale"-------
        continueRoutine = True
        routineTimer.add(3.000000)
        # update component parameters for each repeat
        rating.reset()
        # keep track of which components have finished
        RatingScaleComponents = [rating]
        for thisComponent in RatingScaleComponents:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        RatingScaleClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
        frameN = -1
        
        # -------Run Routine "RatingScale"-------
        while continueRoutine and routineTimer.getTime() > 0:
            # get current time
            t = RatingScaleClock.getTime()
            tThisFlip = win.getFutureFlipTime(clock=RatingScaleClock)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # *rating* updates
            if rating.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                rating.frameNStart = frameN  # exact frame index
                rating.tStart = t  # local t and not account for scr refresh
                rating.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(rating, 'tStartRefresh')  # time at next scr refresh
                rating.setAutoDraw(True)
            continueRoutine &= rating.noResponse  # a response ends the trial
            oxiTask.readInWaiting()
            
            
            # check for quit (typically the Esc key)
            if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
                core.quit()
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in RatingScaleComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # -------Ending Routine "RatingScale"-------
        for thisComponent in RatingScaleComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store data for trials_5 (TrialHandler)
        trials_5.addData('rating.response', rating.getRating())
        trials_5.addData('rating.rt', rating.getRT())
        trials_5.addData('rating.history', rating.getHistory())
        trials_5.addData('rating.started', rating.tStart)
        trials_5.addData('rating.stopped', rating.tStop)
        if condition == 'Intero':
        
            thisExp.addData('accuracy', accuracy)
            thisExp.addData('AverageHR', average_hr)
        
            # Save physio signal
            this_df = pd.DataFrame({'signal': signal,
                                     'nTrial': pd.Series([trials.thisN] * len(signal), dtype="category")})
        
            signal_df = signal_df.append(this_df,
                                         ignore_index=True)
        thisExp.nextEntry()
        
    # completed nRepsRatingScale repeats of 'trials_5'
    
    
    # set up handler to look after randomisation of conditions etc
    trials_4 = data.TrialHandler(nReps=nRepsFeeback, method='random', 
        extraInfo=expInfo, originPath=-1,
        trialList=[None],
        seed=None, name='trials_4')
    thisExp.addLoop(trials_4)  # add the loop to the experiment
    thisTrial_4 = trials_4.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisTrial_4.rgb)
    if thisTrial_4 != None:
        for paramName in thisTrial_4:
            exec('{} = thisTrial_4[paramName]'.format(paramName))
    
    for thisTrial_4 in trials_4:
        currentLoop = trials_4
        # abbreviate parameter names if possible (e.g. rgb = thisTrial_4.rgb)
        if thisTrial_4 != None:
            for paramName in thisTrial_4:
                exec('{} = thisTrial_4[paramName]'.format(paramName))
        
        # ------Prepare to start Routine "Feedback"-------
        continueRoutine = True
        routineTimer.add(2.000000)
        # update component parameters for each repeat
        # keep track of which components have finished
        FeedbackComponents = [text_4]
        for thisComponent in FeedbackComponents:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        FeedbackClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
        frameN = -1
        
        # -------Run Routine "Feedback"-------
        while continueRoutine and routineTimer.getTime() > 0:
            # get current time
            t = FeedbackClock.getTime()
            tThisFlip = win.getFutureFlipTime(clock=FeedbackClock)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *text_4* updates
            if text_4.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                text_4.frameNStart = frameN  # exact frame index
                text_4.tStart = t  # local t and not account for scr refresh
                text_4.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(text_4, 'tStartRefresh')  # time at next scr refresh
                text_4.setAutoDraw(True)
            if text_4.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > text_4.tStartRefresh + 2.0-frameTolerance:
                    # keep track of stop time/frame for later
                    text_4.tStop = t  # not accounting for scr refresh
                    text_4.frameNStop = frameN  # exact frame index
                    win.timeOnFlip(text_4, 'tStopRefresh')  # time at next scr refresh
                    text_4.setAutoDraw(False)
            
            # check for quit (typically the Esc key)
            if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
                core.quit()
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in FeedbackComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # -------Ending Routine "Feedback"-------
        for thisComponent in FeedbackComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        trials_4.addData('text_4.started', text_4.tStartRefresh)
        trials_4.addData('text_4.stopped', text_4.tStopRefresh)
        thisExp.nextEntry()
        
    # completed nRepsFeeback repeats of 'trials_4'
    
    thisExp.nextEntry()
    
# completed 1 repeats of 'trials'


# ------Prepare to start Routine "endScreen"-------
continueRoutine = True
routineTimer.add(1.000000)
# update component parameters for each repeat
# keep track of which components have finished
endScreenComponents = [text]
for thisComponent in endScreenComponents:
    thisComponent.tStart = None
    thisComponent.tStop = None
    thisComponent.tStartRefresh = None
    thisComponent.tStopRefresh = None
    if hasattr(thisComponent, 'status'):
        thisComponent.status = NOT_STARTED
# reset timers
t = 0
_timeToFirstFrame = win.getFutureFlipTime(clock="now")
endScreenClock.reset(-_timeToFirstFrame)  # t0 is time of first possible flip
frameN = -1

# -------Run Routine "endScreen"-------
while continueRoutine and routineTimer.getTime() > 0:
    # get current time
    t = endScreenClock.getTime()
    tThisFlip = win.getFutureFlipTime(clock=endScreenClock)
    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
    # update/draw components on each frame
    
    # *text* updates
    if text.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
        # keep track of start time/frame for later
        text.frameNStart = frameN  # exact frame index
        text.tStart = t  # local t and not account for scr refresh
        text.tStartRefresh = tThisFlipGlobal  # on global time
        win.timeOnFlip(text, 'tStartRefresh')  # time at next scr refresh
        text.setAutoDraw(True)
    if text.status == STARTED:
        # is it time to stop? (based on global clock, using actual start)
        if tThisFlipGlobal > text.tStartRefresh + 1.0-frameTolerance:
            # keep track of stop time/frame for later
            text.tStop = t  # not accounting for scr refresh
            text.frameNStop = frameN  # exact frame index
            win.timeOnFlip(text, 'tStopRefresh')  # time at next scr refresh
            text.setAutoDraw(False)
    
    # check for quit (typically the Esc key)
    if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
        core.quit()
    
    # check if all components have finished
    if not continueRoutine:  # a component has requested a forced-end of Routine
        break
    continueRoutine = False  # will revert to True if at least one component still running
    for thisComponent in endScreenComponents:
        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
            continueRoutine = True
            break  # at least one component has not yet finished
    
    # refresh the screen
    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
        win.flip()

# -------Ending Routine "endScreen"-------
for thisComponent in endScreenComponents:
    if hasattr(thisComponent, "setAutoDraw"):
        thisComponent.setAutoDraw(False)
thisExp.addData('text.started', text.tStartRefresh)
thisExp.addData('text.stopped', text.tStopRefresh)
stairCaseIntero.saveAsExcel(expInfo['participant'])
stairCaseIntero.saveAsPickle(expInfo['participant'])

stairCaseExtero.saveAsExcel(expInfo['participant'])
stairCaseExtero.saveAsPickle(expInfo['participant'])
# group by participant folder: data/JWP/memoryTask-2014_Feb_15_1648
out_path = 'data/%s/%s-%s' %(expInfo['participant'], expName, expInfo['date'])

signal_df.to_csv(out_path + 'signal.txt')

try:
    stairCaseIntero.savePosterior(out_path)
    stairCaseIntero.saveAsPickle(out_path)
    stairCaseIntero.saveAsJson(out_path)
    stairCaseIntero.saveAsText(out_path)
except:
    print('No staircaseIntero provided')

try:
    stairCaseExtero.savePosterior(out_path)
    stairCaseExtero.saveAsPickle(out_path)
    stairCaseExtero.saveAsJson(out_path)
    stairCaseExtero.saveAsText(out_path)
except:
    print('No staircaseExtero provided')

# Flip one final time so any remaining win.callOnFlip() 
# and win.timeOnFlip() tasks get executed before quitting
win.flip()

# these shouldn't be strictly necessary (should auto-save)
thisExp.saveAsWideText(filename+'.csv')
thisExp.saveAsPickle(filename)
logging.flush()
# make sure everything is closed down
thisExp.abort()  # or data files will save again on exit
win.close()
core.quit()
