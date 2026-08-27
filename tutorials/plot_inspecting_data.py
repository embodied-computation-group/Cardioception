"""Build the quality-control figures for the data-inspection tutorial.

The source session is a Psi-only VMP2 participant. Its full posterior arrays stay
under ``tutorials/data/`` and are ignored by git. This script reduces them to
trial-level marginal summaries, writes deidentified compact bundles, and draws
participant-level, warning-pattern, and collection-level figures.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tutorials" / "data" / "vmp2_0341"
SESSION_DIR = ROOT / "tutorials" / "data" / "vmp2_sessions"
SMALL_DIR = ROOT / "tutorials" / "results" / "small"
FIG_DIR = ROOT / "docs" / "source" / "images" / "tutorials"
EXAMPLE_DIR = ROOT / "docs" / "source" / "examples" / "templates" / "data" / "HRD"

TRIAL_FILE = SOURCE_DIR / "0341HRD_final.txt"
POSTERIOR_FILES = {
    "Intero": SOURCE_DIR / "0341Intero_posterior.npy",
    "Extero": SOURCE_DIR / "0341Extero_posterior.npy",
}
TRIAL_BUNDLE = SMALL_DIR / "inspection_example_trials.csv.gz"
PSI_BUNDLE = SMALL_DIR / "inspection_example_psi.csv.gz"
SESSION_BUNDLE = SMALL_DIR / "inspection_session_summary.csv.gz"
EXAMPLE_TRIAL_FILE = EXAMPLE_DIR / "vmp2_example_final.txt"

NAVY = "#1F3352"
BLUE = "#2F7895"
RED = "#B14660"
GOLD = "#D49A45"
GREY = "#7D8795"
LIGHT = "#DCE2EA"
BLACK = "#343A40"
MODALITY_COLOURS = {"Intero": RED, "Extero": BLUE}

ALPHA_GRID = np.arange(-50.5, 51.5, 1.0)
SIGMA_GRID = np.arange(0.1, 25.1, 0.1)


def set_style() -> None:
    """Use the same restrained style as the other revised tutorials."""

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GREY,
            "axes.labelcolor": BLACK,
            "axes.titlecolor": BLACK,
            "xtick.color": BLACK,
            "ytick.color": BLACK,
            "text.color": BLACK,
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
        }
    )


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """Return a quantile from an ordered grid and discrete probability weights."""

    weights = np.asarray(weights, dtype=float)
    total = weights.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Posterior marginal has no finite probability mass")
    cumulative = np.cumsum(weights / total)
    return float(values[np.searchsorted(cumulative, q, side="left")])


def summarize_posterior(path: Path, modality: str) -> pd.DataFrame:
    """Reduce each joint Psi posterior to threshold and sigma summaries."""

    posterior = np.load(path)
    expected = (60, len(ALPHA_GRID), len(SIGMA_GRID))
    if posterior.shape != expected:
        raise ValueError(f"Expected {expected} for {path.name}, got {posterior.shape}")
    if not np.isfinite(posterior).all():
        raise ValueError(f"Non-finite values found in {path.name}")

    rows = []
    for adaptive_trial, raw in enumerate(posterior, start=1):
        probability = raw / raw.sum()
        alpha = probability.sum(axis=1)
        sigma = probability.sum(axis=0)
        rows.append(
            {
                "Modality": modality,
                "adaptive_trial": adaptive_trial,
                "alpha_mean": np.sum(ALPHA_GRID * alpha),
                "alpha_lo": weighted_quantile(ALPHA_GRID, alpha, 0.025),
                "alpha_hi": weighted_quantile(ALPHA_GRID, alpha, 0.975),
                "sigma_mean": np.sum(SIGMA_GRID * sigma),
                "sigma_lo": weighted_quantile(SIGMA_GRID, sigma, 0.025),
                "sigma_hi": weighted_quantile(SIGMA_GRID, sigma, 0.975),
            }
        )
    return pd.DataFrame(rows)


def build_compact_bundle() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate the source files and write the small public plotting inputs."""

    trials = pd.read_csv(TRIAL_FILE)
    source_columns = trials.columns.tolist()
    required = {
        "TrialType",
        "StairCond",
        "Modality",
        "Decision",
        "DecisionRT",
        "Confidence",
        "ConfidenceRT",
        "Alpha",
        "listenBPM",
        "responseBPM",
        "ResponseCorrect",
        "DecisionProvided",
        "RatingProvided",
        "nTrials",
        "EstimatedThreshold",
        "EstimatedSlope",
    }
    missing = required.difference(trials.columns)
    if missing:
        raise ValueError(f"Missing trial columns: {sorted(missing)}")
    if len(trials) != 120 or set(trials["Modality"]) != {"Intero", "Extero"}:
        raise ValueError(
            "The worked session is no longer the expected 120-trial design"
        )
    if (
        not trials["TrialType"].eq("psi").all()
        or not trials["StairCond"].eq("psi").all()
    ):
        raise ValueError("The worked session must contain only Psi trials")
    if trials["nTrials"].duplicated().any():
        raise ValueError("Global trial numbers are not unique")

    trials = trials.sort_values("nTrials").copy()
    trials["adaptive_trial"] = trials.groupby("Modality").cumcount() + 1
    trials["choice"] = trials["Decision"].map({"More": "faster", "Less": "slower"})
    trials["outcome"] = trials["ResponseCorrect"].map(
        {True: "correct", False: "incorrect", 1: "correct", 0: "incorrect"}
    )

    keep = [
        "Modality",
        "adaptive_trial",
        "nTrials",
        "Alpha",
        "listenBPM",
        "responseBPM",
        "Decision",
        "choice",
        "ResponseCorrect",
        "outcome",
        "DecisionProvided",
        "DecisionRT",
        "RatingProvided",
        "Confidence",
        "ConfidenceRT",
        "EstimatedThreshold",
        "EstimatedSlope",
    ]
    compact_trials = trials[keep]
    psi = pd.concat(
        [
            summarize_posterior(path, modality)
            for modality, path in POSTERIOR_FILES.items()
        ],
        ignore_index=True,
    )

    merged = compact_trials.merge(
        psi, on=["Modality", "adaptive_trial"], validate="one_to_one"
    )
    if not np.allclose(merged["EstimatedThreshold"], merged["alpha_mean"]):
        raise ValueError("Posterior summaries do not reproduce EstimatedThreshold")
    if not np.allclose(merged["EstimatedSlope"], merged["sigma_mean"]):
        raise ValueError("Posterior summaries do not reproduce EstimatedSlope")

    SMALL_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    compact_trials.to_csv(TRIAL_BUNDLE, index=False, compression="gzip")
    psi.to_csv(PSI_BUNDLE, index=False, compression="gzip")
    trials[source_columns].to_csv(EXAMPLE_TRIAL_FILE, index=False)
    return compact_trials, psi


def load_bundle() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load committed compact inputs when the source files are unavailable."""

    return pd.read_csv(TRIAL_BUNDLE), pd.read_csv(PSI_BUNDLE)


def build_session_bundle() -> pd.DataFrame:
    """Reduce completed VMP2 sessions to deidentified collection checks."""

    files = sorted(SESSION_DIR.glob("*HRD_final.txt"))
    if not files:
        raise FileNotFoundError(f"No completed sessions found under {SESSION_DIR}")

    rows = []
    for session_number, path in enumerate(files, start=1):
        data = pd.read_csv(path)
        if len(data) != 120 or not data["TrialType"].eq("psi").all():
            raise ValueError(f"Unexpected task design in {path.name}")
        for modality, trials in data.groupby("Modality"):
            decision_provided = trials["Decision"].isin(["More", "Less"])
            rows.append(
                {
                    "session": f"session-{session_number:03d}",
                    "Modality": modality,
                    "trials": len(trials),
                    "missed_decisions_percent": 100 * (1 - decision_provided.mean()),
                    "median_decision_rt": trials["DecisionRT"].median(),
                    "confidence_sd": trials["Confidence"].std(),
                    "unique_confidence": trials["Confidence"].nunique(),
                    "accuracy_percent": 100 * trials["ResponseCorrect"].mean(),
                    "faster_percent": 100 * trials["Decision"].eq("More").mean(),
                }
            )
    summary = pd.DataFrame(rows)
    summary.to_csv(SESSION_BUNDLE, index=False, compression="gzip")
    return summary


def load_session_bundle() -> pd.DataFrame:
    """Load the compact across-session collection checks."""

    return pd.read_csv(SESSION_BUNDLE)


def finish_figure(fig: plt.Figure, name: str) -> None:
    """Lay out, save, and close one documentation figure."""

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_stimulus_trace(trials: pd.DataFrame) -> None:
    """Show stimulus placement and choices for the two adaptive staircases."""

    fig, axes = plt.subplots(2, 1, figsize=(9.2, 5.7), sharex=True, sharey=True)
    titles = {
        "Intero": "Cardiac comparison (Intero)",
        "Extero": "Auditory comparison (Extero)",
    }
    for ax, modality in zip(axes, ["Intero", "Extero"]):
        d = trials[trials["Modality"] == modality].sort_values("adaptive_trial")
        ax.axhline(0, color=LIGHT, linestyle=":", linewidth=1.0)
        ax.plot(
            d["adaptive_trial"],
            d["Alpha"],
            color=GREY,
            linewidth=0.9,
            alpha=0.7,
            zorder=1,
        )
        for choice, marker, colour in [
            ("faster", "^", RED),
            ("slower", "v", BLUE),
        ]:
            q = d[d["choice"] == choice]
            ax.scatter(
                q["adaptive_trial"],
                q["Alpha"],
                marker=marker,
                s=31,
                facecolor=colour,
                edgecolor="white",
                linewidth=0.35,
                zorder=3,
            )
        missed = d[~d["DecisionProvided"].astype(bool)]
        if len(missed):
            ax.scatter(
                missed["adaptive_trial"],
                missed["Alpha"],
                marker="x",
                s=34,
                color=BLACK,
                linewidth=1.2,
                zorder=4,
            )
        ax.text(
            0.01,
            0.93,
            titles[modality],
            transform=ax.transAxes,
            va="top",
            fontweight="semibold",
        )
        ax.set_ylabel("Stimulus ΔBPM")
        ax.set_ylim(-34, 34)

    axes[-1].set_xlabel("Trial within modality")
    handles = [
        Line2D([], [], marker="^", linestyle="", color=RED, label="faster choice"),
        Line2D([], [], marker="v", linestyle="", color=BLUE, label="slower choice"),
        Line2D([], [], color=GREY, linewidth=1, label="stimulus sequence"),
    ]
    axes[0].legend(handles=handles, loc="lower right", frameon=False, ncol=3)
    finish_figure(fig, "fig_inspection_stimulus_trace.png")


def bin_responses(d: pd.DataFrame, width: float = 8.0) -> pd.DataFrame:
    """Bin only for a descriptive participant-level response plot."""

    edges = np.arange(-44, 45, width)
    work = d[d["Decision"].isin(["More", "Less"])].copy()
    work["faster"] = work["Decision"].eq("More").astype(float)
    work["bin"] = pd.cut(work["Alpha"], edges, include_lowest=True)
    return (
        work.groupby(["Modality", "bin"], observed=True)
        .agg(x=("Alpha", "mean"), proportion=("faster", "mean"), n=("faster", "size"))
        .reset_index()
    )


def add_distribution(
    ax: plt.Axes,
    values: np.ndarray,
    position: float,
    colour: str,
    rng: np.random.Generator,
    width: float = 0.28,
) -> None:
    """Add a light violin, deterministic jitter, median, and interquartile range."""

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    parts = ax.violinplot(
        values,
        positions=[position],
        widths=width * 1.7,
        showextrema=False,
    )
    for body in parts["bodies"]:
        body.set_facecolor(colour)
        body.set_edgecolor("none")
        body.set_alpha(0.16)
    jitter = rng.uniform(-width * 0.45, width * 0.45, len(values))
    ax.scatter(
        position + jitter,
        values,
        s=10,
        color=colour,
        alpha=0.34,
        edgecolor="none",
        zorder=2,
    )
    q25, median, q75 = np.quantile(values, [0.25, 0.5, 0.75])
    ax.vlines(position, q25, q75, color=colour, linewidth=3.6, zorder=3)
    ax.scatter(
        position,
        median,
        s=38,
        facecolor="white",
        edgecolor=colour,
        linewidth=1.5,
        zorder=4,
    )


def save_responses_and_timing(trials: pd.DataFrame) -> None:
    """Plot response proportions and response times as separate figures."""

    fig, ax = plt.subplots(figsize=(6.4, 4.1))
    binned = bin_responses(trials)
    ax.axhline(0.5, color=LIGHT, linestyle=":", linewidth=1.0)
    ax.axvline(0, color=LIGHT, linestyle=":", linewidth=1.0)
    for modality in ["Intero", "Extero"]:
        d = binned[binned["Modality"] == modality]
        colour = MODALITY_COLOURS[modality]
        ax.plot(d["x"], d["proportion"], color=colour, linewidth=1.5)
        ax.scatter(
            d["x"],
            d["proportion"],
            s=18 + 10 * np.sqrt(d["n"]),
            color=colour,
            edgecolor="white",
            linewidth=0.5,
            zorder=3,
        )
        last = d.iloc[-1]
        ax.text(
            last["x"] + 1.2, last["proportion"], modality, color=colour, va="center"
        )
    ax.set(
        xlabel="Stimulus ΔBPM",
        ylabel='Proportion choosing "faster"',
        title="Choices follow stimulus intensity",
        ylim=(-0.04, 1.04),
    )
    ax.text(
        0.02,
        0.04,
        "Point area shows trials per bin",
        transform=ax.transAxes,
        color=GREY,
        fontsize=8.2,
    )
    finish_figure(fig, "fig_inspection_responses.png")

    fig, ax = plt.subplots(figsize=(6.4, 4.1))
    rng = np.random.default_rng(410)
    positions = [0.82, 1.18, 1.82, 2.18]
    groups = [
        ("DecisionRT", "Intero", RED),
        ("DecisionRT", "Extero", BLUE),
        ("ConfidenceRT", "Intero", RED),
        ("ConfidenceRT", "Extero", BLUE),
    ]
    for position, (column, modality, colour) in zip(positions, groups):
        values = trials.loc[trials["Modality"] == modality, column].to_numpy()
        add_distribution(ax, values, position, colour, rng, width=0.26)
    ax.axhline(5, color=GREY, linestyle=":", linewidth=1.0)
    ax.text(
        2.38, 4.92, "response limit", ha="right", va="top", color=GREY, fontsize=8.2
    )
    ax.set(
        xticks=[1, 2],
        xticklabels=["Decision", "Confidence"],
        ylabel="Response time (s)",
        title="Response times stay clear of the limit",
        xlim=(0.55, 2.45),
        ylim=(0, 5.2),
    )
    handles = [
        Line2D([], [], marker="o", linestyle="", color=RED, label="Intero"),
        Line2D([], [], marker="o", linestyle="", color=BLUE, label="Extero"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left")
    finish_figure(fig, "fig_inspection_timing.png")


def save_confidence(trials: pd.DataFrame) -> None:
    """Compare confidence by choice and by objective response outcome."""

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), sharey=True)
    rng = np.random.default_rng(341)
    specifications = [
        (
            axes[0],
            "choice",
            [("slower", BLUE), ("faster", RED)],
            "Confidence by response choice",
        ),
        (
            axes[1],
            "outcome",
            [("incorrect", GOLD), ("correct", NAVY)],
            "Confidence by response accuracy",
        ),
    ]
    for ax, column, groups, title in specifications:
        for position, (group, colour) in enumerate(groups, start=1):
            values = trials.loc[trials[column] == group, "Confidence"].to_numpy()
            add_distribution(ax, values, position, colour, rng, width=0.35)
            median = np.nanmedian(values)
            ax.text(
                position,
                104,
                f"median {median:.0f}",
                color=colour,
                ha="center",
                va="bottom",
                fontsize=8.2,
            )
        ax.set(
            xticks=[1, 2],
            xticklabels=[group for group, _ in groups],
            title=title,
            ylim=(-4, 114),
            xlim=(0.5, 2.5),
        )
    axes[0].set_ylabel("Confidence rating")
    finish_figure(fig, "fig_inspection_confidence.png")


def save_heart_rate(trials: pd.DataFrame) -> None:
    """Plot the measured heart rate across cardiac trials."""

    heart = trials.loc[trials["Modality"] == "Intero"].sort_values("adaptive_trial")
    median = heart["listenBPM"].median()
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(
        heart["adaptive_trial"],
        heart["listenBPM"],
        color=LIGHT,
        linewidth=1.2,
    )
    ax.scatter(
        heart["adaptive_trial"],
        heart["listenBPM"],
        color=RED,
        edgecolor="white",
        linewidth=0.45,
        s=25,
        zorder=3,
    )
    ax.axhline(median, color=NAVY, linestyle=":", linewidth=1.2)
    ax.text(
        60,
        median,
        f"session median  {median:.0f} BPM",
        color=NAVY,
        ha="right",
        va="bottom",
        fontsize=8.2,
    )
    ax.set(
        xlabel="Cardiac trial",
        ylabel="Measured heart rate (BPM)",
        title="Heart rate measured during each listening interval",
        xlim=(0, 61),
    )
    finish_figure(fig, "fig_inspection_heart_rate.png")


def save_psi_monitor(psi: pd.DataFrame) -> None:
    """Show the evolving marginal uncertainty for both Psi parameters."""

    fig, axes = plt.subplots(1, 2, figsize=(10.3, 4.0))
    specifications = [
        (
            axes[0],
            "alpha",
            "Threshold α (ΔBPM)",
            "Online threshold posterior",
        ),
        (
            axes[1],
            "sigma",
            "Psi slope σ (ΔBPM)",
            "Online slope posterior",
        ),
    ]
    for ax, stem, ylabel, title in specifications:
        if stem == "alpha":
            ax.axhline(0, color=LIGHT, linestyle=":", linewidth=1.0)
        for modality in ["Intero", "Extero"]:
            d = psi[psi["Modality"] == modality].sort_values("adaptive_trial")
            colour = MODALITY_COLOURS[modality]
            ax.fill_between(
                d["adaptive_trial"],
                d[f"{stem}_lo"],
                d[f"{stem}_hi"],
                color=colour,
                alpha=0.11,
                linewidth=0,
            )
            ax.plot(
                d["adaptive_trial"],
                d[f"{stem}_mean"],
                color=colour,
                linewidth=1.7,
            )
            last = d.iloc[-1]
            ax.text(
                last["adaptive_trial"] + 1.0,
                last[f"{stem}_mean"],
                f"{modality}  {last[f'{stem}_mean']:.1f}",
                color=colour,
                va="center",
                fontsize=8.5,
            )
        ax.set(
            xlabel="Trial within modality",
            ylabel=ylabel,
            title=title,
            xlim=(1, 68),
        )
    axes[0].text(
        0.03,
        0.05,
        "Bands show 95% of the marginal Psi posterior",
        transform=axes[0].transAxes,
        color=GREY,
        fontsize=8.2,
    )
    finish_figure(fig, "fig_inspection_psi.png")


def save_warning_patterns() -> None:
    """Illustrate common response, timing, and confidence warning patterns."""

    fig, axes = plt.subplots(2, 2, figsize=(9.8, 6.4))
    x = np.linspace(-45, 45, 200)
    expected = 1 / (1 + np.exp(-x / 8))
    axes[0, 0].plot(x, expected, color=NAVY, linewidth=2)
    axes[0, 0].plot(x, 1 - expected, color=GOLD, linewidth=2, linestyle="--")
    axes[0, 0].text(20, 0.90, "expected mapping", color=NAVY, ha="center")
    axes[0, 0].text(20, 0.10, "reversed mapping", color=GOLD, ha="center")
    axes[0, 0].axhline(0.5, color=LIGHT, linestyle=":")
    axes[0, 0].axvline(0, color=LIGHT, linestyle=":")
    axes[0, 0].set(
        xlabel="Stimulus ΔBPM",
        ylabel='Proportion "faster"',
        title="Response mapping",
        ylim=(-0.03, 1.03),
    )

    trial = np.arange(1, 61)
    varied = (np.sin(trial * 0.75) > 0).astype(float)
    axes[0, 1].scatter(trial, varied, color=GREY, s=13, alpha=0.35)
    axes[0, 1].plot(trial, np.ones_like(trial), color=RED, linewidth=2)
    axes[0, 1].text(59, 0.95, "one button", color=RED, ha="right", va="top")
    axes[0, 1].set(
        xlabel="Trial",
        yticks=[0, 1],
        yticklabels=["slower", "faster"],
        title="Choice sequence",
        ylim=(-0.25, 1.25),
    )

    rng = np.random.default_rng(47)
    ordinary_rt = np.clip(rng.lognormal(mean=0.45, sigma=0.28, size=60), 0, 4.6)
    limit_rt = np.clip(rng.normal(loc=4.75, scale=0.18, size=60), 4.0, 5.0)
    add_distribution(axes[1, 0], ordinary_rt, 1, BLUE, rng, width=0.34)
    add_distribution(axes[1, 0], limit_rt, 2, GOLD, rng, width=0.34)
    axes[1, 0].axhline(5, color=GREY, linestyle=":")
    axes[1, 0].set(
        xticks=[1, 2],
        xticklabels=["typical spread", "near limit"],
        ylabel="Response time (s)",
        title="Response timing",
        ylim=(0, 5.2),
    )

    varied_confidence = np.clip(
        55 + 25 * np.sin(trial / 5) + rng.normal(0, 8, 60), 0, 100
    )
    fixed_confidence = np.full_like(trial, 50)
    axes[1, 1].scatter(trial, varied_confidence, color=BLUE, s=13, alpha=0.45)
    axes[1, 1].plot(trial, fixed_confidence, color=RED, linewidth=2)
    axes[1, 1].text(59, 47, "one rating", color=RED, ha="right", va="top")
    axes[1, 1].set(
        xlabel="Trial",
        ylabel="Confidence rating",
        title="Confidence-scale use",
        ylim=(-4, 104),
    )
    finish_figure(fig, "fig_inspection_warning_patterns.png")


def save_session_overview(summary: pd.DataFrame) -> None:
    """Show how participant-level checks distribute across VMP2 sessions."""

    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.6))
    specifications = [
        ("missed_decisions_percent", "Trials without a decision (%)", (0, None)),
        ("median_decision_rt", "Median decision time (s)", (0, 5)),
        ("confidence_sd", "Within-session confidence SD", (0, None)),
        ("accuracy_percent", "Descriptive accuracy (%)", (0, 100)),
    ]
    rng = np.random.default_rng(512)
    for ax, (column, ylabel, limits) in zip(axes.flat, specifications):
        for position, modality in enumerate(["Extero", "Intero"], start=1):
            values = summary.loc[summary["Modality"] == modality, column].to_numpy()
            add_distribution(
                ax,
                values,
                position,
                MODALITY_COLOURS[modality],
                rng,
                width=0.34,
            )
        ax.set(
            xticks=[1, 2],
            xticklabels=["Extero", "Intero"],
            ylabel=ylabel,
            xlim=(0.5, 2.5),
        )
        lower, upper = limits
        if upper is not None:
            ax.set_ylim(lower, upper)
        elif lower is not None:
            ax.set_ylim(bottom=lower)
    axes[1, 1].text(
        0.98,
        0.04,
        "Accuracy is descriptive",
        transform=axes[1, 1].transAxes,
        color=GREY,
        ha="right",
        fontsize=8.2,
    )
    fig.suptitle("The same checks across 161 completed VMP2 sessions", y=1.01)
    finish_figure(fig, "fig_inspection_sessions.png")


def main() -> None:
    """Build compact inputs when possible, then regenerate the figures."""

    set_style()
    if TRIAL_FILE.exists() and all(path.exists() for path in POSTERIOR_FILES.values()):
        trials, psi = build_compact_bundle()
    else:
        trials, psi = load_bundle()
    if SESSION_DIR.exists() and any(SESSION_DIR.glob("*HRD_final.txt")):
        sessions = build_session_bundle()
    else:
        sessions = load_session_bundle()
    save_stimulus_trace(trials)
    save_responses_and_timing(trials)
    save_confidence(trials)
    save_heart_rate(trials)
    save_psi_monitor(psi)
    save_warning_patterns()
    save_session_overview(sessions)
    print(f"Wrote compact inputs to {SMALL_DIR}")
    print(f"Wrote tutorial figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
