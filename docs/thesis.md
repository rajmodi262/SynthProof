# SynthProof — Thesis & Research Framing

> **This file is the one-page framing. The full thesis lives in [`thesis/`](thesis/),
> which carries the chapter scaffolds, word budgets and writing order.**

---

## Thesis statement

Empirical canary auditing of tabular DP synthesis mechanisms reveals systematic gaps below the
formal RDP bound; budget-charged domain profiling combined with a signed hash-chain ledger
prevents that budget from silently degrading across a multi-release programme.

---

## Hypotheses

1. **H1 — Proved vs. audited gap.** Across tabular DP synthesis mechanisms, the empirical
   privacy loss recovered by one-run canary auditing is strictly lower than the formal RDP
   bound, and the magnitude of the gap varies systematically by mechanism family.
2. **H2 — Subgroup disparate impact.** Under uniform budget allocation, records belonging to
   minority demographic subgroups exhibit higher empirical leakage than majority records at
   fixed target epsilon.
3. **H3 — Ledger-driven allocation.** Utility-weighted budget allocation across feature columns,
   driven by historic spend, yields higher downstream macro F1 than uniform allocation at equal
   total privacy spend.

---

## Status of each hypothesis

| | Testable today? | Blocked on |
|---|---|---|
| H1 | No | Two genuinely distinct mechanism families (M1.8), real data (M1.1-M1.3), multi-seed sweep (M1.11) |
| H2 | No | ACS PUMS with subgroup labels (M1.4), per-subgroup audits (M2.8) |
| H3 | No | Allocator wired into the generators (M3.5) |

Reporting a hypothesis as untested is not a failure; presenting an untested hypothesis as
supported would be. See [`TASKBOARD.md`](TASKBOARD.md).

---

## Related documents

- [`thesis/`](thesis/) — chapter scaffolds and writing order
- [`preregistration.md`](preregistration.md) — the commitments the results chapter must honour
- [`threat_model.md`](threat_model.md) — adversary model (expanded in `thesis/ch03`)
- [`AUDIT_AND_ROADMAP.md`](AUDIT_AND_ROADMAP.md) — current state and remaining work
