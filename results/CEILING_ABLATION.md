# Ceiling ablation — what a reader can conclude, with and without the field

> Regenerate: `python -m scripts.run_ceiling_ablation`. Figure: `docs/thesis/figures/fig-ceiling-ablation.png`.
> Every number below is from a committed result file, named inline.

## The configuration

The H1 grid: **AIM on UCI Adult**, proved ε = **6.543** (`results/h1_all_families.json`, mechanism `aim`),
audited ε = **0.000** (`results/h1_all_families.json`), from a canary audit at
**m = 60**, α = 0.05 (`results/AUDITOR_COMPARISON.md`).

Recomputed here from the audit configuration alone:

    2.9721 epsilon (estimator=one_run, budget=60, alpha=0.05, closed form, source=steinke.max_provable_epsilon (corollary of Steinke et al. Thm 2.1))

## Arm A — without the ceiling field

The reader sees two numbers:

| field | value |
|---|---|
| `dp:epsilonProved` | 6.543 |
| `dp:epsilonAudited` | 0.000 |

**The only inference available is "the mechanism leaks nothing measurable."**

That inference is wrong, and this project drew it. The auditor at m = 60 could not
have reported above **2.972** *even against a release that was 100% verbatim training
data*. Everything in **[2.972, 6.543]** — a span of **3.571** — was
unreachable before the mechanism ran. The zero was the instrument's floor.

### The emitter now refuses to produce this artefact

```
Refusing to emit: this sheet reports dp:epsilonAudited = 0.0 but is missing audit_ceiling, audit_estimator, audit_budget, audit_alpha.
A reader cannot tell an audited 0.0 that means 'nothing leaked' from an audited 0.0 that means 'the instrument could not have seen anything'. This project published exactly that confusion once: eps_audited 0.000 against eps_proved 7.36, where 60 canaries capped the auditor at 2.97.
Fix: derive the ceiling with `synthproof.audit.ceiling.ceiling_for(estimator, budget, alpha)` and set audit_estimator / audit_budget / audit_alpha on the sheet before signing.
```

That refusal is the ablation's real result: the failure mode is not merely documented, it is
unreachable. Removing the guard is the only way back to Arm A, and 5 tests fail when it is
removed.

## Arm B — with the ceiling field

| field | value |
|---|---|
| `dp:epsilonProved` | 6.5426925748221745 |
| `dp:epsilonAudited` | 0.0 |
| `dp:auditCeiling` | 2.9721 |
| `dp:auditEstimator` | one_run |
| `dp:auditBudget` | 60 |
| `dp:auditAlpha` | 0.05 |

Machine-readable interpretation carried in the same record:

> UNINFORMATIVE. The auditor's ceiling is 2.972 — the largest epsilon this canary count could certify even against a release that was 100% verbatim training data — while the proved epsilon is 6.543. The audited value of 0.000 is therefore the instrument reading its own floor, NOT evidence that the mechanism leaks less than it is permitted to. Certifying an epsilon costs canaries exponential in that epsilon (Steinke, Nasr & Jagielski, NeurIPS 2023, Thm 2.1). Auditing catches broken implementations; it does not confirm tight ones.

`dp:auditIsInformative` = **False**.

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
