# Real DP releases through the boundary auditor (W11)

<!-- provenance: results/real_release_study.json, research/real_releases/releases.json -->

> **Run 2026-10-16.** Corpus: [`research/real_releases/releases.json`](../research/real_releases/releases.json)
> (six releases, every coded cell citing a source fetched that day, with a short quote) ·
> Runner: `python -m scripts.run_real_release_study` (refuses a cell marked documented without a
> source and evidence) · Output: [`real_release_study.json`](real_release_study.json).

## What was done

Each release's own primary documentation (the producer's paper, technical report or repository
README) was read and coded against the eleven boundary properties P1–P11 that the Privacy Data
Sheet is designed to carry. The documented values were then written in Privacy Data Sheet field
names and run through `synthproof.audit.boundary.audit_sheet`, the same checker that audits
SynthProof's own releases. A property is coded **N** when the fetched sources do not address
it; that is a statement about those sources, not proof that the producer documents it nowhere.

## Coverage of the eleven properties

<!-- BEGIN GENERATED: real-release-coverage -->
| Release | type | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Israel National Registry of Live Births, 2014 (singleton births) | synthetic microdata | Y | Y | Y | Y | Y | Y | – | Y | – | N | N |
| 2020 US Census Redistricting Data (P.L. 94-171), TopDown Algorithm | statistics (and microdata detail file) | Y | ~ | Y | Y | Y | Y | – | N | – | N | N |
| 2020 US Census Detailed DHC-A, SafeTab-P | statistics | Y | N | Y | Y | Y | N | – | N | – | N | N |
| Google COVID-19 Community Mobility Reports | statistics | Y | Y | Y | Y | Y | N | – | Y | – | N | N |
| Microsoft US Broadband Usage Percentages (zip-code level) | statistics | N | N | ~ | N | N | N | – | N | – | N | N |
| Wikimedia differentially private pageviews (Feb 2023 onward) | statistics | Y | ~ | Y | Y | Y | N | – | Y | – | N | N |
| **documented / applicable** | | 5/6 | 2/6 | 5/6 | 5/6 | 5/6 | 2/6 | n/a | 3/6 | n/a | 0/6 | 0/6 |

*Y documented · ~ partial · N not found in the fetched sources · – not applicable. Generated from `results/real_release_study.json`.*
<!-- END GENERATED: real-release-coverage -->

P1 privacy parameter · P2 delta · P3 mechanism · P4 unit of privacy · P5 basis of any exact size
· P6 randomness withheld · P7 keyed fingerprint · P8 measurements on confidential data labelled
or charged · P9 operating range of an empirical privacy metric · P10 signed artefact ·
P11 machine-checkable claim.

P9 transfers limit-of-detection reporting from analytical chemistry (MIQE 2.0, Bustin et al.,
*Clinical Chemistry* 2025;71(6):634–651), where a non-detect is reported as "< LoD" with the limit
beside it. The ceiling it asks for is a corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1, and
the quantity is already named "maximum auditable epsilon" by Annamalai, Ganev & De Cristofaro
(arXiv:2405.10994) §2.2; neither is this project's invention.

## What the auditor reports on the documented values

<!-- BEGIN GENERATED: real-release-audit -->
| Release | leaks | unverifiable | findings |
|---|---:|---:|---|
| Israel National Registry of Live Births, 2014 (singleton births) | 0 | 2 | RB2 unverifiable, RB5 unverifiable, RB1 note, RB8 note |
| 2020 US Census Redistricting Data (P.L. 94-171), TopDown Algorithm | 0 | 2 | RB5 unverifiable, RB6 unverifiable, RB1 note, RB8 note |
| 2020 US Census Detailed DHC-A, SafeTab-P | 0 | 4 | RB1 unverifiable, RB5 unverifiable, RB6 unverifiable, RB8 unverifiable |
| Google COVID-19 Community Mobility Reports | 0 | 2 | RB1 unverifiable, RB5 unverifiable |
| Microsoft US Broadband Usage Percentages (zip-code level) | 1 | 3 | RB4 leak, RB1 unverifiable, RB5 unverifiable, RB6 unverifiable |
| Wikimedia differentially private pageviews (Feb 2023 onward) | 0 | 3 | RB1 unverifiable, RB5 unverifiable, RB7 unverifiable |

*Generated from `results/real_release_study.json`.*
<!-- END GENERATED: real-release-audit -->

## Reading

- **The guarantee is documented; the artefact is not checkable.** Five of six state their privacy
  parameter, mechanism and unit of privacy. None ships a signed artefact (P10) or a privacy claim a
  program can check from the artefact itself (P11). No release publishes an empirical privacy
  metric or a fingerprint, so P7 and P9 do not arise.
- **RB5 is unverifiable everywhere.** No artefact publishes its noisy steps in a form that lets a
  reader recompose the epsilon with an independent accountant; every reader must take the stated
  parameter on trust (Census publishes its code, which is a route for an expert, not a check an
  artefact supports).
- **The one leak** is Microsoft's: error metrics computed against the non-private estimate are
  published in the README with no statement that the privacy guarantee does not cover them (RB4).
- **Seed handling is stated by two of six** (the Israel births release and the 2020 redistricting
  data); for the other four the auditor reports RB1 as unverifiable rather than assuming it.
- **Invariants:** both Census products and the Israel release publish exact totals by policy. The
  redistricting paper and the Israel paper give the basis; for the Detailed DHC-A the fetched
  sources state that the exact US total is released but not why, so RB8 is unverifiable there.

## Limits

- Six releases, coded by one coder from the sources listed in the corpus. A second coder and a
  larger corpus (the twelve registry deployments in `research/21`, Hugging Face releases that state
  an epsilon) would strengthen it; the runner and the corpus format take more records unchanged.
- Five of the six are statistics, not synthetic tables; several properties were designed with
  synthetic-data releases in mind. The one synthetic release (Israel births) is the
  best-documented release in the corpus and still has neither P10 nor P11.
- This is a documentation audit through a checker. It finds what the artefacts let a reader verify,
  not whether the underlying mechanisms are correctly implemented.
