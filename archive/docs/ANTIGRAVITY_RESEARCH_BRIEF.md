# Antigravity research brief — is the "release-boundary" work novel, and how should we frame it?

**Written 2026-09-14 for a parallel research agent (Antigravity / Gemini). You do RESEARCH ONLY.
Do not modify code, tests, results, or any file under `synthproof/`, `tests/`, `results/`, or
`scripts/`. Your deliverable is a single new markdown file, `research/12_boundary_prior_art.md`,
written to the format in section 6. Everything else in the repo is being changed live by another
agent; stay out of it.**

## 0. The one rule that governs everything you write

This project runs an honesty protocol (`CLAUDE.md`, "Standing rules"). You inherit it:

1. **No citation without a fetched URL / DOI / arXiv ID.** If you cannot open it, mark the claim
   `[UNVERIFIED]` and let no conclusion rest on it. Never invent a paper, an author list, a venue,
   or a quote. A plausible-sounding citation you did not open is a fabrication.
2. **No fabricated numbers.** Quote from the source or write `[NOT REPORTED]`.
3. Prefix reasoning with `INFERENCE:` and every confidence with `CONFIDENCE: low/med/high + why`.
4. **Be adversarial. Your job is to KILL our novelty claims, not to support them.** We would rather
   find the prior art now than have an examiner find it tomorrow. A confirmed kill is a *good*
   result and must be reported as prominently as a survivor.
5. If a search tool is unavailable or returns nothing, say so. Never simulate a result.

The person reading your output is a B.Tech capstone student defending this project tomorrow. They
need to know exactly which sentences they may say out loud and which they may not.

## 1. What the project is (one paragraph)

SynthProof generates differentially private synthetic tabular data and ships each release with a
signed "Privacy Data Sheet" (a machine-readable privacy label) plus an optional Croissant record.
The project's own novelty verdict (`research/08_novelty_verdict.md`, and the memory) is already
humble: eight invention claims are dead, three narrow survivors remain, and the honest position is
**integration, not invention**. The single most important related work is **Dibia, Lu,
Bhattacharjee, Near & Feng, arXiv 2507.15997 (2025)** — an expert-elicited nine-category privacy
label for DP that overlaps the Privacy Data Sheet field-for-field. Read that framing in `CLAUDE.md`
before you start; do not re-derive it.

## 2. The new work you are assessing (what happened today, 2026-09-14)

While auditing whether AIM's selection step was accounted correctly, the team found that the
*artefact* accompanying a DP release leaked information that the release's epsilon does not cover.
Full spec: `docs/design/PUBLIC_RELEASE_BOUNDARY.md`. Evidence: `research/release_boundary/` and
`research/11_selection_accounting.md`. Five findings:

- **D1** — AIM/fixed_workload fitted the graphical model with `known_total = n`, the exact private
  row count, and the selection step's sensitivity was therefore >1 while it was charged as 1
  (under-charged by ≥1.71×, measured). Fixed.
- **D5 (the headline)** — the signed sheet published the **run seed**. Every noise draw derives from
  it, so a release is a deterministic function of `(table, seed)`. The standard DP adversary (knows
  every record but one) replays the release for both candidate tables with the published seed and
  sees which matches. **Measured: 15/15 exact matches from the true table, 0/15 from its
  neighbour.** A membership decision with certainty, at any epsilon. Fix: the seed is withheld and
  drawn from the OS.
- **D2** — the exact row count `n` was published (private under add/remove-one). Now a declared or
  DP-counted public size.
- **D3** — the input fingerprint was an unkeyed SHA-256 of the table = a deterministic membership
  test. Now a keyed HMAC.
- **D4** — utility / MIA / audited-eps are computed on the real table and were published unlabelled.
  Now labelled "not covered by epsilon".

Two artefacts were built on top of this that we might want to *frame* as contributions:

- **A `boundary-audit` checker** (`synthproof/audit/boundary.py`): reads a published sheet or
  Croissant record — only the artefact, never the data or the producer's code — and reports every
  channel that discloses something epsilon does not cover, each tagged `leak` / `unverifiable` /
  `note`. It is deliberately asymmetric: it can prove a channel is OPEN (a published seed is a
  published seed) but never that one is CLOSED (a keyed HMAC and a plain hash look identical from
  outside).
- **A cross-check fix**: the second-accountant gate (autodp vs dp_accounting) ignored Poisson
  subsampling and refused correct DP-SGD releases; a subsampled release is now reported `unsupported`
  rather than falsely refused or falsely "agreed". (Likely NOT novel — an implementation bug — but
  confirm nobody has written up "differential-privacy library cross-checking disagrees on
  subsampled composition" as a finding.)

## 3. The exact questions to answer (in priority order)

**Q1 (highest value). Is "the published run seed of a DP synthetic-data release is a membership
oracle" a known result?** This is the strongest and most surprising claim. Hunt for prior art in
these framings, and report each as KILLED / WOUNDED / SURVIVES with the source:
- reproducibility / seed disclosure as a privacy side channel in ML or DP;
- determinism of a DP mechanism's output enabling membership or reconstruction when the randomness
  is revealed or low-entropy;
- "the privacy of DP depends on the secrecy of the sampled noise" stated as a threat, not just
  folklore. Look specifically at: DP implementation-attack literature (Mironov 2012 on floating
  point is related but DIFFERENT — that is representation, not seed disclosure — state the
  distinction precisely); Jagielski / Nasr / Steinke auditing papers; Cebere et al. 2026
  (arXiv:2602.17454, DP library violations); Tramèr et al. on DP debugging; anything on "randomness
  reuse" or "nonce reuse" analogies imported from cryptography.
- **INFERENCE we want you to test:** is this just a special case of "DP assumes the adversary does
  not see the internal randomness", which is textbook (Dwork & Roth)? If so, the novelty is not the
  principle but the demonstration that a *shipped, signed artefact* violated it in practice. Judge
  whether that demonstration is publishable or merely a good bug. Be honest.

**Q2. Is a "release-boundary auditor" — a tool that checks a DP artefact for non-epsilon side
channels from the artefact alone — novel?** Compare against:
- DP validation / auditing tools that check the *mechanism* (ala Cebere et al.; DP-Auditorium,
  Google; the Ganev/Annamalai/De Cristofaro cluster) — these audit the algorithm, we audit the
  published *document*. Is that distinction real or cosmetic?
- privacy-label / datasheet / model-card *validators* (Croissant's own validator, MLCommons; Dibia
  et al.; datasheets for datasets; model cards) — do any of them check for privacy leakage in the
  card's own fields, or only for completeness/format?
- data-release checklists in official statistics / SDC (Five Safes, SACRO, the SDC Handbook — note
  the SDC Handbook returned HTTP 403 for us before; try again). SACRO checks OUTPUTS; we check the
  METADATA artefact. Is metadata-level disclosure control a named thing?

**Q3. Frame the honest contribution.** Given Q1 and Q2, write the single most defensible sentence
the student can say tomorrow about what is new here, and the single sentence they must NOT say.
Both must survive an examiner who has read the Ganev/Annamalai/De Cristofaro/Kulynych cluster.

**Q4 (lower priority, only if time). The DP-VAE cross-check.** Confirm/deny that "two DP accounting
libraries disagree on subsampled-Gaussian composition" is already documented (it almost certainly
is — it is the DP-SGD implementation gap; find the canonical reference, likely Chua et al. on
"How Private is DP-SGD?" or the Opacus/TF-Privacy discrepancy literature). We only need the citation
to say "known issue", not a novelty claim.

## 4. Where to look first (do not treat as exhaustive)

arXiv (cs.CR, cs.LG, stat.ML), USENIX Security, IEEE S&P, CCS, NeurIPS/ICML privacy tracks, PoPETs /
PETS, TPDP. The author cluster **Ganev, Annamalai, De Cristofaro, Kulynych** is ~2 years ahead of us
on DP synthetic-data auditing — assume they or their neighbours have thought about this, and look
hard before concluding otherwise. Start from the reference lists of arXiv:2405.10994 and
arXiv:2604.18352.

## 5. Traps (things that will waste your time or embarrass us)

- Do not confuse **seed disclosure** (our D5) with **floating-point noise leakage** (Mironov 2012)
  or with **weak PRNGs**. Ours is: the seed is *correctly* strong but *published*. Keep them apart.
- Do not claim SACRO/Five Safes "does the same thing" without checking — the project's existing note
  is that SACRO reads output *values* and does not autonomously refuse; verify before repeating.
- "Membership inference against synthetic data" is a huge, crowded field (Stadler et al.,
  Annamalai et al., etc.) — but almost all of it is *statistical* MI against the synthetic rows. Ours
  is *deterministic replay* from published randomness, which is a different mechanism. Do not let the
  crowded statistical-MI field bury the distinction; state it explicitly and judge whether the
  distinction is enough to survive.
- If you find our claim is fully anticipated, SAY SO plainly at the top. That is the most valuable
  outcome you can produce.

## 6. Deliverable format — write ONLY this file: `research/12_boundary_prior_art.md`

```
# 12 — Prior-art kill pass on the release-boundary work (Antigravity, 2026-09-14)

> Status: research pass. Standing rules applied. Every citation below was fetched; anything I
> could not open is marked [UNVERIFIED] and nothing rests on it.

## Verdict in three lines
- Q1 (seed = membership oracle): KILLED / WOUNDED / SURVIVES — <one line + the killer citation>
- Q2 (release-boundary auditor):  KILLED / WOUNDED / SURVIVES — <one line + the killer citation>
- The one sentence the student MAY say: "<...>"
- The one sentence the student may NOT say: "<...>"

## Q1 — the published seed as a membership oracle
<verified facts, each with a fetched source; INFERENCE: / CONFIDENCE: as required>

## Q2 — the release-boundary auditor
<same>

## Q3 — the honest framing
<same>

## Q4 — the DP-VAE cross-check (only if reached)
<the canonical "known issue" citation, or [NOT FOUND]>

## Sources (every one fetched; URL/DOI/arXiv ID + one line on what it says)
```

Keep it tight. Confirmed kills are the point. A short file that correctly kills two claims is worth
more than a long one that hedges.
```
