# H1 confirmatory run — AIM vs pairwise on structure (W10)

<!-- provenance: results/h1_confirmatory/analysis.json, results/h1_confirmatory/adult.json -->

> **Run 2026-10-16.** Plan: [`docs/prereg/W10_h1_confirmatory.md`](../docs/prereg/W10_h1_confirmatory.md),
> committed before the run, with amendment A1
> ([`W10_h1_confirmatory.amendments.md`](../docs/prereg/W10_h1_confirmatory.amendments.md)), which cut
> the design to adult at epsilon 8 for runtime **before any confirmatory result was read**. Seeds
> 100–114, disjoint from the pilot's 0–4. Raw: [`h1_confirmatory/`](h1_confirmatory/) · analysis:
> `python -m scripts.analyse_h1_confirmatory`.

<!-- BEGIN GENERATED: h1-confirmatory-table -->
| Dataset | eps | mechanism | seeds | correlation error, mean [95% CI] | SD |
|---|---:|---|---:|---|---:|
| adult | 8 | `aim` | 15 | 0.0137 [0.0083, 0.0190] | 0.0097 |
| adult | 8 | `pairwise` | 15 | 0.0241 [0.0176, 0.0306] | 0.0117 |
| adult | 8 | `independent` | 15 | 0.1078 [0.0957, 0.1200] | 0.0219 |

**adult, eps 8: AIM lower** -- AIM minus pairwise -0.0104, Welch p = 0.0132 (Holm-adjusted 0.0132); TOST p = 0.9104 at margin +/-0.005; minimum detectable difference at 80% power 0.0114.

*Generated from `results/h1_confirmatory/analysis.json`. Preregistration SHA-256 abdbb9e51cc9..., amendments f6970495c543...*
<!-- END GENERATED: h1-confirmatory-table -->

## Reading

- The 5-seed pilot (`results/H1_RESULTS.md`) could not separate AIM from pairwise at epsilon 8 on
  Adult. With 15 fresh seeds, the preregistered test separates them in AIM's favour; equivalence
  within the margin is not supported.
- The observed difference is close to the minimum detectable difference at this sample size, so the
  run had little room to spare. It is one dataset and one epsilon: acs, bank, diabetes and epsilon 1
  were not run (amendment A1, with the measured cost), and nothing here generalises to them.
- `independent`, which measures no two-way structure, is far behind both, as in the pilot.
- The two epsilon-1 cells finished before the amendment are kept unread in
  `h1_confirmatory/_discarded_before_amendment/`.
