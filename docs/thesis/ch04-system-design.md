# Chapter 4 — System Design & Architecture

**Target: 2,000 words.** M0 is complete, so the architecture is settled. **Write this third.**

---

## 4.1 Design principles (~300 words)

State the four rules the system is built on, and note that three of them were adopted *after*
a self-audit found violations. That the project audited itself and changed its own design is a
methodological point worth making, not hiding.

1. **Nothing reads the sensitive table for free.** Schema discovery, range estimation, and
   category-domain discovery all charge the accountant. Most pipelines take these for free,
   which silently invalidates the headline ε.
2. **Never write a bound that cannot be cited.** Composition is delegated to `dp_accounting`.
   Motivation: our own RDP implementation used `min(q·ρ(α), truncated_MTZ)` for subsampling —
   neither branch a theorem — and it under-reported ε by ~2× at q = 0.01.
3. **A mechanism that is charged must be applied.** Two modules were found charging ε and then
   releasing exact values. Paying budget and skipping the noise is strictly worse than not
   paying: budget is consumed *and* the data leaks deterministically.
4. **Every reported number is computed.** No hardcoded fallbacks, no metric derived as an
   affine function of another and presented as independent.

---

## 4.2 Pipeline architecture (~500 words)

Reuse the diagram from `docs/deck/`. Walk the stages in order:

```
SENSITIVE ──► DP PROFILER ──► GENERATOR ──► SYNTHETIC
                  │               │              │
                  └── charges ────┴──────────────┤
                          ▼                      ▼
                  PRIVACY ACCOUNTANT      CANARY AUDIT
                          │               ATTACK RANGE
                          │               UTILITY EVAL
                          ▼                      │
                     LEDGER ◄──────► PRIVACY DATA SHEET
```

Cover per stage: what it reads, what it charges, what it emits.

**The invariant to emphasise:** no path from the sensitive table to the output bypasses the
accountant. Every arrow that touches *D* has a charge attached.

---

## 4.3 The privacy accountant (~350 words)

The design argument: **we own the interface, not the theory.**

- `MechanismSpec` → `dp_accounting.DpEvent` translation, including the deliberate mapping of
  zero noise to `NonPrivateDpEvent` so ε is ∞ rather than a misleadingly finite number.
- The API that makes it usable as a *system* rather than a formula: `dry_run` (what would this
  cost?), `charge` (spend it, or raise), `remaining`, `snapshot`/`restore` (speculative
  execution and rollback).
- Why unknown mechanism names now raise rather than defaulting to Gaussian.
- `PrivacySpend` records both cumulative and marginal ε, because composition is sublinear and
  the running total is not the sum of the marginals — a point worth a sentence, since it
  surprises people.

Contribution framing: the RDP mathematics is not novel and we do not claim it. The **budget
enforcement interface** is the systems contribution.

---

## 4.4 ε-calibration (~350 words)

This section carries a concrete, measurable result — lead with it.

- **The problem.** `noise_scale = √d / target_eps` is a heuristic, not an inversion of the
  composition theorem. Measured drift on the toy sweep: target 0.5 → 2.53 (5.1×), target
  8.0 → 70.49 (**8.8×**), and the error grew with ε.
- **The method.** ε is strictly decreasing in the noise scale, so the inverse is well-posed.
  Bracket, then bisect on **bracket width** rather than on |ε(mid) − target|.
- **The bug worth reporting.** Terminating on the epsilon gap is unsafe: if the final probe
  lands just above the target it updates the lower bracket, leaving the upper bracket stale.
  Laplace at 5 steps with target 2.0 returned a scale achieving ε = 1.25. The invariant
  ε(hi) ≤ target < ε(lo) holds every iteration, so shrinking the bracket and returning `hi` is
  both correct and conservative. **Including this in the thesis is a strength** — it shows the
  implementation was validated rather than assumed.
- **The result.** proved/target = 0.92 across the grid, never exceeding 1.0.
- **`BudgetPlan`.** One release budget split across stages (10% profiling, 90% synthesis) so
  the composed total approximates the request instead of exceeding it by whatever earlier
  stages happened to spend.
- **Known residual.** ~8% under-spend, because RDP composition across the two stages is
  sublinear. Safe, but leaves utility unclaimed. Report it; do not hide it.

**Figure:** target vs achieved ε across mechanisms and step counts.

---

## 4.5 DP domain profiler (~250 words)

- Public vs sensitive: column *names* and coarse types are treated as public schema metadata;
  column *contents* are sensitive. State this assumption explicitly — it is load-bearing.
- Calibrated so the whole profiling pass costs its allotted ε regardless of column count.
  (The previous `eps_per_col` design meant total cost grew with the schema and no caller could
  predict a release's ε.)
- **The category-domain leak and its fix.** The profiler charged ε and then published
  `df[col].unique()` — the exact domain including values occurring once. Now categories survive
  only if their noisy count clears a threshold at 3σ.
- **Open limitation.** min/max over an unbounded column has unbounded sensitivity, so the
  declared `sensitivity = 1.0` for range queries is not yet justified. The fix is
  caller-declared public bounds (M1.7). State this as open.

---

## 4.6 Generators (~200 words)

Be scrupulous here.

- What is implemented at submission: name it accurately.
- If real AIM (`private-pgm`) has landed, describe it and keep the independent-marginal
  generator as a **deliberate ablation** — it isolates the value of modelling cross-column
  structure, which is a legitimate experimental role.
- If it has not landed, say the generator bank contains two independent-marginal baselines and
  that H1's mechanism-family comparison is correspondingly limited. **Do not call it AIM.**

---

## 4.7 The budget ledger (~250 words)

- Append-only SQLite; each entry commits to its predecessor's SHA-256; Ed25519 over canonical
  bytes. Canonicalisation matters — fixed-precision float formatting and sorted keys, or
  signatures are not reproducible.
- Threat addressed: **cross-release budget erosion.** Nothing in standard practice stops a
  second team re-releasing the same table at full budget.
- Verification: chain linkage, per-entry hash, and signature, checked in order.
- **Honest limitation.** Tamper-*evident*, not tamper-*proof*. An adversary with the private key
  rewrites and re-signs freely. Key custody is an organisational control. Also state the current
  implementation gap: the key is generated in memory per instance and not yet persisted, so
  file-backed ledgers cannot be verified after restart (M3.1).

---

## 4.8 The Privacy Data Sheet (~200 words)

- Contents: both ε values, δ, per-stage budget breakdown, mechanism and hyperparameters, canary
  counts and audit p-value, attack results, utility, ledger head, seed.
- Lineage from Gebru et al.'s datasheets; the difference is that the central claim is
  **machine-checkable**.
- Verification flow: `synthproof verify sheet.json --pubkey org.pub`.
- **State the current gap plainly** if M3.2 has not landed: the ledger head is real, the
  signature is not yet implemented.

---

## Figures for this chapter

| Figure | Source |
|---|---|
| Pipeline architecture | `docs/deck/pitch-interactive.html` diagram |
| Ledger hash-chain schematic | new |
| Target vs achieved ε (calibration) | measurable today |
| Data sheet example | `synthproof demo` output |
