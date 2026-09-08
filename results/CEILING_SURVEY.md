# Ceiling survey — how many published empirical-privacy claims could have been made?

> **K = 0 of 1. **No included paper was underpowered without saying so.** The honest conclusion is that this literature reports its own limits; the contribution reduces to the NOT-REPORTED count (0) and the artefact work. Declared acceptable in advance by protocol S10.**

> Protocol: [`docs/CEILING_SURVEY_PROTOCOL.md`](../docs/CEILING_SURVEY_PROTOCOL.md),
> frozen and committed before any paper was read. Raw output:
> [`ceiling_survey.json`](ceiling_survey.json). Regenerate:
> `python -m scripts.run_ceiling_survey`.

**This is not our mathematics.** The ceiling is a corollary of Steinke, Nasr & Jagielski
(2023) Thm 2.1; Keinan, Shenfeld & Ligett ([arXiv:2503.07199](https://arxiv.org/abs/2503.07199))
Thm 5.2 formalise the one-run case; and the concept is already named **"maximum auditable
epsilon"** by Annamalai, Ganev & De Cristofaro ([arXiv:2405.10994](https://arxiv.org/abs/2405.10994))
§2.2, who compute it **for their own configuration only**. Applying it per-paper across the
literature is what is new here.

## Headline

- **K = 0 / 1** included papers (0.0%, 95% Wilson CI [0.0%, 79.3%])
- **NOT REPORTED: 0** — papers that state no audit configuration,
  so the reach of their instrument cannot be recomputed at all. A separate finding about
  reporting practice, never merged into K.
- **Excluded (undeterminable estimator): 0** —
  the ceiling series could not be read, so the row was excluded rather than guessed.
- **Underpowered but candid: 0** — these papers
  disclosed their own limit. Restatements, not findings; excluded from K by construction.

## Sensitivity — alpha sweep (protocol §9.1)

| alpha | K |
|---|---:|
| 0.01 | 0 |
| 0.05 | 0 |
| 0.1 | 0 |

K must not depend on our choice of alpha. If it does, say so here and treat the result
as alpha-dependent rather than as a property of the literature.

## Per-estimator split (protocol §9.2)

A K driven entirely by one estimator family is a finding about that family, not the field.

```json
{
  "gdp": {
    "EXCLUDED": 0,
    "INTERPRETABLE": 1,
    "NOT REPORTED": 0,
    "SATURATED": 0,
    "UNDERPOWERED": 0
  }
}
```

## The table

| paper | config | estimator | budget | alpha | eps_emp | eps_proved | ceiling | class | ack? |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| SynthProof (this project) | H1 grid, canary audit, m=60 | one_run | 60 | 0.05 | 0 | 7.36 | 2.97209 | **UNDERPOWERED** | yes |
| SynthProof (this project) | GDP audit, independent mechanism, 2500 runs per world | gdp | 2500 | 0.05 | 0.4014 | 0.4547 | 5.94602 | **INTERPRETABLE** | yes |


## The objection this must survive

**"Post-hoc power is uninformative."** Correct, and standard — observed power is a
one-to-one function of the p-value. **This is not observed power.**
`eps_max(r) ~= log(r / ln(1/alpha))` depends only on the design parameters *r* and
*alpha*, never on the observed outcome. It is a minimum-detectable-effect bound,
computable before any data is seen.
