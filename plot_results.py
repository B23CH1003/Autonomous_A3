"""
plot_results.py -- draw results/fraction_strategyproof.png from results/summary_by_p.csv.

Usage: python plot_results.py [results_dir]      (needs matplotlib; nothing else does)
"""

import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def main(outdir: str = "results") -> None:
    with open(os.path.join(outdir, "summary_by_p.csv"), newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["p"] != "all"]
    ps = [float(r["p"]) for r in rows]
    sp = [float(r["fraction_strategyproof"]) for r in rows]
    cond = [float(r["fraction_condition_holds"]) for r in rows]
    n = int(rows[0]["instances"])

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.plot(ps, sp, color=BLUE, lw=2, marker="o", ms=6, mec=SURFACE, mew=1.5, label="strategyproof (Theorem 5.3 check)")
    ax.plot(ps, cond, color=ORANGE, lw=2, marker="o", ms=6, mec=SURFACE, mew=1.5, label="Theorem 5.4 condition holds")
    ax.fill_between(ps, cond, sp, color=BLUE, alpha=0.10, lw=0)
    ax.annotate("strategyproof although\nthe condition fails", xy=(0.2, (sp[2] + cond[2]) / 2), xytext=(0.3, 0.62),
                color=MUTED, fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    for x, y in zip(ps, sp):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8.5, color=INK)
    ax.set_xlabel("attack probability p", color=MUTED)
    ax.set_ylabel(f"fraction of instances (n = {n} per p)", color=MUTED)
    ax.set_xticks(ps)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    ax.legend(frameon=False, loc="upper right", labelcolor=INK, fontsize=9)
    ax.set_title("Grounded direct mechanism: how often is truthful revelation optimal?",
                 loc="left", color=INK, fontsize=11, pad=12)
    fig.tight_layout()
    path = os.path.join(outdir, "fraction_strategyproof.png")
    fig.savefig(path, facecolor=SURFACE)
    print("wrote", path)


if __name__ == "__main__":
    main(*sys.argv[1:2])
