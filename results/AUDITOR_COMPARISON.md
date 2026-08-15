# Auditor comparison — paired Clopper-Pearson vs one-run (Steinke et al. 2023)

> UCI Adult, n = 3,000, 3 seeds, α = 0.05, leakage supplied by `LeakyGenerator`.
> Reproduce with `make audit-compare`.

Both auditors are given the **same total canary budget**, which is the comparison a
practitioner faces. The paired auditor spends two canaries per comparison (one planted, one
held out); the one-run construction includes each canary independently at random and uses all
of them.

## Measured

| canary budget | leak | paired ε | one-run ε | one-run ceiling |
|---:|---:|---:|---:|---:|
| 60 | 1.00 | 2.034 | **2.168** | 2.972 |
| 60 | 0.25 | 0.000 | **0.168** | 2.972 |
| 60 | 0.00 | 0.000 | 0.000 | 2.972 |
| 120 | 1.00 | **2.758** | 2.748 | 3.678 |
| 120 | 0.25 | 0.000 | 0.000 | 3.678 |
| 120 | 0.00 | 0.000 | 0.000 | 3.678 |
| 400 | 1.00 | 3.984 | **4.090** | 4.891 |
| 400 | 0.25 | 0.018 | **0.162** | 4.891 |
| 400 | 0.00 | 0.000 | 0.000 | 4.891 |

## What this actually shows

**The improvement is real but modest, and smaller than the literature might lead you to
expect at this scale.** On a verbatim release the two are within a few percent of each other,
and at budget 120 the paired auditor is fractionally ahead — well inside seed noise.

**The one-run construction's genuine advantage is sensitivity to partial leakage.** At 25%
verbatim copying it certifies ε ≈ 0.17 where the paired auditor certifies nothing at both 60
and 400 canaries. That is the regime a real mechanism lives in, so it is the regime that
matters — but 0.17 is still a very weak bound.

**Both correctly report zero on the negative control** (a release with perfect marginals and
no real records), which is what makes the rest of the table trustworthy.

## The limit is information-theoretic, not an implementation detail

With a perfect adversary the one-run bound solves `p^r = α`, so

```
ε_max(r) = log(a / (1 − a)),   a = α^(1/r)     ≈  log(r / ln(1/α))
```

Certifying a given ε therefore needs about **ln(1/α) · e^ε** canaries — exponential in ε:

| ε to certify | canaries needed (perfect adversary) |
|---:|---:|
| 1.0 | 10 |
| 2.0 | 24 |
| 4.0 | 166 |
| **7.36** | **4,711** |
| 8.0 | 8,932 |

The proved ε in the H1 experiments is **7.36**. Certifying it by canary auditing would require
roughly 4,700 canaries *every one of which the adversary identifies correctly* — with a real
adversary, far more.

> **No canary audit at any scale this project can run will certify an ε near its proved
> bound.** Switching to the one-run construction does not change that, and neither would a
> better adversary. It is a property of what auditing can prove, not of this implementation.

## Consequence, and what it means for the thesis

The proved-versus-audited gap **cannot be closed by measurement** at these epsilon values.
That reframes the project's central question, and the reframing is the contribution:

- Reporting "ε_proved = 7.36, ε_audited = 0" as a *finding about a mechanism* is wrong.
- Reporting it as "the formal bound is 7.36; no adversary we ran recovered more than the
  instrument's floor, and that instrument could not have certified more than 2.97 at this
  canary count regardless" is correct, and useful.
- The practitioner-facing conclusion is that **auditing is a tool for catching broken
  implementations, not for confirming tight ones.** It found a verbatim release at m=10. It
  will never confirm that ε=7.36 is tight.

That is a defensible, reportable result, and it is more honest than a confident null.

## Threats to validity

- **One adversary.** Both auditors use the same nearest-neighbour similarity score. A stronger,
  mechanism-aware adversary would raise both columns; the ordering might change.
- **3 seeds.** Differences under ~0.2 in this table are inside noise.
- **`LeakyGenerator` is coarse.** Verbatim copying is the easiest leak to detect; real
  mechanisms leak in subtler ways.
- **δ is handled by a union bound**, not the paper's tighter treatment. At δ = 1e-5 the
  correction is negligible, but it is conservative rather than exact.
