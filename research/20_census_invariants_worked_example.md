# 20 — Worked example: the 2020 Census "invariants" as a checkable outside-ε label

> P9 (Abowd et al., 2020 Census TopDown, HDSR 2022) is the canonical real deployment that ships
> quantities **outside the privacy budget**: the **invariants** — exact **state population totals**
> (aggregation only, no noise), plus structural zeros and edit constraints "passed to post-processing
> without noise injection." Their own words: invariants are "statistics that the Census Bureau has
> determined, as a matter of policy, to exclude from the privacy-loss accounting." **They are
> documented in prose/policy — not as a machine-checkable field.** This is the release-boundary
> problem in production, and here we show `boundary-audit` turning it into something a validator reads.

## The rule
SynthProof's release boundary (rule 3): anything that leaves the curator and is *not* covered by ε must
be **labelled in the artifact itself** as outside ε. `boundary-audit`'s **RB4** enforces exactly this —
real-table quantities without an `evaluation_privacy` label are an open channel; with the label they are
a sound, declared disclosure.

## The worked example
Model a Census-style release whose sheet carries three invariants (state population total, occupied
housing units, an enforced structural zero) alongside a DP mechanism output.

**A) Invariants published WITHOUT a label** — what a prose-only, naive sheet does:
```
open channels (leak): 1
[LEAK] RB4 evaluation: real-table quantities published with no statement that epsilon does not cover them
[UNVERIFIABLE] RB2 num_rows = 331,449,281 is 'declared' (a reader must trust it wasn't read off the table)
FAILED: this artefact discloses something its epsilon does not cover.
```
A reader reasonably assumes the headline ε covers everything in the artifact — so the exact totals read
as if they were private outputs. That is precisely the confusion P9's prose leaves open.

**B) Invariants DECLARED outside ε** — SynthProof's labelled artifact (add `evaluation_privacy`:
"these are invariants, published as policy OUTSIDE the budget; ε does not cover them"):
```
open channels (leak): 0
[ ok ] RB4 evaluation_privacy: real-table quantities published and labelled as outside epsilon
[UNVERIFIABLE] RB2 num_rows = 331,449,281 is 'declared'
PASSED: no open channel found. (Not proof of soundness; see UNVERIFIABLE.)
```

## What this shows (and the honest nuance)
- **The label is the contribution.** The Census *does* the right thing (invariants are a deliberate,
  disclosed policy choice — a *declared* outside-ε quantity, not a hidden leak). But that disclosure is
  **prose**; no standard field lets a validator confirm "these fields are outside ε." RB4 makes it a
  checkable label. This is exactly the P10 gap (a label with no way to state limits) applied to P9.
- **The honest nuance stays visible.** Even labelled, the exact population total is **RB2
  UNVERIFIABLE**: a declared exact count that equals the input's length still leaks it, and the artifact
  alone cannot prove otherwise. `boundary-audit` never certifies it safe — it surfaces that the
  guarantee rests on the curator's declaration. That asymmetry is the whole design.
- **Not obtainable to run on real Census data** (Title-13 restricted) — this is a faithful model of the
  release, not a run on the confidential file.

## One line for the paper / viva
*The 2020 Census proves this matters at national scale: it publishes state totals and structural
constraints outside the privacy budget, documented only in prose. `boundary-audit` turns "which fields
are outside ε" into a signed, machine-checkable label — and still honestly marks the exact totals as
resting on the curator's word.*

*(Natural small extension, tracked as future: a dedicated `public_invariants` field so invariants are
named explicitly rather than folded into the evaluation-privacy label.)*
