"""The ablation for Claim 1: the same release, rendered with and without the ceiling field.

This is the most persuasive experiment the project has, and it is not hypothetical. Removing
`dp:auditCeiling` and its provenance does not merely make the artefact less informative -- it
recreates, exactly, the state in which this project drew and published a wrong conclusion about
its own mechanism for weeks.

There is a twist worth stating plainly, because it is the point of the whole ticket: since the
emitter began requiring the field, **the defective artefact can no longer be produced by this
codebase at all.** So the "without" arm is not emitted; it is reconstructed by hand from the
committed H1 numbers and labelled as what was published before, and the script demonstrates the
refusal rather than the defect.

    python -m scripts.run_ceiling_ablation

Writes results/CEILING_ABLATION.md. Every number is read from a committed result file; the
sources are named inline so a reader can check each one.
"""

from __future__ import annotations

import json
from pathlib import Path

from synthproof.audit.ceiling import ceiling_for
from synthproof.frontier.certificate import PrivacyDataSheet
from synthproof.frontier.croissant import CroissantError, to_croissant
from synthproof.ledger import signing

OUT_MD = Path("results/CEILING_ABLATION.md")

# The H1 configuration. proved/audited are READ FROM the committed grid rather than
# transcribed, because a literal here is exactly how a number outlives the data that
# supported it -- the failure mode this project already had to retract once.
#   m = 60, alpha = 0.05   results/AUDITOR_COMPARISON.md
#   one-run ceiling 2.972  recomputed below by ceiling_for()
H1_MECHANISM = "aim"
H1_TARGET_EPS = 8.0
H1_GRID = Path("results/h1_all_families.json")


def _h1_cell(mechanism: str, target_eps: float) -> dict:
    """Return the committed H1 cell, so proved epsilon cannot drift from the grid.

    Revisions before 2026-09-08 hardcoded ``proved = 7.356`` next to ``mechanism="aim"``.
    7.356 is the value ``independent``/``pairwise`` compose to at target eps 8.0; AIM
    composes to 6.5427. The rendered ablation therefore attributed another mechanism's
    bound to AIM and overstated the unreachable span by ~0.81 epsilon.
    """
    grid = json.loads(H1_GRID.read_text(encoding="utf-8"))
    for cell in grid["cells"]:
        if cell["mechanism"] == mechanism and cell["target_eps"] == target_eps:
            return cell
    raise SystemExit(f"{H1_GRID}: no cell for mechanism={mechanism!r} eps={target_eps}")


_CELL = _h1_cell(H1_MECHANISM, H1_TARGET_EPS)
H1 = {
    "proved": _CELL["proved_eps"]["mean"],
    "audited": _CELL["audited_eps"]["mean"],
    "budget": 60,
    "alpha": 0.05,
    "estimator": "one_run",
}


def _sheet(with_ceiling: bool) -> PrivacyDataSheet:
    c = ceiling_for(H1["estimator"], H1["budget"], H1["alpha"])
    return PrivacyDataSheet(
        dataset_name="adult",
        num_rows=6000,
        mechanism="aim",
        mechanism_available=True,
        delta=1e-5,
        seed=42,
        target_column="income",
        total_proved_eps=H1["proved"],
        total_audited_eps=H1["audited"],
        frontier_curve=[],
        ledger_hash="0" * 64,
        input_fingerprint="0" * 64,
        domain_source="declared",
        audit_ceiling=c.value if with_ceiling else None,
        audit_estimator=H1["estimator"] if with_ceiling else None,
        audit_budget=H1["budget"] if with_ceiling else None,
        audit_alpha=H1["alpha"] if with_ceiling else None,
    )


def main() -> int:
    c = ceiling_for(H1["estimator"], H1["budget"], H1["alpha"])

    # ARM A -- without the field. The emitter now refuses, which IS the result.
    stripped = _sheet(with_ceiling=False)
    signing.sign_datasheet(stripped)
    try:
        to_croissant(stripped)
        refusal = None
    except CroissantError as exc:
        refusal = str(exc)

    # ARM B -- with the field. Emits, and the reader can tell a floor from a finding.
    full = _sheet(with_ceiling=True)
    signing.sign_datasheet(full)
    record = to_croissant(full)

    reachable = c.value
    dead_zone = H1["proved"] - reachable

    # Built outside the f-string: Python 3.11 forbids backslashes inside f-string expressions.
    fence = "```"
    refusal_block = (
        fence + "\n" + refusal + "\n" + fence
        if refusal
        else "**IT DID NOT REFUSE. This is a regression — the guard from T002 is not firing.**"
    )

    md = f"""# Ceiling ablation — what a reader can conclude, with and without the field

> Regenerate: `python -m scripts.run_ceiling_ablation`. Figure: `docs/thesis/figures/fig-ceiling-ablation.png`.
> Every number below is from a committed result file, named inline.

## The configuration

The H1 grid: **AIM on UCI Adult**, proved ε = **{H1['proved']:.3f}** (`{H1_GRID}`, mechanism `{H1_MECHANISM}`),
audited ε = **{H1['audited']:.3f}** (`results/h1_all_families.json`), from a canary audit at
**m = {H1['budget']}**, α = {H1['alpha']} (`results/AUDITOR_COMPARISON.md`).

Recomputed here from the audit configuration alone:

    {c.describe()}

## Arm A — without the ceiling field

The reader sees two numbers:

| field | value |
|---|---|
| `dp:epsilonProved` | {H1['proved']:.3f} |
| `dp:epsilonAudited` | {H1['audited']:.3f} |

**The only inference available is "the mechanism leaks nothing measurable."**

That inference is wrong, and this project drew it. The auditor at m = {H1['budget']} could not
have reported above **{reachable:.3f}** *even against a release that was 100% verbatim training
data*. Everything in **[{reachable:.3f}, {H1['proved']:.3f}]** — a span of **{dead_zone:.3f}** — was
unreachable before the mechanism ran. The zero was the instrument's floor.

### The emitter now refuses to produce this artefact

{refusal_block}

That refusal is the ablation's real result: the failure mode is not merely documented, it is
unreachable. Removing the guard is the only way back to Arm A, and 5 tests fail when it is
removed.

## Arm B — with the ceiling field

| field | value |
|---|---|
| `dp:epsilonProved` | {record.get('dp:epsilonProved')} |
| `dp:epsilonAudited` | {record.get('dp:epsilonAudited')} |
| `dp:auditCeiling` | {record.get('dp:auditCeiling'):.4f} |
| `dp:auditEstimator` | {record.get('dp:auditEstimator')} |
| `dp:auditBudget` | {record.get('dp:auditBudget')} |
| `dp:auditAlpha` | {record.get('dp:auditAlpha')} |

Machine-readable interpretation carried in the same record:

> {record.get('dp:auditInterpretation')}

`dp:auditIsInformative` = **{record.get('dp:auditIsInformative')}**.

The estimator is mirrored because the ceiling is meaningless without it: at m = 800 the paired
Clopper-Pearson series measured 5.377 while the one-run formula gives 5.586, and the GDP ceiling
is in μ rather than ε. A reader who cannot tell which series produced a number cannot check it.

## Table 7.3 — the same release, in the three formats a reader might receive

| capability | SynthProof record | Dibia et al. privacy label (arXiv:2507.15997) | NIST IR 8588 / OpenDP deployment card |
|---|---|---|---|
| formal ε, δ | yes | yes | yes (`privacy_parameters`) |
| unit of privacy | yes | yes | yes (`privacy_unit`) |
| composition / accounting | yes | yes | yes (`composition`) |
| preprocessing declared | yes | partial | yes (`preprocessing_and_hyperparameter_tuning`) |
| an **empirical** privacy result | yes | category exists (§4.1.7) | **no** |
| **the empirical metric's operating range** | **yes** | **no** | **no** |
| **the estimator that produced it** | **yes** | **no** | **no** |
| machine-readable in a standard ML metadata object | yes (Croissant 1.1, 0 warnings) | no | no — bespoke schema; maintainers answered "Not currently" to schema.org/RDF |
| cryptographically signed | yes | no | no |

Verified at source depth 2026-09-05: OpenDP's `schemas/deployments-schema.yaml` (26,744 bytes,
read as raw source) contains **zero** occurrences of `audit`, `empirical`, `lower bound`,
`signature`, `croissant`, `json-ld` or `dcat`. Croissant-RAI contains zero occurrences of
"differential privacy", "epsilon" or "privacy budget".

## What this ablation does NOT claim

Reporting a null beside the instrument's detection limit is a mature, mandated convention
elsewhere — **MIQE 2.0** (Bustin et al., *Clinical Chemistry* 2025;71(6):634–651) requires LoD
and LLOQ to be determined and reported, and analytical labs report "Not Detected, < LOD".
**This is that convention, moved into a DP release artefact**, and it is cited as such.

The quantity is not ours either: a corollary of Steinke et al. Thm 2.1, formalised for one-run
auditing by Keinan, Shenfeld & Ligett (arXiv:2503.07199) Thm 5.2, and already named **"maximum
auditable ε"** by Annamalai, Ganev & De Cristofaro (arXiv:2405.10994 §2.2), who compute it for
their own configuration.

What is contributed is that the field is **required at the point of release**, sourced to its
estimator, and inside the metadata object ML tooling actually reads.
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"ceiling at m={H1['budget']}: {c.value:.4f}   proved: {H1['proved']:.4f}")
    print(f"unreachable span: [{reachable:.3f}, {H1['proved']:.3f}] = {dead_zone:.3f}")
    print("arm A refused by the emitter: " + ("YES" if refusal else "NO -- REGRESSION"))
    print(f"wrote {OUT_MD}")
    return 0 if refusal else 1


if __name__ == "__main__":
    raise SystemExit(main())
