# Chapter 8 — Discussion, Limitations & Future Work

**Target: 1,500 words.**

> **REWRITTEN 2026-08-24 as a specification.** The previous version built §8.1 on *"if
> ε_proved = 8 but no attack recovers more than ε_audited = 0.6"* — the comparison the
> audit-ceiling finding disqualifies, and a number the project never measured. It called the
> self-audit "genuinely distinctive" (killed by Cebere et al., Feb 2026) and hedged §8.3 on
> milestones that have since landed.
>
> **Nobody outside the four authors writes the prose.**

---

## 8.1 Interpretation — what the gap does and does not mean (~350 words)

**Do not frame this as "the bounds are loose or the attacks are weak."** On this project's
evidence it is neither: the instrument's working range did not cover the regime, and that was
determined before any mechanism ran.

The honest interpretation for a practitioner:

- `ε_audited = 0.000` against a proved 7.36 and a one-run ceiling of 2.97 at m = 60 means the
  auditor **could not have detected** the budget spent. It is not evidence of low leakage.
- Certifying an ε costs canaries **exponential** in that ε (≈ `ln(1/α)·e^ε`). Certifying
  ε = 7.36 needs ~4,711 perfectly-detected canaries. Raising m is not a fix: m = 800 lifts the
  paired ceiling only to 5.38.
- **What *our* auditor is for:** catching broken implementations. It found a verbatim release
  at m = 10. It will never confirm that ε = 7.36 is tight at m = 60.

**Do not generalise that to auditing as such** — it is the one overstatement an examiner in
this area will catch. Ganev, Annamalai & Kulynych (Apr 2026,
[arXiv 2604.18352](https://arxiv.org/abs/2604.18352)) obtain **tight** audits of MST and AIM
with a Gaussian-DP / f-DP estimator, on the same mechanism family where ours returned 0.000.
The ceiling is a property of **the single-threshold binomial estimator this project chose**.

The honest reframing, and it is still worth making: *a canary audit reported without its
operating range is uninterpretable, and the estimator you choose sets that range.* Volunteering
the paper that beats us is stronger than being shown it, and it converts a limitation into a
named, costed piece of future work (§8.4).

**Trap.** A failed attack is not proof of safety, and the audit only lower-bounds what *these*
adversaries achieved. Say it.

`[WRITE: ~350 words.]`

---

## 8.2 What the novelty protocol returned (~350 words)

**Replaces the old "self-audit as method" section**, whose central claim is dead: Cebere et al.
(Feb 2026) audited 12 DP libraries and found 13 violations, so a defect count is **typical of
code that was actually audited**, not a distinction.

**The section that survives is stronger, and it is the best answer in the viva:** open with the
eight claims we disproved about ourselves.

| Killed | By |
|---|---|
| Dual-sided assurance | Annamalai, Ganev & De Cristofaro, USENIX Sec 2024 |
| Budget-charged domain profiling | Ganev, Annamalai, Mahiou & De Cristofaro, Apr 2025 |
| The audit ceiling *as a result* | Corollary of Steinke et al. Thm 2.1, verified bit-identical |
| Defect-finding by self-audit | Cebere et al., Feb 2026 |
| Structured privacy labels | Dibia et al., 2025 |
| Automated release gating | Five Safes + SACRO, UK TREs since 2022 |
| Machine-checkable release artefacts | Croissant, MRM3, Laminator |
| Cross-release budget management | PrivateKube (OSDI'21), Cohere, DPack, DPolicy |

**Four of eight come from one author cluster** (Ganev, Annamalai, De Cristofaro, Kulynych)
running this exact programme roughly two years ahead. Competing on their axis loses; say so.

**The position that survives is integration, not invention** — and it now has a runnable
artefact behind it, not just a paragraph. Dibia et al. is simultaneously the strongest kill and
the strongest validation: a panel of DP experts converged on almost exactly the field set we
built, including `unit_of_privacy` and provenance. They propose **no signing** and **no standard
for reporting the limits of an empirical privacy metric** — an omission one of their own experts
called *"privacy theater"*. Those two gaps are what we fill.

**Source:** `research/08_novelty_verdict.md` — §3.1 for the kills, §3.3 for the position,
§4.1 for the built artefact.

`[WRITE: ~350 words. Volunteer the kills first. A viva answer that opens with eight things you
disproved about yourselves is stronger than any claim.]`

---

## 8.3 Limitations (~450 words)

Thorough. A reviewer trusts a document that finds its own holes. **The old hedges are resolved
— state these as facts, not conditionals.**

| Limitation | Status |
|---|---|
| Audited ε is uninformative at the ε values claimed | **Confirmed**, and the ceiling is reported beside every value |
| Ledger is tamper-**evident**, not tamper-proof; key custody is an organisational control | Confirmed. Anyone holding the key can rewrite and re-sign |
| The signature proves the sheet is unaltered, **not** that the numbers are right | Confirmed; the certificate says this itself |
| **No cross-release budget enforcement** | Confirmed. DPolicy occupies that ground |
| Systematic ε under-spend (proved/target ≈ 0.92) | **Diagnosed** — `BudgetPlan` splits linearly while RDP composition is sublinear. Fix is known and deliberately deferred; it would invalidate every committed result |
| LiRA not implemented | Recorded decision, ~21 h for a likely wide-CI null |
| Anonymeter not integrated | Hard dependency conflict: pins `numpy < 2`, breaks AIM |
| H1 structure result is Adult-specific | ACS contradicts it; see §7.5 |
| H2 and H3 are nulls at this scale | Instrument-limited; detectability stated |
| Tabular only, record-level only, single holder, central model | Scope |
| Croissant `dp:` vocabulary is a **project namespace**, not a registered one | Carries no external authority; the record says so |
| Many 2026-08-22/23 citations were read at **abstract level** | Marked as such in `research/BIBLIOGRAPHY.bib`. Citing an abstract as a full read is the same failure as reporting an uncomputed number |
| S3 (data-blind refusal) rests on one practice guide | The SDC Handbook returned **HTTP 403**. State as unrefuted, never novel |

`[WRITE: ~450 words.]`

---

## 8.4 Future work (~250 words)

Name the algorithm, the expected cost and the **kill criterion**. A wish list does not read as
a research programme.

| Direction | Why it follows |
|---|---|
| **Replace the single-threshold binomial estimator with a Gaussian-DP / f-DP one** | The highest-value item here. Ganev, Annamalai & Kulynych (arXiv 2604.18352) get **tight** audits of MST and AIM with it where ours returns 0.000. **Kill criterion:** if the audited ε on a verbatim release at m = 60 does not exceed the 2.97 one-run ceiling, the estimator is not the binding constraint |
| Adopt an **algorithm-aware adversary** and re-run the three-point comparison | Tests whether the ceiling, the estimator or the **adversary** binds. With the row above it separates all three — currently they are confounded |
| Fix the `BudgetPlan` under-spend by outer bisection over stage shares | Composition is monotone in the multiplier, so it is well-posed; costs a full grid re-run (~4 h/dataset) |
| Read the SDC Handbook and settle the refusal-gate claim | The weakest of the three survivors |
| Per-subgroup risk equalisation | *Risk-Equalized DP Synthetic Data* (arXiv 2602.10232) assumes the effect H2 could not resolve and builds a mechanism for it |
| Register the `dp:` vocabulary, or propose the fields to MLCommons | Turns an engineering artefact into an ecosystem contribution |

**Trap.** Do **not** write "extend the Privacy Data Sheet toward a community standard" as
though it were open. Dibia et al. proposed the label; Croissant is the standard. What is open
is **registering our extension**, which is a narrower and more honest thing to say.

`[WRITE: ~250 words.]`

---

## 8.5 Conclusion (~150 words)

`[WRITE: ~150 words. Return to the thesis statement. State what was demonstrated and, with
equal clarity, what was not — the proved-vs-audited comparison was retracted, H2 and H3 are
nulls, and the H1 structure result did not reproduce on a second dataset.]`

---

**Before submitting this chapter,** run `python scripts/check_thesis_claims.py`. It currently
reports `missing-ceiling` against ch08.
