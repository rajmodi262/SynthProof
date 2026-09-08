# Ceiling survey — extraction protocol

> **PRE-REGISTERED. Frozen before any paper was read.**
> This file is committed *before* the first extraction commit; `git log` order is the evidence.
> Nothing below may be changed once extraction begins. If something turns out to be wrong, add a
> dated **amendment** at the bottom and say what changed and why — never edit the original text.

## 0. Why this document exists first

The survey's contribution is a table. A table is only as credible as its provenance, and the
single easiest way to destroy it is to decide the rules after seeing the numbers. So the rules are
fixed here, in advance, including the one number the whole claim reduces to.

This project has already been burned twice by the failure this document prevents: a confound
published three times before its own ablation refuted it, and a fabricated quote that reached a
committed research note. Pre-registration is cheap; a retraction in the viva is not.

## 1. The research question

For each published paper reporting an empirical privacy estimate — or reporting a null ("no
leakage detected") — for a mechanism with a stated analytic bound: **could the instrument that
produced that estimate have detected the bound at all?**

## 2. Sampling frame — declared, not assembled by us

**Primary frame.** The 45 DP-auditing papers systematically identified by Annamalai, Balle, Hayes,
Kaissis & De Cristofaro, *"The Hitchhiker's Guide to Efficient, End-to-End, and Tight DP
Auditing"* ([arXiv:2506.16666](https://arxiv.org/abs/2506.16666), IEEE SaTML 2026), Table 1 and
Appendix B. **This is cited AS the sampling frame.** We did not assemble it and must never imply
we did. Their Appendix A gives the Scopus query that produced it.

**Supplementary frame.** 2025–26 papers surfaced during this protocol's own prior-art search and
not obviously inside that frame:

`2606.12733` · `2509.08704` · `2605.27292` · `2506.15349` · `2507.15836` · `2507.04457` ·
`2510.23427` · `2509.07055` · `2605.14591` · `2501.17750` · `2606.16952` · `2509.18014`

**The frame is frozen at this commit.** A paper discovered later goes in a dated amendment and is
reported separately, never folded silently into the primary count.

## 3. Inclusion rule

**INCLUDE** a paper if, for at least one reported configuration, it reports **both**
(a) an empirical privacy quantity — ε_emp, μ_emp, or an explicit statement that no leakage was
detected — **and** (b) the analytic bound of the mechanism being audited at that operating point.

**EXCLUDE**, recording the reason:
- purely theoretical papers with no empirical estimate
- papers auditing a mechanism with no stated analytic bound to compare against
- papers whose reported quantity is not a privacy parameter (e.g. attack AUC alone)

**Unit of analysis is the *configuration*, not the paper.** A paper reporting several audits
contributes several rows. The headline denominator N is **papers**; a per-configuration count is
reported separately. Where a paper has multiple configurations, its paper-level class is the
**most favourable** one — the reading most generous to the paper.

## 4. Fields extracted per configuration

Every field is either a value **with a section, table, figure or page locator**, or the literal
string `NOT REPORTED`. **A number without a locator is not admissible.**

| Field | Definition |
|---|---|
| `paper_id` | arXiv ID or DOI |
| `config_label` | how the paper identifies this configuration |
| `estimator_family` | one of `one_run` · `paired_cp` · `gdp` · `other` · `NOT REPORTED` |
| `budget` | canaries *m*, or runs per world *r*, as the estimator requires |
| `alpha` | confidence level of the reported lower bound |
| `eps_emp` | the empirical estimate, in the paper's own unit |
| `emp_unit` | `epsilon` or `mu` |
| `eps_proved` | the analytic bound at that operating point |
| `proved_unit` | `epsilon` or `mu` |
| `acknowledged_limit` | did the paper **itself** state its bound was budget- or power-limited? `yes` / `no`, with a locator or quote |
| `extractor` | initials |
| `source_depth` | `full text` · `abstract only` · `could not obtain` |
| `notes` | anything ambiguous |

## 5. The exclusion rule that matters most

**If `estimator_family` cannot be read from the paper, the row is EXCLUDED — never guessed.**

Three ceiling series live in this repo, in two units, and applying the wrong one is a checkable
error an examiner can catch by recomputing a single cell. Excluded rows are **counted and
reported** as a separate line ("k configurations excluded for undeterminable estimator"), because
that count is itself evidence about reporting practice.

## 6. Double-coding

- Every paper is extracted **independently by two people** who do not confer.
- Disagreements are adjudicated by a third, and the adjudicated value is recorded.
- **The inter-coder disagreement rate is reported in the paper**, per field.
- A disagreement rate above 20% on `estimator_family` or `budget` invalidates that field and it
  must be re-extracted with a sharpened definition, recorded as an amendment.

## 7. Classification

`ceiling = ceiling_for(estimator_family, budget, alpha)` — `synthproof/audit/ceiling.py`, which
refuses a units mismatch and refuses to interpolate a measured series.

Comparison is only ever made **within a unit**. A μ estimate is compared against a μ bound.

| Class | Condition |
|---|---|
| **UNDERPOWERED** | `ceiling < eps_proved` — the instrument could not have confirmed the bound *even against a fully verbatim release* |
| **SATURATED** | `eps_emp >= 0.95 * ceiling` — the estimate is pinned at the instrument's top |
| **INTERPRETABLE** | otherwise |
| **NOT REPORTED** | `budget` or `alpha` absent |

## 8. THE HEADLINE NUMBER — defined here, in advance, so it cannot be chosen later

> **K = the number of papers classified UNDERPOWERED that did *not* themselves acknowledge the
> limitation, out of N included papers.**
>
> Reported as `K/N` with a **Wilson score interval** at 95%.

Reported **alongside**, never merged into it:
- the **NOT REPORTED** count — a separate result about reporting practice
- the **excluded-for-undeterminable-estimator** count
- the count of papers that *were* underpowered **and** said so — these are restatements, not
  findings, and are excluded from K by construction

## 9. Sensitivity analyses — committed to in advance, all three reported whatever they show

1. **α sweep** at 0.01 / 0.05 / 0.10. K must not depend on our choice of α.
2. **Per-estimator split.** A K driven entirely by one estimator family is a finding about that
   family, not about the field, and must be reported as such.
3. **Leave-one-out** over the frame, to show no single paper drives the result.

## 10. Stopping rule and the null

Extraction stops when the frozen frame is exhausted. **There is no stopping rule based on the
result**, and no paper may be added or dropped after seeing its class.

**If K is small or zero, that is the finding and it is reported as the finding**, in the first
line of `results/CEILING_SURVEY.md`. The honest conclusion in that case is that the literature
knew its own limits, and the contribution reduces to the NOT-REPORTED count plus the artefact
work. This outcome is declared *in advance* as acceptable so that it cannot later be avoided.

## 11. What this survey does NOT claim

- **Not the ceiling mathematics.** A corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1 / Eq.
  (3); formalised for one-run auditing by Keinan, Shenfeld & Ligett
  ([arXiv:2503.07199](https://arxiv.org/abs/2503.07199), NeurIPS 2025) Thm 5.2.
- **Not the concept, which already has a published name.** *"maximum auditable ε"* — Annamalai,
  Ganev & De Cristofaro, USENIX Security 2024
  ([arXiv:2405.10994](https://arxiv.org/abs/2405.10994)) §2.2, who also compute it numerically in
  §7.5 **for their own configuration only**.
- **Not the survey of DP auditing.** That is arXiv:2506.16666, whose frame we borrow.
- **Not the observation that published privacy evaluations mislead.** Aerni, Zhang & Tramèr
  (CCS 2024, [arXiv:2404.17399](https://arxiv.org/abs/2404.17399)) show 2×–50× understatement
  across five defenses. **They demonstrate it by running stronger attacks; we compute a bound no
  attack can exceed.** That is the distinction to lead with.
- **Not the genre.** Retrospective reclassification of published claims from their own reported
  numbers is live in this subfield — Jebreel, Sánchez & Domingo-Ferrer
  ([arXiv:2603.22987](https://arxiv.org/abs/2603.22987), Mar 2026) — and in ML at large (Card et
  al., [arXiv:2010.06595](https://arxiv.org/abs/2010.06595)).

**What is claimed:** the first *per-paper* recomputation of the instrument ceiling from each
paper's own reported configuration, and the first reclassification of published **null** results
as readings of the instrument's floor rather than as evidence about the mechanism.

## 12. The objection this survey must survive, and the answer

**"Post-hoc power is uninformative."** Correct, and standard. Observed power is a one-to-one
function of the p-value and adds nothing.

**This is not observed power.** `ε_max(r) ≈ log(r / ln(1/α))` depends **only on the design
parameters r and α** — never on the observed outcome. It is a *minimum-detectable-effect* bound,
computable before any data is seen. The post-hoc power critique does not apply, and the reason it
does not apply must be stated in the paper rather than left for the viva.

---

## Amendments
*(append dated entries below, never edit above this line)*

### A1 — 2026-09-06 — Machine first pass. THIS IS A DEVIATION FROM §6.

§6 requires every paper to be extracted independently by **two people**. It is being extracted
**first by an LLM agent**, one pass, and the resulting rows are marked `extractor:
"machine-pass-1"` and `verified_by_human: false`.

**This does not satisfy §6 and the resulting table cannot carry the claim on its own.** It is a
labour-saving first pass: it converts "read 45 papers from scratch" into "check 45 pre-filled
rows against the source", which is the same verification work a second human coder would do
anyway, done against a draft instead of a blank sheet.

**What must still happen before any number from this table is published:**
1. A human second-codes **every** row against the source, independently of the machine's values.
2. The disagreement rate between the machine pass and the human pass is computed and reported,
   exactly as §6 requires between two human coders.
3. `verified_by_human` is flipped to `true` per row, by the person who checked it.
4. Any row still `false` at write-up time is **excluded from K** and counted separately.

**Why this is recorded rather than quietly done:** an LLM extracting numbers from papers is
precisely the failure mode that produced a fabricated quote in this project's own research notes
on 2026-09-05 (retracted in commit `2da35ea`). The mitigation is not trust, it is that the value
is worthless until a human has looked at the source. Rows the agent could not verify must say
`NOT REPORTED` or `could not obtain`, never a plausible guess.

**Frame coverage:** the machine pass covers a named subset, not the full frozen frame. The
subset and the count are recorded in the extraction file. **A partial frame yields a partial
result and must be reported as one** — K over a subset is not K over the frame.

**A structural caveat the extracting agents raised themselves, and it is the strongest argument
for §6:** the fetch tool available to them does not return raw page text — it runs a small
summarising model over the page and returns *that model's reading*. So every "verbatim" quote in
the machine rows is **a quote as relayed by a summariser, not a string anyone read in the
source.** The agents mitigated it (two-to-four independent passes per paper with differently
worded prompts, keeping only values that survived, cross-checking against a second renderer) and
they flagged the residual risk without being asked. It cannot be eliminated by more passes. It is
eliminated by a human opening the PDF.

**Enforced in code, not in a reviewer's memory:** `Row.verified_by_human` defaults to `False`,
`Classified.counts_toward_k` requires it, and `Summary.headline()` refuses to report K at all
while any included row is unverified — it returns *"PRELIMINARY — K IS NOT YET COMPUTABLE … Do
not quote K from this run."* A K of 0 must never be readable as "we looked and found nothing"
when it actually means "nobody has checked yet."
