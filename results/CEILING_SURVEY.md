# Ceiling survey — how many published empirical-privacy claims could have been made?

> **K = 0 of 5. **No included paper was underpowered without saying so.** The honest conclusion is that this literature reports its own limits; the contribution reduces to the NOT-REPORTED count (1) and the artefact work. Declared acceptable in advance by protocol S10.**

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

- **K = 0 / 5** included papers (0.0%, 95% Wilson CI [0.0%, 43.4%])
- **NOT REPORTED: 1** — papers that state no audit configuration,
  so the reach of their instrument cannot be recomputed at all. A separate finding about
  reporting practice, never merged into K.
- **Excluded (undeterminable estimator): 8** —
  the ceiling series could not be read, so the row was excluded rather than guessed.
- **Underpowered but candid: 1** — these papers
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
  "NOT REPORTED": {
    "EXCLUDED": 3,
    "INTERPRETABLE": 0,
    "NOT REPORTED": 0,
    "SATURATED": 0,
    "UNDERPOWERED": 0
  },
  "gdp": {
    "EXCLUDED": 1,
    "INTERPRETABLE": 2,
    "NOT REPORTED": 0,
    "SATURATED": 0,
    "UNDERPOWERED": 0
  },
  "one_run": {
    "EXCLUDED": 0,
    "INTERPRETABLE": 1,
    "NOT REPORTED": 1,
    "SATURATED": 0,
    "UNDERPOWERED": 0
  },
  "other": {
    "EXCLUDED": 2,
    "INTERPRETABLE": 0,
    "NOT REPORTED": 0,
    "SATURATED": 0,
    "UNDERPOWERED": 0
  },
  "paired_cp": {
    "EXCLUDED": 2,
    "INTERPRETABLE": 0,
    "NOT REPORTED": 0,
    "SATURATED": 0,
    "UNDERPOWERED": 1
  }
}
```

## The table

| paper | config | estimator | budget | alpha | eps_emp | eps_proved | ceiling | class | ack? |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| SynthProof (this project) | H1 grid, canary audit, m=60 | one_run | 60 | 0.05 | 0 | 7.36 | 2.97209 | **UNDERPOWERED** | yes |
| SynthProof (this project) | GDP audit, independent mechanism, 2500 runs per world | gdp | 2500 | 0.05 | 0.4014 | 0.4547 | 5.94602 | **INTERPRETABLE** | yes |
| arXiv:2405.10994 | Black-box audit, PrivBayes (Hazy), worst-case dataset, theoretical eps=4.0 (headline) | paired_cp | 2000 | 0.05 | 3.23 | 4 | — | **EXCLUDED** | yes |
| arXiv:2405.10994 | Active white-box audit, DPWGAN (NIST), worst-case neighbouring dataset (small+repeat), theoretical eps=10.0 | paired_cp | 2000 | 0.05 | 8.31 | 10 | — | **EXCLUDED** | yes |
| arXiv:2405.10994 | Active white-box audit, same setting, theoretical eps=1.0 (strong-privacy end of the same sweep) | paired_cp | 2000 | 0.05 | 0.56 | 1 | — | **EXCLUDED** | yes |
| arXiv:2604.18352 | GDP audit of MST/AIM, restricted one-way-marginal configuration, (eps,delta)=(1,1e-2) (headline and only reported setting) | gdp | 10000 | 0.1 | 0.43 | 0.45 | 6.86408 | **INTERPRETABLE** | no |
| arXiv:2405.14106 | Black-box DP-SGD audit, worst-case initial parameters, MNIST 1,000-record sample, theoretical eps=10.0 (headline) | paired_cp | 200 | 0.05 | 7.21 | 10 | 3.98376 | **UNDERPOWERED** | yes |
| arXiv:2405.14106 | Black-box DP-SGD audit, CIFAR-10 1,000-record sample, theoretical eps=10.0 | paired_cp | 200 | 0.05 | 6.95 | 10 | 3.98376 | **UNDERPOWERED** | yes |
| arXiv:2405.14106 | Black-box DP-SGD audit, CIFAR-10 FULL dataset, theoretical eps=10.0 (loosest reported headline config) | paired_cp | 200 | 0.05 | 4.96 | 10 | 3.98376 | **UNDERPOWERED** | yes |
| arXiv:2504.06923 | NO DP AUDIT PERFORMED - membership inference measured as AUC only (PS1 privacy-leakage experiment) | NOT REPORTED | 200 | — | — | — | — | **EXCLUDED** | NOT REPORTED |
| arXiv:2305.08846 | White-box gradient-space canary attack on CIFAR-10 SoTA (De et al.) DP-SGD, theoretical eps=4 | one_run | 5000 | 0.05 | 1.8 | 4 | 7.4197 | **INTERPRETABLE** | yes |
| arXiv:2305.08846 | White-box gradient-space canary attack on CIFAR-10 SoTA DP-SGD, theoretical eps=8 | one_run | 5000 | 0.05 | 3.5 | 8 | 7.4197 | **UNDERPOWERED** | yes |
| arXiv:2302.07956 | White-box (adversary sees all intermediate models) gradient canary, CIFAR-10 WRN-16, f-DP lower bound with Clopper-Pearson, theoretical eps=8 | gdp | 2 | 0.05 | 5.8 | 8 | — | **EXCLUDED** | NOT REPORTED |
| arXiv:2302.07956 | White-box gradient canary, CIFAR-10 WRN-16, (eps,delta)-DP lower bound with Clopper-Pearson, theoretical eps=8 | paired_cp | 2 | 0.05 | 3.63 | 8 | — | **EXCLUDED** | NOT REPORTED |
| arXiv:2302.07956 | Black-box (last iterate only) canary, CIFAR-10 Wide ResNet, f-DP with Zanella-Beguelin Bayesian credible interval, theoretical eps=8 | other | 1000 | 0.05 | 1.6 | 8 | — | **EXCLUDED** | NOT REPORTED |
| arXiv:2503.07199 | Simulation study of one-run auditing of DP-SGD (dimension=1000, 10 epochs, 10 batches/epoch) at theoretical eps=2 | one_run | 5000 | — | — | 2 | — | **NOT REPORTED** | yes |
| arXiv:2507.04457 | UniAud, orthogonal canaries with self-comparison, 2-Layer ReLU, theoretical eps=8 | NOT REPORTED | 2000 | 0.05 | 3.059 | 8 | — | **EXCLUDED** | yes |
| arXiv:2507.04457 | UniAud, orthogonal canaries with self-comparison, 2-Layer ReLU, theoretical eps=1 | NOT REPORTED | 2000 | 0.05 | 1.089 | 1 | — | **EXCLUDED** | yes |
| arXiv:2507.04457 | UniAud, orthogonal canaries with self-comparison, 2-Layer ReLU, non-private reference (eps=infinity) -- the attack-capability ceiling | NOT REPORTED | 2000 | 0.05 | 6.449 | — | — | **EXCLUDED** | yes |
| arXiv:2011.07018 | Stadler et al. — DP synthetic data (PrivBayes, PATE-GAN) at eps=0.1, linkability/MIA privacy-gain evaluation | NOT REPORTED | 10 | — | — | 0.1 | — | **EXCLUDED** | no |
| arXiv:2411.16516 | Curator Attack — DP-Sniper as the audited blackbox auditor | other | 1.07e+07 | 0.05 | — | — | — | **EXCLUDED** | yes |
| arXiv:2411.16516 | Curator Attack — MPL (Askin et al.) as the audited blackbox auditor | other | 3e+06 | 0.05 | — | — | — | **EXCLUDED** | yes |
| arXiv:2411.16516 | Curator Attack — DPSGD-Audit as the audited blackbox auditor | other | 10000 | 0.03 | — | — | — | **EXCLUDED** | yes |
| arXiv:2411.10614 | To Shuffle or not to Shuffle — BGM audit of SOTA published settings (headline, Table 1, MNLI row) | paired_cp | 1e+07 | 0.05 | 12.73 | 3 | — | **EXCLUDED** | yes |
| arXiv:2411.10614 | To Shuffle or not to Shuffle — BGM convergence study, largest-budget configuration (Section 4.2.1) | paired_cp | 1e+09 | 0.05 | — | — | — | **EXCLUDED** | yes |
| arXiv:2411.10614 | To Shuffle or not to Shuffle — end-to-end DP-SGD (Shuffle) audit of real models, batch-size study (Section 6.2.2) | paired_cp | 1e+06 | 0.05 | — | — | — | **EXCLUDED** | yes |
| arXiv:2606.16952 | Phantoms and Disclosures — rewrites mechanism, user-match derived eps (headline, Table 3) | other | — | 0.05 | 5.28 | — | — | **EXCLUDED** | no |
| arXiv:2606.16952 | Phantoms and Disclosures — SFT (non-private fine-tuning) baseline, user-match derived eps (Table 7) | other | 100000 | 0.05 | 3.24 | — | — | **EXCLUDED** | no |
| arXiv:2606.16952 | Phantoms and Disclosures — DP-SGD at theoretical eps=10 (the audit that returns nothing) | other | 100000 | 0.05 | — | 10 | — | **EXCLUDED** | no |


## The objection this must survive

**"Post-hoc power is uninformative."** Correct, and standard — observed power is a
one-to-one function of the p-value. **This is not observed power.**
`eps_max(r) ~= log(r / ln(1/alpha))` depends only on the design parameters *r* and
*alpha*, never on the observed outcome. It is a minimum-detectable-effect bound,
computable before any data is seen.

---

### Measurement convention — the ceiling is borrowed, and attributed

The audit ceiling reported beside every ε_audited is `log(r / ln(1/α))`, a one-line corollary
of Steinke, Nasr & Jagielski (NeurIPS 2023, arXiv:2305.08846) Thm 2.1 — **not a result of
ours** — and the same quantity is already named *maximum auditable epsilon* by Annamalai,
Ganev & De Cristofaro (USENIX Sec 2024, arXiv:2405.10994) §2.2.

Reporting it alongside the measurement is a transfer of **limit-of-detection (LoD) reporting**
from analytical chemistry, where **MIQE 2.0** (Bustin et al., *Clinical Chemistry*
2025;71(6):634–651) mandates LoD/LLOQ disclosure and a laboratory reports *"Not Detected,
< LOD"* rather than zero. The transfer is the claim; the convention is not our invention.

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](docs/MEASUREMENT_CONVENTIONS.md).
