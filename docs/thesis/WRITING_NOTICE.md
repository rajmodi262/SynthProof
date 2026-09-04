# Writing notice — read before drafting any chapter

**Dated 2026-08-23.** One page. It exists because several claims changed today, and four
chapters are still unwritten — so the risk is that someone drafts, in good faith, something that
was true last week and is not true now.

**This is not prose to paste.** It is a list of things that must not be written.

---

## UPDATE 2026-08-24 — the four stubs were rewritten as specifications

**Re-read `ch01`, `ch05`, `ch07` and `ch08` before drafting.** They were written before the
audit-ceiling finding, before ACSIncome, and before fairness/linkability/Croissant landed, and
they instructed the writer toward claims that are now false:

- **ch01 §1.4** listed *"dual-sided assurance"* and *"budget-charged domain profiling"* as
  contributions. **Both are dead.** The contributions table is rewritten around the five that
  survive, led by the clique-selection confound.
- **ch07 §7.3** made the proved-vs-audited gap *"the primary result"* — the comparison the
  ceiling finding disqualifies. It is now §7.4 and it is a **retraction section**. §7.5 (the
  confound) is the new lead. §7.5-old told the writer to report **LiRA and anonymeter**, neither
  of which exists.
- **ch08 §8.1** was built on *"ε_proved = 8, ε_audited = 0.6"*, a number never measured. §8.2's
  *"self-audit is genuinely distinctive"* is dead (Cebere et al.).
- **ch05** predated six modules and under-counted the suite by ~100 tests.

Each rewritten file states at the top what changed and why. They remain **specifications** —
section list, word budget, the committed number that supports each claim, and the trap to avoid.
Not one sentence of them is thesis prose.

Also corrected: `results/RESULTS.md` listed **H3 as "not started"** when it ran on both datasets,
and deferred the ratio claim to a one-run construction that has since landed.

**Current suite: 607 passed, 93% coverage, `make reproduce` passes.**

---

## UPDATE 2026-08-24 (second pass) — ch02 and ch06 reviewed

**ch02 — the survey does not cover the literature that killed us.** §2.1–2.5 cite **none** of
the eight killing sources; all of Annamalai, Ganev, Cebere, Dibia, SACRO and Laminator appear
only inside the §2.6 working-note callout. Whole-file counts: `Croissant 0 · Song 0 ·
DPolicy 0 · PrivateKube 0 · SynthGuard 0 · MRM3 0`. **§2.4 and §2.5 now each carry a
specification block** listing exactly what to add and why. The §2.6 callout has been replaced —
it still claimed the protocol was interrupted at 2 of 8 families and that no verdict existed.
The matrix note has been corrected in **both** directions: `Verifiable: partial` understates a
signed, validator-accepted artefact, and `Lower bound ✅` overstates an ε_audited that was
0.000 in every cell.

**One ch02 item left for you, deliberately:** whether `Lower bound` stays a tick in the
positioning matrix.

**CORRECTION 2026-08-25 — ε = 70.49 IS traceable; an earlier note here said it was not.**
That was wrong, and acting on it would have deleted a sound, well-documented number. It is
recorded in `accounting/calibration.py:6`, `generators/independent.py:74`,
`docs/ARCHITECTURE.md` (§101, §432), `docs/defence/DEFENCE.md` (three places), and
`docs/AUDIT_AND_ROADMAP.md:86`, which carries the full before/after row
`| 8.0 | 70.49 | 8.81x | 7.437 | 0.93x |` and ties it to named audit finding **F2**. It is
safe to cite. The lesson worth keeping: `git log -S` over thesis files answers "when did this
text enter the prose", not "does this number have a source" — grep the code and docs.

**ch06 — no dead claims**, and §6.7–6.10 are the strongest prose in the thesis. Six accuracy
defects are listed in a review block at the top of the file; the two that matter are **§6.4
naming TPR@0.1%FPR when the code computes TPR@1%FPR**, and **§6.6 needing to declare that
`make reproduce` re-aggregates H1 checkpoints rather than re-fitting**.

**The ceiling overstatement was mine and is fixed.** ch07 §7.4 and ch08 §8.1 said canary
auditing cannot confirm tight bounds. Ganev, Annamalai & Kulynych (arXiv 2604.18352, Apr 2026)
get tight audits of MST and AIM with a Gaussian-DP/f-DP estimator. The ceiling is a property of
**our single-threshold binomial estimator**, not of auditing. Both specs now say so, and §8.4
carries replacing the estimator as the highest-value future work with a kill criterion.

---

## Where the thesis actually is

| Chapter | Words | State |
|---|---:|---|
| ch01 Introduction | — | **stub; spec rewritten 08-24** |
| ch02 Literature review | 2,442 | drafted; corrected today |
| ch03 Threat model | 1,270 | drafted |
| ch04 System design | 1,135 | drafted |
| ch05 Implementation | — | **stub; spec rewritten 08-24** |
| ch06 Methodology | 2,418 | drafted |
| ch07 Results | — | **stub; spec rewritten 08-24** |
| ch08 Discussion | — | **stub; spec rewritten 08-24** |
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
