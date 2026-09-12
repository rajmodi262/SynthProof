# A second adversary, and where it actually helps

**Task 4.1.** The roadmap called a stronger adversary *"the one open item that could change a
published number"*, because both auditors in this project score a record by its similarity to
the nearest synthetic row. That is algorithm-agnostic, and it means every ε_audited ever
reported here is a lower bound produced by **one** attack. A weak attack makes a weak bound
look like a strong guarantee.

So a second adversary was built and run against the same releases.

Run: `python -m scripts.run_adversary_comparison` → [`adversary_comparison.json`](adversary_comparison.json)
Protocol: n = 2,000, 150 members vs 150 non-members, **5 seeds per cell**, AUC = P(a member
outranks a non-member). 0.5 is a coin flip. 116 s.

---

## The result

| Mechanism | ε | **algorithm-aware** | distance (current) | Δ | focal points |
|---|---:|---|---|---:|---:|
| `independent` | 1 | 0.527 ± 0.039 | 0.538 ± 0.025 | **−0.011** | 4 |
| `independent` | 4 | 0.529 ± 0.041 | 0.534 ± 0.039 | **−0.005** | 4 |
| `independent` | 8 | 0.531 ± 0.041 | 0.535 ± 0.043 | **−0.004** | 4 |
| `pairwise` | 1 | 0.555 ± 0.039 | 0.516 ± 0.036 | +0.039 | 4 |
| `pairwise` | 4 | 0.587 ± 0.051 | 0.530 ± 0.036 | +0.057 | 4 |
| `pairwise` | 8 | 0.589 ± 0.032 | 0.532 ± 0.033 | +0.058 | 4 |
| `aim` | 1 | 0.576 ± 0.054 | 0.538 ± 0.039 | +0.038 | 10 |
| `aim` | 4 | 0.587 ± 0.048 | 0.500 ± 0.037 | +0.086 | 10 |
| `aim` | 8 | 0.590 ± 0.041 | 0.498 ± 0.036 | +0.092 | 10 |
| `fixed_workload` | 1 | 0.573 ± 0.049 | 0.515 ± 0.027 | +0.058 | 10 |
| `fixed_workload` | 4 | 0.608 ± 0.052 | 0.516 ± 0.026 | +0.091 | 10 |
| `fixed_workload` | 8 | 0.587 ± 0.039 | 0.512 ± 0.017 | +0.075 | 10 |

**Three things, and the second is the one that constrains what we may claim.**

### 1. The current adversary is at chance on every structured mechanism

Across all twelve cells the distance baseline reads **0.498–0.538**. On `aim` at ε = 4 and 8 it
is 0.500 and 0.498 — indistinguishable from guessing. A nearest-neighbour attack asks *"does
this record look like the output?"*, and a marginals-based generator never emits anything that
looks like a particular record. It emits samples from a fitted model.

This is the finding that matters for everything else in the repository: **the instrument behind
every ε_audited in this project is, on these mechanisms, approximately blind.**

### 2. The algorithm-aware attack does NOT help on `independent` — and that is the control working

On `independent` the delta is **negative at every epsilon** (−0.011, −0.005, −0.004). That is not
a failure; it is the prediction. `independent` measures one-way marginals and nothing else, so
"the marginals the algorithm selected" are just the per-column histograms, and there is no
multi-way structure for an algorithm-aware attack to exploit. It has no advantage because there
is no algorithm-specific structure to be aware of.

Any claim that the new attack is *uniformly* stronger would be refuted by this row. It is
stronger **where the generator measures multi-way structure**, which is exactly the scope
Golob et al. claim for it.

### 3. Where it does help, the advantage grows with the budget

`aim` goes +0.038 → +0.086 → +0.092 as ε goes 1 → 4 → 8; `pairwise` goes +0.039 → +0.057 →
+0.058. More budget means less noise on the measured marginals, which means more membership
signal in exactly the statistics this attack reads. The direction is the one theory predicts,
which is a useful sanity check on the implementation.

---

## What this does NOT establish

**It does not raise any published ε_audited.** No number in `results/` changes on the strength of
this document. An AUC of 0.59 is better than chance and better than the baseline, but it is a
weak attack in absolute terms, and converting it into an epsilon lower bound requires running it
*inside* the audit construction with its Clopper–Pearson intervals — which is the next task, not
this one. Until that is run, the honest statement is: *the existing bounds were produced by an
adversary that these experiments show to be near-blind on structured mechanisms, and a better
one exists.*

**And a better adversary cannot lift the audit ceiling.** This is the part that keeps the result
in proportion. The ceiling — `log(r / ln(1/α))`, a corollary of Steinke et al. Thm 2.1, and the
same quantity Annamalai, Ganev & De Cristofaro call the *maximum auditable epsilon* — depends on
the **canary count alone**. It is information-theoretic: at m = 60 it is ≈ 2.97 against a proved
ε of 7.36, and no adversary, however strong, can certify past it. A better attack can move
ε_audited **up to** the ceiling; it cannot move the ceiling. So the disqualification of the
proved-vs-audited comparison recorded in `H1_RESULTS.md` stands exactly as it did, and this work
does not rehabilitate it. What it changes is the *other* half of the sentence: that gap can no
longer be attributed even partly to the instrument's adversary being weak, because a stronger
one now exists and is measured. See [`docs/MEASUREMENT_CONVENTIONS.md`](../docs/MEASUREMENT_CONVENTIONS.md).

**It is not evidence about real data.** The table is a controlled synthetic population with known
pairwise dependence, chosen so the attacks can be compared against each other with the structure
held fixed. The committed H1 grid is where UCI Adult and ACSIncome belong.

**It is not MAMA-MIA.** The score is theirs; the threat model is not. See below.

---

## Attribution, and one deliberate deviation

The score is ζ from **Golob, Pentyala, Maratkhan & De Cock, "Privacy Vulnerabilities in
Marginals-based Synthetic Data", IEEE SaTML 2025** ([arXiv:2410.05506](https://arxiv.org/abs/2410.05506)):

> ζ(t) = Σ_{F ∈ ℱ} w_F · P̂_synth(F(t)) / P̂_aux(F(t))

where ℱ are the *focal points* — the marginals the generator actually measured. The authors
describe it as incorporating "the normalization idea from DOMIAS, but ... tailored to which
marginals-based algorithm was used".

**The implementation here is deliberately not called MAMA-MIA**, and the class is
`MarginalRatioScorer`. This project has shipped a misnamed attack once already — an earlier
`distance_mia` carried the label "LiRA" that it had not earned, together with a fabricated
AUC — and the rule from that incident (audit finding F7) is that **a name is a claim**. Two differences:

- **Oracle focal points.** MAMA-MIA recovers ℱ by shadow-modelling the generator "up to the
  statistics selection step" on ~50 subsets of auxiliary data, because a real attacker cannot
  see which marginals were chosen. An **auditor can** — our generators record them. We read the
  true set. That makes this adversary *stronger* than the paper's, which is the right choice for
  an audit, and it makes every number here an **upper bound on what MAMA-MIA proper would
  achieve** against the same release.
- **No shadow weights where selection is public.** For `pairwise`, `fixed_workload`, `independent`
  and `moments` the workload is fixed and data-independent, so w_F is uniform by construction.
  Only `aim` selects adaptively, and there the weights follow selection order.

---

## A finding from building it, kept because it was a surprise

On a release containing **verbatim copies** of training rows, the distance baseline *wins*, and
by a wide margin — AUC ≈ 0.86 against ≈ 0.67 at a 50% leak. A copied record sits at distance
zero and nothing else does, so nearest-neighbour is close to an optimal detector there, while a
single extra row barely moves a marginal over hundreds.

The two adversaries detect **different failure modes**, which is why both are reported rather
than one replacing the other. It also explains why the detection-floor study — which uses
verbatim copying as its leak model — was right to use the distance auditor: that study measures
the instrument against the leak it is good at. Pinned by
`test_the_distance_baseline_WINS_on_verbatim_copying`.

---

## Method note

The first version of the claim test read AUC 0.530 against 0.552 at a single configuration and
would have concluded the attack was useless. A sweep over n and ε showed the algorithm-aware
score winning at every setting with the baseline pinned at chance. **One noisy draw is not a
result** — the preregistration commits to five seeds per cell for this reason, and the test now
averages over five.

---

### Measurement convention — the ceiling is borrowed, and attributed

The audit ceiling referenced above is `log(r / ln(1/α))`, a one-line corollary of Steinke, Nasr
& Jagielski (NeurIPS 2023, arXiv:2305.08846) Thm 2.1 — **not a result of ours** — and the same
quantity is already named *maximum auditable epsilon* by Annamalai, Ganev & De Cristofaro
(USENIX Sec 2024, arXiv:2405.10994) §2.2.

Reporting it alongside the measurement is a transfer of **limit-of-detection (LoD) reporting**
from analytical chemistry, where **MIQE 2.0** (Bustin et al., *Clinical Chemistry*
2025;71(6):634–651) mandates LoD/LLOQ disclosure and a laboratory reports *"Not Detected,
< LOD"* rather than zero. The transfer is the claim; the convention is not our invention.

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](../docs/MEASUREMENT_CONVENTIONS.md).
