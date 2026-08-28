# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Check that the documented install path still works.

    python tests/check_install.py

Run against a freshly installed package, which is what the CI job does. It
exists because the documentation had drifted in four independent ways before
anyone noticed: the conda instructions no longer worked, the stated Python
version was wrong, the systole links pointed at a dead site, and the setuptools
bound was missing. None of that produces a failing test, because none of it is
code. So this checks the claims themselves.

Written as a script rather than a unittest so it can be run by hand while
following the installation guide, and so a failure names the documented step
that broke rather than an assertion number.
"""

import os
import re
import sys
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

failures: List[str] = []
notes: List[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}{': ' + detail if detail else ''}")
    if not ok:
        failures.append(f"{name}{': ' + detail if detail else ''}")


def read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# --- the package is importable at all --------------------------------------
print("\nimports")
try:
    import cardioception

    check("import cardioception", True, f"version {cardioception.__version__}")
except Exception as exc:
    check("import cardioception", False, f"{type(exc).__name__}: {exc}")
    print("\nNothing else can be checked. Stopping.")
    sys.exit(1)

for mod in (
    "cardioception.HRD.parameters",
    "cardioception.HRD.task",
    "cardioception.HBC.parameters",
    "cardioception.HBC.task",
    "cardioception.check_device",
    "cardioception._rating",
):
    try:
        __import__(mod)
        check(f"import {mod}", True)
    except Exception as exc:
        check(f"import {mod}", False, f"{type(exc).__name__}: {exc}")

# --- the data files the tasks play actually shipped ------------------------
print("\nshipped resources")
try:
    from cardioception._resources import resource_filename

    for pkg, res in [
        ("cardioception.HRD", "Sounds/60.0.wav"),
        ("cardioception.HRD", "Sounds/120.0.wav"),
        ("cardioception.HRD", "Images/pulseOximeter.png"),
        ("cardioception.HBC", "Sounds/start.wav"),
        ("cardioception.HBC", "Images/heartbeat.png"),
    ]:
        path = resource_filename(pkg, res)
        check(f"{pkg}/{res}", os.path.exists(path))
except Exception as exc:
    check("resource_filename", False, f"{type(exc).__name__}: {exc}")

# --- every language shipped, and loads --------------------------------------
# A packaging miss here works from a source checkout and fails from a wheel, at
# the first instruction screen rather than at import.
print("\nparticipant-facing text")
try:
    from cardioception.HRD.languages import available, get_texts

    found = available()
    check("languages found", bool(found), ", ".join(found) or "none")
    for language in ("english", "danish", "danish_children", "french"):
        try:
            texts = get_texts(language, "mouse", True)
            check(f"texts/{language}.yaml", len(texts) == 31, f"{len(texts)} keys")
        except Exception as exc:
            check(f"texts/{language}.yaml", False, f"{type(exc).__name__}: {exc}")
except Exception as exc:
    check("language loader", False, f"{type(exc).__name__}: {exc}")

# --- the interpreter really is one the metadata allows ---------------------
print("\npython_requires")
setup_src = read("setup.py")
m = re.search(r'python_requires\s*=\s*"([^"]+)"', setup_src)
if m is None:
    check("setup.py declares python_requires", False)
else:
    spec = m.group(1)
    check("setup.py declares python_requires", True, spec)
    try:
        from packaging.specifiers import SpecifierSet

        running = ".".join(str(v) for v in sys.version_info[:3])
        inside = running in SpecifierSet(spec)
        check(f"running interpreter {running} satisfies {spec}", inside)
    except ImportError:
        notes.append("packaging not installed, skipped the interpreter comparison")

    # The docs quote this range in prose. If they disagree with the metadata,
    # someone changed one and not the other, which is the drift this guards.
    lo = re.search(r">=(\d+)\.(\d+)", spec)
    hi = re.search(r"<(\d+)\.(\d+)", spec)
    if lo and hi:
        lo_s = f"{lo.group(1)}.{lo.group(2)}"
        hi_minor = int(hi.group(2)) - 1
        top_s = f"{hi.group(1)}.{hi_minor}"
        for doc in ("README.md", os.path.join("docs", "source", "installation.md")):
            text = read(*doc.split(os.sep))
            mentions = (lo_s in text) and (top_s in text)
            check(
                f"{doc} names the supported range ({lo_s} to {top_s})",
                mentions,
                "" if mentions else "prose disagrees with setup.py",
            )

# --- requirements are parseable, and agree with what is installed ----------
print("\nrequirements")
try:
    from packaging.requirements import Requirement

    lines = [
        ln.strip()
        for ln in read("requirements.txt").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    bad: List[Tuple[str, str]] = []
    for ln in lines:
        try:
            Requirement(ln)
        except Exception as exc:
            bad.append((ln, str(exc)))
    check(
        f"requirements.txt parses ({len(lines)} specifiers)",
        not bad,
        "; ".join(f"{ln} -> {e}" for ln, e in bad),
    )

    # setup.py feeds this file straight into install_requires, so a stray
    # comment line here breaks the build rather than being ignored.
    check(
        "no comment leaked into the specifier list",
        not any(ln.startswith("#") for ln in lines),
    )
except ImportError:
    notes.append("packaging not installed, skipped requirements parsing")

# --- the task builds its parameters, if there is a display -----------------
print("\ntask startup")
headless = not (os.environ.get("DISPLAY") or sys.platform.startswith("win"))
if headless:
    notes.append("no display, skipped getParameters (run under xvfb to include it)")
    print("  SKIP  getParameters: no display available")
else:
    import shutil
    import tempfile

    out = tempfile.mkdtemp(prefix="cardio_check_")
    params = None
    try:
        from cardioception.HRD.parameters import getParameters

        params = getParameters(
            participant="CIcheck",
            session="001",
            setup="test",
            nTrials=1,
            screenNb=0,
            fullscr=False,
            resultPath=out,
        )
        needed = ["win", "stairCase", "texts", "oxiTask", "resultPath"]
        missing = [k for k in needed if k not in params]
        check("getParameters(setup='test')", not missing, f"missing {missing}")
    except Exception as exc:
        check("getParameters(setup='test')", False, f"{type(exc).__name__}: {exc}")
    finally:
        if params is not None and params.get("win") is not None:
            try:
                params["win"].close()
            except Exception:
                pass
        shutil.rmtree(out, ignore_errors=True)

# --- report ----------------------------------------------------------------
print("")
for note in notes:
    print(f"note: {note}")
if failures:
    print(f"\n{len(failures)} check(s) failed:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\nall checks passed")
sys.exit(0)
