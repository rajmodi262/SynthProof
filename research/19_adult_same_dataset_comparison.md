# 19 — Same-dataset comparison on UCI Adult (vs P7 Mohapatra & P8 AIM)

> The guide's #1 ask: run our technique on the same dataset prior work used and show the comparison.
> UCI **Adult** is the field-standard benchmark — used by P1, P2, P5, **P7**, **P8**. Every number in
> the "SynthProof" columns is from our committed results (`results/h1_all_families.json`) or a live
> `boundary-audit` run; prior-work numbers are quoted from the papers with the metric named. Honesty
> rules apply: where a metric differs, it is said so; nothing is forced into a false apples-to-apples.

## 0. What is and isn't directly comparable (read first)
- **Directly comparable (relative finding):** on Adult, AIM beats the independent baseline by a wide
  margin — we reproduce that, and P8 reports the same ordering.
- **Not directly comparable (absolute):** our runs use an **n = 6,000 protocol subsample** of Adult;
  P7 uses the full **32,561** rows, P8/P5 use **48,842**. So our absolute error values are not to be
  set numerically equal to theirs. And the metrics differ: **we report correlation error / TSTR-F1 /
  MIA-AUC / audited ε**, P8 reports **workload error (TVD over marginals)**, P7 reports **1-/2-way TVD
  and downstream F1**. We compare *within* each metric, and lead with the capability none of them have.

## 1. SynthProof on Adult — utility & privacy across ε (verified)
`results/h1_all_families.json`, n = 6,000, 5 seeds. Correlation error ↓ better; MIA-AUC ≈ 0.5 = safe.

| Mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 | proved ε (ε=8) | audited ε |
|---|--:|--:|--:|--:|--:|--:|--:|
| independent | 0.0934 | 0.0930 | 0.0939 | 0.0935 | **0.0947** | 7.356 | 0.000 |
| pairwise | 0.0611 | 0.0694 | 0.0493 | 0.0197 | 0.0283 | 7.356 | 0.000 |
| **AIM** | 0.0941 | 0.0443 | 0.0545 | 0.0349 | **0.0105** | 6.543 | 0.000 |

**Finding:** at ε=8, **AIM's correlation error 0.0105 vs independent 0.0947 — ~9× better**, reproducing
the "marginal graphical models win" result of P8. MIA-AUC sits at chance (≈0.50) for all — the
membership attack learns nothing at these settings (consistent with P2's finding that black-box MIAs
on DP-SDGs are underpowered; our audited ε=0.000 is therefore a *loose* bound, see §4).

## 2. What P7 and P8 report on Adult (quoted, with the metric named)
| Work | Adult size | Metric on Adult | Their headline |
|---|--:|---|---|
| **P8 McKenna (AIM)** | 48,842 (15 dim) | workload error (TVD over 3-way marginals) | AIM is best; **up to 118× lower** than MST; avg 1.3–5.6× over other mechanisms |
| **P7 Mohapatra** | 32,561 | 1-/2-way TVD + downstream F1, under injected missingness | existing methods lose **5–23%** utility at ≤5% missing, **10–190%** at ≤20%; adaptive methods recover 15–72%; missingness *amplifies* ground-truth privacy (ε̄ = 0.1–0.65× ε) |
| **P5 Ganev (discretize)** | 48,842 | utility vs #bins; MIA AUC | optimizing discretizer/bins +9–44%; DP domain drops MIA **100%→≈50%** |

INFERENCE: our AIM-vs-independent ordering matches P8's; our "no measurable membership leak" matches
P2/P5's message that black-box audits read low. CONFIDENCE: high on the ordering; the absolute values
are not cross-comparable (different n, different metric).

## 3. The comparison that matters — the capability NONE of them ship
P7, P8 and P5 all stop at *utility (and, for P5, a mechanism-side MIA)*. **None ships a checkable
release artifact.** SynthProof does, and it is runnable on the same Adult release. Live
`boundary-audit` on a leaky Adult release (`demo/sheet.json`, seed 42):

```
Release-boundary audit of a privacy-data-sheet
  open channels (leak): 5   rest on producer honesty: 0
  [LEAK] RB1 seed: publishes the run seed (42)            -> deterministic membership oracle
  [LEAK] RB2 num_rows: 3000 with no stated basis          -> exact private count
  [LEAK] RB3 input_fingerprint: unkeyed 64-hex SHA-256    -> membership test
  [LEAK] RB4 evaluation: real-table metrics, unlabelled   -> read as covered by epsilon
  [LEAK] RB6 domain_source: inferred-nonprivate           -> the domain itself leaks (P4/P5)
  [ ok ] RB5 accountant_agreement: agree
  FAILED: this artefact discloses something its epsilon does not cover.
```
The **RB6 line is the direct, checkable realisation of P4/P5**: Ganev et al. *proved* that reading the
domain from the data breaks DP; SynthProof *flags it from the shipped document alone*. A corrected
Adult release (seed withheld, `release_rows_source=protocol`, keyed HMAC, `evaluation_privacy` label,
`domain_source=declared`) passes with 0 open channels.

Plus two things unique to our Adult evaluation:
- **Audited ε = 0.000 reported beside its 2.97 ceiling** (60 canaries) — honest "below detection
  limit," a report P2 shows is exactly what's missing when black-box audits read ≈0.
- **A membership audit of the missing-data handling step** (our imputation audit, Adult) — the check
  P7 leaves open.

## 4. Honest caveats (state these in the viva)
- Our absolute utility numbers are on a 6k subsample, not the full Adult; only the *ordering* transfers.
- Audited ε=0.000 is a **black-box-loose** bound (P2: black-box MIAs read ε≈0 even at true ε=4), not a
  proof of safety — reported next to the ceiling for that reason.
- We **use** AIM (P8); we do not claim to beat it. Our contribution is the release-boundary layer.

## 5. One-line takeaway
*On the same Adult benchmark, we reproduce AIM's ~9× utility edge, and then do the thing P7/P8/P5
never do — read the shipped release and flag every channel that leaks outside ε, including the
domain-extraction leak P4/P5 proved but never made checkable.*
