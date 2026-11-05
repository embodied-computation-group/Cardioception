"""Draw the HRD overview figure on the Heart Rate Discrimination page.

Panel a puts the task's own screens in trial order for both conditions, with
the durations read from the ``TaskConfig`` defaults so that they cannot drift
from the code. Panels b and c show one Psi-only session from the Visceral Mind
Project, the same participant as the "Inspecting data" tutorial: the
staircase in each condition, and the psychometric function at the final online
estimate.

The screens come from ``render_hrd_screens.py``. This script needs only
numpy, pandas, scipy, matplotlib and Pillow::

    python tutorials/plot_hrd_overview.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from PIL import Image
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cardioception.HRD.config import TaskConfig  # noqa: E402

SCREENS = ROOT / "docs" / "source" / "images" / "hrd_screens"
SMALL_DIR = ROOT / "tutorials" / "results" / "small"
OUT = ROOT / "docs" / "source" / "images" / "hrd_overview.png"

# PsychoPy's Yes/No Psi model as the HRD configures it (see plot_psi_adaptation.py).
DELTA = 0.02
CURVE_X = np.linspace(-50.5, 50.5, 401)

INTERO = "#A8455F"
EXTERO = "#2F6F8F"
GREY = "#a4acb8"
INK = "#333333"
COLOURS = {"Intero": INTERO, "Extero": EXTERO}
NAMES = {"Intero": "Interoceptive", "Extero": "Exteroceptive"}
LABEL = {"fontsize": 11, "fontweight": "bold", "va": "bottom", "ha": "left"}


def psi_probability(x: np.ndarray, alpha: float, sigma: float) -> np.ndarray:
    """P('faster') under the cumulative Gaussian Psi model."""

    return 0.5 * DELTA + (1 - DELTA) * ndtr((x - alpha) / sigma)


def seconds(value: float) -> str:
    return f"{value:g} s"


def style() -> None:
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
            "text.color": INK,
        }
    )


def draw_trial(fig: plt.Figure, gs, config: TaskConfig) -> plt.Axes:
    """Panel a: the screens of one trial in each condition."""

    isi = config.isi
    fixation = seconds(isi[0]) if isi[0] == isi[1] else f"{isi[0]:g} to {isi[1]:g} s"
    columns = [
        ("Fixation", fixation),
        ("Listening", seconds(config.listeningDuration)),
        ("Decision", f"up to {seconds(config.respMax)}"),
        (
            "Confidence",
            f"{config.minRatingTime:g} to {seconds(config.maxRatingTime)}",
        ),
    ]
    notes = {
        "Intero": [
            "",
            "the pulse is recorded\nand the heart rate measured",
            "tones at the heart rate + Δ:\nslower or faster?",
            "optional",
        ],
        "Extero": [
            "",
            "tones at a random rate",
            "tones at that rate + Δ:\nslower or faster?",
            "optional",
        ],
    }
    files = {
        "Intero": ["fixation", "intero_listen", "intero_decision", "confidence"],
        "Extero": ["fixation", "extero_listen", "extero_decision", "confidence"],
    }

    inner = gs.subgridspec(2, 4, wspace=0.12, hspace=0.55)
    first = None
    for row, modality in enumerate(("Intero", "Extero")):
        for col in range(4):
            ax = fig.add_subplot(inner[row, col])
            first = first or ax
            image = Image.open(SCREENS / f"{files[modality][col]}.png").convert("RGB")
            ax.imshow(image)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_edgecolor(COLOURS[modality])
                spine.set_linewidth(1.6)
            name, duration = columns[col]
            ax.set_title(f"{name}\n{duration}", fontsize=9, color=INK, pad=4)
            ax.text(
                0.5,
                -0.06,
                notes[modality][col],
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=8,
                color="#555555",
            )
            if col == 0:
                ax.set_ylabel(
                    NAMES[modality],
                    color=COLOURS[modality],
                    fontsize=10,
                    fontweight="bold",
                    labelpad=8,
                )
            if col < 3:
                ax.annotate(
                    "",
                    xy=(1.115, 0.5),
                    xytext=(1.01, 0.5),
                    xycoords="axes fraction",
                    arrowprops={"arrowstyle": "-|>", "color": GREY, "lw": 1.2},
                )
    return first


def draw_staircase(
    ax: plt.Axes, trials: pd.DataFrame, psi: pd.DataFrame, modality: str
) -> None:
    """Panel b: stimuli, responses and the Psi threshold for one condition."""

    colour = COLOURS[modality]
    t = trials[trials["Modality"] == modality].sort_values("adaptive_trial")
    s = psi[psi["Modality"] == modality].sort_values("adaptive_trial")

    ax.axhline(0, color=GREY, linestyle=":", linewidth=0.8)
    ax.fill_between(
        s["adaptive_trial"], s["alpha_lo"], s["alpha_hi"], color=colour, alpha=0.13
    )
    ax.plot(
        s["adaptive_trial"],
        s["alpha_mean"],
        color=colour,
        linewidth=1.4,
        label="threshold estimate",
    )
    faster = t["Decision"].eq("More")
    slower = t["Decision"].eq("Less")
    ax.scatter(
        t.loc[faster, "adaptive_trial"],
        t.loc[faster, "Alpha"],
        marker="^",
        s=22,
        facecolor=colour,
        edgecolor="white",
        linewidth=0.4,
        label="answered faster",
        zorder=3,
    )
    ax.scatter(
        t.loc[slower, "adaptive_trial"],
        t.loc[slower, "Alpha"],
        marker="v",
        s=22,
        facecolor="white",
        edgecolor=colour,
        linewidth=0.9,
        label="answered slower",
        zorder=3,
    )
    ax.set(xlim=(0, len(t) + 1), ylim=(-52, 52), xlabel="Trial")
    ax.set_title(NAMES[modality], color=colour, fontsize=10)


def draw_functions(ax: plt.Axes, psi: pd.DataFrame) -> None:
    """Panel c: the psychometric function at the final online estimate."""

    ax.axhline(0.5, color=GREY, linestyle=":", linewidth=0.8)
    ax.axvline(0, color=GREY, linestyle=":", linewidth=0.8)
    for modality in ("Intero", "Extero"):
        colour = COLOURS[modality]
        final = psi[psi["Modality"] == modality].sort_values("adaptive_trial").iloc[-1]
        alpha, sigma = float(final["alpha_mean"]), float(final["sigma_mean"])
        ax.plot(
            CURVE_X,
            psi_probability(CURVE_X, alpha, sigma),
            color=colour,
            linewidth=1.8,
            label=f"α = {alpha:+.1f}, σ = {sigma:.1f}".replace("-", "−"),
        )
        ax.plot([alpha, alpha], [0, 0.5], color=colour, linestyle="--", linewidth=0.9)
    ax.set(
        xlim=(-50.5, 50.5),
        ylim=(-0.02, 1.02),
        xlabel="ΔBPM (tones minus reference)",
        ylabel='P(answer "faster")',
        yticks=[0, 0.5, 1],
    )
    ax.set_title("Final online estimate", fontsize=10)
    ax.legend(
        loc="center right",
        bbox_to_anchor=(1.0, 0.3),
        frameon=False,
        fontsize=8,
        handlelength=0,
        handletextpad=0,
        labelcolor="linecolor",
    )


def main() -> None:
    style()
    config = TaskConfig()
    trials = pd.read_csv(SMALL_DIR / "inspection_example_trials.csv.gz")
    psi = pd.read_csv(SMALL_DIR / "inspection_example_psi.csv.gz")

    fig = plt.figure(figsize=(10, 8.6))
    outer = GridSpec(2, 1, height_ratios=[1.25, 1], hspace=0.38, figure=fig)
    first = draw_trial(fig, outer[0], config)

    lower = outer[1].subgridspec(1, 3, wspace=0.32, width_ratios=[1, 1, 1.15])
    ax_i = fig.add_subplot(lower[0])
    ax_e = fig.add_subplot(lower[1], sharey=ax_i)
    ax_c = fig.add_subplot(lower[2])
    draw_staircase(ax_i, trials, psi, "Intero")
    draw_staircase(ax_e, trials, psi, "Extero")
    ax_i.set_ylabel("ΔBPM")
    ax_i.legend(loc="lower right", frameon=False, fontsize=7.5)
    plt.setp(ax_e.get_yticklabels(), visible=False)
    draw_functions(ax_c, psi)

    # Panel labels sit just above the titles of the axes they introduce.
    top = first.get_position()
    fig.text(0.04, top.y1 + 0.055, "a. One trial in each condition", **LABEL)
    bottom = ax_i.get_position().y1 + 0.04
    fig.text(0.04, bottom, "b. The Psi staircase", **LABEL)
    fig.text(
        ax_c.get_position().x0 - 0.05, bottom, "c. Psychometric functions", **LABEL
    )

    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
