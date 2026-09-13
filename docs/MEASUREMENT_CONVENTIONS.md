# Measurement conventions — where the audit ceiling comes from, and what it borrows

One page, cited once, referenced everywhere the ceiling appears. It exists because two
attributions in this project are easy to forget and expensive to be caught missing: the
ceiling is **not our theorem**, and reporting it beside a measurement is **not our idea
either**. Both belong to other people, and saying so first is the difference between a
transfer and an undone literature search.

## 1. The ceiling is a corollary, not a contribution

`audit_ceiling = log(r / ln(1/α))` is a one-line corollary of **Steinke, Nasr & Jagielski,
"Privacy Auditing with One (1) Training Run", NeurIPS 2023** (arXiv:2305.08846), Theorem 2.1
and Equation (3). It is verified bit-identical to `max_provable_epsilon` at r = 10, 60, 100,
400 and 800 by `tests/test_audit_power.py`, so the code cannot drift from the paper without a
test failing.

Citing Steinke alone is **not sufficient**. The same quantity is already named
**"maximum auditable epsilon"** by **Annamalai, Ganev & De Cristofaro, USENIX Security 2024**
(arXiv:2405.10994), §2.2. An examiner who opens the paper we cite will find our framing there
under a different name, and the omission will read as though we had not looked. Cite both.

## 2. Reporting an instrument's reach is borrowed from analytical chemistry

Stating the audit ceiling next to every ε_audited — so that a zero reads as *"below what this
instrument could see"* rather than *"no leakage"* — is a **transfer of limit-of-detection
reporting**, which analytical science has required for decades.

The governing standard is **MIQE 2.0 — Bustin, Kubista, Ruijter, Shipley, Untergasser, Wittwer
et al., "MIQE 2.0: Revision of the Minimum Information for Publication of Quantitative
Real-Time PCR Experiments Guidelines", *Clinical Chemistry* 2025;71(6):634–651**, which
mandates that the **limit of detection (LoD)** and **lower limit of quantification (LLOQ)** be
reported alongside any quantitative result. An analytical laboratory does not report a
concentration of zero; it reports **"Not Detected, < LOD"**, and names the LOD. That is
exactly the shape of the claim this project makes about ε_audited.

> **Corrected 2026-09-13 — the borrowed vocabulary was applied backwards.** The capsule, CLI,
> API and console all showed a green `NOT DETECTED (< LoD)` whenever ε_audited sat below the
> ceiling, and the capsule added *"Bounded under MIQE 2.0"*. That misreads the transfer in two
> ways. The audit ceiling is an **upper** limit on what an audit can certify, not a lower limit
> of detection, so an audited 1.5 under a 2.97 ceiling is a detection, not a non-detection.
> And the comparison that matters is **ε_proved against the ceiling**: whether the audit could
> have certified the claim at all. The old check never made it, so a release proving ε = 7.36
> against a ceiling of 2.97 — this project's own H1 situation — rendered green. The single
> verdict in `synthproof/audit/ceiling.py::range_verdict` replaces all four copies, and reports
> `CLAIM EXCEEDS AUDIT RANGE` for exactly that case. It also recomputes the ceiling from the
> declared estimator, budget and α, because the two shipped demo capsules carried signed
> ceilings (3.50 at 60 canaries, 4.00 at 100) that their own declared audits cannot produce.

**The transfer is the claim, not the invention.** What survived the novelty protocol (see
`research/08_novelty_verdict.md`, survivor S1) is narrower and should always be stated in this
form: *no standard exists for reporting the operating limits of an empirical privacy metric,
and we adopt the analytical-chemistry convention for one.* Dibia, Lu, Bhattacharjee, Near &
Feng (arXiv:2507.15997, 2025) elicited a nine-category privacy label for DP and propose
empirical privacy metrics **with no way to report their limits** — an omission one of their own
experts called *"privacy theater"*. That gap is what S1 fills.

## 3. Why every document repeats the citation

`scripts/check_thesis_claims.py` enforces the rule `missing-lod-transfer`: any document that
mentions `audit_ceiling`, an operating range, or a maximum auditable epsilon must also mention
MIQE, limit of detection, LoD or LLOQ. That is deliberate. A reader arrives at one document,
not at the set, and an attribution that lives only in a central file is one the reader of any
single page never sees.

## References

- Steinke, Nasr & Jagielski. *Privacy Auditing with One (1) Training Run.* NeurIPS 2023.
  arXiv:2305.08846.
- Annamalai, Ganev & De Cristofaro. *"What do you want from theory alone?" Experimenting with
  Tight Auditing of Differentially Private Synthetic Data Generation.* USENIX Security 2024.
  arXiv:2405.10994.
- Bustin, Kubista, Ruijter, Shipley, Untergasser, Wittwer et al. *MIQE 2.0.* Clinical Chemistry
  2025;71(6):634–651.
- Dibia, Lu, Bhattacharjee, Near & Feng. *Asking the right questions: a privacy label for
  differential privacy.* arXiv:2507.15997, 2025.
