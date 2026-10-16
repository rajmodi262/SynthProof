"""Regenerates the results tables inside the results documents from their JSON.

Tables in `results/*.md` were typed by hand, and a re-run that changed the JSON left them stale
(commit a8a31b1 updated eight result files and none of their documents). Each table now lives
between markers and is rebuilt from data:

    <!-- BEGIN GENERATED: adversary-table -->
    ...table...
    <!-- END GENERATED: adversary-table -->

    python -m scripts.build_results_docs            # rewrite every generated block in place
    python -m scripts.build_results_docs --check    # exit 1 if any block is out of date

`tests/test_results_docs_generated.py` runs `--check`, so a JSON change without a document
change fails CI.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _signed(x: float, places: int = 3) -> str:
    return f"{x:+.{places}f}".replace("-", "−")


# ---------------------------------------------------------------------------- generators


def adversary_table() -> str:
    d = _load("results/adversary_comparison.json")
    rows = [
        "| Mechanism | ε | **algorithm-aware** | distance (current) | Δ | focal points |",
        "|---|---:|---|---|---:|---:|",
    ]
    for c in d["cells"]:
        delta = c["delta_auc"]
        cell = _signed(delta)
        rows.append(
            f"| `{c['mechanism']}` | {c['target_eps']:g} | "
            f"{c['aware_auc_mean']:.3f} ± {c['aware_auc_sd']:.3f} | "
            f"{c['distance_auc_mean']:.3f} ± {c['distance_auc_sd']:.3f} | "
            f"{'**' + cell + '**' if delta < 0 else cell} | {c['n_focal_points']} |"
        )
    seeds = sorted({c["seeds"] for c in d["cells"]})
    rows.append("")
    rows.append(
        f"*{len(d['cells'])} cells, {'/'.join(map(str, seeds))} seeds each, "
        f"{d['n_rows']:,} rows; generated from `results/adversary_comparison.json`.*"
    )
    return "\n".join(rows)


def _ablation_table(rel: str) -> str:
    d = _load(rel)
    rows = [
        "| pair | \\|true corr\\| | err measured | err not measured | effect | 95% CI | relative |",
        "|---|---:|---:|---:|---:|---|---:|",
    ]
    effects = sorted(d["effects"].items(), key=lambda kv: -kv[1]["abs_true_corr"])
    for k, e in effects:
        lo, hi = e["effect_ci_95"]
        spans = " *(spans 0)*" if lo < 0 < hi else ""
        rel_eff = f"{100 * e['relative_effect']:+.1f}%".replace("-", "−")
        rows.append(
            f"| `{k.replace('|', ' x ')}` | {e['abs_true_corr']:.4f} | "
            f"{e['err_when_measured']:.4f} | {e['err_when_not_measured']:.4f} | "
            f"{_signed(e['effect'], 4)} | "
            f"[{_signed(lo, 4)}, {_signed(hi, 4)}]{spans} | {rel_eff} |"
        )
    r_all = d["corr_abs_true_vs_effect"]
    r_ex = d.get("corr_abs_true_vs_effect_excluding_degrading")
    rows.append("")
    line = f"`corr(|true corr|, effect)` = **{_signed(r_all)}** over all {len(effects)} pairs"
    if r_ex is not None and d["pairs_where_measuring_helped"] < d["pairs_compared"]:
        line += f", and **{_signed(r_ex)}** with any pair where measuring hurt excluded"
    rows.append(
        line
        + f". Measuring helped on {d['pairs_where_measuring_helped']} of {d['pairs_compared']} "
        f"pairs. *Generated from `{rel}`.*"
    )
    return "\n".join(rows)


def selection_table_adult() -> str:
    return _ablation_table("results/selection_ablation.json")


def selection_table_acs() -> str:
    return _ablation_table("results/acs/selection_ablation.json")


def selection_floor_table() -> str:
    """Measured vs the `none` arm (no two-way marginal measured at all), both datasets."""
    rows = [
        "| dataset | pair | \\|true corr\\| | err measured | err none arm "
        "| effect vs none | 95% CI |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for label, rel in (
        ("Adult", "results/selection_ablation.json"),
        ("ACS", "results/acs/selection_ablation.json"),
    ):
        effects = _load(rel)["effects"]
        for k, e in sorted(effects.items(), key=lambda kv: -kv[1]["abs_true_corr"]):
            lo, hi = e["effect_vs_none_ci_95"]
            spans = " *(spans 0)*" if lo < 0 < hi else ""
            rows.append(
                f"| {label} | `{k.replace('|', ' x ')}` | {e['abs_true_corr']:.4f} | "
                f"{e['err_when_measured']:.4f} | {e['err_none_arm']:.4f} | "
                f"{_signed(e['effect_vs_none'], 4)} | [{_signed(lo, 4)}, {_signed(hi, 4)}]{spans} |"
            )
    rows.append("")
    rows.append(
        "*Generated from `results/selection_ablation.json` and "
        "`results/acs/selection_ablation.json`.*"
    )
    return "\n".join(rows)


def auditor_table() -> str:
    d = _load("results/auditor_comparison.json")
    rows = [
        "| canary budget | leak | paired ε | one-run ε | one-run ceiling |",
        "|---:|---:|---:|---:|---:|",
    ]
    for c in d["cells"]:
        p, o = c["paired_eps_mean"], c["one_run_eps_mean"]
        ps, os_ = f"{p:.3f}", f"{o:.3f}"
        if o > p:
            os_ = f"**{os_}**"
        elif p > o:
            ps = f"**{ps}**"
        rows.append(
            f"| {c['canary_budget']} | {c['leak_fraction']:.2f} | {ps} | {os_} | "
            f"{c['one_run_ceiling']:.3f} |"
        )
    rows.append("")
    rows.append(
        f"*Means over seeds {d['seeds']}, UCI Adult n = {d['n_rows']:,}, α = {d['alpha']}; "
        "generated from `results/auditor_comparison.json` "
        "(`python -m scripts.run_auditor_comparison`).*"
    )
    return "\n".join(rows)


def _h1_by_mechanism(rel: str) -> Dict[str, Dict[float, dict]]:
    out: Dict[str, Dict[float, dict]] = {}
    for c in _load(rel)["cells"]:
        out.setdefault(c["mechanism"], {})[c["target_eps"]] = c
    return out


def h1_trend_table() -> str:
    """Mean correlation error per mechanism across the epsilon grid (UCI Adult)."""
    rel = "results/h1_all_families.json"
    by = _h1_by_mechanism(rel)
    grid = sorted(next(iter(by.values())))
    rows = [
        f"| mechanism | ε = {grid[0]:g} → {grid[-1]:g} | change |",
        "|---|---|---:|",
    ]
    for mech in ("independent", "pairwise", "aim"):
        vals = [by[mech][e]["correlation_error"]["mean"] for e in grid]
        series = " → ".join(f"{v:.4f}" for v in vals)
        rows.append(f"| {mech} | {series} | {_signed(vals[-1] - vals[0], 4)} |")
    rows.append("")
    rows.append(f"*Means over seeds; generated from `{rel}`.*")
    return "\n".join(rows)


def h1_ratio_table() -> str:
    """proved ε / target ε per mechanism across the grid (UCI Adult)."""
    rel = "results/h1_all_families.json"
    by = _h1_by_mechanism(rel)
    rows = ["| mechanism | proved/target across the grid |", "|---|---|"]
    for mech in ("independent", "pairwise", "aim"):
        cells = by[mech]
        ratios = [cells[e]["proved_eps"]["mean"] / e for e in sorted(cells)]
        rows.append(f"| {mech} | {', '.join(f'{r:.3f}' for r in ratios)} |")
    rows.append("")
    rows.append(f"*Generated from `{rel}`.*")
    return "\n".join(rows)


_IMP = "results/imputation_audit.json"
_ARM_LABEL = {
    "A0": "Complete-case drop (`dropna`)",
    "A1": "Sentinel (`__MISSING__`)",
    "A2": "Uncharged Private Imputation",
    "A3": "Charged DP Imputation",
}
_MECH_LABEL = {"independent": "Independent", "dpvae": "DP-VAE"}


def _ci(stat: dict) -> str:
    lo, hi = stat["ci_95"]
    return f"{stat['mean']:.4f} [{lo:.4f}, {hi:.4f}]"


def _overlap(a: dict, b: dict) -> bool:
    return not (a["ci_95"][1] < b["ci_95"][0] or b["ci_95"][1] < a["ci_95"][0])


def _imp_cell(cells: dict, arm: str, mech: str, eps: float, cond: str) -> dict:
    return cells[f"{arm}_{mech}_eps{eps:.1f}_{cond}"]


def imputation_arms_table() -> str:
    """Every arm, on Adult with its native missingness: research/imputation_audit/RESULTS.md."""
    cells = _load(_IMP)["cells"]
    rows = [
        "| Mechanism | $\\varepsilon$ | Arm | Handling Description | DistanceMIA AUC [95% CI] "
        "| DOMIAS AUC [95% CI] | Verdict vs Pre-Reg |",
        "|---|---|---|---|---|---|---|",
    ]
    for mech in ("independent", "dpvae"):
        for eps in (1.0, 4.0):
            a2 = _imp_cell(cells, "A2", mech, eps, "native")["distance_mia"]
            a3 = _imp_cell(cells, "A3", mech, eps, "native")["distance_mia"]
            for arm in ("A0", "A1", "A2", "A3"):
                c = _imp_cell(cells, arm, mech, eps, "native")
                dist = _ci(c["distance_mia"])
                verdict = {"A0": "Baseline control", "A1": "Structural control"}.get(arm)
                if arm == "A2":
                    dist = f"**{dist}**"
                    verdict = (
                        "**Null ($H_0$): Overlaps A3**"
                        if _overlap(a2, a3)
                        else "**Separates from A3**"
                    )
                elif arm == "A3":
                    dist = f"**{dist}**"
                    verdict = "Charged baseline"
                rows.append(
                    f"| **{_MECH_LABEL[mech]}** | {eps:.1f} | **{arm}** | {_ARM_LABEL[arm]} | "
                    f"{dist} | {_ci(c['domias'])} | {verdict} |"
                )
    rows.append("")
    rows.append(f"*Generated from `{_IMP}`.*")
    return "\n".join(rows)


def imputation_conditions_table() -> str:
    """Injected missingness, IndependentMarginalGenerator: research/imputation_audit/RESULTS.md."""
    cells = _load(_IMP)["cells"]
    label = {"mcar": "MCAR", "mar": "MAR", "mnar": "MNAR"}
    rows = [
        "| Condition | $\\varepsilon$ | Arm A2 (Uncharged) DistMIA | Arm A3 (Charged DP) DistMIA "
        "| Overlap? | Arm A0 (`dropna`) DistMIA |",
        "|---|---|---|---|---|---|",
    ]
    for kind in ("mcar", "mar", "mnar"):
        for rate in (10, 20):
            for eps in (1.0, 4.0):
                cond = f"{kind}_{rate}"
                a2, a3, a0 = (
                    _imp_cell(cells, arm, "independent", eps, cond)["distance_mia"]
                    for arm in ("A2", "A3", "A0")
                )
                ov = "**YES**" if _overlap(a2, a3) else "**NO**"
                rows.append(
                    f"| **{label[kind]} {rate}%** | {eps:.1f} | {_ci(a2)} | {_ci(a3)} | {ov} | "
                    f"{_ci(a0)} |"
                )
    rows.append("")
    rows.append(f"*Generated from `{_IMP}`.*")
    return "\n".join(rows)


def imputation_paper_table() -> str:
    """The same native-missingness cells, one row per mechanism and budget: PAPER_SECTION.md."""
    cells = _load(_IMP)["cells"]
    rows = [
        "| Generative Model | Privacy Budget | Arm A0 (`dropna`) | Arm A1 (Sentinel) "
        "| Arm A2 (Uncharged) | Arm A3 (Charged DP) |",
        "|---|---|---|---|---|---|",
    ]
    for mech in ("independent", "dpvae"):
        for eps in (1.0, 4.0):
            v = [_ci(_imp_cell(cells, a, mech, eps, "native")["distance_mia"]) for a in _ARM_LABEL]
            rows.append(
                f"| **{_MECH_LABEL[mech]}** | $\\varepsilon = {eps:.1f}$ | {v[0]} | {v[1]} | "
                f"**{v[2]}** | **{v[3]}** |"
            )
    rows.append("")
    rows.append(f"*Distance-MIA AUC [95% CI]. Generated from `{_IMP}`.*")
    return "\n".join(rows)


# (document, block name, generator)

# The preregistered W9 cells, in the order docs/prereg/W9_gdp_audit.md lists them.
W9_CELLS = [
    (m, e) for m in ("independent", "moments", "pairwise", "fixed_workload", "mst") for e in (1, 4)
] + [("aim", 1), ("dpvae", 1)]


def gdp_w9_table() -> str:
    """Audited vs proved epsilon per mechanism: results/gdp/*.json (W9)."""
    rows = [
        "| Mechanism | target ε | proved ε | **audited ε** (lower bound) | ceiling ε "
        "| audited / proved | μ_emp | comparator μ | violation | bounded runs/world |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    hashes = set()
    for mech, eps in W9_CELLS:
        rel = f"results/gdp/{mech}_eps{eps}.json"
        if not (ROOT / rel).exists():
            rows.append(f"| `{mech}` | {eps} | not run | | | | | | | |")
            continue
        d = _load(rel)
        hashes.add(d["preregistration_sha256"])
        verdict = (
            "**claimed**"
            if d["violation_claimed"]
            else ("flagged" if d["violation_flagged"] else "none")
        )
        rows.append(
            f"| `{mech}` | {d['target_eps']:g} | {d['proved_eps']:.4f} | "
            f"**{d['eps_emp']:.4f}** | {d['eps_ceiling_at_this_n']:.2f} | "
            f"{d['eps_emp'] / d['proved_eps']:.3f} | {d['mu_emp']:.4f} | "
            f"{d['comparator_mu']:.4f} | {verdict} | {d['bounded_per_world']} |"
        )
    rows.append("")
    rows.append(
        f"*Generated from `results/gdp/*.json`. delta = 1e-2, alpha = 0.05; every cell ran under "
        f"the preregistration with SHA-256 {', '.join(sorted(h[:12] for h in hashes)) or '—'}…*"
    )
    return "\n".join(rows)


_STATUS_MARK = {"documented": "Y", "partial": "~", "not_documented": "N", "not_applicable": "–"}


def real_release_coverage_table() -> str:
    """Which of P1-P11 each release documents: results/real_release_study.json (W11)."""
    d = _load("results/real_release_study.json")
    props = list(d["property_definitions"])
    rows = [
        "| Release | type | " + " | ".join(props) + " |",
        "|---|---|" + ":-:|" * len(props),
    ]
    for r in d["releases"]:
        marks = " | ".join(_STATUS_MARK[r["properties"][p]] for p in props)
        rows.append(f"| {r['name']} | {r['release_type']} | {marks} |")

    def _total(p: str) -> str:
        applicable = d["n_releases"] - d["coverage"][p]["not_applicable"]
        return f"{d['coverage'][p]['documented']}/{applicable}" if applicable else "n/a"

    totals = " | ".join(_total(p) for p in props)
    rows.append(f"| **documented / applicable** | | {totals} |")
    rows.append("")
    rows.append(
        "*Y documented · ~ partial · N not found in the fetched sources · – not applicable. "
        "Generated from `results/real_release_study.json`.*"
    )
    return "\n".join(rows)


def real_release_audit_table() -> str:
    """What the boundary auditor reports on each release's documented values (W11)."""
    d = _load("results/real_release_study.json")
    rows = ["| Release | leaks | unverifiable | findings |", "|---|---:|---:|---|"]
    for r in d["releases"]:
        a = r["audit"]
        found = ", ".join(f"{f['code']} {f['severity']}" for f in a["findings"])
        rows.append(f"| {r['name']} | {a['leaks']} | {a['unverifiable']} | {found} |")
    rows.append("")
    rows.append("*Generated from `results/real_release_study.json`.*")
    return "\n".join(rows)


def h1_confirmatory_table() -> str:
    """The preregistered AIM-vs-pairwise confirmatory run (W10): results/h1_confirmatory/."""
    d = _load("results/h1_confirmatory/analysis.json")
    rows = [
        "| Dataset | eps | mechanism | seeds | correlation error, mean [95% CI] | SD |",
        "|---|---:|---|---:|---|---:|",
    ]
    verdicts = []
    for r in d["comparisons"]:
        for mech, c in r["cells"].items():
            lo, hi = c["ci95"]
            rows.append(
                f"| {r['dataset']} | {r['eps']:g} | `{mech}` | {c['n']} | "
                f"{c['mean']:.4f} [{lo:.4f}, {hi:.4f}] | {c['sd']:.4f} |"
            )
        verdicts.append(
            f"**{r['dataset']}, eps {r['eps']:g}: {r['verdict']}** -- AIM minus pairwise "
            f"{r['difference_aim_minus_pairwise']:+.4f}, Welch p = {r['welch_p']:.4f} "
            f"(Holm-adjusted {r['welch_p_holm']:.4f}); TOST p = {r['tost_p']:.4f} at margin "
            f"+/-{d['margin']:g}; minimum detectable difference at 80% power "
            f"{r['mde_at_80pct_power']:.4f}."
        )
    rows.append("")
    rows.extend(verdicts)
    rows.append("")
    rows.append(
        f"*Generated from `results/h1_confirmatory/analysis.json`. Preregistration SHA-256 "
        f"{d['preregistration_sha256'][:12]}..., amendments {d['amendments_sha256'][:12]}...*"
    )
    return "\n".join(rows)


BLOCKS: List[Tuple[str, str, Callable[[], str]]] = [
    ("results/ADVERSARY_COMPARISON.md", "adversary-table", adversary_table),
    ("results/SELECTION_ABLATION.md", "selection-table-adult", selection_table_adult),
    ("results/SELECTION_ABLATION.md", "selection-table-acs", selection_table_acs),
    ("results/SELECTION_ABLATION.md", "selection-floor-table", selection_floor_table),
    ("results/AUDITOR_COMPARISON.md", "auditor-table", auditor_table),
    ("results/GDP_AUDIT.md", "gdp-w9-table", gdp_w9_table),
    ("results/REAL_RELEASE_STUDY.md", "real-release-coverage", real_release_coverage_table),
    ("results/REAL_RELEASE_STUDY.md", "real-release-audit", real_release_audit_table),
    ("results/H1_RESULTS.md", "h1-trend-table", h1_trend_table),
    ("results/H1_RESULTS.md", "h1-ratio-table", h1_ratio_table),
    ("results/H1_CONFIRMATORY.md", "h1-confirmatory-table", h1_confirmatory_table),
    (
        "research/imputation_audit/RESULTS.md",
        "imputation-arms-table",
        imputation_arms_table,
    ),
    (
        "research/imputation_audit/RESULTS.md",
        "imputation-conditions-table",
        imputation_conditions_table,
    ),
    (
        "research/imputation_audit/PAPER_SECTION.md",
        "imputation-paper-table",
        imputation_paper_table,
    ),
]


def _block_re(name: str) -> re.Pattern:
    n = re.escape(name)
    return re.compile(rf"(<!-- BEGIN GENERATED: {n} -->)(.*?)(<!-- END GENERATED: {n} -->)", re.S)


def build(check_only: bool) -> List[str]:
    stale: List[str] = []
    by_doc: Dict[str, List[Tuple[str, Callable[[], str]]]] = {}
    for doc, name, gen in BLOCKS:
        by_doc.setdefault(doc, []).append((name, gen))
    for doc, blocks in by_doc.items():
        path = ROOT / doc
        raw = path.read_text(encoding="utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        text = raw.replace("\r\n", "\n")
        for name, gen in blocks:
            pat = _block_re(name)
            if not pat.search(text):
                raise SystemExit(f"{doc}: no '{name}' generated block markers")
            body = "\n" + gen() + "\n"
            new = pat.sub(lambda m, b=body: m.group(1) + b + m.group(3), text)
            if new != text:
                stale.append(f"{doc}:{name}")
                text = new
        if not check_only:
            path.write_text(text.replace("\n", nl), encoding="utf-8", newline="")
    return stale


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale = build(check_only=args.check)
    if args.check and stale:
        print("Out of date (run `python -m scripts.build_results_docs`):", *stale, sep="\n  ")
        sys.exit(1)
    print("rebuilt:" if not args.check else "up to date", *stale, sep="\n  ")


if __name__ == "__main__":
    main()
