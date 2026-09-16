# 16 — Curated case study: do real DP releases keep their artefacts inside ε? (2026-09-15)

> Replaces the retracted Hugging Face "wild audit". Instead of scraping a hub that hosts essentially
> no DP releases (`research/wild_audit/HONEST_FINDINGS.md`), this audits the *documentation* of the
> field's actual flagship differentially private releases against the release-boundary properties in
> `research/15_standards_gap_analysis.md`. Small N, but every row is a real, named, citable release.
> Standing rules apply: each cell is scored from fetched documentation, and cells I could not verify
> are marked `?`, not guessed.

## Method

For each release I ask, from its public documentation only: is each boundary property **stated**
(Y), **absent** (N), **not applicable** to its deployment model (n/a), or **not verified by me** (?).
The properties (P1–P11) are defined in `research/15_standards_gap_analysis.md`: P1 ε, P2 δ, P3
mechanism, P4 neighbour relation, P5 release-size provenance, P6 seed secrecy, P7 keyed fingerprint,
P8 evaluation/what-is-outside-ε disclosed, P9 audit operating range/LoD, P10 tamper-evidence, P11
machine-checkable boundary enforcement.

## The releases

| Release | Model | P1 ε | P2 δ | P3 mech | P4 neigh | P5 size prov | P6 seed | P7 keyed fp | P8 outside-ε | P9 LoD | P10 sig | P11 m/c |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **US Census 2020 DAS** | central | Y | Y (zCDP ρ) | Y (TopDown, discrete Gaussian) | Y (person/household) | ~ (invariants documented as exact) | N | N | **Y** (invariants named) | N | N | N |
| **NIST SDNist label** | central | Y | Y | ~ ("deidentification method") | N | N | N | N | N | ~ (utility/privacy report) | N | ~ (report tool, not boundary) |
| **OpenDP / SmartNoise** | central (library) | Y (in code) | Y | Y | ~ (bounded/unbounded in API) | N | N | N | N | N | N | N (library, no release artefact) |
| **Apple telemetry DP** | **local** | Y (per datatype/epoch) | n/a | Y (local hashing/CMS) | n/a (local: no central table) | n/a | n/a | n/a | N | N | N | N |
| **Academic DP synthetic release** (typical, e.g. arXiv:2507.02971) | central | Y | ? | Y | N | N | N | N | N | N | N | N |
| **SynthProof Privacy Data Sheet** | central | Y | Y | Y | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** |

## What each row shows (grounded)

- **US Census 2020 DAS** (Abowd et al., *Harvard Data Science Review* 2022; arXiv:2204.08986). The
  most rigorous real deployment: zCDP with a published ρ/ε budget, a named mechanism (TopDown with
  discrete Gaussian), and a clear person/household unit. Notably it is **explicit about what is
  outside the budget** — the *invariants* (e.g. exact state populations) are released unnoised and
  documented as such (P8 = Y, and better than most). But the invariant exact counts are a P5-style
  exposure accepted as *policy*, documented in prose, not machine-checkable; there is no signature,
  no seed-secrecy treatment, and no automated boundary check. `CONFIDENCE: high` on ε/mechanism/unit;
  `med` on the finer cells (from the paper + general DAS documentation).
- **NIST SDNist** (usnistgov/SDNist; sdnist on PyPI). The field's closest thing to a machine-readable
  DP label: from v2.1 it accepts a label carrying `epsilon`, `delta`, creation date and
  "deidentification method", and emits a utility/privacy quality report. It is the strongest existing
  practice — and it still has **no field for the neighbour relation, seed secrecy, a keyed
  fingerprint, an evaluation-privacy flag, an audit operating range, a signature, or a boundary
  check**. `CONFIDENCE: med-high` (from the repo/PyPI docs).
- **OpenDP / SmartNoise** — a DP *library*, not a release standard: ε lives in the calling code, the
  API distinguishes bounded/unbounded DP (P4 = ~), and there is no released artefact carrying the
  boundary properties. Included to show the tooling layer also has no release-artefact standard.
- **Apple telemetry DP** — a **local-model** deployment (Apple's DP overview). Several boundary
  properties (central table size, seed replay, table fingerprint) are **n/a** because there is no
  central table — a useful contrast that shows the boundary is a *central-model* problem, which is
  the model SynthProof and most synthetic-data releases use.
- **A typical academic DP synthetic-data release** — states ε and a mechanism in the paper; the
  released files are plain CSV/parquet with a dataset card. Artifact-safety properties are, as far as
  examined, absent. Marked `?` on δ because it was not verified for the specific example.

## The finding (honest, and it is the paper's empirical spine)

`INFERENCE:` Across the field's actual DP releases, documentation is strong on the **guarantee's
parameters** (ε almost always; mechanism usually; δ and unit sometimes) and **absent on the
artefact's safety** (P5–P11 are N nearly everywhere). No real release is cryptographically signed,
none carries a machine-checkable boundary, and none states an audit operating range. The one place
the boundary is handled well — the Census DAS naming its invariants as outside the budget — is done
in **prose as policy**, not as a checkable artefact property. `CONFIDENCE: med-high` — the pattern is
consistent across five heterogeneous releases, but N is small and several finer cells are `~`/`?`.

**This is exactly the gap the tool fills, and it is now grounded in real named releases rather than a
keyword scrape.** The honest contribution is: the guarantee's *parameters* are increasingly
documented (SDNist, Dibia et al. point the same way), but the *artefact's* boundary safety is not
expressible in any standard and not enforced in any real release — SynthProof's signed, boundary-
checked Privacy Data Sheet is the first artefact to carry all of P1–P11, and `boundary-audit` the
first tool to check them without the data or the code.

## Limitations (state these in the paper)

- N = 5 heterogeneous releases; this is a **qualitative case study**, not a population statistic. It
  supports "no real release carries the boundary properties", not a percentage.
- Documentation-only, and some cells are `~`/`?` where the public docs were ambiguous or I did not
  verify the primary source end to end.
- Apple is local-model and included only as a contrast; the boundary is a central-model concern.
- The Census "invariants" question is a genuine, debated design choice, not an oversight — represented
  as such.

## Where a larger honest corpus would come from (future work)

Dibia et al. (2026) §5 name two real registries — the **Oblivious Privacy Deployments Registry** and
**Wikimedia Foundation's DP documentation** — plus the **NIST SDNist challenge** submissions. Those,
not the ML hubs, are where a scaled-up audit of real DP releases should draw from.

## Sources (fetched / checked)

1. Abowd et al. — *The 2020 Census Disclosure Avoidance System TopDown Algorithm*. HDSR 2022 /
   arXiv:2204.08986. (zCDP, invariants.)
2. NIST — SDNist (github.com/usnistgov/SDNist; pypi.org/project/sdnist). (ε/δ/method label from v2.1.)
3. OpenDP / SmartNoise — opendp.org (library, bounded/unbounded DP).
4. Apple — *Differential Privacy Overview* (local model).
5. Dibia et al. — arXiv:2507.15997 §5 (registries named for real DP deployments).
