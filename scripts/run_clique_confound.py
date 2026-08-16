"""Tests the clique-selection confound directly, instead of inferring it from one pair.

THE CLAIM THIS EXISTS TO CHECK — and it is our own claim, so it is written to be able to
refute us. `results/acs/H1_RESULTS.md` §4 argues that AIM's apparent advantage on the H1
structure metric is largely an artefact of WHICH column pair the metric happens to measure:
AIM selects `age x hours_per_week` as a clique at every epsilon on Adult, and `AGEP x WKHP` at
only one of three on ACS, and AIM's correlation error tracks that selection.

That argument rests on a single measured pair per dataset. It is suggestive, not established.

THE TEST. For every numeric column pair, at every epsilon and seed, record two things: the
correlation error AIM achieves on that pair, and whether that pair was among the two-way
cliques AIM actually selected. The prediction is sharp and falsifiable:

    AIM's correlation error should be markedly LOWER on pairs it selected than on pairs it
    did not, and on unselected pairs it should be no better than the independent-marginals
    baseline — which models no dependence at all.

If that holds, the confound is demonstrated rather than asserted, and the H1 structure result
has to be read as a statement about clique selection. If it does not hold, our own write-up is
overstated and must be corrected. Both outcomes are reported.

`independent` and `pairwise` are fitted on the same cells as reference. `independent` is the
important one: it is the floor a mechanism that models no cross-column structure achieves.

Usage:
    python -m scripts.run_clique_confound                 # UCI Adult
    python -m scripts.run_clique_confound --dataset acs   # ACSIncome
"""

import argparse
import json
import time
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.profiler import DPDomainProfiler
from synthproof.frontier.experiment import MECHANISMS, bootstrap_ci

N_ROWS = 6000
EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)
SEEDS = (0, 1, 2, 3, 4)
MECHS = ("independent", "pairwise", "aim")

DATASETS = {
    "adult": {"out": "results/clique_confound.json", "label": "UCI Adult"},
    "acs": {"out": "results/acs/clique_confound.json", "label": "ACSIncome (CA 2018)"},
}


def _load(name):
    if name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
        ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
        return ds
    if name == "acs":
        from synthproof.data.acs import load_acs_income

        ds, _ = load_acs_income(n_rows=N_ROWS, seed=0, download=True)
        return ds
    raise SystemExit(f"Unknown dataset {name!r}")


def corr_err(real_df, synth_df, a, b, truth):
    """Absolute error in Pearson correlation for one column pair."""
    try:
        got = float(synth_df[a].corr(synth_df[b]))
    except Exception:
        return float("nan")
    if not np.isfinite(got):
        # A synthetic column can come out constant under heavy noise; correlation is then
        # undefined. Treat it as maximal error rather than dropping the cell, which would
        # quietly bias the comparison toward whichever mechanism degenerates more often.
        return abs(truth)
    return abs(truth - got)


def run_cell(ds, mech, eps, seed, pairs, truth):
    """One fit. Returns (per-pair errors, set of selected 2-way cliques)."""
    plan = BudgetPlan.split(eps, delta=1e-5, profile_frac=0.1)
    acc = Accountant(budget_eps=eps * 1.02, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)

    gen = MECHANISMS[mech](seed=seed)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    synth = gen.generate(num_samples=ds.num_rows)

    errs = {f"{a}|{b}": corr_err(ds.df, synth, a, b, truth[(a, b)]) for a, b in pairs}

    selected = set()
    for attr in ("measured_cliques_", "edges_"):
        cl = getattr(gen, attr, None)
        if cl:
            for c in cl:
                if len(c) == 2:
                    selected.add(frozenset(c))
            break
    return errs, selected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="adult", choices=sorted(DATASETS))
    ap.add_argument(
        "--analyse-only",
        action="store_true",
        help="Recompute the verdict from the saved observations without re-running the grid.",
    )
    args = ap.parse_args()
    cfg = DATASETS[args.dataset]

    ds = _load(args.dataset)
    pairs = list(combinations(ds.numerical_cols, 2))
    truth = {(a, b): float(ds.df[a].corr(ds.df[b])) for a, b in pairs}

    print(f"dataset: {cfg['label']}  n={ds.num_rows}")
    print(f"numeric pairs ({len(pairs)}):")
    for a, b in pairs:
        print(f"   {a} x {b}   true corr = {truth[(a, b)]:+.4f}")
    print(f"\ngrid: {len(MECHS)} mechanisms x {len(EPS_GRID)} eps x {len(SEEDS)} seeds\n")

    t0 = time.time()
    obs = []  # one row per (mech, eps, seed, pair)
    if args.analyse_only:
        obs = json.loads(Path(cfg["out"]).read_text(encoding="utf-8"))["observations"]
        print(f"re-analysing {len(obs)} saved observations; no fits re-run\n")
    for mech in [] if args.analyse_only else MECHS:
        for eps in EPS_GRID:
            for seed in SEEDS:
                errs, selected = run_cell(ds, mech, eps, seed, pairs, truth)
                for a, b in pairs:
                    obs.append(
                        {
                            "mechanism": mech,
                            "target_eps": eps,
                            "seed": seed,
                            "pair": f"{a}|{b}",
                            "corr_err": errs[f"{a}|{b}"],
                            "selected": bool(frozenset((a, b)) in selected),
                        }
                    )
            sel_rate = np.mean(
                [o["selected"] for o in obs if o["mechanism"] == mech and o["target_eps"] == eps]
            )
            print(f"  {mech:<12} eps={eps:<5} pair-selection rate {sel_rate:.2f}", flush=True)

    def ci(rows):
        vals = [r["corr_err"] for r in rows if np.isfinite(r["corr_err"])]
        return asdict(bootstrap_ci(vals)) if vals else None

    aim = [o for o in obs if o["mechanism"] == "aim"]
    aim_sel = [o for o in aim if o["selected"]]
    aim_unsel = [o for o in aim if not o["selected"]]
    indep = [o for o in obs if o["mechanism"] == "independent"]
    pw = [o for o in obs if o["mechanism"] == "pairwise"]

    # WITHIN-PAIR comparison. Comparing selected against unselected across DIFFERENT pairs is
    # itself confounded: `capital_gain x capital_loss` is a far easier pair to reproduce than
    # `age x hours_per_week`, so a difference could be pair difficulty rather than selection.
    # Since AIM's selection varies with epsilon and seed, most pairs appear in both states,
    # and the honest comparison holds the pair fixed.
    per_pair = {}
    for p in {o["pair"] for o in aim}:
        s = [o["corr_err"] for o in aim if o["pair"] == p and o["selected"]]
        u = [o["corr_err"] for o in aim if o["pair"] == p and not o["selected"]]
        s = [v for v in s if np.isfinite(v)]
        u = [v for v in u if np.isfinite(v)]
        per_pair[p] = {
            "n_selected": len(s),
            "n_not_selected": len(u),
            "mean_selected": float(np.mean(s)) if s else None,
            "mean_not_selected": float(np.mean(u)) if u else None,
            "delta": (float(np.mean(s) - np.mean(u)) if s and u else None),
        }

    comparable = [v for v in per_pair.values() if v["delta"] is not None]
    within = {
        "pairs_with_both_states": len(comparable),
        "pairs_where_selection_helped": sum(1 for v in comparable if v["delta"] < 0),
        "mean_delta": float(np.mean([v["delta"] for v in comparable])) if comparable else None,
        "delta_ci": (
            asdict(bootstrap_ci([v["delta"] for v in comparable])) if len(comparable) > 1 else None
        ),
    }

    summary = {
        "aim_selected": ci(aim_sel),
        "aim_not_selected": ci(aim_unsel),
        "independent_all": ci(indep),
        "pairwise_all": ci(pw),
        "n_aim_selected": len(aim_sel),
        "n_aim_not_selected": len(aim_unsel),
        "within_pair": within,
        "per_pair": per_pair,
    }

    print("\n" + "=" * 74)
    print("CORRELATION ERROR, conditioned on whether AIM selected the pair")
    print("=" * 74)
    for k in ("aim_selected", "aim_not_selected", "independent_all", "pairwise_all"):
        s = summary[k]
        if s:
            print(f"  {k:<20} {s['mean']:.4f}  [{s['lo']:.4f}, {s['hi']:.4f}]  (n={s['n']})")

    # The two questions the experiment was built to answer.
    sel, unsel, ind = (
        summary["aim_selected"],
        summary["aim_not_selected"],
        summary["independent_all"],
    )
    findings = []
    if sel and unsel:
        separated = sel["hi"] < unsel["lo"]
        findings.append(
            f"AIM's error on SELECTED pairs ({sel['mean']:.4f}) vs UNSELECTED "
            f"({unsel['mean']:.4f}): CIs {'DO NOT overlap' if separated else 'overlap'}."
        )
    if unsel and ind:
        beats = unsel["hi"] < ind["lo"]
        findings.append(
            f"On UNSELECTED pairs AIM ({unsel['mean']:.4f}) vs independent-marginals "
            f"({ind['mean']:.4f}): AIM is "
            f"{'still better' if beats else 'NOT distinguishably better'}."
        )
    print("\nWITHIN-PAIR (same pair, selected vs not — controls for pair difficulty)")
    for p, v in sorted(per_pair.items()):
        if v["delta"] is None:
            state = "always selected" if v["n_selected"] else "never selected"
            print(f"  {p:<34} {state} ({v['n_selected']}/{v['n_not_selected']})")
        else:
            print(
                f"  {p:<34} sel {v['mean_selected']:.4f}  unsel {v['mean_not_selected']:.4f}  "
                f"delta {v['delta']:+.4f}"
            )
    if within["delta_ci"]:
        d = within["delta_ci"]
        print(
            f"\n  mean within-pair delta {d['mean']:+.4f} [{d['lo']:+.4f}, {d['hi']:+.4f}] "
            f"over {within['pairs_with_both_states']} pairs; selection helped in "
            f"{within['pairs_where_selection_helped']} of them"
        )

    # THE DECIDING TEST, and it is not the within-pair one.
    #
    # The within-pair comparison was the intended control, but it turned out to be
    # underpowered by construction: AIM's selection barely varies, so on Adult only ONE pair
    # ever appeared in both states and the comparison had n=1. Reporting that as "not
    # confirmed" would conflate "could not test" with "tested and found nothing" — the exact
    # error this project criticises elsewhere.
    #
    # The better test compares AIM against the INDEPENDENT-MARGINAL baseline separately on the
    # pairs it selects and the pairs it does not. That baseline models no cross-column
    # dependence at all, so:
    #
    #   * if AIM beats it on selected pairs but NOT on unselected ones, AIM's structure
    #     advantage exists only where it spent a clique — which is the confound;
    #   * the "it was just an easy pair" objection is answered by reading the baseline's own
    #     error on that pair, since an intrinsically easy pair is easy for the baseline too.
    by_pair = {}
    all_pairs = {o["pair"] for o in obs}
    for p in all_pairs:
        a = [o for o in aim if o["pair"] == p]
        chosen = sum(1 for o in a if o["selected"])
        by_pair[p] = chosen >= 0.5 * len(a)
    selected_pairs = {p for p, v in by_pair.items() if v}
    unselected_pairs = all_pairs - selected_pairs

    def split(mech, ps):
        return ci([o for o in obs if o["mechanism"] == mech and o["pair"] in ps])

    conditional = {
        "selected_pairs": sorted(selected_pairs),
        "unselected_pairs": sorted(unselected_pairs),
        "aim_on_selected": split("aim", selected_pairs),
        "independent_on_selected": split("independent", selected_pairs),
        "aim_on_unselected": split("aim", unselected_pairs),
        "independent_on_unselected": split("independent", unselected_pairs),
    }
    summary["conditional"] = conditional

    def beats(a, b):
        return bool(a and b and a["hi"] < b["lo"])

    wins_where_selected = beats(
        conditional["aim_on_selected"], conditional["independent_on_selected"]
    )
    wins_where_not = beats(
        conditional["aim_on_unselected"], conditional["independent_on_unselected"]
    )

    print("\nAIM vs the no-dependence baseline, split by whether AIM selects the pair")
    for lbl, ak, ik in (
        ("SELECTED", "aim_on_selected", "independent_on_selected"),
        ("NOT selected", "aim_on_unselected", "independent_on_unselected"),
    ):
        a, i = conditional[ak], conditional[ik]
        if a and i:
            print(
                f"  pairs AIM {lbl}: aim {a['mean']:.4f} [{a['lo']:.4f}, {a['hi']:.4f}]  vs  "
                f"independent {i['mean']:.4f} [{i['lo']:.4f}, {i['hi']:.4f}]"
            )

    confirmed = bool(wins_where_selected and not wins_where_not)
    if confirmed:
        verdict = (
            "CONFOUND CONFIRMED. AIM beats the independent-marginal baseline on the pairs it "
            "selects as cliques, and does NOT beat it on the pairs it does not select — on "
            "those it is statistically indistinguishable from a mechanism that models no "
            "cross-column dependence at all. AIM's structure advantage therefore exists "
            "exactly where it spent a clique, and the H1 headline measured precisely such a "
            "pair. The H1 structure result must be read as a statement about clique selection."
        )
    elif wins_where_selected and wins_where_not:
        verdict = (
            "CONFOUND REFUTED. AIM beats the no-dependence baseline on unselected pairs too, "
            "so its structure advantage is general rather than an artefact of which pair the "
            "metric happens to measure. results/acs/H1_RESULTS.md §4 overstates the case and "
            "must be corrected."
        )
    else:
        verdict = (
            "INCONCLUSIVE: AIM does not separate from the baseline even on the pairs it "
            "selects, so this design cannot speak to the confound either way."
        )
    print()
    for f in findings:
        print(f"  - {f}")
    print(f"\n{verdict}")

    payload = {
        "dataset": args.dataset,
        "dataset_label": cfg["label"],
        "n_rows": ds.num_rows,
        "pairs": [f"{a}|{b}" for a, b in pairs],
        "true_correlations": {f"{a}|{b}": truth[(a, b)] for a, b in pairs},
        "mechanisms": list(MECHS),
        "eps_grid": list(EPS_GRID),
        "seeds": list(SEEDS),
        "summary": summary,
        "confound_confirmed": confirmed,
        "verdict": verdict,
        "elapsed_seconds": round(time.time() - t0, 1),
        "observations": obs,
    }
    Path(cfg["out"]).parent.mkdir(parents=True, exist_ok=True)
    Path(cfg["out"]).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {cfg['out']}")


if __name__ == "__main__":
    main()
