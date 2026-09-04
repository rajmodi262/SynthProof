# Chapter 1 — Introduction & Motivation

**Target: 1,200 words.** Write *after* Ch.2 and Ch.3, and draft it last.

> **REWRITTEN 2026-08-24 as a specification.** The previous §1.4 instructed the writer to list
> as contributions (1) "a dual-sided assurance pipeline" and (2) "budget-charged domain
> profiling". **Both were killed by this project's own novelty protocol** — the first by
> Annamalai, Ganev & De Cristofaro (USENIX Sec 2024), the second by Ganev, Annamalai, Mahiou &
> De Cristofaro (Apr 2025). Drafting to the old file would have opened the thesis with two
> claims an examiner can refute from the literature.
>
> **Nobody outside the four authors writes the prose.**

---

## 1.1 Motivation (~350 words)

The old three-beat opening (de-identification fails → regulation binds → synthetic data is the
escape hatch) is still correct and still usable:

- Sweeney (2000): 87% of the US population uniquely identified by ZIP + date of birth + sex.
- Narayanan & Shmatikov (2008): Netflix Prize re-identified from public IMDb ratings.
- GDPR Art. 9, HIPAA, India's DPDP Act 2023.

**But the motivation now has a sharper and better-evidenced fourth beat, and it should carry
the chapter.** Three fetched sources make one argument:

| Beat | Source | What it establishes |
|---|---|---|
| The field **agrees** what a DP release should disclose | Dibia, Lu, Bhattacharjee, Near & Feng, [arXiv 2507.15997](https://arxiv.org/abs/2507.15997) (2025) | Expert-elicited nine-category privacy label |
| **Nobody checks it** | Song, Sarathy, Shoemate & Vadhan, CSCW 2024, [arXiv 2410.09721](https://arxiv.org/abs/2410.09721) | Practitioners do not verify DP guarantees; they trust implicitly |
| **Implementations lose the guarantee anyway** | Cebere et al., Feb 2026, [arXiv 2602.17454](https://arxiv.org/abs/2602.17454) | 12 DP libraries audited, 13 guarantee violations |

That is the gap the thesis addresses: not "nobody discloses", but **disclosure that nothing
checks, resting on implementations that demonstrably drift.**

`[WRITE: ~350 words. Three citations, one argument.]`

---

## 1.2 Problem statement (~250 words)

Two communities solving halves. Formal DP proves an upper bound nobody verifies against the
implementation. Empirical auditing measures a lower bound that carries no guarantee and is not
attached to the artefact it describes.

**Trap.** Do **not** write "nothing ships both" or "no existing system ships a checkable
release artefact." Occupied on all three counts — dual-sided assurance (USENIX Sec 2024),
structured privacy labels (Dibia et al. 2025), machine-checkable artefacts (Croissant, MRM3,
Laminator). `scripts/check_thesis_claims.py` has a `no-existing-system` rule that will fail the
build on this phrasing, and it is right to.

Write what **we found**, and name the adjacent work: *"we found no proposal that reports the
operating range of its own empirical privacy measurement inside the artefact"* — that is
survivable, and Dibia et al.'s own expert calling the omission *"privacy theater"* is the
evidence for it.

`[WRITE: ~250 words.]`

---

## 1.3 Thesis statement (~100 words)

`[WRITE: ~100 words. Tighten the statement in ../thesis.md. It must not contain a first-to
claim — `check_thesis_claims.py` has a `first-to` rule and no first-to claim survived the
protocol.]`

---

## 1.4 Contributions (~300 words)

**Rewritten because two of the four were dead.** Number them and mark each honestly as
*implemented*, *evaluated*, or *both*. A reviewer will separate these whether or not you do.

| # | Contribution | Status | Strength — state it this way |
|---|---|---|---|
| 1 | **The clique-selection confound**: any DP-synthesis benchmark scoring a marginal-based mechanism on a small fixed set of low-order statistics risks measuring clique selection rather than fidelity | evaluated, two datasets | ⭐ **Strongest. A methodological contribution, and it was invisible from one dataset.** Lead with it |
| 2 | **Reporting the empirical measurement's operating range inside the release artefact** (`audit_ceiling`) | implemented + evaluated | Narrow but defensible. Dibia et al. propose empirical metrics and **no** standard for their limits |
| 3 | **A signed, standards-conformant release artefact**: the Privacy Data Sheet emitted as a Croissant 1.1 record with a DP vocabulary extension, Ed25519-signed, accepted by the official MLCommons validator | implemented | **Engineering novelty, not science.** Say so |
| 4 | **A data-blind refusal gate** — schema and row count only, autonomous refusal | implemented | State as **UNREFUTED, never novel.** The SDC Handbook returned HTTP 403 |
| 5 | An empirical study of mechanism families (H1), subgroup leakage (H2) and allocation (H3) on **two** datasets, with the proved-vs-audited comparison **retracted** and why | evaluated | The retraction is a result |

**Traps in this section.**
- Do not claim dual-sided assurance, budget-charged profiling, the ceiling *as a result*,
  self-audit defect-finding, structured privacy labels, automated release gating,
  machine-checkable artefacts, or cross-release budget management. **Eight dead claims**, all
  killed by our own protocol. `research/08_novelty_verdict.md` §3.1 is the list.
- The ledger is **not** cross-release. There is no cross-session budget enforcement; DPolicy
  ([arXiv 2505.06747](https://arxiv.org/abs/2505.06747)) is the system that does that properly.
  ch02's positioning matrix currently ticks "Cross-release" and contradicts the README — fix
  one of them before submission.

`[WRITE: ~300 words.]`

---

## 1.5 Scope and non-goals (~100 words)

Tabular data only. Single data holder. Record-level privacy. Central DP model — the curator
reads the raw table, and every ε is conditional on that curator being trusted
(`deployment_model: central` on the certificate). Forward-pointer to Ch.3 §3.5.

`[WRITE: ~100 words.]`

---

## 1.6 Thesis structure (~100 words)

`[WRITE: ~100 words. One sentence per chapter.]`

---

## Writing note

The introduction is the most-read and least-carefully-written chapter in most theses. Draft it
last, then cut it by a third.

**Before submitting this chapter,** run `python scripts/check_thesis_claims.py`. It currently
reports `missing-ceiling` against ch01: the chapter mentions an audited ε without the ceiling
beside it. A zero with no ceiling beside it is precisely the "privacy theater" failure Dibia
et al.'s experts warned about, and it is the single easiest thing for an examiner to catch.
