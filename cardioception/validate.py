# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Check that a finished session's output is internally consistent.

The same checks serve two purposes. In the test suite they run against a
replayed session on every push. After a real session they can be run from the
command line, which is how the audit of 2026-08-28 confirmed on live hardware
that the behavioural bookkeeping is sound and that two specific defects were
present.

They are invariants rather than expected values: nothing here asserts a
particular threshold or a particular trial order, only that the recorded numbers
agree with each other. That is what makes them usable as a regression gate
across a refactor, where the values legitimately change but the relationships
must not.

    python -m cardioception.validate <run_dir>
"""

import os
import sys
from typing import List, NamedTuple, Optional

import numpy as np
import pandas as pd

BPM_FLOOR, BPM_CEIL = 15.0, 199.0


class Check(NamedTuple):
    name: str
    passed: bool
    detail: str = ""


def check_trials(df: pd.DataFrame, resp_max: Optional[float] = None) -> List[Check]:
    """Every invariant that holds within the trial table alone."""
    out: List[Check] = []

    def add(name, passed, detail=""):
        out.append(Check(name, bool(passed), detail))

    expected = (df.listenBPM + df.Alpha).clip(BPM_FLOOR, BPM_CEIL)
    bad = int((~np.isclose(df.responseBPM, expected)).sum())
    add("responseBPM == clip(listenBPM + Alpha)", bad == 0, f"{bad} mismatched")

    expected_cond = np.where(df.Alpha < 0, "Less", "More")
    bad = int((df.Condition != expected_cond).sum())
    add("Condition matches sign(Alpha)", bad == 0, f"{bad} mismatched")

    answered = df[df.DecisionProvided.astype(bool)]
    bad = int(
        (
            answered.ResponseCorrect.astype(bool)
            != (answered.Decision == answered.Condition)
        ).sum()
    )
    add("ResponseCorrect == (Decision == Condition)", bad == 0, f"{bad} mismatched")

    add(
        "every trial carries a modality",
        bool(df.Modality.isin(["Intero", "Extero"]).all()),
    )

    on_grid = bool(np.allclose((df.listenBPM * 2) % 1, 0))
    add("listenBPM on the half beat grid", on_grid)

    rt = pd.to_numeric(df.DecisionRT, errors="coerce").dropna()
    if resp_max is not None:
        add(
            "DecisionRT within the response deadline",
            bool((rt <= resp_max).all()),
            f"max={rt.max():.3f}" if len(rt) else "no responses",
        )

    # A decision cannot be instantaneous. Exactly zero means the button was
    # already down when the response window opened, which the task used to
    # accept as a real answer.
    zero = int((rt == 0.0).sum())
    add("no instantaneous decisions", zero == 0, f"{zero} at exactly 0.0")

    # Ratings are only offered when a decision was made.
    orphan = int(
        (df.RatingProvided.astype(bool) & ~df.DecisionProvided.astype(bool)).sum()
    )
    add("no rating without a decision", orphan == 0, f"{orphan} orphaned")

    stamps = [
        "StartListening",
        "StartDecision",
        "ResponseMade",
        "RatingStart",
        "RatingEnds",
        "endTrigger",
    ]
    present = [c for c in stamps if c in df.columns]
    viol = 0
    for a, b in zip(present, present[1:]):
        pair = df[[a, b]].dropna()
        viol += int((pair[a] > pair[b]).sum())
    add("trial timestamps run forwards", viol == 0, f"{viol} violations")

    psi = df[df.TrialType == "psi"]
    if len(psi):
        add(
            "psi trials carry a threshold estimate",
            bool(psi.EstimatedThreshold.notna().all()),
            f"{int(psi.EstimatedThreshold.isna().sum())} missing of {len(psi)}",
        )
    return out


def check_run(run_dir: str) -> List[Check]:
    """Run the trial-table checks against the finished session in ``run_dir``."""
    finals = [f for f in os.listdir(run_dir) if f.endswith("_final.txt")]
    if not finals:
        return [Check("a final results file exists", False, f"none in {run_dir}")]
    df = pd.read_csv(os.path.join(run_dir, finals[0]))
    return [Check("a final results file exists", True, finals[0])] + check_trials(df)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    failed = 0
    for check in check_run(argv[0]):
        status = "PASS" if check.passed else "FAIL"
        print(
            f"  {status}  {check.name}"
            + (f"  ({check.detail})" if check.detail else "")
        )
        failed += not check.passed
    print(f"\n{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
