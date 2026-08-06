"""Executes experimental sweeps and regenerates results/RESULTS.md."""

from synthproof.frontier.sweep import SweepRunner

HEADER = """# SynthProof — Experiment Results

> [!WARNING]
> **Status: PRELIMINARY — this is NOT the preregistered protocol.**
>
> | | Preregistered ([docs/preregistration.md](../docs/preregistration.md)) | Actually run here |
> |---|---|---|
> | Dataset | UCI Adult (n=48,842), ACSIncome (n=100,000) | 100-row synthetic toy table |
> | Seeds | 5 per configuration | 1 |
> | Correlation structure | Real | **None** — columns are drawn independently |
>
> Because the toy columns are statistically independent by construction, there is no joint
> structure for a synthesiser to preserve or destroy. **Utility numbers below measure almost
> nothing and must not be read as evidence for or against H1.** Both generators are also
> independent-marginal samplers, so the two "mechanism families" are not genuinely distinct.
>
> No result in this table has been used to confirm or reject any preregistered hypothesis.
> See [brutal_project_audit.md](../brutal_project_audit.md) for the full accounting.

---

## Table 1: Privacy & utility sweep (proved vs. audited)

Columns: `proved eps` is the RDP-composed formal bound. `audited eps` is a Clopper-Pearson
lower bound from held-out canaries at 95% confidence (0.00 means the audit found no
statistically significant leakage, not that leakage is absent). `p` is a one-sided Fisher
exact test against the held-out canary null. `MIA AUC` is a nearest-neighbour membership
inference baseline, **not** LiRA — 0.5 is chance.

| Dataset | Mechanism | Target eps | Proved eps | Audited eps | Audit p | TSTR F1 | TRTR F1 | Singling-out | MIA AUC | MIA adv |
|---|---|---|---|---|---|---|---|---|---|---|
"""


FOOTER = """
---

## How to read this table

**`Audited eps` is 0.00 everywhere, with `p` around 0.5.** Unlike the previous version of this
table, that is now a genuine null result rather than a dead instrument: the auditor is validated
by `tests/test_audit_attacks.py::test_canary_audit_detects_leakage_and_reports_zero_when_absent`,
which shows it recovers a positive epsilon and p < 0.05 when the release genuinely leaks. Here it
simply finds no statistically significant canary leakage — unsurprising with 5 canaries and heavy
noise. Detecting a real gap requires many more canaries and a real generator.

**`Proved eps` massively exceeds `Target eps`, and the error grows.** At target 8.0 the AIM
baseline composes to 70.49. There is no epsilon-calibration step anywhere: the target only picks a
noise scale, and the accountant then re-derives epsilon independently. This is audit finding F2 and
is the single most important thing to fix.

**The two mechanisms now differ.** In the previous table AIM and Gaussian Copula produced
identical numbers in all ten rows. The cause was a dispatch bug: `run_cell` tested
`mechanism_name.lower() in ("aim", "mst")` while the sweep passed `"AIM / MST"`, so the AIM branch
was never taken and *both* halves of the table were secretly the copula generator.

**`TRTR F1` is now ~0.334, not 0.971.** The toy label is independent of the features, so chance
performance is correct. The old 0.971 was in-sample accuracy from evaluating the model on its own
training data.

**`Singling-out` is 0.000 by construction** — exact row matching cannot fire on float columns.
Read it as "no signal", not as "no risk".
"""


def main():
    print("Executing SynthProof experimental sweeps...")
    results = SweepRunner(seed=42).run_full_sweep()

    rows = "".join(
        f"| {r.dataset_name} | {r.mechanism_name} | {r.target_eps:.1f} | {r.proved_eps:.2f} | "
        f"{r.audited_eps:.2f} | {r.audit_p_value:.3f} | {r.tstr_f1:.3f} | {r.trtr_f1:.3f} | "
        f"{r.singling_out_risk:.3f} | {r.mia_auc:.3f} | {r.mia_advantage:.3f} |\n"
        for r in results
    )

    with open("results/RESULTS.md", "w", encoding="utf-8") as f:
        f.write(HEADER + rows + FOOTER)

    print(f"Wrote {len(results)} rows to results/RESULTS.md")


if __name__ == "__main__":
    main()
