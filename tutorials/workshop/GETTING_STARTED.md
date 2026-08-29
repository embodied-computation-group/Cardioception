# Python setup for participants who mainly use R

This page introduces the few Python and Jupyter concepts used in
[PREINSTALL.md](PREINSTALL.md). It is not a general Python tutorial, and the workshop
does not assume that you can write Python code independently.

## The terminal

The terminal accepts commands for the operating system, much as the R console accepts
commands for R.

| System | How to open it |
|---|---|
| macOS | Press Command+Space, type `Terminal`, and press Enter |
| Windows | Open the Start menu and search for `PowerShell` |
| Linux | Press Ctrl+Alt+T on many desktop environments |

RStudio’s Terminal tab is also suitable. When documentation displays `$` or `>` before
a command, that symbol represents the prompt and should not be typed.

## Python interpreters

A computer can contain several Python installations. The command `python` or `python3`
selects one of them according to the system `PATH`. Cardioception requires Python 3.10
or 3.11.

The workshop instructions use explicit paths such as
`./cardioception-env/bin/python`. This states exactly which interpreter should run the
command and which package library it should use.

You can inspect the interpreter selected by the shell with:

```bash
which python3       # macOS or Linux
where.exe python    # Windows PowerShell
```

## Installing Python packages

`pip` installs packages from [PyPI](https://pypi.org/), which serves a role similar to
CRAN. The rough R equivalent is:

| Python | R |
|---|---|
| `python -m pip install package` | `install.packages("package")` |
| `import package` | `library(package)` |

For this project, the installation name and import name differ:

| Use | Name |
|---|---|
| Install from PyPI | `cardioception-toolbox` |
| Import in Python | `cardioception` |

The distribution named only `cardioception` on PyPI is a different package.

## Virtual environments

A virtual environment is a project-specific Python interpreter and package library.
It keeps Cardioception’s dependencies separate from other Python projects.

```bash
python3 -m venv cardioception-env
```

This creates a directory containing its own Python executable. The closest R analogue
is an `renv` project library. Removing the environment directory removes the installed
packages without changing the system Python.

Python guides often activate an environment before use. The workshop instead calls
the executable by its full path:

```bash
./cardioception-env/bin/python -m pip install cardioception-toolbox
```

Both approaches are valid. Explicit paths are useful here because they remain clear
when several Python or conda installations are present.

## JupyterLab, notebooks, and kernels

A notebook contains text cells and executable code cells. JupyterLab is the local
application used to open and run it. It displays in a browser, but the code and data
remain on your computer.

The kernel is the language process that executes a notebook. This workshop uses two:

| Notebook | Kernel |
|---|---|
| `01_running_the_hrd.ipynb` | Python (cardioception) |
| `02_analysing_the_hrd.ipynb` | R (cardioception) |
| `03_power_analysis.ipynb` | R (cardioception) |

The kernel name appears near the upper-right corner of an open notebook. If it is
incorrect, click the name and select the required kernel.

From `tutorials/workshop`, start JupyterLab with:

```bash
../../cardioception-env/bin/jupyter lab
```

Stop the JupyterLab server by returning to the terminal and pressing Ctrl+C twice.

## Running a notebook

- Shift+Enter runs the selected cell and moves to the next one.
- Cells share an active session, so run them in order from the top.
- `[*]` beside a cell means that it is still running.
- Editing a completed cell does not undo its earlier effects.
- If the state becomes unclear, restart the kernel, clear the outputs, and run again
  from the first cell.

## Diagnosing two common problems

If a package was installed but the notebook cannot import it, the installation and the
notebook are probably using different Python interpreters. Confirm that the kernel is
**Python (cardioception)** and run:

```python
import sys
print(sys.executable)
```

If the R kernel is absent, R may be installed correctly but not registered with the
same Jupyter installation. Repeat the `IRkernel::installspec()` command in
[PREINSTALL.md](PREINSTALL.md), then restart JupyterLab.

For a general introduction, see the
[JupyterLab interface guide](https://jupyterlab.readthedocs.io/en/stable/user/interface.html)
or [Real Python’s virtual-environment guide](https://realpython.com/python-virtual-environments-a-primer/).
