# Thesis data pack — every number, table and figure, per chapter

**The prose in `ch01`–`ch08` is yours to write.** This document exists so that writing it never
requires hunting for a number: each section below lists what to cite, where it came from, and
the exact command that regenerates it.

Every figure is produced by `make figures` from `results/*.json`, so a figure cannot drift from
its data. Every number traces to a committed experiment with a recorded seed. `make reproduce`
verifies the whole set against `results/MANIFEST.json`.

> **House rule, from `docs/thesis/README.md`:** if you cannot point at the script and the seed
> that produced a number, it does not go in the thesis.

---

## Regenerating everything

```bash
make reproduce-all
```

```bash
make figures
```

| Artefact | Command | Output |
|---|---|---|
| H1 grid | `make h1` | `results/h1_all_families.json` |
| H2 subgroups | `make h2` | `results/h2_subgroups.json` |
| Detection floor | `make floor` | `results/detection_floor.json` |
| All figures | `make figures` | `docs/thesis/figures/*.pdf` |
| Manifest | `make manifest` | `results/MANIFEST.json` |

---

## Chapter 3 — Threat model

Nothing here is measured; it is the specification the rest of the thesis is checked against.
The requirements table (R1–R8) in `ch03-threat-model.md` §3.4 already maps each requirement to
the code that enforces it. **Two rows now need updating:**

- **R7** (release claims verifiable without trusting the holder) — was "planned"; the signed
  data sheet and `synthproof verify` now exist. See Ch.4 §4.8.
- **R8** (empirical leakage measured with uncertainty quantified) — still true, but must now
  carry the caveat that the instrument's working range does not cover the epsilons being
  claimed. See Ch.7 §7.2.

---

## Chapter 4 — System design

| Claim | Number | Source |
|---|---|---|
| Calibration never overspends | proved/target = 0.92 across the grid, never > 1.0 | `results/h1_all_families.json`, every cell |
| Calibration is CI-gated | 24 configurations (2 mechanisms × 3 step counts × 4 targets) | `.github/workflows/ci.yml`, `calibration-guard` job |
| Composition is delegated | agreement with `autodp` within **0.05%** across 12 configurations | `tests/test_accounting_properties.py::test_epsilon_agrees_with_autodp` |
| Hand-rolled bound was unsound | under-reported ε by ~2× (0.485 vs 0.956 at q = 0.01) | `docs/AUDIT_AND_ROADMAP.md` §2, finding F4 |
| Profiler charges for domain discovery | profiling spends exactly its allotted ε regardless of column count | `tests/test_data.py::test_profiling_spends_exactly_its_budget_despite_mixed_sensitivities` |

**Figure:** `fig-calibration.pdf` — requested vs achieved ε, log-log, with the y = x diagonal.
The point of the figure is that no marker sits above the line.

---

## Chapter 5 — Implementation

| Claim | Number | Source |
|---|---|---|
| Test suite | **201 tests**, 1 skipped (AIM without private-pgm), 86% coverage | `make test` |
| Static analysis | ruff clean; bandit clean at medium severity and above | `make lint`, `make security` |
| Dependency CVEs | pip-audit and npm audit clean | `make security` |
| Property tests | 35 over the accounting laws | `tests/test_accounting_properties.py` |
| Mechanisms implemented | 4 (`independent`, `copula`, `pairwise`, `aim`) | `synthproof/frontier/experiment.py::MECHANISMS` |
| Attacks implemented | 2 membership (distance MIA, DOMIAS) + exact-match singling out | `synthproof/attacks/` |
| Attacks NOT implemented | LiRA, attribute inference — named in the API and console | `synthproof/api/main.py::NOT_IMPLEMENTED_ATTACKS` |

**Defects worth reporting in §5.6.** Each is now defended by a named regression test; this is
the material for the self-audit argument in Ch.8 §8.2.

| Defect | Consequence | Test that now guards it |
|---|---|---|
| σ < 0.3 zero-noise shortcut | charged ε, added no noise | `test_accounting.py` |
| `abs()` on Gaussian noise | biased the mechanism | `test_generators.py` |
| Profiler published `.unique()` | paid ε, leaked the exact domain | `test_data.py::test_rare_categories_are_suppressed_not_published` |
| TRTR scored in-sample | constant 0.971 utility ceiling | `test_utility_frontier.py::test_trtr_is_held_out_not_in_sample` |
| `auc = accuracy + 0.05` | fabricated metric | `test_audit_attacks.py::test_distance_mia_reports_real_auc` |
| Mechanism dispatch never matched | two "different" generators were one | pipeline deleted entirely |
| `AIM_Marginal_Generator` label | CLI/API/console reported AIM for independent marginals | `test_utility_frontier.py::test_data_sheet_names_the_mechanism_that_actually_ran` |
| `.gitignore` swallowed `web/src/lib/` | CI failed on an unresolvable import | anchored patterns; caught by CI |
| DOMIAS reference self-match | AUC 0.576 on a release with no real records | `test_domias.py::test_negative_control_stays_at_chance...` |
| AIM unbounded model size | `MemoryError` at cell 59 of 75 | `test_aim.py::test_a_tiny_model_budget_refuses_cliques...` |

---

## Chapter 6 — Methodology

| Commitment | What was actually run |
|---|---|
| 5 seeds per cell | ✅ 5 (0–4) |
| ε grid {0.5, 1, 2, 4, 8} | ✅ all five |
| δ = 1e-5, δ < 1/n | ✅ n = 6,000 so 1/n = 1.7e-4 |
| Datasets: UCI Adult, ACS PUMS | ⚠️ **Adult only.** ACS not run — state this as a deviation |
| Report regardless of direction | ✅ H2 reported as not supported |
| TSTR/TRTR on the same held-out split | ✅ `evaluate/utility.py` |
| Primary privacy metric: one-run canary audit | ✅ `audit/steinke.py` |

**Deviations to declare in §6.1.** A preregistration is only worth something if the deviations
are stated:

1. **ACS PUMS was not run.** One dataset only.
2. **Utility is measured on a second, canary-free fit.** Not in the original protocol; added
   because measuring it on the canary-trained model destroyed the signal (Ch.7 §7.4).
3. **The auditor changed** from paired Clopper-Pearson to the one-run construction mid-project.
   Both are reported and compared.

---

## Chapter 7 — Results

### §7.1 Calibration validation
`fig-calibration.pdf`. proved/target = 0.92, never above 1.0, across every cell.

### §7.2 Auditor validation — **write this before any audit result**
`fig-detection-floor.pdf`, `fig-audit-ceiling.pdf`. Source: `results/DETECTION_FLOOR.md`,
`results/AUDITOR_COMPARISON.md`.

| Claim | Number |
|---|---|
| Positive control | verbatim release detected at m = 10, TPR 1.00, FPR 0.00, p < 0.001 |
| Negative control | shuffled release (perfect marginals, no real records) never detected |
| Detection floor | 25% leakage needs m = 400; 5% undetected at m = 800 |
| **Audit ceiling** | **2.97 at m = 60**, 5.59 at m = 800 |
| Cost of certification | ~ln(1/α)·e^ε canaries — **4,711 for ε = 7.36** |

**The sentence this chapter turns on:** at m = 60 the instrument could not have reported
ε_audited > 2.97 even against a release that was 100% verbatim training data, and the proved ε
is 7.36. The gap was guaranteed before any mechanism ran.

### §7.3 H1 — mechanism families
`fig-h1-structure-frontier.pdf`, `fig-h1-utility-frontier.pdf`. Source: `results/H1_RESULTS.md`.

Report the structure and utility halves as **supported**, and the privacy half as
**disqualified** by §7.2 — not as untested.

### §7.4 The contamination finding
No figure; a table and three paragraphs. Source: `results/H1_RESULTS.md` §4.

| | |
|---|---|
| corr(age, hours) on the fit split | 0.1014 |
| after planting 60 canaries | **0.0109** — 89% of the signal destroyed |
| pairwise corr error, contaminated vs decoupled (ε=8) | 0.1098 → **0.0459** |
| independent, same comparison | 0.9804 → 0.9778 (unchanged — the control working) |

### §7.5 Attack range
`fig-attacks.pdf`. Both membership attacks across ε.

**Report the honest comparison:** DOMIAS is *not* uniformly stronger. On a verbatim release the
nearest-neighbour baseline reaches AUC 1.000 where DOMIAS reaches 0.559, because dividing by a
reference density hurts when a leaked record is also typical. Asserted as a test
(`test_domias.py::test_domias_is_not_uniformly_stronger...`) so the claim cannot rot.

### §7.6 H2 — subgroup disparity
`fig-h2-subgroups.pdf`. Source: `results/H2_RESULTS.md`.

**Not supported.** The direction is consistent — the rarest subgroup (`Other`, 0.8%) has the
highest attack accuracy at both ε, and `White` (85.7%) sits at exactly chance (0.500 at ε = 1)
— but no mean p-value clears 0.05, the largest audited ε is 0.036 against a ceiling of 3.27,
and with 20 tests one false positive is expected by chance.

### §7.7 H3 — allocation strategy
**Not run.** Report as such rather than omitting the hypothesis.

---

## Chapter 8 — Discussion

### §8.1 Interpretation
The reframing is the contribution: **auditing is a tool for catching broken implementations,
not for confirming tight ones.** It found a verbatim release at m = 10. It will never confirm
that ε = 7.36 is tight, and that is a property of what auditing can prove rather than of this
implementation.

### §8.2 The self-audit as method
The defect table in Ch.5 is the evidence. The general argument: DP implementations need
adversarial code review as standard practice, because a privacy claim is only as strong as its
least-checked line — and none of these were exotic. They were ordinary software defects with
extraordinary consequences.

Add the two found by *automated* review (CodeRabbit) and the two found by *controls*: the
DOMIAS self-match and the AIM memory bound were both caught by a negative control and a full
grid run respectively, not by reading the code.

### §8.3 Limitations
- Audit working range does not cover the proved epsilons (§7.2). **The headline limitation.**
- One dataset; ACS PUMS not run.
- Canaries are synthetic outliers, not real records.
- LiRA and attribute inference not implemented.
- The ledger is tamper-**evident**, not tamper-proof; key custody is organisational.
- `dp_accounting` is trusted, mitigated by the `autodp` differential test.
- H3 untested.

### §8.4 Future work
The full Steinke construction with a mechanism-aware adversary; ACS PUMS; H3; user-level
privacy for multi-row individuals; a formal proof of the pipeline invariant.

---

## Citations needed

`docs/thesis/references.bib` does not exist yet. These are cited across chapters and should go
in first:

| Key | Work |
|---|---|
| dwork2006 | Calibrating Noise to Sensitivity |
| dwork2014 | The Algorithmic Foundations of DP |
| mironov2017 | Rényi Differential Privacy |
| mironov2012 | On Significance of the Least Significant Bits (floating-point attack) |
| canonne2020 | The Discrete Gaussian for Differential Privacy |
| mckenna2019 | Graphical-model based estimation (private-PGM) |
| mckenna2022 | AIM: An Adaptive and Iterative Mechanism |
| shokri2017 | Membership Inference Attacks Against ML Models |
| carlini2022 | Membership Inference Attacks From First Principles (LiRA) |
| vanbreugel2023 | DOMIAS |
| steinke2023 | Privacy Auditing with One (1) Training Run |
| jagielski2020 | Auditing Differentially Private ML |
| stadler2022 | Synthetic Data — Anonymisation Groundhog Day |
| giomi2023 | Anonymeter |
| gebru2021 | Datasheets for Datasets |
| mitchell2019 | Model Cards |
| lecuyer2019 | Sage: privacy budget as a systems resource |
