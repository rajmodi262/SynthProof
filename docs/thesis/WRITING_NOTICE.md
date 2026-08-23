# Writing notice — read before drafting any chapter

**Dated 2026-08-23.** One page. It exists because several claims changed today, and four
chapters are still unwritten — so the risk is that someone drafts, in good faith, something that
was true last week and is not true now.

**This is not prose to paste.** It is a list of things that must not be written.

---

## Where the thesis actually is

| Chapter | Words | State |
|---|---:|---|
| ch01 Introduction | 344 | **stub** |
| ch02 Literature review | 2,442 | drafted; corrected today |
| ch03 Threat model | 1,270 | drafted |
| ch04 System design | 1,135 | drafted |
| ch05 Implementation | 288 | **stub** |
| ch06 Methodology | 2,418 | drafted |
| ch07 Results | 354 | **stub** |
| ch08 Discussion | 393 | **stub** |
| **Total** | **8,644** | against a 15,700 target |

**~7,000 words remain, and 82% of them are in the four stubs.** Nothing else in this repository
is the blocker.

---

## Five things that are now false. Do not write them.

1. **"The audit ceiling is our finding."**
   It is a one-line corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1 / Eq. (3) — the paper
   we implement. Verified bit-identical to `max_provable_epsilon` at r = 10/60/100/400/800 and
   pinned by `tests/test_audit_power.py`. **Ours is the measurement**, not the inequality.
   Affects **ch07, ch08**.

2. **"No existing system ships both bounds / a checkable release artefact."**
   Occupied. Dual-sided assurance: USENIX Sec 2024. Structured privacy labels: Dibia et al.
   2025. Machine-checkable artefacts: Croissant, MRM3, Laminator. Affects **ch01, ch02, ch08**.

3. **"Charging domain profiling is our contribution."**
   Published: Ganev, Annamalai, Mahiou & De Cristofaro, Apr 2025. Ours is the **checkable
   `domain_source` field**, not the insight. Affects **ch04, ch08**.

4. **"Our refusal gate is novel."**
   Automated release gating is production practice under Five Safes; SACRO has automated it
   since 2022. Our difference — schema-only, autonomous refusal — is real but **the SDC Handbook
   could not be retrieved**, so write it as *unrefuted*, never *novel*. Affects **ch04, ch08**.

5. **"Finding twelve defects by self-audit is unusual."**
   Cebere et al. (Feb 2026) audited 12 DP libraries and found 13 violations. Our defect count is
   **typical of code that was actually audited** — which is still the point worth making, but it
   is not a distinction. Affects **ch08**.

---

## Two things that are now true, and are your best material

**Dibia, Lu, Bhattacharjee, Near & Feng, arXiv 2507.15997 (2025)** — an expert-elicited
nine-category DP privacy label. It overlaps our Privacy Data Sheet almost field for field. Write
that as **validation, not defeat**: DP experts converged on the fields we built. Then the two
gaps they explicitly leave open — **no signing**, and **no standard for reporting the limits of
an empirical privacy metric**, which one of their own experts called *"privacy theater"*. That
is our position, and it is narrow. Keep it narrow.

**Song, Sarathy, Shoemate & Vadhan, CSCW 2024 (arXiv 2410.09721)** — practitioners do **not**
verify DP guarantees; they trust implicitly. This is the premise ch01 has been missing. It is
also why signing and differential accounting matter.

---

## What to write where

- **ch01** — motivation is now: the field agrees what to disclose (Dibia), nobody checks it
  (Song), and implementations lose guarantees anyway (Cebere). Three citations, one argument.
- **ch05** — pure reportage. The modules exist and their docstrings carry the arguments; read
  `synthproof/audit/steinke.py` and `synthproof/data/preflight.py` first. New since your last
  read: `accounting/differential.py` and `cli.py::audit-power`.
- **ch07** — pure reportage from `results/`. Every number is committed with seeds and CIs.
  Report the ceiling beside every audited ε.
- **ch08** — the honest spine: eight claims we killed ourselves, three narrow survivors, and
  integration rather than invention. `research/08_novelty_verdict.md` is the source.

---

## Ground rules that still bind

Standing rules 1–6 in `docs/AUDIT_AND_ROADMAP.md` §7. Plus: **every citation must be read before
it is cited.** Much of what arrived on 2026-08-22/23 was read at abstract level and is marked as
such in `research/BIBLIOGRAPHY.bib` and `docs/thesis/references-additions.bib`. Citing an
abstract as if you read the paper is the same failure as reporting a number you did not compute.

**Nobody outside the four of you writes this prose.**
