# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import papermill as pm
import subprocess
import os

dataPath = 'C:/Users/au646069/Downloads/ECG/1_VPN_aux'
subjects = os.listdir(dataPath)
notebookTemplate = 'C:/Users/au646069/github/Cardioception/notebooks/HeartRateDiscrimination.ipynb'
sub = 'sub_0019'
reportsPath = 'C:/Users/au646069/Downloads/ECG/6_reports/HRD/'

for sub in subjects:

    try:
        pm.execute_notebook(
           notebookTemplate,
           reportsPath + sub + '.ipynb',
           parameters=dict(subject=sub, path=dataPath)
        )

        command = f'jupyter nbconvert {reportsPath}{sub}.ipynb --output {reportsPath}{sub}_report.html --no-input'
        subprocess.call(command)
    except:
        print('Files missing')
