import papermill as pm
import subprocess
import os

path = 'C:/Users/au646069/Downloads/Reports/'

for sub in os.listdir(os.path.join(os.getcwd(), 'data')):

    pm.execute_notebook(
       'Analyses.ipynb',
       'C:/Users/au646069/Downloads/Reports/' + sub + '.ipynb',
       parameters = dict(subject=sub)
    )

    command = f'jupyter nbconvert {path}{sub}.ipynb --output {path}{sub}_report.html --no-input'
    subprocess.call(command)