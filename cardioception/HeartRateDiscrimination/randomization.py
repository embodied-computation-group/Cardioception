import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

prob = (np.sin(np.arange(0, 45*60) * 2 * np.pi * (1/180)) + 1)/2

condList, condVal = [0, 0, 0], []
plt.figure(figsize=(13, 5))
for i in np.arange(14, 45*60, 14):
    p = prob[i-14:i].mean()
    if (condList[-1] == 'Intero') & (condList[-2] == 'Intero') & (condList[-3] == 'Intero'):
        cond = 'Extero'
    elif (condList[-1] == 'Extero') & (condList[-2] == 'Extero') & (condList[-3] == 'Extero'):
        cond = 'Intero'
    else:
        cond = np.random.choice(['Intero', 'Extero'], p=[p, 1-p])
    condList.append(cond)
    condVal.extend([p] * 14)

condList = condList[3:]
plt.subplot(211)
plt.plot(np.array(condList) == 'Intero', 'bo-', alpha=.5)
#plt.plot(np.array(condList) == 'Extero', 'ro', alpha=.5)
plt.subplot(212)
plt.fill_between(y1=condVal, x=np.arange(0, len(condVal))/60)

pd.DataFrame({'condtion': condList}).to_csv('randomzedConditions.txt')
