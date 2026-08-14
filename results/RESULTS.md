# SynthProof — Results index

> **The toy sweep that used to live here has been deleted.** It ran 100 rows whose columns
> were drawn independently, with one seed and two generators that were both independent-
> marginal samplers. There was no joint structure for a synthesiser to preserve, so every
> utility number in it measured nothing. Its generator, `scripts/run_sweep.py`, and the
> pipeline behind it are gone rather than left in place with a disclaimer.

## Current results

| Result | Status | Document |
|---|---|---|
| **H1** — mechanism families | ✅ Supported on structure and utility; the privacy half is blocked on the auditor | [`H1_RESULTS.md`](H1_RESULTS.md) |
| **H2** — subgroup disparity | ❌ Not started. Needs per-subgroup audits (M2.8) | — |
| **H3** — ledger-driven allocation | ❌ Not started. Needs the allocator wired into the generators (M3.5) | — |

Raw output: [`h1_all_families.json`](h1_all_families.json).
Regenerate everything in this directory with `make h1`.

## The one number that is not yet interpretable

`ε_audited = 0.000` in every cell of every experiment this project has run. The auditor is a
real instrument — it recovers ε > 0 with p < 0.05 against a deliberately leaky release, and a
test asserts that — but its **detection floor has never been measured**. Until it has, a
proved-versus-audited gap of "7.36 versus 0.00" is an instrument reading its own noise floor,
not a finding about differential privacy.

No claim about the ratio ε_audited / ε_proved appears anywhere in this repository, and none
should until M2.2 lands.

## How to read anything here

Every number traces to a committed experiment with a recorded seed, and carries an
uncertainty estimate. Where a result is uninformative, it says so rather than being omitted.
See [`../docs/AUDIT_AND_ROADMAP.md`](../docs/AUDIT_AND_ROADMAP.md) §7 for the standing rules
this follows.
