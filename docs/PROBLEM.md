# The problem SynthProof addresses

<!-- provenance: results/gdp/independent_eps1.json, results/real_release_study.json, research/release_boundary/seed_replay_probe.json -->

Every factual sentence below cites a source or a committed result. Citations are to arXiv
identifiers verified in `research/08_novelty_verdict.md` and `research/25_prior_art_release_auditing.md`.

## 1. A differentially private release is published with a number nobody checks

A synthetic table released under differential privacy comes with an epsilon. The people who
receive it do not, in practice, verify that number: interviewed practitioners trusted DP guarantees
implicitly rather than checking them (Song, Sarathy, Shoemate & Vadhan, CSCW 2024,
arXiv:2410.09721).

Trust in the implementation is not well founded. A grey-box audit of twelve open-source DP
libraries found thirteen guarantee violations (Cebere et al., arXiv:2602.17454). This project found
its own: until D5, its sheets published the run seed, and replaying a release from that seed
identified the true table in 15 of 15 trials and the neighbouring table in none
(`docs/design/PUBLIC_RELEASE_BOUNDARY.md` §D5, `research/release_boundary/seed_replay_probe.json`).
The epsilon on those releases was correct; the release still decided membership.

## 2. What a release artefact lets a reader verify today

Six real DP releases, read from their own primary documentation (`results/REAL_RELEASE_STUDY.md`):
most state their privacy parameter, mechanism and unit of privacy; none ships a signed artefact,
none carries a privacy claim a program can check from the artefact, and for every one the epsilon
cannot be recomposed from what is published. An expert-elicited privacy label for DP proposes the
fields such an artefact should carry (Dibia, Lu, Bhattacharjee, Near & Feng, arXiv:2507.15997) but
builds no checker and no signature.

An empirical audit is not a substitute unless its reach is reported with it. On the worst-case
instance, a strong membership adversary certified audited epsilon 0.2161 against a proved 0.9999,
with a ceiling of 26.01 for that run count (`results/gdp/independent_eps1.json`): the gap between
audited and proved is a property of this adversary, and only the ceiling beside it says the
instrument could have seen more.

## 3. What SynthProof does

It produces the release and an artefact a third party can check without trusting the producer:
the proved epsilon recomposable from the signed list of noisy steps; the boundary channels that
leak outside epsilon (seed, row count, fingerprint, domain, evaluation, invariants) checked by a
program (RB1–RB15); the GDP audit of the mechanism with its ceiling; all of it under an Ed25519
signature, with a hash-chained, signed ledger of what each release spent, whose signed head
commits to the entry count and tip hash.

## 4. What it does not do

- **Central model only.** SynthProof reads the sensitive table. Every guarantee is conditional on
  that curator being trusted, so it does not serve a deployment where no party may see the raw
  data: a local-model collection (each record noised on the user's device before it is sent) or a
  shuffle-model one is out of scope. The sheet records `deployment_model: central` so the
  assumption travels with the release.
- It proves what was charged, not that the code charged correctly: the signature binds the
  producer to its claim; it is not attestation of execution.
- The audit is mechanism-level on a fixed worst-case instance, not a measurement of each release.
- A holder of the signing key can rewrite and re-sign the ledger: it is tamper-evident, not
  tamper-proof (`docs/threat_model.md`).
