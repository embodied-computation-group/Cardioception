"""Plot one PAT session from its final.txt.

Three panels: chosen phases on the cardiac cycle (polar, radius = confidence), the
trial sequence against the start phase, and the chosen delay in ms against the
anticipated heart period with constant-phase lines.

Usage:

    python bench/plot_pat_session.py data/<participant><session>/final.txt [out.png]

The output defaults to results.png next to final.txt. Participant, session and the
confidence scale are read from parameters.txt in the same folder when it exists.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SURF, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#b8b7b1"
BLUE, GREY = "#2a78d6", "#9a9994"


def read_parameters(path: Path) -> dict:
    """Read the task's parameters.txt (tab separated, JSON encoded values)."""
    params = {}
    if not path.exists():
        return params
    for line in path.read_text().splitlines()[1:]:
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        value = value.strip().strip('"')
        try:
            params[key] = json.loads(value)
        except ValueError:
            params[key] = value.strip('"')
    return params


def circular_mean(theta: np.ndarray):
    vec = np.exp(1j * theta).mean()
    return abs(vec), np.angle(vec)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("final", type=Path, help="final.txt of one PAT session")
    ap.add_argument(
        "out",
        type=Path,
        nargs="?",
        help="output image (default: results.png next to final.txt)",
    )
    args = ap.parse_args()
    out = args.out or args.final.with_name("results.png")

    df = pd.read_csv(args.final, sep="\t")
    params = read_parameters(args.final.with_name("parameters.txt"))
    main_ = df[df.Block == "main"].copy()
    prac = df[df.Block == "practice"].copy()
    if main_.empty:
        raise SystemExit("no main-block trials in " + str(args.final))

    conf_lo, conf_hi = params.get(
        "confScale", [df.Confidence.min(), df.Confidence.max()]
    )
    conf_mid = (conf_lo + conf_hi) / 2
    participant = params.get("participant", args.final.parent.name)
    session = params.get("session", "")
    extero = bool(
        params.get("extero", bool(main_.Extero.iloc[0]) if "Extero" in main_ else False)
    )
    mode = params.get("mode", main_.Mode.iloc[0] if "Mode" in main_ else "")

    plt.rcParams.update(
        {
            "figure.facecolor": SURF,
            "axes.facecolor": SURF,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK2,
            "xtick.color": INK2,
            "ytick.color": INK2,
            "text.color": INK,
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#e6e5e1",
            "grid.linewidth": 0.6,
        }
    )

    fig = plt.figure(figsize=(14, 5.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.5, 1.0], wspace=0.35)

    # Panel 1: phases on the cycle, clockwise from the R-wave at the top.
    ax = fig.add_subplot(gs[0], projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_facecolor(SURF)
    ax.grid(True)
    ax.spines["polar"].set_color(MUTED)
    ax.set_rlim(0, conf_hi * 1.1)
    ax.set_rticks([conf_mid, conf_hi])
    ax.set_yticklabels([f"conf {conf_mid:g}", f"{conf_hi:g}"], color=INK2, fontsize=8)
    ax.set_xticks(np.deg2rad([0, 90, 180, 270]))
    ax.set_xticklabels(["R-wave\n0°", "90°", "180°", "270°"], color=INK2)
    if not prac.empty:
        ax.scatter(
            np.deg2rad(prac.ChosenPhaseDeg),
            prac.Confidence,
            s=36,
            facecolors="none",
            edgecolors=GREY,
            linewidths=1.2,
            zorder=3,
            label=f"practice ({len(prac)})",
        )
    th = np.deg2rad(main_.ChosenPhaseDeg)
    ax.scatter(
        th,
        main_.Confidence,
        s=42,
        color=BLUE,
        edgecolors=SURF,
        linewidths=1.0,
        zorder=4,
        label=f"main ({len(main_)})",
    )
    R, ang = circular_mean(th.to_numpy())
    ax.annotate(
        "",
        xy=(ang, R * conf_hi),
        xytext=(0, 0),
        arrowprops=dict(arrowstyle="-|>", color=INK, lw=2, mutation_scale=14),
        zorder=5,
    )
    ax.text(
        0.98,
        0.02,
        f"mean resultant R = {R:.2f}\nat {np.rad2deg(ang) % 360:.0f}°",
        transform=ax.transAxes,
        color=INK,
        fontsize=9,
        ha="right",
        va="bottom",
    )
    ax.set_title(
        "Chosen phase of the cardiac cycle\nradius = confidence, arrow = mean resultant",
        color=INK,
        fontsize=10,
        pad=14,
    )
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(-0.25, -0.18),
        frameon=False,
        fontsize=8,
        labelcolor=INK2,
    )

    # Panel 2: trial sequence.
    ax2 = fig.add_subplot(gs[1])
    n_trials = int(df.Trial.max())

    def size(conf):
        # Marker area from confidence, scaled as if the scale ran 0 to 10.
        return 20 + 8 * (conf - conf_lo) * (10 / max(conf_hi - conf_lo, 1))

    if not prac.empty:
        ax2.axvspan(
            prac.Trial.min() - 0.5, prac.Trial.max() + 0.5, color="#f1f0ec", zorder=0
        )
        ax2.text(
            prac.Trial.mean(), 372, "practice", ha="center", color=INK2, fontsize=9
        )
        ax2.scatter(
            prac.Trial,
            prac.ChosenPhaseDeg,
            s=size(prac.Confidence),
            facecolors="none",
            edgecolors=GREY,
            linewidths=1.2,
            zorder=3,
        )
    ax2.scatter(
        df.Trial,
        df.StartPhaseDeg,
        marker="_",
        s=90,
        color=GREY,
        linewidths=1.2,
        zorder=2,
        label="start phase",
    )
    ax2.scatter(
        main_.Trial,
        main_.ChosenPhaseDeg,
        s=size(main_.Confidence),
        color=BLUE,
        edgecolors=SURF,
        linewidths=0.8,
        zorder=4,
        label="chosen phase (size = confidence)",
    )
    med = main_.ChosenPhaseDeg.median()
    ax2.axhline(med, color=INK, lw=1, ls=(0, (4, 3)), zorder=1)
    ax2.text(
        main_.Trial.min() + 0.5,
        med + 7,
        f"median {med:.0f}°",
        color=INK,
        fontsize=9,
        ha="left",
    )
    low_conf = main_[main_.Confidence <= conf_lo + 0.1 * (conf_hi - conf_lo)]
    for _, r in low_conf.iterrows():
        ax2.annotate(
            f"conf {r.Confidence:g}",
            (r.Trial, r.ChosenPhaseDeg),
            textcoords="offset points",
            xytext=(0, 9),
            ha="center",
            fontsize=8,
            color=INK2,
        )
    ax2.set_xlim(0.5, n_trials + 0.5)
    ax2.set_ylim(0, 400)
    ax2.set_yticks([0, 90, 180, 270, 360])
    ax2.set_xlabel("trial")
    ax2.set_ylabel("phase after the R-wave (degrees)")
    ax2.set_title(
        "Trial by trial: chosen phase against the start phase", color=INK, fontsize=10
    )
    ax2.grid(axis="y")
    ax2.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 0.95),
        frameon=False,
        fontsize=8,
        labelcolor=INK2,
    )

    # Panel 3: delay in ms against the heart period.
    ax3 = fig.add_subplot(gs[2])
    per = main_.AnticipatedPeriodMs
    p_lo = np.floor(per.min() / 50) * 50 - 10
    p_hi = np.ceil(per.max() / 50) * 50 + 10
    d_hi = max(main_.ChosenDelayMs.max() * 1.08, p_hi * 0.55)
    ax3.scatter(
        per,
        main_.ChosenDelayMs,
        s=size(main_.Confidence),
        color=BLUE,
        edgecolors=SURF,
        linewidths=0.8,
        zorder=4,
    )
    pp = np.array([p_lo, p_hi - 20])
    for deg in (90, 180, 270):
        ax3.plot(pp, pp * deg / 360, color=MUTED, lw=0.8, zorder=1)
        ax3.text(
            p_hi - 18,
            (p_hi - 20) * deg / 360,
            f"{deg}°",
            color=INK2,
            fontsize=8,
            va="center",
        )
    med_ms = main_.ChosenDelayMs.median()
    ax3.axhline(med_ms, color=INK, lw=1, ls=(0, (4, 3)), zorder=2)
    ax3.text(
        p_hi - 2,
        med_ms - 0.035 * d_hi,
        f"median {med_ms:.0f} ms",
        color=INK,
        fontsize=9,
        ha="right",
    )
    ax3.set_xlim(p_lo, p_hi)
    ax3.set_ylim(0, d_hi)
    ax3.set_xlabel("anticipated heart period (ms)")
    ax3.set_ylabel("chosen delay after the R-wave (ms)")
    ax3.set_title(
        "Delay vs heart period\nlines: constant phase", color=INK, fontsize=10
    )
    ax3.grid(axis="y")

    label = f"PAT-ECG, {participant}" + (f", session {session}" if session else "")
    label += f" ({'extero' if extero else 'intero'}, {mode}): {len(main_)} main trials"
    fig.suptitle(label, color=INK, fontsize=12, y=1.0)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
