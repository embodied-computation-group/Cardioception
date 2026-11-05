# Contributing to Cardioception

Bug reports and questions go in the [issue tracker](https://github.com/embodied-computation-group/Cardioception/issues). Code and documentation changes come as pull requests.

## Branches

Branch from `dev` and open the pull request against `dev`. `main` holds the released version.

## A development install

Cardioception needs Python 3.10 or 3.11. In a fresh virtual environment, from a clone of the repository:

```bash
pip install -e ".[lsl]" pytest pytest-timeout
```

## Running the tests

> **Warning: the session tests play tones at full volume.** `tests/test_hrd.py`, `tests/test_hbc.py`, `tests/test_headless.py` and `tests/test_tone_player.py` play sound through PsychoPy's audio backend, which ignores the system volume. Unplug the headphones or mute the output device before you run them.

These run without a window or sound, and are the quick check:

```bash
pytest tests/test_rng.py tests/test_stimuli.py tests/test_hsd_psi.py
```

The whole suite, as CI runs it:

```bash
pytest tests/ --timeout=180 --timeout-method=thread
```

CI also checks types, formatting and lint on Python 3.11:

```bash
mypy ./cardioception/ --ignore-missing-imports
black --check --diff ./cardioception/ ./tests/
isort --check --diff ./cardioception/ ./tests/
flake8 ./cardioception/ --extend-ignore=E501
```

## Building the documentation

The documentation builds on Python 3.10 with Sphinx 5.3. In a separate environment:

```bash
pip install --no-deps -e .
pip install -r requirements-docs.txt
sphinx-build -b html docs/source docs/build/html
```

The pages are MyST markdown in `docs/source/`. Every push to `dev` or `main` builds them.

## Adding a language

Each task reads its instructions from `cardioception/<task>/texts/<language>.yaml`. To add one:

1. Copy `english.yaml` to `<language>.yaml` in the same folder and translate the values, not the keys or the `{placeholders}`.
2. Add the language to the tests that list `available()` exactly: `tests/test_languages.py` (HRD), `tests/test_hbc_languages.py` and `tests/test_pat_languages.py`.
3. Add it to the language tables in the documentation: Languages in `docs/source/getting-started/running-a-session.md`, and the `language` row of the task page.

## Copyright and licence

Cardioception is released under the [Apache 2.0 licence](LICENSE). Every Python file starts with the copyright header:

```python
# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
```

By opening a pull request you agree that your contribution is licensed under Apache 2.0.

## Review

The maintainers review every pull request before it is merged. Say what the change does and why, and how you checked it.
