# AGENTS.md

Guidance for AI coding agents working in this repository. Human contributors may find
it useful too, but the audience is agents.

## What this project is

Cardioception is a Python package that runs two psychophysical tasks in PsychoPy:

- **Heart Rate Discrimination task (HRD)** — the primary task. Participants judge
  whether tones are faster or slower than their own heart, under an adaptive staircase.
- **Heartbeat Counting task (HBC)** — the classic counting task, kept because the
  literature rests on it. Not recommended for new studies.

The package **collects** data. It does not analyse it. Modelling happens in R with the
[Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception).

## Naming, and a trap

| Thing | Value |
|---|---|
| PyPI distribution | `cardioception-toolbox` |
| Python import name | `cardioception` |

These differ deliberately. `pip install cardioception` installs a **different,
third-party package**. Any instruction, script, environment file or doc that says
`pip install cardioception` is a bug. Never "fix" `cardioception-toolbox` back to
`cardioception` in an install command.

## Layout

```
cardioception/
  HRD/          the Heart Rate Discrimination task (parameters.py, task.py)
  HBC/          the Heartbeat Counting task
  notebooks/    report templates executed by reports.report()
  reports.py    preprocessing and HTML reports (legacy, due to be rebuilt)
  _resources.py locates bundled images and sounds
docs/source/    Sphinx documentation (MyST markdown, furo theme)
R_analysis/     legacy R scripts, maintained for existing pipelines
wrappers/       example run scripts for the tasks
tests/
```

## Conventions

- Sentence case headings in documentation. No decorative emoji anywhere.
- No em dashes or en dashes in prose. Page ranges inside citations keep theirs.
- Spelling: US for the `-ize`/`-yze` family (`analyze`, `visualization`), British for
  `-our` and `modelling`/`behavioural`. This matches the existing code and notebooks.
  `setup='behavioral'` is a code literal, not prose. Do not change it.
- Python is formatted with black, imports sorted with isort, and checked with flake8
  and mypy. Linting runs on **Python 3.8**, so do not use 3.9+ only APIs in the
  package. `importlib.resources.files` in particular is 3.9+; use
  `cardioception._resources.resource_filename` instead.
- Docs build on Python 3.9 with Sphinx 5.3 and furo. `conf.py` must not import the
  package: it reads `__version__` from `__init__.py` with a regex, because importing
  would drag PsychoPy and its GUI stack onto the docs runner, where wxPython cannot
  build.
- Do not add a `.. contents::` directive to a page. Furo renders the page TOC in the
  sidebar and prints an error into the page if one is present.

## Data

The task writes one `final.txt` per participant, one row per trial. Columns that
matter: `Modality` (`Intero`/`Extero`), `Alpha` (stimulus intensity in ΔBPM),
`Decision` (`More`/`Less`), `ResponseCorrect`, `Confidence` (0-100 slider),
`EstimatedThreshold` and `EstimatedSlope` (the staircase's own online estimates).

`EstimatedThreshold` and `EstimatedSlope` are a by-product of the Psi staircase. They
are useful as a sanity check. They are **not** an analysis, and must not be used as a
dependent variable in a group-level test.

## Analysis

For anything involving fitting psychometric functions, testing an effect on threshold
or slope, choosing priors, or modelling confidence ratings, use the **`hrd-brms`
skill** in `.claude/skills/hrd-brms/`. It carries the model specification, the
normative priors, the mapping from experimental design to formula, and the
diagnostics.

Two rules worth stating here because they are the most common errors:

1. A factor gets a random slope only if it varies **within** a participant.
   `condition` does; `gender`, `group` and `age` do not.
2. Confidence is a bounded continuous scale with mass at both ends. Model it with
   ordered beta regression, not with the m-ratio, which assumes discrete bins and a
   stable type-1 sensitivity that an adaptive staircase does not provide.

## Before you commit

- Docs changes: the build runs on every push to `master` and deploys to
  <https://www.the-ecg.org/Cardioception/>. It takes about a minute. Check the run.
- Do not commit large fitted model objects. Cache them locally with brms `file =`.
- Participant-level data with demographics is sensitive. Do not move it from a private
  repository into this public one without an explicit instruction that acknowledges the
  data is being published.
