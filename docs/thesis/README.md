# SynthProof — Thesis

**Target: 15,700 words across 8 chapters.** Current total: see the word count below.

The thesis is the single most likely thing to sink this project. It is ~94 hours of work that
**cannot be compressed at the end**, and roughly 43% of it depends on no code at all.

## Word count

```bash
wc -w docs/thesis/ch*.md
```

| Chapter | Target | Depends on | Status |
|---|--:|---|---|
| [Ch.1 Introduction](ch01-introduction.md) | 1,200 | — | outline |
| [Ch.2 Literature review](ch02-literature-review.md) | 2,500 | — | ✅ **first draft ~2,300 words** |
| [Ch.3 Threat model](ch03-threat-model.md) | 1,500 | **nothing — write now** | outline + draft |
| [Ch.4 System design](ch04-system-design.md) | 2,000 | M0 ✅ **write now** | outline |
| [Ch.5 Implementation](ch05-implementation.md) | 1,500 | M1 | stub |
| [Ch.6 Methodology](ch06-methodology.md) | 1,200 | M1.11 | stub |
| [Ch.7 Results](ch07-results.md) | 2,500 | M1.13, M2.8 | stub |
| [Ch.8 Discussion](ch08-discussion.md) | 1,500 | M2 | stub |
| **Total** | **13,900** | | |

Plus ~1,800 words of API reference and reproducibility guide outside the thesis proper.

## Order of writing

1. **Ch.2 Literature review** — 2,500 words, zero dependencies, and it forces you to
   understand the field before defending a contribution in it. Start here.
2. **Ch.3 Threat model** — 1,500 words, zero dependencies. Sharpens what the system must do.
3. **Ch.4 System design** — 2,000 words. M0 is complete, so the architecture is settled.
4. Everything else follows the code.

## House rules

These exist because the first self-audit found fabricated metrics in four separate modules.
The same discipline applies to prose.

1. **Every number in the thesis traces to a committed experiment.** If you cannot point at the
   script and the seed that produced it, it does not go in.
2. **Report results that contradict the hypotheses.** The preregistration commits to this.
   A refuted hypothesis honestly reported is a contribution; a quietly dropped one is misconduct.
3. **Name algorithms accurately.** If the implementation is an independent-marginal baseline,
   the thesis calls it that, not AIM.
4. **Distinguish "we proved", "we measured", and "we expect".** These are three different
   claims and reviewers will separate them whether or not you do.
5. **Cite the implementation you actually used.** Composition comes from `dp_accounting`;
   say so, and say why (see the audit — the hand-rolled version under-reported ε by ~2×).

## Figures to produce

| Figure | Source | Chapter |
|---|---|---|
| Pipeline architecture | `docs/deck/` diagram | Ch.4 |
| Privacy–utility frontier with CI bands | M1.12 | Ch.7 |
| ε_proved vs ε_audited across mechanisms | M1.13 | Ch.7 |
| Per-subgroup leakage (H2) | M2.8 | Ch.7 |
| Calibration: target vs achieved ε | already measurable | Ch.5 |
| Ledger hash-chain schematic | — | Ch.4 |
| Attack ROC curves at low FPR | M2.7 | Ch.7 |

## Related documents

- [`../AUDIT_AND_ROADMAP.md`](../AUDIT_AND_ROADMAP.md) — findings and remaining work
- [`../TASKBOARD.md`](../TASKBOARD.md) — trackable tasks
- [`../preregistration.md`](../preregistration.md) — the commitments Ch.6 must honour
- [`../../brutal_project_audit.md`](../../brutal_project_audit.md) — the self-audit, which is
  itself worth a paragraph in Ch.8 as a methodological contribution
