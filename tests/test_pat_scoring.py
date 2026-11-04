# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""PAT scoring: hand-computed cases, the paper's threshold, and the grid."""

import numpy as np
import pandas as pd
import pytest

from cardioception.PAT.scoring import (
    FINAL_COLUMNS,
    GRID_COLUMNS,
    consistency_grid,
    extero_threshold,
    mad_outliers,
    mean_resultant_length,
    monte_carlo_threshold,
    phase_angles,
)

#: Small enough to keep the suite fast, large enough for stable quantiles.
N_SIM = 20_000


def participant(phases, confidence=None, seed=0, n_practice=4):
    """A ``final.txt``-like table for chosen phases (fractions of a cycle).

    Anticipated periods wander around 900 ms; the observed period is the
    anticipated one plus a little noise, as the paper found.
    """
    rng = np.random.default_rng(seed)
    n = len(phases)
    anticipated = 900 + rng.normal(0, 30, n)
    observed = anticipated + rng.normal(0, 10, n)
    if confidence is None:
        confidence = rng.integers(1, 11, n)
    main = pd.DataFrame(
        {
            "Trial": np.arange(1, n + 1),
            "Block": "main",
            "ChosenDelayMs": np.asarray(phases) * anticipated,
            "AnticipatedPeriodMs": anticipated,
            "ObservedPeriodMs": observed,
            "Confidence": confidence,
        }
    )
    # Practice rows at wildly inconsistent phases must not count.
    practice = pd.DataFrame(
        {
            "Trial": np.arange(1, n_practice + 1),
            "Block": "practice",
            "ChosenDelayMs": np.linspace(0, 800, n_practice),
            "AnticipatedPeriodMs": 900.0,
            "ObservedPeriodMs": 900.0,
            "Confidence": 5,
        }
    )
    return pd.concat([practice, main], ignore_index=True)


# Phase angles and the mean resultant length ---------------------------------


def test_phase_angles():
    theta = phase_angles([0, 250, 500, 1000, 1250], 1000)
    np.testing.assert_allclose(theta, [0, np.pi / 2, np.pi, 0, np.pi / 2])
    # One period per delay.
    np.testing.assert_allclose(phase_angles([200, 300], [800, 1200]), [np.pi / 2] * 2)
    assert np.isnan(phase_angles([np.nan], [1000])).all()


def test_mrl_identical_angles_is_one():
    assert mean_resultant_length(np.full(10, 1.234)) == pytest.approx(1.0)


def test_mrl_four_quadrants_is_zero():
    theta = np.deg2rad([0, 90, 180, 270])
    assert mean_resultant_length(theta) == pytest.approx(0.0, abs=1e-12)


def test_mrl_two_angles():
    # 0 and 90 degrees: |1 + i| / 2 = sqrt(2) / 2.
    assert mean_resultant_length([0, np.pi / 2]) == pytest.approx(np.sqrt(2) / 2)


def test_mrl_weighted():
    # 0 (weight 3) and 180 degrees (weight 1): |3 - 1| / 4.
    assert mean_resultant_length([0, np.pi], [3, 1]) == pytest.approx(0.5)
    # 0 (weight 2) and 90 degrees (weight 1): |2 + i| / 3.
    assert mean_resultant_length([0, np.pi / 2], [2, 1]) == pytest.approx(
        np.sqrt(5) / 3
    )
    # Equal weights change nothing.
    theta = np.deg2rad([10, 40, 200])
    assert mean_resultant_length(theta, [7, 7, 7]) == pytest.approx(
        mean_resultant_length(theta)
    )
    # A zero weight removes the trial.
    assert mean_resultant_length([0, np.pi], [1, 0]) == pytest.approx(1.0)


def test_mrl_nan_and_empty():
    assert mean_resultant_length([0, np.nan, 0]) == pytest.approx(1.0)
    assert np.isnan(mean_resultant_length([]))
    assert np.isnan(mean_resultant_length([0, 1], [0, 0]))
    with pytest.raises(ValueError):
        mean_resultant_length([0, 1], [1, -1])
    with pytest.raises(ValueError):
        mean_resultant_length([0, 1], [1])


# MAD outlier rule -----------------------------------------------------------


def test_mad_outliers_hand_computed():
    # Median 1010; absolute deviations 60, 30, 10, 10, 40, 990, whose median is
    # 35; robust SD 1.4826 * 35 = 51.9; cut-off 5 * 51.9 = 259.5 ms.
    x = [950, 980, 1000, 1020, 1050, 2000]
    assert mad_outliers(x).tolist() == [False] * 5 + [True]
    # A tighter cut-off (k = 1, 51.9 ms) also catches 950.
    assert mad_outliers(x, k=1).tolist() == [True, False, False, False, False, True]


def test_mad_outliers_edge_cases():
    # NaN is missing, not an outlier.
    assert mad_outliers([1000, np.nan, 1010, 990]).tolist() == [False] * 4
    # Identical periods (MAD 0): the robust SD is floored at 1 ms, so float
    # noise and small differences are not outliers, and more than 5 ms is.
    assert not mad_outliers([1000] * 5).any()
    assert not mad_outliers([1000] * 5 + [1000 + 1e-9]).any()
    assert not mad_outliers([1000] * 5 + [1001]).any()
    assert not mad_outliers([1000] * 5 + [1005]).any()
    assert mad_outliers([1000] * 5 + [1005.1]).tolist() == [False] * 5 + [True]
    # Without the floor the old rule comes back.
    assert mad_outliers([1000] * 5 + [1001], min_sd=0).tolist() == [False] * 5 + [True]
    with pytest.raises(ValueError):
        mad_outliers([1, 2], min_sd=-1)
    assert not mad_outliers([np.nan, np.nan]).any()
    with pytest.raises(ValueError):
        mad_outliers([1, 2], k=0)


def test_grid_keeps_a_fixed_period_with_float_noise():
    # An exteroceptive run at a fixed 1000 ms, written through float sums.
    n = 28
    period = 1000.0 + np.random.default_rng(5).choice([0, 1e-10, -1e-10], n)
    df = pd.DataFrame(
        {
            "Block": "main",
            "ChosenDelayMs": 300.0,
            "AnticipatedPeriodMs": period,
            "ObservedPeriodMs": period,
            "Confidence": 5,
        }
    )
    grid = consistency_grid(df, n_sim=100)
    assert (grid["n_trials"] == n).all()


def test_grid_drops_outlying_and_missing_periods():
    rng = np.random.default_rng(3)
    df = participant(0.3 + rng.normal(0, 0.01, 28))
    main = df.index[df["Block"] == "main"]
    df.loc[main[0], "ObservedPeriodMs"] = 3000.0  # a missed R-wave
    df.loc[main[1], "ObservedPeriodMs"] = np.nan  # next R never arrived
    grid = consistency_grid(df, n_sim=1_000).set_index(
        ["mapping", "period", "weighting"]
    )
    assert grid.loc[("variable", "anticipated", "none"), "n_trials"] == 28
    assert grid.loc[("variable", "observed", "none"), "n_trials"] == 26


# Monte Carlo thresholds -----------------------------------------------------


def test_extero_threshold_matches_paper():
    # Hodgetts et al. (2026): 28 trials at a fixed 1000 ms period give 0.33.
    # Analytically, sqrt(-ln(0.05) / 28) = 0.327 (Rayleigh approximation).
    threshold = extero_threshold(28, period_ms=1000, n_sim=N_SIM)
    assert threshold == pytest.approx(0.33, abs=0.01)
    assert threshold == monte_carlo_threshold(
        [1000], 28, n_sim=N_SIM, fixed=True, seed=0
    )


def test_threshold_is_reproducible_and_seedable():
    a = monte_carlo_threshold([900, 950, 1000], 20, n_sim=2_000)
    b = monte_carlo_threshold([900, 950, 1000], 20, n_sim=2_000)
    c = monte_carlo_threshold([900, 950, 1000], 20, n_sim=2_000, seed=1)
    assert a == b
    assert a != c


def test_threshold_falls_with_more_trials():
    thresholds = [extero_threshold(n, n_sim=N_SIM) for n in (10, 28, 60)]
    assert thresholds[0] > thresholds[1] > thresholds[2]
    for n, threshold in zip((10, 28, 60), thresholds):
        assert threshold == pytest.approx(np.sqrt(-np.log(0.05) / n), rel=0.06)


def test_threshold_does_not_depend_on_the_periods():
    # Uniform delays over any period give uniform angles, so with the same
    # seed the threshold is the same whatever the periods and the mapping.
    periods = np.linspace(700, 1200, 28)
    for n in (28, 20):
        reference = monte_carlo_threshold([1000], n, n_sim=N_SIM)
        assert monte_carlo_threshold(periods, n, n_sim=N_SIM) == reference
        assert monte_carlo_threshold(periods, n, n_sim=N_SIM, fixed=True) == reference
        assert extero_threshold(n, period_ms=650, n_sim=N_SIM) == reference
    assert monte_carlo_threshold(periods, 28, n_sim=N_SIM) == pytest.approx(
        np.sqrt(-np.log(0.05) / 28), rel=0.06
    )


def test_weighted_threshold():
    # Equal weights give the unweighted threshold.
    assert monte_carlo_threshold(
        [1000], 28, n_sim=N_SIM, weights=np.full(28, 4.0)
    ) == pytest.approx(monte_carlo_threshold([1000], 28, n_sim=N_SIM))
    # Unequal weights mean fewer effective trials, so a higher threshold.
    weights = np.r_[np.full(4, 10.0), np.full(24, 1.0)]
    assert monte_carlo_threshold(
        [1000], 28, n_sim=N_SIM, weights=weights
    ) > monte_carlo_threshold([1000], 28, n_sim=N_SIM)


def test_threshold_validation():
    with pytest.raises(ValueError):
        monte_carlo_threshold([], 10)
    with pytest.raises(ValueError):
        monte_carlo_threshold([1000], 0)
    with pytest.raises(ValueError):
        monte_carlo_threshold([1000], 10, q=1.5)
    with pytest.raises(ValueError):
        monte_carlo_threshold([1000], 3, weights=[1, 2])


# The 2 x 2 x 2 grid ---------------------------------------------------------


def test_grid_columns_and_cells():
    df = participant(np.linspace(0, 1, 28, endpoint=False))
    grid = consistency_grid(df, n_sim=1_000)
    assert list(grid.columns) == GRID_COLUMNS
    assert len(grid) == 8
    cells = set(zip(grid["mapping"], grid["period"], grid["weighting"]))
    assert cells == {
        (m, p, w)
        for m in ("variable", "fixed")
        for p in ("anticipated", "observed")
        for w in ("none", "confidence")
    }
    assert grid["interoceptive"].dtype == bool


def test_grid_drops_trials_that_are_not_ok():
    rng = np.random.default_rng(4)
    df = participant(0.3 + rng.normal(0, 0.01, 28))
    main = df.index[df["Block"] == "main"]
    df["TrialStatus"] = "ok"
    df.loc[main[0], "TrialStatus"] = "stale"
    df.loc[main[0], "AnticipatedPeriodMs"] = np.nan
    df.loc[main[1], "TrialStatus"] = "timeout"
    df.loc[main[1], "ChosenDelayMs"] = np.nan
    # A stale trial with a plausible period would still be scored without the
    # status: it is the status that drops it.
    df.loc[main[2], "TrialStatus"] = "stale"
    df.loc[df["Block"] == "practice", "TrialStatus"] = "timeout"  # not counted
    grid = consistency_grid(df, n_sim=1_000)
    assert (grid["n_dropped"] == 3).all()
    assert (grid.loc[grid["weighting"] == "none", "n_trials"] == 25).all()
    # An empty status counts as ok, and a file without the column drops none.
    df["TrialStatus"] = np.nan
    assert (consistency_grid(df, n_sim=100)["n_dropped"] == 0).all()
    grid = consistency_grid(df.drop(columns="TrialStatus"), n_sim=100)
    assert (grid["n_dropped"] == 0).all()


def test_grid_requires_final_columns():
    df = participant([0.3] * 10)
    for column in FINAL_COLUMNS:
        with pytest.raises(ValueError, match=column):
            consistency_grid(df.drop(columns=column), n_sim=100)


def test_consistent_participant_is_interoceptive_everywhere():
    rng = np.random.default_rng(1)
    df = participant(0.3 + rng.normal(0, 0.03, 28))
    grid = consistency_grid(df, n_sim=N_SIM)
    assert grid["interoceptive"].all()
    assert (grid["score"] > 0.9).all()
    assert (grid["n_trials"] == 28).all()
    # Practice rows are ignored: 28 main trials only.
    assert grid["threshold"].between(0.25, 0.45).all()


def test_spread_participant_is_interoceptive_nowhere():
    # Phases spread evenly round the cycle, in random order.
    rng = np.random.default_rng(2)
    phases = rng.permutation(np.arange(28) / 28 + rng.uniform(0, 0.02, 28))
    grid = consistency_grid(participant(phases), n_sim=N_SIM)
    assert not grid["interoceptive"].any()
    assert (grid["score"] < grid["threshold"]).all()


def test_uniform_random_participants_false_positive_rate():
    # Participants choosing uniformly at random pass each cell about 5 % of
    # the time, by construction of the threshold.
    hits = []
    for seed in range(100):
        rng = np.random.default_rng(100 + seed)
        grid = consistency_grid(participant(rng.uniform(0, 1, 28)), n_sim=2_000)
        hits.append(grid["interoceptive"].to_numpy())
    rate = np.mean(hits, axis=0)
    assert (rate <= 0.12).all()
    assert rate.mean() == pytest.approx(0.05, abs=0.04)


def test_fixed_mapping_drops_delays_beyond_median():
    df = participant([0.3] * 28)
    main = df.index[df["Block"] == "main"]
    df.loc[main[:3], "ChosenDelayMs"] = 1500.0  # beyond any period
    grid = consistency_grid(df, n_sim=1_000).set_index(
        ["mapping", "period", "weighting"]
    )
    assert grid.loc[("fixed", "anticipated", "none"), "n_trials"] == 25
    assert grid.loc[("variable", "anticipated", "none"), "n_trials"] == 28


def test_fixed_mapping_uses_median_period():
    # Same delay every trial, periods alternating 800 and 1000 ms: perfectly
    # consistent in delay (fixed mapping, R = 1) but not in phase.
    n = 28
    period = np.tile([800.0, 1000.0], n // 2)
    df = pd.DataFrame(
        {
            "Block": "main",
            "ChosenDelayMs": 300.0,
            "AnticipatedPeriodMs": period,
            "ObservedPeriodMs": period,
            "Confidence": 5,
        }
    )
    grid = consistency_grid(df, n_sim=1_000).set_index(
        ["mapping", "period", "weighting"]
    )
    assert grid.loc[("fixed", "observed", "none"), "score"] == pytest.approx(1.0)
    expected = mean_resultant_length(phase_angles(300.0, period))
    assert grid.loc[("variable", "observed", "none"), "score"] == pytest.approx(
        expected
    )
    assert expected < 1


def test_weighted_cells_use_confidence():
    # Half the trials at 0.2 with confidence 10, half at 0.7 with confidence 1.
    phases = np.r_[np.full(14, 0.2), np.full(14, 0.7)]
    confidence = np.r_[np.full(14, 10), np.full(14, 1)]
    grid = consistency_grid(participant(phases, confidence), n_sim=1_000)
    grid = grid.set_index(["mapping", "period", "weighting"])
    unweighted = grid.loc[("variable", "anticipated", "none"), "score"]
    weighted = grid.loc[("variable", "anticipated", "confidence"), "score"]
    assert unweighted == pytest.approx(0.0, abs=1e-9)
    assert weighted == pytest.approx(9 / 11)


def test_missing_confidence_and_observed_periods():
    df = participant([0.3] * 28)
    df["Confidence"] = np.nan
    df["ObservedPeriodMs"] = np.nan
    grid = consistency_grid(df, n_sim=1_000).set_index(
        ["mapping", "period", "weighting"]
    )
    assert grid.loc[("variable", "anticipated", "none"), "interoceptive"]
    empty = grid.loc[
        [i for i in grid.index if i[1] == "observed" or i[2] == "confidence"]
    ]
    assert (empty["n_trials"] == 0).all()
    assert empty["score"].isna().all()
    assert not empty["interoceptive"].any()
