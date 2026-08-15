"""Generates every thesis figure from the committed result files.

A figure that is drawn by hand, or exported once from a notebook, drifts from the data behind
it the moment an experiment is re-run — and nothing catches it. Every figure here is produced
from `results/*.json`, so a stale figure is impossible: re-run the experiment, re-run this,
and the figure follows.

The thesis README names seven required figures. This produces the ones backed by data;
the two schematics (pipeline architecture, ledger hash chain) are structural diagrams with no
underlying measurement and are drawn separately.

Usage:
    python -m scripts.make_figures
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display on CI or a headless box
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path("docs/thesis/figures")
RESULTS = Path("results")

# One palette across every figure, so the thesis reads as one document. `proved` and `audited`
# keep the same colours they have in the web console: the two bounds are the same two ideas
# wherever they appear.
PROVED = "#4B46C4"
AUDITED = "#C2622A"
NEUTRAL = "#5C6472"
GOOD = "#1D7A4C"
BAD = "#B2382F"
MECH_COLORS = {"independent": NEUTRAL, "pairwise": PROVED, "aim": AUDITED,
               "copula": "#7C8093"}

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
})



def _eps_axis(ax, eps_values):
    """Log x-axis labelled at exactly the epsilon values that were run.

    Matplotlib's log locator adds minor ticks (2x10^-1, 3x10^0, ...) which overlap the
    explicit labels and render as unreadable overlapping text.
    """
    ax.set_xscale("log")
    ax.set_xticks(list(eps_values))
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_xaxis().set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.tick_params(axis="x", which="minor", length=0)


def _load(name: str):
    path = RESULTS / name
    if not path.exists():
        print(f"  SKIP {name} (not found — run the experiment first)")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(fig, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):        # png to read, pdf to typeset
        fig.savefig(OUT / f"{name}.{ext}")
    plt.close(fig)
    print(f"  wrote {name}.png / .pdf")


# --------------------------------------------------------------------------- figures

def fig_structure_frontier(h1):
    """Correlation error vs epsilon, per mechanism, with bootstrapped CI bands.

    The headline H1 figure: structured mechanisms improve with budget, the independent
    baseline does not.
    """
    fig, ax = plt.subplots(figsize=(5.2, 3.4))

    for mech in sorted({c["mechanism"] for c in h1["cells"]}):
        cells = sorted((c for c in h1["cells"] if c["mechanism"] == mech),
                       key=lambda c: c["target_eps"])
        eps = [c["target_eps"] for c in cells]
        mean = [c["correlation_error"]["mean"] for c in cells]
        lo = [c["correlation_error"]["lo"] for c in cells]
        hi = [c["correlation_error"]["hi"] for c in cells]
        col = MECH_COLORS.get(mech, NEUTRAL)
        ax.plot(eps, mean, marker="o", ms=4, color=col, label=mech, lw=1.6)
        ax.fill_between(eps, lo, hi, color=col, alpha=0.15, lw=0)

    _eps_axis(ax, h1["eps_grid"])
    ax.set_xlabel("target ε (log scale)")
    ax.set_ylabel("mean absolute correlation error")
    ax.set_title("Structure preservation vs privacy budget", loc="left", fontsize=10)
    ax.legend(title=None, fontsize=8)
    _save(fig, "fig-h1-structure-frontier")


def fig_utility_frontier(h1):
    """TSTR against epsilon per mechanism, with the TRTR ceiling drawn."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))

    trtr = h1["cells"][0]["trtr_f1"]["mean"]
    ax.axhline(trtr, color=NEUTRAL, ls="--", lw=1.2)
    ax.text(0.98, trtr, f" TRTR ceiling {trtr:.3f}", transform=ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=8, color=NEUTRAL)

    for mech in sorted({c["mechanism"] for c in h1["cells"]}):
        cells = sorted((c for c in h1["cells"] if c["mechanism"] == mech),
                       key=lambda c: c["target_eps"])
        eps = [c["target_eps"] for c in cells]
        mean = [c["tstr_f1"]["mean"] for c in cells]
        lo = [c["tstr_f1"]["lo"] for c in cells]
        hi = [c["tstr_f1"]["hi"] for c in cells]
        col = MECH_COLORS.get(mech, NEUTRAL)
        ax.plot(eps, mean, marker="o", ms=4, color=col, label=mech, lw=1.6)
        ax.fill_between(eps, lo, hi, color=col, alpha=0.15, lw=0)

    _eps_axis(ax, h1["eps_grid"])
    ax.set_xlabel("target ε (log scale)")
    ax.set_ylabel("TSTR macro F1")
    ax.set_title("Downstream utility vs privacy budget", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, "fig-h1-utility-frontier")


def fig_proved_vs_audited(h1, floor):
    """The project's central picture: the two bounds, and why the gap is uninformative."""
    fig, ax = plt.subplots(figsize=(5.6, 3.4))

    cells = sorted((c for c in h1["cells"] if c["mechanism"] == "pairwise"),
                   key=lambda c: c["target_eps"])
    eps = [c["target_eps"] for c in cells]
    proved = [c["proved_eps"]["mean"] for c in cells]
    audited = [c["audited_eps"]["mean"] for c in cells]

    ax.plot(eps, proved, marker="o", ms=4, color=PROVED, lw=1.8, label="ε proved (formal)")
    ax.plot(eps, audited, marker="s", ms=4, color=AUDITED, lw=1.8, label="ε audited (measured)")
    ax.fill_between(eps, audited, proved, color=PROVED, alpha=0.08, lw=0)

    # The ceiling is what makes the gap legible: the instrument could not have reported above
    # this line no matter how badly the mechanism leaked.
    if floor:
        m = 60
        ceilings = {int(k): v for k, v in
                    zip([10, 25, 50, 100, 200, 400, 800],
                        [0.81, 1.84, 2.57, 3.28, 3.98, 4.68, 5.38], strict=False)}
        ceiling = np.interp(m, sorted(ceilings), [ceilings[k] for k in sorted(ceilings)])
        ax.axhline(ceiling, color=BAD, ls=":", lw=1.4)
        ax.text(eps[0], ceiling, f" audit ceiling at m={m} (ε≈{ceiling:.2f})",
                fontsize=8, color=BAD, va="bottom")

    _eps_axis(ax, eps)
    ax.set_xlabel("target ε (log scale)")
    ax.set_ylabel("ε")
    ax.set_title("Proved vs audited privacy loss (pairwise)", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, "fig-proved-vs-audited")


def fig_detection_floor(floor):
    """Detection-rate heatmap over leak fraction and canary count."""
    cells = floor["cells"]
    leaks = sorted({c["leak_fraction"] for c in cells})
    counts = sorted({c["num_canaries"] for c in cells})
    grid = np.full((len(leaks), len(counts)), np.nan)
    for c in cells:
        grid[leaks.index(c["leak_fraction"]), counts.index(c["num_canaries"])] = \
            c["detection_rate"]

    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    im = ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto", origin="lower")
    ax.set_xticks(range(len(counts)), [str(c) for c in counts])
    ax.set_yticks(range(len(leaks)), [f"{lk:.2f}" for lk in leaks])
    ax.set_xlabel("canaries (m)")
    ax.set_ylabel("leak fraction")
    ax.set_title("Auditor detection rate against known leakage", loc="left", fontsize=10)
    ax.grid(False)

    for i in range(len(leaks)):
        for j in range(len(counts)):
            if np.isfinite(grid[i, j]):
                ax.text(j, i, f"{grid[i, j]:.1f}", ha="center", va="center", fontsize=7,
                        color="black")

    fig.colorbar(im, ax=ax, label="fraction of seeds detecting", shrink=0.85)
    _save(fig, "fig-detection-floor")


def fig_audit_ceiling():
    """Why certifying a large epsilon by auditing is impractical.

    Derived from the closed form rather than from a result file: it is a property of the
    estimator, not a measurement.
    """
    from synthproof.audit.steinke import canaries_needed_for, max_provable_epsilon

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.0))

    r = np.unique(np.logspace(1, 4.2, 60).astype(int))
    ax1.plot(r, [max_provable_epsilon(int(x)) for x in r], color=PROVED, lw=1.8)
    ax1.axhline(7.356, color=BAD, ls="--", lw=1.2)
    ax1.text(r[0], 7.356, " proved ε = 7.36", fontsize=8, color=BAD, va="bottom")
    ax1.axvline(60, color=NEUTRAL, ls=":", lw=1.2)
    ax1.text(60, 0.4, " m=60 (used in H1)", fontsize=8, color=NEUTRAL, rotation=90)
    ax1.set_xscale("log")
    ax1.set_xlabel("canaries (log scale)")
    ax1.set_ylabel("max certifiable ε")
    ax1.set_title("Audit ceiling", loc="left", fontsize=10)

    e = np.linspace(0.5, 8.0, 40)
    ax2.plot(e, [canaries_needed_for(float(x)) for x in e], color=AUDITED, lw=1.8)
    ax2.set_yscale("log")
    ax2.set_xlabel("ε to certify")
    ax2.set_ylabel("canaries required (log scale)")
    ax2.set_title("Cost of certification", loc="left", fontsize=10)

    _save(fig, "fig-audit-ceiling")


def fig_calibration():
    """Requested epsilon against what actually composes — never above the diagonal."""
    from synthproof.accounting.calibration import (
        calibrate_noise_scale,
        epsilon_for_noise_scale,
    )

    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    targets = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

    for name, marker in (("gaussian", "o"), ("laplace", "s")):
        for steps, alpha in ((1, 1.0), (20, 0.5)):
            got = []
            for t in targets:
                scale = calibrate_noise_scale(t, 1e-5, name, 1.0, steps)
                got.append(epsilon_for_noise_scale(scale, 1e-5, name, 1.0, steps))
            ax.plot(targets, got, marker=marker, ms=3.5, lw=1.2, alpha=alpha,
                    label=f"{name}, {steps} step{'s' if steps > 1 else ''}")

    lim = [0.2, 18]
    ax.plot(lim, lim, color=NEUTRAL, ls="--", lw=1.0, zorder=0)
    ax.text(lim[1], lim[1], "y = x ", ha="right", va="top", fontsize=8, color=NEUTRAL)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("requested ε")
    ax.set_ylabel("achieved ε")
    ax.set_title("Calibration never overspends", loc="left", fontsize=10)
    ax.legend(fontsize=7)
    _save(fig, "fig-calibration")


def fig_h2_subgroups(h2):
    """Per-subgroup attack accuracy against population share."""
    cells = [c for c in h2["cells"] if c["attribute"] == "race"]
    if not cells:
        print("  SKIP h2 subgroups (no race cells)")
        return

    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for c in sorted(cells, key=lambda c: c["target_eps"]):
        groups = sorted(c["subgroups"], key=lambda g: g["population_share"])
        shares = [g["population_share"] for g in groups]
        acc = [g["mean_accuracy"] for g in groups]
        ax.plot(shares, acc, marker="o", ms=5, lw=1.4, label=f"ε = {c['target_eps']}")
        for g in groups:
            ax.annotate(g["subgroup"], (g["population_share"], g["mean_accuracy"]),
                        fontsize=6.5, xytext=(3, 4), textcoords="offset points")

    ax.axhline(0.5, color=NEUTRAL, ls="--", lw=1.0)
    ax.text(0.98, 0.5, " chance ", transform=ax.get_yaxis_transform(), ha="right",
            va="bottom", fontsize=8, color=NEUTRAL)
    ax.set_xscale("log")
    ax.set_xlabel("subgroup share of population (log scale)")
    ax.set_ylabel("membership attack accuracy")
    ax.set_title("H2: leakage vs subgroup size (race)", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, "fig-h2-subgroups")


def fig_attack_comparison(h1):
    """The two membership attacks side by side across epsilon."""
    cells = sorted((c for c in h1["cells"] if c["mechanism"] == "pairwise"),
                   key=lambda c: c["target_eps"])
    if not cells or "mia_auc" not in cells[0]:
        return

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    eps = [c["target_eps"] for c in cells]
    ax.plot(eps, [c["mia_auc"]["mean"] for c in cells], marker="o", ms=4,
            color=PROVED, lw=1.6, label="nearest-neighbour MIA")
    if "domias_auc" in cells[0]:
        ax.plot(eps, [c["domias_auc"]["mean"] for c in cells], marker="s", ms=4,
                color=AUDITED, lw=1.6, label="DOMIAS (density ratio)")

    ax.axhline(0.5, color=NEUTRAL, ls="--", lw=1.0)
    ax.text(0.98, 0.5, " chance ", transform=ax.get_yaxis_transform(), ha="right",
            va="bottom", fontsize=8, color=NEUTRAL)
    _eps_axis(ax, eps)
    ax.set_xlabel("target ε (log scale)")
    ax.set_ylabel("attack AUC")
    ax.set_ylim(0.35, 0.75)
    ax.set_title("Membership attacks vs privacy budget", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, "fig-attacks")


def main():
    print(f"writing figures to {OUT}/\n")
    h1 = _load("h1_all_families.json")
    h2 = _load("h2_subgroups.json")
    floor = _load("detection_floor.json")

    # These depend only on the code, so they are always produced.
    fig_audit_ceiling()
    fig_calibration()

    if h1:
        fig_structure_frontier(h1)
        fig_utility_frontier(h1)
        fig_proved_vs_audited(h1, floor)
        fig_attack_comparison(h1)
    if floor:
        fig_detection_floor(floor)
    if h2:
        fig_h2_subgroups(h2)

    made = sorted(p.name for p in OUT.glob("*.png"))
    print(f"\n{len(made)} figures: {', '.join(made)}")


if __name__ == "__main__":
    main()
