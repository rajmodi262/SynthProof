# Amendments to the W9 GDP-audit preregistration

The preregistration itself (`docs/prereg/W9_gdp_audit.md`, SHA-256 `233f53e650e4…`) is frozen: every
result file records that hash, so editing its §7 in place would break the check it exists for.
Amendments are recorded here instead.

## A1 (2026-10-16, after all 12 cells ran): the comparator was mis-implemented for two mechanisms

**What the plan says (§4):** the violation comparator is the mu implied by `proved_eps`, or "the
mechanism's own composed mu where the code exposes its noise (independent)".

**What the runner did:** it computed `sqrt(3) / sigma`, the composed mu of three one-way Gaussian
marginals, for any mechanism that exposed a noise scale, not only `independent`. That number is
wrong for `fixed_workload`, which charges six Gaussian measurements on this instance (three one-way
and three two-way marginals; the accountant's recorded events confirm six), and for `dpvae`, whose
noise is subsampled DP-SGD.

**Effect:** `fixed_workload` at eps 4 was flagged as a violation at alpha 0.05 (mu_emp 0.9736 against
the mis-computed 0.9402). It was not family-wise significant, so no violation was claimed. Against the
preregistered comparator (implied mu 1.4946) there is no flag; against its true composed mu
(sqrt(6) / 1.842 = 1.3297) there would be none either. `dpvae`'s comparator moved from 0.0557 to
0.5325; its mu_emp is 0, so nothing else changed.

**Correction:** the runner now applies the composed-mu comparator to `independent` alone
(`scripts/run_gdp_audit.py`). For the three affected cells (`fixed_workload` eps 1 and 4, `dpvae`
eps 1), `comparator_mu` and the two violation fields were recomputed from values already in each
file (`implied_mu_from_eps_delta`, `mu_emp`, `mu_emp_familywise`); the values as run are kept in the
file (`mechanism_mu_from_composition_as_run`, `amendment`). No measured number changed, and no cell
was re-run.
