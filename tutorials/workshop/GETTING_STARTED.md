# Never used Python before? Start here

**Read this only if the commands in [PREINSTALL.md](PREINSTALL.md) look like magic.**
If you already work in Python, skip it — there is nothing here you do not know.

This page does not teach you Python. It explains the five ideas you need to get the
workshop environment running, and points you at the good existing guides for everything
else. You will write essentially no Python at the workshop: the notebooks are already
written, and you run them.

Most of you know R. So each idea below is given with its R equivalent, which is usually
the fastest way in.

---

## The five ideas

### 1. The terminal

A window where you type commands instead of clicking. Every install instruction assumes
you have one open.

| | How to open it |
|---|---|
| **macOS** | Cmd+Space, type `Terminal`, Enter |
| **Windows** | Start menu, type `PowerShell`, Enter |
| **Linux** | Ctrl+Alt+T |

*R equivalent:* the RStudio Console, except it talks to your operating system rather than
to R. If you have used RStudio's **Terminal** tab, that is exactly this.

When a guide shows a line starting with `$` or `>`, that is the prompt — do not type it.

New to this? [Ubuntu's terminal overview](https://ubuntu.com/tutorials/command-line-for-beginners)
is short and applies almost unchanged to macOS.

### 2. Python, and *a* Python

R is one thing you install once. Python is not: a machine can have several Pythons, and
which one you get when you type `python` depends on your PATH. This is the single biggest
source of confusion for people arriving from R.

This is why the workshop instructions write out full paths like
`./cardioception-env/bin/python` instead of just `python`. It removes all ambiguity about
which interpreter is running.

**We need Python 3.10 or 3.11 specifically** — PsychoPy's dependencies do not build on
newer versions.

Install it from [python.org/downloads](https://www.python.org/downloads/). If you want
hand-holding, [Real Python's installation guide](https://realpython.com/installing-python/)
covers every platform properly and is better than anything we would write here.

### 3. `pip` — installing packages

`pip install X` is Python's `install.packages("X")`.

Packages come from [PyPI](https://pypi.org), which is Python's CRAN. It is less curated
than CRAN: **check you are installing the name you were given.** For us that is
`cardioception-toolbox`.

### 4. Virtual environments — the one genuinely new idea

R installs packages into one shared library, and mostly gets away with it. Python
projects conflict more, so the convention is to give each project its own private folder
of packages, called a **virtual environment**.

```bash
python3 -m venv cardioception-env
```

That creates a folder `cardioception-env/` containing its own Python and its own
packages. Nothing is installed system-wide, and deleting the folder removes everything
cleanly — which is also your escape hatch if the install goes wrong. Just delete it and
start Step 2 again.

*R equivalent:* [`renv`](https://rstudio.github.io/renv/), if you have met it.

Guides usually tell you to "activate" the environment. We deliberately do not, and use
full paths instead, because activation is where people lose an hour to a shell alias
silently pointing `python` somewhere else.

If you want the concept properly:
[Real Python on virtual environments](https://realpython.com/python-virtual-environments-a-primer/).

### 5. Jupyter, notebooks, and kernels

A **notebook** is a document of alternating text and code cells that you run one at a
time, seeing the output under each. *R equivalent:* an R Markdown or Quarto document, run
interactively.

**JupyterLab** is the app you open notebooks in. It runs in your browser but everything is
local — nothing is uploaded anywhere.

A **kernel** is the language process running behind a notebook. This matters here because
the workshop uses two:

| Notebook | Kernel | Why |
|---|---|---|
| `01_running_the_hrd.ipynb` | Python (cardioception) | The task is a PsychoPy program |
| `02_analysing_the_hrd.ipynb` | R (cardioception) | The models are `brms` models |

Same app, same browser tab, different language behind the cells. The kernel name shows in
the **top right** of an open notebook — if it says something else, click it and choose the
right one. Registering these two kernels is what the `ipykernel install` and
`IRkernel::installspec` lines in PREINSTALL do.

Start JupyterLab with:

```bash
/path/to/cardioception-env/bin/jupyter lab
```

It opens a browser tab. To stop it, press Ctrl+C twice in the terminal.

---

## Running a notebook, briefly

- **Shift+Enter** runs the current cell and moves to the next
- Cells share state, so **run them in order, top to bottom**
- `[*]` beside a cell means still running; a number means finished
- If things get confused: **Kernel → Restart Kernel and Clear Outputs**, then run from the top
- Editing a cell does not undo what it already did — the restart is how you get a clean slate

The [JupyterLab interface tour](https://jupyterlab.readthedocs.io/en/stable/user/interface.html)
covers the rest.

---

## Three confusions worth pre-empting

**"Which Python am I using?"** Run `which python3` (macOS/Linux) or `where python`
(Windows). If the answer surprises you, that is the problem. Use full paths.

**"I installed it but the notebook says it is missing."** You installed into one Python and
the notebook is running another. Check the kernel name in the top right — it must be
**Python (cardioception)**, not plain "Python 3".

**"Do I need RStudio?"** No. Both notebooks run in JupyterLab. R must be installed, but you
never have to open RStudio — though you can use it for the R packages in Step 3 if you
find that more comfortable.

---

## If it goes wrong

1. Run `preflight.py` (Step 5 of PREINSTALL) — it names the problem and the fix
2. Delete the `cardioception-env` folder and redo Step 2. This is cheap and fixes most things
3. Send the preflight output to the organiser and come 15 minutes early

**Do not spend more than 30 minutes on this alone.** Every part of the workshop has a
fallback, and arriving with a half-working setup is completely fine.

---

## Worth reading afterwards, not before

- [The Cardioception documentation](https://www.the-ecg.org/Cardioception/)
- [PsychoPy's Coder tutorials](https://www.psychopy.org/coder/index.html) — if you want to build experiments
- [Real Python](https://realpython.com/) — the best general Python reference for scientists
