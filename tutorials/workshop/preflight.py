#!/usr/bin/env python3
"""Check that this machine is ready for the Cardioception workshop.

Run it with the workshop environment's Python:

    ./cardioception-env/bin/python preflight.py         # macOS / Linux
    cardioception-env\\Scripts\\python preflight.py       # Windows

Stdlib only, so it also runs on a bare system Python before anything is
installed - it will simply tell you what is missing.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str, str]] = []   # (status, area, what, fix)


def record(status: str, area: str, what: str, fix: str = "") -> None:
    results.append((status, area, what, fix))


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    """Run a command, returning (returncode, combined output)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


# --------------------------------------------------------------- Python
def check_python() -> None:
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if (3, 10) <= (v.major, v.minor) <= (3, 11):
        record(PASS, "Python", f"version {ver}")
    else:
        record(FAIL, "Python", f"version {ver} - need 3.10 or 3.11",
               "PsychoPy's dependencies do not build above 3.11. Install Python 3.10 "
               "or 3.11 and rebuild the virtual environment.")

    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        record(PASS, "Python", f"running inside a virtual environment ({Path(sys.prefix).name})")
    else:
        record(WARN, "Python", "not running inside a virtual environment",
               "Not fatal, but installing into the system Python tends to end badly. "
               "See step 1 of PREINSTALL.md.")


def check_python_packages() -> None:
    required = {
        "cardioception": "pip install cardioception-toolbox",
        "psychopy":      "installed with cardioception-toolbox",
        "systole":       "installed with cardioception-toolbox",
        "serial":        "pip install pyserial",
        "numpy":         "pip install numpy",
        "scipy":         "pip install scipy",
        "pandas":        "pip install pandas",
        "matplotlib":    "pip install matplotlib",
        "ipywidgets":    "pip install ipywidgets",
        "jupyterlab":    "pip install jupyterlab",
    }
    for mod, fix in required.items():
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "installed")
            record(PASS, "Python pkg", f"{mod} {ver}")
        except Exception as e:  # ImportError, but PsychoPy can raise others
            record(FAIL, "Python pkg", f"{mod} missing ({type(e).__name__})", fix)


def check_media() -> None:
    """The tone files are the bulk of the install and a common partial-download victim."""
    try:
        import cardioception
    except Exception:
        record(WARN, "Media", "skipped - cardioception not importable", "")
        return
    sounds = Path(cardioception.__file__).parent / "HRD" / "Sounds"
    n = len(list(sounds.glob("*.wav"))) if sounds.is_dir() else 0
    if n >= 350:
        record(PASS, "Media", f"{n} tone files present")
    else:
        record(FAIL, "Media", f"only {n} tone files (expect ~370)",
               "The install was incomplete. Reinstall: "
               "pip install --force-reinstall cardioception-toolbox")


def check_task_import() -> None:
    """Importing the task pulls in the full PsychoPy stack - the real smoke test."""
    code = "from cardioception.HRD import task; print('ok')"
    rc, out = run([sys.executable, "-c", code], timeout=300)
    if rc == 0 and "ok" in out:
        record(PASS, "Task", "cardioception.HRD.task imports")
    else:
        record(FAIL, "Task", "cannot import cardioception.HRD.task",
               "This is the one that matters. Last lines:\n      "
               + "\n      ".join(out.strip().splitlines()[-4:]))


def check_kernels() -> None:
    exe = shutil.which("jupyter") or str(Path(sys.executable).parent / "jupyter")
    rc, out = run([exe, "kernelspec", "list"])
    if rc != 0:
        record(FAIL, "Jupyter", "cannot list kernels",
               "pip install jupyterlab, then re-run this script.")
        return
    for name, label, fix in [
        ("cardioception", "Python (cardioception)",
         'python -m ipykernel install --user --name cardioception '
         '--display-name "Python (cardioception)"'),
        ("ir-cardioception", "R (cardioception)",
         'Rscript -e \'IRkernel::installspec(name="ir-cardioception", '
         'displayname="R (cardioception)")\'  '
         '(with the venv bin directory on PATH)'),
    ]:
        if name in out:
            record(PASS, "Jupyter", f"kernel '{name}' registered  [{label}]")
        else:
            record(FAIL, "Jupyter", f"kernel '{name}' NOT registered", fix)


# --------------------------------------------------------------- R
R_PROBE = r"""
pkgs <- c("brms", "cmdstanr", "IRkernel", "ggplot2", "dplyr", "tidyr", "readr",
          "posterior", "patchwork")
for (p in pkgs) {
  cat(sprintf("PKG|%s|%s\n", p,
      if (requireNamespace(p, quietly = TRUE)) as.character(packageVersion(p)) else "MISSING"))
}
cat(sprintf("RVER|%s\n", paste(R.version$major, R.version$minor, sep = ".")))
cs <- tryCatch({
  suppressMessages(library(cmdstanr))
  paste(cmdstanr::cmdstan_path(), cmdstanr::cmdstan_version(), sep = "|")
}, error = function(e) "NONE")
cat(sprintf("CMDSTAN|%s\n", cs))
"""


def check_r() -> None:
    if not shutil.which("Rscript"):
        record(FAIL, "R", "Rscript not found on PATH",
               "Install R 4.2+ from https://cran.r-project.org, then see step 3 of "
               "PREINSTALL.md. Without R you can still do notebook 1 and the "
               "no-fitting parts of notebook 2.")
        return

    rc, out = run(["Rscript", "-e", R_PROBE], timeout=300)
    if rc != 0:
        record(FAIL, "R", "Rscript failed to run the probe", out.strip()[-300:])
        return

    fixes = {
        "brms":      'install.packages("brms")',
        "cmdstanr":  'install.packages("cmdstanr", repos = c("https://stan-dev.r-universe.dev", getOption("repos")))',
        "IRkernel":  'install.packages("IRkernel")',
    }
    for line in out.splitlines():
        if line.startswith("RVER|"):
            record(PASS, "R", f"version {line.split('|')[1]}")
        elif line.startswith("PKG|"):
            _, pkg, ver = line.split("|")
            if ver == "MISSING":
                record(FAIL, "R pkg", f"{pkg} missing",
                       fixes.get(pkg, f'install.packages("{pkg}")'))
            else:
                record(PASS, "R pkg", f"{pkg} {ver}")
        elif line.startswith("CMDSTAN|"):
            rest = line[len("CMDSTAN|"):]
            if rest == "NONE":
                record(WARN, "CmdStan", "not installed",
                       'In R: cmdstanr::install_cmdstan(cores = 2)   '
                       '(one-off, 10-20 min - it compiles). Without it the model-fitting '
                       'cell falls back to precomputed results and the workshop still works.')
            else:
                path, ver = rest.split("|")
                record(PASS, "CmdStan", f"version {ver}  ({path})")


def check_stan_compiles() -> None:
    """CmdStan being installed is not the same as being able to compile."""
    rc, out = run(["Rscript", "-e",
                   'suppressMessages(library(cmdstanr)); '
                   'f <- write_stan_file("parameters {real y;} model {y ~ std_normal();}"); '
                   'm <- cmdstan_model(f, compile = TRUE); cat("COMPILED\\n")'],
                  timeout=600)
    if "COMPILED" in out:
        record(PASS, "CmdStan", "compiles a test model")
    else:
        record(WARN, "CmdStan", "could not compile a test model",
               "Usually a missing C++ toolchain. macOS: xcode-select --install. "
               "Windows: install RTools. The workshop falls back to precomputed fits.")


# --------------------------------------------------------------- report
def main() -> int:
    print("=" * 72)
    print("  Cardioception workshop - preflight check")
    print("=" * 72)
    print(f"  {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Python: {sys.executable}")
    print()

    check_python()
    check_python_packages()
    check_media()
    check_task_import()
    check_kernels()
    check_r()
    if any(s == PASS and "version" in w and a == "CmdStan" for s, a, w, _ in results):
        check_stan_compiles()

    width = max(len(a) for _, a, _, _ in results)
    icons = {PASS: "  ok  ", FAIL: " FAIL ", WARN: " warn "}
    for status, area, what, _ in results:
        print(f"[{icons[status]}] {area:<{width}}  {what}")

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]

    print()
    print("-" * 72)
    if not fails and not warns:
        print("  Everything is ready. Nothing to do before the workshop.")
    elif not fails:
        print(f"  Ready, with {len(warns)} warning(s). You can run the whole workshop.")
    else:
        print(f"  {len(fails)} problem(s) to fix before the workshop.")

    for label, group in (("MUST FIX", fails), ("OPTIONAL", warns)):
        if not group:
            continue
        print(f"\n  {label}")
        for _, area, what, fix in group:
            print(f"    - {area}: {what}")
            if fix:
                for ln in fix.splitlines():
                    print(f"        {ln}")

    print()
    print("  Stuck? Send this entire output to the organiser. Do not spend")
    print("  more than 30 minutes on it - arrive 15 minutes early instead.")
    print("-" * 72)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
