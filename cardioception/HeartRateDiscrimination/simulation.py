import time
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from psychopy import data
from scipy.stats import weibull_min, norm

plt.plot(np.linspace(-40.5, 40.5, 100),
         weibull_min.cdf(np.linspace(-40.5, 40.5, 100), c=2, loc=0, scale=15))
plt.axvline(x=0)

intensityVals = np.arange(0, 40.5)
thresholdVals = np.arange(0, 40.5)
slopeVals = np.arange(0, 5, 0.2)
lapseRateVals = np.arange(.01, 1, 0.05)
lowerAsymptoteVals = np.arange(0.01, .1, 0.01)

# Create staricase
staircase = data.QuestPlusHandler(
                nTrials=100, responseVals=(1, 0),
                intensityVals=intensityVals,
                thresholdVals=thresholdVals,
                slopeVals=slopeVals,
                lapseRateVals=lapseRateVals,
                lowerAsymptoteVals=lowerAsymptoteVals)
trials = np.arange(0, 50)

posteriorThreshold = []
res, ol_thr, ol_sl = [], [], []
for i in trials:
    ol_thr.append(staircase.paramEstimate['threshold'])
    ol_sl.append(staircase.paramEstimate['slope'])
    posteriorThreshold.append(staircase.posterior['threshold'])
    # Generate response
    proba_true = (norm.cdf(staircase.next(), loc=15, scale=5))
    res.append(np.random.choice([1, 0], p=[proba_true, 1-proba_true]))

    # Update staricase
    staircase.addResponse(res[-1])

    print(f'New theshold: {ol_thr[-1]} - New slope: {ol_sl[-1]}')




% ## Posteriors
plt.figure(figsize=(12, 6))
plt.subplot(221)
plt.plot(thresholdVals, staircase.posterior['threshold'], color='gray')
plt.fill_between(thresholdVals, staircase.posterior['threshold'], color='b', alpha=.3)
plt.title('Threshold')
plt.subplot(222)
plt.plot(slopeVals, staircase.posterior['slope'], color='gray')
plt.fill_between(slopeVals, staircase.posterior['slope'], color='r', alpha=.3)
plt.title('Slope')
plt.subplot(223)
plt.plot(lapseRateVals, staircase.posterior['lapseRate'], color='gray')
plt.fill_between(lapseRateVals, staircase.posterior['lapseRate'], color='g', alpha=.3)
plt.title('Lapse Rate')
plt.subplot(224)
plt.plot(lowerAsymptoteVals, staircase.posterior['lowerAsymptote'], color='gray')
plt.fill_between(lowerAsymptoteVals, staircase.posterior['lowerAsymptote'], color='y', alpha=.3)
plt.title('Lower Asymptote')
sns.despine()
plt.tight_layout()



sns.set_context('talk')
plt.figure(figsize=(11, 5))
plt.axhline(y=0, linestyle='-', color='k')
plt.plot(trials, staircase.intensities, '--', color='gray')
plt.plot(trials, ol_thr, '-', color='k')
plt.plot(trials[np.where(np.asarray(res) == 1)[0]],
                np.array(staircase.intensities)[np.where(np.asarray(res)==1)[0]],
         'bo', alpha=0.6, markeredgecolor='k')
plt.plot(trials[np.where(np.asarray(res) == 0)[0]],
                np.array(staircase.intensities)[np.where(np.asarray(res)==0)[0]],
          'ro', alpha=0.6, markeredgecolor='k')
plt.ylabel('Stimulus intensity (BPM)')
plt.xlabel('Trials')
plt.ylim(-30, 30)
plt.title('QUEST - Theshold')
