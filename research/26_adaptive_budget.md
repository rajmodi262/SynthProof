# 26 — AIM adaptive budget (annealing): a modest, honest utility gain

> Opt-in `AIMGenerator(adaptive_budget=True)`. Default stays `False`, so **every committed H1
> number is unaffected** (the fixed split is byte-identical). This is a **fidelity gain, not a
> novelty claim** — it implements the budget annealing AIM's own paper uses (McKenna et al. 2022
> §4), which our code previously skipped for accounting simplicity.

## What changed

The fixed path spends one calibrated σ across all measurements. The adaptive path halves a round's
σ (spends more) after a round whose measurement was **noise-dominated** — when the signal it tried
to capture (the model's pre-measurement error on that marginal) is below the expected L1 of the
noise just added (`size · σ · sqrt(2/π)`). This concentrates the *same* fixed budget into the
informative marginals. Safety: every spend is `dry_run`-gated against the accountant before it is
charged, and the RDP accountant is the hard cap — annealing can never exceed the budget.

## Measured gain (correlation error, lower = better)

Synthetic 4-column table (a→b→c strongly correlated, d independent), n=4000, mean absolute error of
the three pairwise correlations vs the real data, averaged over 3 seeds:

| ε | fixed split | adaptive | spent ≤ cap? |
|---|---|---|---|
| 0.5 | 0.2865 | **0.2795** | yes (0.411 ≤ 0.510) |
| 1.0 | 0.1673 | **0.1558** | yes (0.828 ≤ 1.020) |
| 2.0 | 0.1106 | **0.1091** | yes (1.913 ≤ 2.040) |

Adaptive is better at every ε, by a small margin. Honest reading: this is a **modest** improvement,
largest in the mid-ε regime where concentrating budget helps most; at high ε both paths already have
enough budget, so the gap shrinks.

## Honest limits

- **Modest, and dataset-dependent.** On a table where every pair matters equally (or none do), the
  gain is near zero — annealing only helps when budget is better spent unevenly.
- **Not run on the committed H1 grids.** Those use the fixed split and stay as published. A separate
  `--mechanisms aim` grid with `adaptive_budget=True` could be run to add an "AIM-adaptive" row, but
  that is a deliberate compute run, not done here.
- **Not novel.** AIM as published anneals; our fixed split was the simplification. This restores
  fidelity to the paper, nothing more. Do not present it as a contribution.

## One line

*Implementing AIM's own budget annealing (opt-in) gives a small but consistent correlation-fidelity
gain over our previous fixed split, at the same ε and with the budget provably respected — a
faithfulness fix, not a novelty claim.*
