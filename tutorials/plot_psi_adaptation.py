"""Draw the Psi figures used by the psychophysics tutorial.

The input is the example HRD session bundled with the documentation. Cardioception
saves the joint Psi posterior over threshold and slope after every adaptive trial,
so the animation shows the actual online calculation rather than a simulation.

Run from anywhere with::

    python tutorials/plot_psi_adaptation.py
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.special import ndtr
from scipy.stats import gaussian_kde


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "source" / "examples" / "templates" / "data" / "HRD"
FIG_DIR = ROOT / "docs" / "source" / "images" / "tutorials"
SMALL_DIR = ROOT / "tutorials" / "results" / "small"

TRIAL_PATH = DATA_DIR / "HRD_final.txt"
POSTERIOR_PATH = DATA_DIR / "Intero_posterior.npy"

# These grids and the blind-response rate match cardioception.HRD.parameters.
ALPHA = np.arange(-50.5, 51.5, 1.0)
SIGMA = np.arange(0.1, 25.1, 0.1)
INTENSITY = np.arange(-50.5, 51.5, 1.0)
CURVE_X = np.linspace(-50.5, 50.5, 401)
DELTA = 0.02

NAVY = "#1f3352"
RED = "#A8455F"
BLUE = "#2F6F8F"
GREY = "#a4acb8"
LIGHT = "#e8eaf0"


def normalize(p: np.ndarray) -> np.ndarray:
    """Return a probability array whose entries sum to one."""

    total = p.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Psi posterior has no finite probability mass")
    return p / total


def psi_probability(x: np.ndarray, alpha: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """P('faster') under PsychoPy's Yes/No cumulative Gaussian Psi model."""

    return 0.5 * DELTA + (1 - DELTA) * ndtr((x - alpha) / sigma)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """Quantile for an ordered grid with probability weights."""

    cdf = np.cumsum(weights)
    cdf /= cdf[-1]
    return float(np.interp(q, cdf, values))


def load_data() -> tuple[pd.DataFrame, np.ndarray]:
    """Load adaptive interoceptive trials and their stored posteriors."""

    raw = pd.read_csv(TRIAL_PATH)
    trials = raw.loc[
        (raw["Modality"] == "Intero") & (raw["TrialType"] == "psi")
    ].reset_index(drop=True)
    posterior = np.load(POSTERIOR_PATH)

    expected_shape = (len(trials), len(ALPHA), len(SIGMA))
    if posterior.shape != expected_shape:
        raise ValueError(
            f"Expected posterior shape {expected_shape}, found {posterior.shape}"
        )

    # The stored estimates are posterior means. This guards the grid definition
    # and prevents a plausible-looking figure if the task configuration changes.
    final = normalize(posterior[-1])
    alpha_mean = np.sum(final.sum(axis=1) * ALPHA)
    sigma_mean = np.sum(final.sum(axis=0) * SIGMA)
    saved = trials.iloc[-1]
    if not np.allclose(
        [alpha_mean, sigma_mean],
        [saved["EstimatedThreshold"], saved["EstimatedSlope"]],
    ):
        raise ValueError("Posterior grid does not reproduce the saved Psi estimates")

    return trials, posterior


def posterior_summaries(posterior: np.ndarray) -> pd.DataFrame:
    """Summarize the online alpha and sigma posterior after every trial."""

    rows = []
    for trial, raw_p in enumerate(posterior, start=1):
        p = normalize(raw_p)
        pa = p.sum(axis=1)
        ps = p.sum(axis=0)
        rows.append(
            {
                "trial": trial,
                "alpha": np.sum(pa * ALPHA),
                "alpha_lo": weighted_quantile(ALPHA, pa, 0.025),
                "alpha_hi": weighted_quantile(ALPHA, pa, 0.975),
                "sigma": np.sum(ps * SIGMA),
            }
        )
    return pd.DataFrame(rows)


def curve_interval(
    p: np.ndarray, n: int = 1600, seed: int = 1024
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample the joint grid and return a pointwise interval for the Psi curve."""

    rng = np.random.default_rng(seed)
    flat = normalize(p).ravel()
    chosen = rng.choice(flat.size, size=n, replace=True, p=flat)
    ai, si = np.unravel_index(chosen, p.shape)
    curves = psi_probability(CURVE_X[:, None], ALPHA[ai][None, :], SIGMA[si][None, :])
    return tuple(np.quantile(curves, [0.025, 0.5, 0.975], axis=1))


def entropy(p: np.ndarray, axis: tuple[int, ...] | None = None) -> np.ndarray:
    """Shannon entropy in nats, treating zero-probability cells as zero."""

    return -np.sum(np.where(p > 0, p * np.log(p), 0.0), axis=axis)


def expected_information(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Expected information gain for every candidate stimulus intensity."""

    p = normalize(p)
    likelihood = psi_probability(
        INTENSITY[:, None, None],
        ALPHA[None, :, None],
        SIGMA[None, None, :],
    )
    prob_faster = np.sum(likelihood * p[None, :, :], axis=(1, 2))

    post_faster = likelihood * p[None, :, :]
    post_faster /= prob_faster[:, None, None]
    post_slower = (1 - likelihood) * p[None, :, :]
    post_slower /= (1 - prob_faster)[:, None, None]

    expected_entropy = prob_faster * entropy(post_faster, axis=(1, 2))
    expected_entropy += (1 - prob_faster) * entropy(post_slower, axis=(1, 2))
    return entropy(p) - expected_entropy, likelihood


def style() -> None:
    """Set a restrained documentation figure style."""

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.edgecolor": "#5f6670",
            "axes.linewidth": 0.7,
            "xtick.color": "#5f6670",
            "ytick.color": "#5f6670",
            "text.color": "#333333",
        }
    )


def draw_trace(
    ax: plt.Axes,
    trials: pd.DataFrame,
    summaries: pd.DataFrame,
    through: int,
) -> None:
    """Draw selected intensities and the evolving alpha posterior."""

    shown = trials.iloc[:through]
    sm = summaries.iloc[:through]
    trial_number = np.arange(1, through + 1)

    ax.axhline(0, color=GREY, linestyle=":", linewidth=0.8)
    ax.fill_between(sm["trial"], sm["alpha_lo"], sm["alpha_hi"], color=RED, alpha=0.13)
    ax.plot(sm["trial"], sm["alpha"], color=RED, linewidth=1.3, label="Psi threshold")

    faster = shown["Decision"].eq("More").to_numpy()
    ax.scatter(
        trial_number[~faster],
        shown.loc[~faster, "Alpha"],
        marker="v",
        s=24,
        facecolor=BLUE,
        edgecolor="white",
        linewidth=0.4,
        label="slower response",
        zorder=3,
    )
    ax.scatter(
        trial_number[faster],
        shown.loc[faster, "Alpha"],
        marker="^",
        s=24,
        facecolor=RED,
        edgecolor="white",
        linewidth=0.4,
        label="faster response",
        zorder=3,
    )
    ax.set(
        xlim=(0, len(trials) + 1),
        ylim=(-53, 53),
        xlabel="Adaptive trial",
        ylabel="ΔBPM",
    )
    ax.set_title("Stimuli and responses")


def draw_posterior(ax: plt.Axes, p: np.ndarray) -> None:
    """Draw the current joint threshold and sigma posterior."""

    p = normalize(p)
    ax.imshow(
        (p / p.max()).T,
        origin="lower",
        aspect="auto",
        extent=(ALPHA[0], ALPHA[-1], SIGMA[0], SIGMA[-1]),
        cmap="magma_r",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )
    pa = p.sum(axis=1)
    ps = p.sum(axis=0)
    ax.scatter(
        np.sum(pa * ALPHA),
        np.sum(ps * SIGMA),
        s=28,
        color=NAVY,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    ax.set(xlabel="Threshold α (ΔBPM)", ylabel="Psi slope σ (ΔBPM)")
    ax.set_title("Joint Psi posterior")


def draw_curve(
    ax: plt.Axes,
    trials: pd.DataFrame,
    p: np.ndarray,
    through: int,
    seed: int,
) -> None:
    """Draw the current psychometric function and accumulated responses."""

    p = normalize(p)
    lo, median, hi = curve_interval(p, n=700, seed=seed)
    ax.fill_between(CURVE_X, lo, hi, color=RED, alpha=0.16)
    ax.plot(CURVE_X, median, color=RED, linewidth=1.8)
    ax.axhline(0.5, color=GREY, linestyle=":", linewidth=0.8)

    pa = p.sum(axis=1)
    alpha_mean = np.sum(pa * ALPHA)
    ax.axvline(alpha_mean, color=NAVY, linestyle="--", linewidth=1.0)

    shown = trials.iloc[:through]
    faster = shown["Decision"].eq("More").to_numpy()
    ax.scatter(
        shown.loc[~faster, "Alpha"],
        np.full((~faster).sum(), 0.015),
        marker="v",
        s=18,
        color=BLUE,
        alpha=0.65,
        clip_on=False,
    )
    ax.scatter(
        shown.loc[faster, "Alpha"],
        np.full(faster.sum(), 0.985),
        marker="^",
        s=18,
        color=RED,
        alpha=0.65,
        clip_on=False,
    )
    ax.set(
        xlim=(-53, 53),
        ylim=(-0.03, 1.03),
        xlabel="ΔBPM (tone - measured heart rate)",
        ylabel='P(response "faster")',
    )
    ax.set_yticks([0, 0.5, 1])
    ax.set_title("Implied psychometric function")


def save_adaptation_figure(
    trials: pd.DataFrame, posterior: np.ndarray, summaries: pd.DataFrame
) -> None:
    """Save the static trace, posterior, and curve figure."""

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.55))
    draw_trace(axes[0], trials, summaries, len(trials))
    draw_posterior(axes[1], posterior[-1])
    draw_curve(axes[2], trials, posterior[-1], len(trials), seed=481)

    handles, labels = axes[0].get_legend_handles_labels()
    order = [1, 2, 0]
    axes[0].legend(
        [handles[i] for i in order],
        [labels[i] for i in order],
        frameon=False,
        fontsize=7.5,
        loc="lower left",
    )
    fig.suptitle("How one Psi staircase becomes a psychometric function", y=1.01)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_psi_adaptation.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_information_figure(trials: pd.DataFrame, posterior: np.ndarray) -> None:
    """Show how Psi selects the next intensity by expected information gain."""

    completed = 8
    p = normalize(posterior[completed - 1])
    gain, likelihood = expected_information(p)
    chosen_index = int(np.argmax(gain))
    chosen_x = INTENSITY[chosen_index]
    observed_next = float(trials.iloc[completed]["Alpha"])
    if not np.isclose(chosen_x, observed_next):
        raise ValueError(
            f"Expected Psi to choose {chosen_x}, but the saved trial used {observed_next}"
        )

    likelihood_at_x = likelihood[chosen_index]
    post_faster = normalize(p * likelihood_at_x)
    post_slower = normalize(p * (1 - likelihood_at_x))

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.35))
    draw_posterior(axes[0], p)
    axes[0].set_title(f"Belief after {completed} trials")

    axes[1].plot(INTENSITY, gain, color=NAVY, linewidth=1.6)
    axes[1].axvline(chosen_x, color=RED, linestyle="--", linewidth=1.1)
    axes[1].scatter([chosen_x], [gain[chosen_index]], color=RED, s=28, zorder=3)
    axes[1].annotate(
        f"next stimulus\n{chosen_x:+.1f} ΔBPM",
        xy=(chosen_x, gain[chosen_index]),
        xytext=(chosen_x + 12, gain[chosen_index] * 0.82),
        arrowprops={"arrowstyle": "->", "color": RED, "lw": 0.8},
        fontsize=8,
        color=RED,
    )
    axes[1].set(
        xlabel="Candidate stimulus (ΔBPM)",
        ylabel="Expected information gain (nats)",
        title="Evaluate every available stimulus",
    )

    axes[2].plot(ALPHA, p.sum(axis=1), color=GREY, linestyle="--", label="current")
    axes[2].plot(
        ALPHA, post_slower.sum(axis=1), color=BLUE, label="if response is slower"
    )
    axes[2].plot(
        ALPHA, post_faster.sum(axis=1), color=RED, label="if response is faster"
    )
    axes[2].axvline(chosen_x, color=LIGHT, linewidth=1.0)
    axes[2].set(
        xlabel="Threshold α (ΔBPM)",
        ylabel="Posterior probability",
        title="Anticipate both possible updates",
    )
    axes[2].legend(frameon=False, fontsize=7.5)

    fig.suptitle("Psi chooses the trial expected to reduce uncertainty most", y=1.01)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_psi_information.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_response_coding_figure() -> None:
    """Contrast the monotonic response model with ground-truth accuracy."""

    x = np.r_[np.linspace(-45, -0.5, 220), np.linspace(0.5, 45, 220)]
    alpha = -10.0
    sigma = 8.0
    p_faster = psi_probability(x, alpha, sigma)
    p_correct = np.where(x < 0, 1 - p_faster, p_faster)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.3), sharey=True)
    for ax in axes:
        ax.axhline(0.5, color=GREY, linestyle=":", linewidth=0.8)
        ax.axvline(0, color=GREY, linestyle=":", linewidth=0.8)
        ax.set(xlim=(-46, 46), ylim=(-0.02, 1.02), xlabel="ΔBPM")
        ax.set_yticks([0, 0.5, 1])

    axes[0].plot(x, p_faster, color=RED, linewidth=2)
    axes[0].axvline(alpha, color=NAVY, linestyle="--", linewidth=1.0)
    axes[0].annotate(
        "threshold α",
        xy=(alpha, 0.5),
        xytext=(-35, 0.62),
        arrowprops={"arrowstyle": "->", "color": NAVY, "lw": 0.8},
        color=NAVY,
        fontsize=8,
    )
    axes[0].set(
        ylabel="Probability",
        title='Model P(response "faster")',
    )

    neg = x < 0
    axes[1].plot(x[neg], p_correct[neg], color=BLUE, linewidth=2)
    axes[1].plot(x[~neg], p_correct[~neg], color=RED, linewidth=2)
    axes[1].text(-31, 0.92, 'correct = "slower"', color=BLUE, fontsize=8)
    axes[1].text(8, 0.92, 'correct = "faster"', color=RED, fontsize=8)
    axes[1].set(title="Derived P(objectively correct)")

    fig.suptitle("Response probability and accuracy are different functions", y=1.01)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_response_vs_accuracy.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def load_single_subject() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load compact outputs from the worked single-subject brms fit."""

    draws = pd.read_csv(SMALL_DIR / "psy_single_subject_draws.csv.gz")
    curve = pd.read_csv(SMALL_DIR / "psy_single_subject_curve.csv.gz")
    observed = pd.read_csv(SMALL_DIR / "psy_single_subject_data.csv.gz")
    return draws, curve, observed


def save_single_subject_fit(
    draws: pd.DataFrame, curve: pd.DataFrame, observed: pd.DataFrame
) -> None:
    """Plot real trials with the posterior psychometric function."""

    fig, ax = plt.subplots(figsize=(8.7, 4.25))
    ax.axhline(0.5, color=GREY, linestyle=":", linewidth=0.8)
    ax.axvline(0, color=GREY, linestyle=":", linewidth=0.8)

    ax.fill_between(curve["x"], curve["q2.5"], curve["q97.5"], color=RED, alpha=0.10)
    ax.fill_between(curve["x"], curve["q10"], curve["q90"], color=RED, alpha=0.14)
    ax.fill_between(curve["x"], curve["q25"], curve["q75"], color=RED, alpha=0.20)
    ax.plot(curve["x"], curve["median"], color=RED, linewidth=2.0)

    alpha_median = float(draws["alpha"].median())
    sigma_median = float(draws["sigma"].median())
    lapse_median = float(draws["lapse"].median())
    ax.axvline(alpha_median, color=NAVY, linestyle="--", linewidth=1.1)

    sizes = 22 + 18 * np.sqrt(observed["n"])
    ax.scatter(
        observed["x"],
        observed["proportion"],
        s=sizes,
        color=NAVY,
        edgecolor="white",
        linewidth=0.55,
        alpha=0.72,
        zorder=3,
    )

    ax.text(
        0.025,
        0.96,
        f"posterior medians\nα = {alpha_median:+.1f} ΔBPM\n"
        f"σ = {sigma_median:.1f} ΔBPM\nlapse = {100 * lapse_median:.1f}%",
        transform=ax.transAxes,
        va="top",
        color=NAVY,
        fontsize=8.3,
        bbox={"facecolor": "white", "edgecolor": LIGHT, "alpha": 0.92, "pad": 5},
    )
    ax.text(
        0.975,
        0.05,
        "Bands: 50%, 80%, and 95% credible intervals",
        transform=ax.transAxes,
        ha="right",
        color="#68717d",
        fontsize=7.8,
    )
    ax.set(
        xlim=(-53, 53),
        ylim=(-0.03, 1.03),
        xlabel="ΔBPM (tone - measured heart rate)",
        ylabel='P(response "faster")',
        title="One participant's trials and posterior psychometric function",
    )
    ax.set_yticks([0, 0.5, 1])
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_single_subject_brms.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def density_panel(
    ax: plt.Axes,
    prior: np.ndarray,
    posterior: np.ndarray,
    label: str,
) -> None:
    """Draw prior and posterior densities on a common scientific scale."""

    combined = np.r_[prior, posterior]
    lower, upper = np.quantile(combined, [0.001, 0.999])
    if label == "Lapse probability":
        lower = 0
        upper = min(0.6, upper)
    grid = np.linspace(lower, upper, 350)
    prior_density = gaussian_kde(prior)(grid)
    posterior_density = gaussian_kde(posterior)(grid)

    ax.fill_between(grid, prior_density, color=GREY, alpha=0.24)
    ax.plot(grid, prior_density, color="#87909c", linewidth=1.2, label="prior")
    ax.fill_between(grid, posterior_density, color=RED, alpha=0.18)
    ax.plot(grid, posterior_density, color=RED, linewidth=1.6, label="posterior")
    ax.set(xlim=(lower, upper), xlabel=label, ylabel="Density")
    ax.set_yticks([])


def save_single_subject_sampling(draws: pd.DataFrame) -> None:
    """Show prior learning and chain mixing for the single-subject fit."""

    columns = [
        ("alpha", "prior_alpha", "Threshold α (ΔBPM)"),
        ("sigma", "prior_sigma", "Slope σ (ΔBPM)"),
        ("lapse", "prior_lapse", "Lapse probability"),
    ]
    chain_colors = ["#1f3352", "#2F6F8F", "#A8455F", "#D88768"]
    fig, axes = plt.subplots(2, 3, figsize=(11.7, 6.1))

    for j, (col, prior_col, label) in enumerate(columns):
        density_panel(
            axes[0, j],
            draws[prior_col].to_numpy(),
            draws[col].to_numpy(),
            label,
        )

    axes[0, 0].legend(frameon=False, fontsize=8)

    for j, (col, _, label) in enumerate(columns):
        ax = axes[1, j]
        for color, chain in zip(chain_colors, sorted(draws["chain"].unique())):
            d = draws.loc[draws["chain"] == chain]
            ax.plot(
                d["iteration"],
                d[col],
                color=color,
                linewidth=0.45,
                alpha=0.75,
                label=f"chain {chain}",
            )
        ax.set(xlabel="Post-warmup iteration", ylabel=label)
        if j == 0:
            ax.legend(frameon=False, fontsize=7, ncol=2)

    fig.suptitle(
        "From priors to the sampled posterior for one participant\n"
        "4 chains, 0 divergences, maximum R-hat = 1.001",
        y=1.01,
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(
        FIG_DIR / "fig_single_subject_sampling.png", dpi=300, bbox_inches="tight"
    )
    plt.close(fig)


def save_animation(
    trials: pd.DataFrame, posterior: np.ndarray, summaries: pd.DataFrame
) -> None:
    """Animate the stored posterior after each adaptive trial."""

    frames: list[Image.Image] = []
    for t, p in enumerate(posterior, start=1):
        fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.25), dpi=82)
        draw_trace(axes[0], trials, summaries, t)
        draw_posterior(axes[1], p)
        draw_curve(axes[2], trials, p, t, seed=1000 + t)

        pn = normalize(p)
        alpha_mean = np.sum(pn.sum(axis=1) * ALPHA)
        sigma_mean = np.sum(pn.sum(axis=0) * SIGMA)
        fig.suptitle(
            f"Psi after {t} adaptive trial{'s' if t != 1 else ''}"
            f"   α = {alpha_mean:+.1f} ΔBPM, σ = {sigma_mean:.1f} ΔBPM",
            y=1.01,
            fontsize=10,
        )
        fig.tight_layout()

        buffer = BytesIO()
        fig.savefig(
            buffer, format="png", dpi=82, bbox_inches="tight", facecolor="white"
        )
        plt.close(fig)
        buffer.seek(0)
        frame = Image.open(buffer).convert("RGB")
        frames.append(frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT))

    gif_path = FIG_DIR / "fig_psi_adaptation.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=170,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> None:
    """Generate all Psi tutorial figures."""

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    style()
    trials, posterior = load_data()
    draws, curve, observed = load_single_subject()
    summaries = posterior_summaries(posterior)
    save_response_coding_figure()
    save_information_figure(trials, posterior)
    save_adaptation_figure(trials, posterior, summaries)
    save_animation(trials, posterior, summaries)
    save_single_subject_fit(draws, curve, observed)
    save_single_subject_sampling(draws)

    for name in (
        "fig_response_vs_accuracy.png",
        "fig_psi_information.png",
        "fig_psi_adaptation.png",
        "fig_psi_adaptation.gif",
        "fig_single_subject_brms.png",
        "fig_single_subject_sampling.png",
    ):
        path = FIG_DIR / name
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
