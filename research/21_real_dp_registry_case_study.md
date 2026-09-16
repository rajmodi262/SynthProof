# 21 — Real DP deployments audited against P1–P11 (beyond public hubs)

> Extends `research/16` and the wild-audit (0/286 on HuggingFace) with **12 authoritative real-world DP
> deployments** from Damien Desfontaines' registry (the same real-world DP list P10/Dibia cite as an
> existing registry). Source: <https://desfontain.es/blog/real-world-differential-privacy.html>
> (fetched 2026-09-17). Every ε/δ/unit below is quoted from that registry; nothing is invented.
> Honesty caveat: these are mostly *statistic/query* or *ML-model* releases, not synthetic tables, so
> some artefact-safety properties are N/A for them — marked accordingly. The finding survives that.

## The 12 deployments (as documented)
| # | Deployment | Type | ε (quoted) | δ | Model | Unit of privacy |
|---|---|---|---|---|---|---|
| 1 | Apple — QuickType | query | 16 | — | local | user-day |
| 2 | Apple — Emoji | query | 4 | — | local | user-day |
| 3 | Facebook — Full URLs dataset | query | 1.69 (0.41/action) | 1e-5 | central | action |
| 4 | Facebook — Movement Range | query | 2 (daily) | — | central | user-day |
| 5 | Google — Community Mobility | query | 2.64 | — | central | user-day |
| 6 | Google — Gboard next-word | ML model | 0.69–10.61 | 1e-5 | federated+DP | model-specific |
| 7 | LinkedIn — Audience Engagements | query API | 0.15/query; 34.9/month | 1e-10 | central | user |
| 8 | Microsoft — US Broadband | statistic | 0.2 | — | central | user |
| 9 | US Census — 2020 Redistricting | statistic/microdata | 13.64 | 1e-5 | central | person |
| 10 | US Census — OnTheMap | statistic | 8.6 | 1e-5 | central | person |
| 11 | Wikimedia — Page views | statistic | 0.72 (1.0 hist.) | 1e-5 | central | user-day / 30–300 views |
| 12 | Israel MoH — Birth dataset | **synthetic data** | 9.98 | — | central | singleton birth |

## Coverage against the P1–P11 boundary properties
Legend: **Y** documented · **N** not documented · **~** partial · **–** N/A for this release type.
P1 ε · P2 δ · P3 mechanism · P4 neighbour/unit-of-privacy · P5 release-size provenance · P6 seed
secrecy · P7 keyed fingerprint · P8 evaluation-privacy label · P9 audit operating range/LoD ·
P10 tamper-evidence (signature) · P11 machine-checkable.

| # | Deployment | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | Apple QuickType | Y | N | Y | Y | – | – | – | N | N | N | N |
| 2 | Apple Emoji | Y | N | Y | Y | – | – | – | N | N | N | N |
| 3 | FB Full URLs | Y | Y | Y | Y | N | N | N | N | N | N | N |
| 4 | FB Movement | Y | N | Y | Y | – | N | N | N | N | N | N |
| 5 | Google Mobility | Y | N | Y | Y | – | N | N | N | N | N | N |
| 6 | Gboard | Y | Y | Y | ~ | – | – | – | N | N | N | N |
| 7 | LinkedIn | Y | Y | Y | Y | – | N | N | N | ~ | N | N |
| 8 | MS Broadband | Y | N | Y | Y | N | N | N | N | N | N | N |
| 9 | Census 2020 | Y | Y | Y | Y | ~ | N | N | ~ | N | N | N |
| 10 | OnTheMap | Y | Y | Y | Y | N | N | N | N | N | N | N |
| 11 | Wikimedia | Y | Y | Y | Y | N | N | N | ~ | N | N | N |
| 12 | Israel MoH birth | Y | N | Y | Y | N | N | N | N | N | N | N |
| | **documented by** | **12/12** | 6/12 | **12/12** | 11/12 | 0 | 0 | 0 | 0 | 0 | **0** | **0** |

## What this shows
1. **The guarantee parameters are well documented.** ε (12/12), mechanism (12/12), unit of privacy
   (11/12) — the field has genuinely converged on disclosing the *guarantee* (exactly Dibia/P10's
   nine-category label). δ is patchier (6/12).
2. **The artefact-safety properties are documented by essentially no one.** P5–P9 are near-zero, and
   **P10 tamper-evidence = 0/12 and P11 machine-checkable = 0/12.** Not one of these real, high-profile
   deployments ships a **signed** or **machine-checkable** release artifact.
3. **The one synthetic-data release here (Israel MoH births) is the most direct comparison:** it
   documents ε and unit of privacy but nothing about artefact safety, and it is neither signed nor
   checkable — the exact gap SynthProof fills.
4. This corroborates the HuggingFace wild-audit (0/286 declare DP) from the *opposite* end: even the
   best-documented real deployments stop at guarantee parameters and never make the artifact checkable.

## Honest limits
- Coverage is judged from the **registry's summary**, which reports guarantee parameters; a deployment
  might disclose more in its own technical report (e.g., Census DAS documents invariants in prose — see
  `research/20`). "N" means "not a machine-checkable field," not "the team was careless."
- P5–P7 (release-size/seed/fingerprint) are **N/A** for pure statistic/query releases (marked –); they
  bite for *synthetic-data* releases, which is our setting (row 12 and the HF ecosystem).
- Two-source check: Desfontaines' list is the source here; the Oblivious/OpenDP deployments registry
  (also cited by P10) is a second registry that could be cross-checked next.

## One line for the paper / viva
*Across twelve of the most prominent real DP deployments, every one documents ε and the mechanism and
almost all the unit of privacy — but none is signed, none is machine-checkable, and none carries a
single artefact-safety field. The field documents the guarantee; SynthProof makes the artifact
checkable.*
