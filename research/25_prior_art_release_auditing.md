# 25 — Prior-art check: is "auditing a DP release's non-ε channels" novel?

> Resolves the gate `CLAUDE.md` flagged as open: *"Whether auditing a DP release's non-epsilon
> channels has prior art has not been checked yet. Until it is, describe this as a checker, not a
> contribution."* Searched 2026-09-17 (US web index). Every source below was returned by search;
> none is recalled from memory. This note fixes the paper's honest novelty framing.

## What the literature already has (so we must NOT claim it)

1. **The leak phenomena are partly known.** Metadata/domain leakage — released category sets and
   numeric min/max bounds leaking rare records — is documented for DP synthesizers (PrivBayes /
   PATE-GAN / DataSynthesizer), surfaced again in the DP-SDG auditing literature
   ([Annamalai & Ganev et al., arXiv:2405.10994](https://arxiv.org/pdf/2405.10994)). This is
   exactly the channel our **RB6 `domain_source`** and **RB9 `discretization_source`** catch. So
   those checks catch a *known* leak; the novelty is only that we make it a **checkable field**,
   not that we discovered it. `[The specific 2022 origin paper was named in a search summary but
   not fetched — do not cite a 2022 source until fetched.]`

2. **Empirical auditing of DP-SDG is crowded.** MIA/GDP auditing that runs attacks on the
   synthetic data is an active, mature line: tight GDP auditing of MST/AIM
   ([arXiv:2604.18352](https://arxiv.org/html/2604.18352)), the framework paper
   ([arXiv:2405.10994](https://arxiv.org/pdf/2405.10994)), a testbed
   ([Synth-MIA, arXiv:2509.18014](https://arxiv.org/pdf/2509.18014)), and attack-based release
   auditing ([local likelihood attacks, arXiv:2508.21146](https://arxiv.org/pdf/2508.21146)). Our
   `research/24` GDP audit is a **replication** of this, not a contribution — already stated as
   such.

3. **The machine-checkable label is PROPOSED, not built.** Our base paper — Dibia, Lu,
   Bhattacharjee, Near & Feng, *"We Need a Standard"*
   ([arXiv:2507.15997](https://arxiv.org/html/2507.15997)) — explicitly proposes a machine-readable
   privacy label embedded in release metadata to *"enable automatic compliance checking for
   deployments claiming differential privacy,"* and lists "verification of correctness" as a
   documentation element. But it stops at the proposal: it builds no checker, adds no signature,
   and (per `CLAUDE.md`, verified 2026-08-25) defines no way to report an empirical metric's
   operating range — a gap one of their own experts called *"privacy theater."*

## What survives as ours (state exactly this, not more)

**An implemented, signed, artifact-only conformance checker for a DP synthetic-data release
label** — i.e. we *build* what Dibia proposes and fill its two named gaps:

- **`boundary-audit` RB1–RB14** — a checker that reads only the released artifact (the Privacy
  Data Sheet / Croissant record), never the data or the producer's code, so a third party can run
  it. It bundles the known leak channels (domain, discretisation) with the artifact-hygiene ones
  (published seed, exact row count, unkeyed fingerprint, unlabelled evaluation, multi-table) into
  one machine-checkable pass. Novelty type: **engineering / integration**, not scientific.
- **Ed25519 signature** over the label (`ledger/signing.py`) — the first Dibia gap.
- **Operating-range / audit-ceiling field** (`research/18`, `audit-power`) — the second Dibia gap.
- **Conformance = passing the checker** (`docs/design/DP_RELEASE_LABEL_SPEC.md`), validated end to
  end by `scripts/build_release.py` and cross-checked against the official MLCommons validator.

This is consistent with the standing verdict (`CLAUDE.md`): **integration, not invention**; the
surviving claims are S1 (report the metric's operating range in the artefact) and S2 (sign the
claim) — both narrow, S2 being engineering novelty.

## The empirical backbone that makes it a paper (already collected)

- **0 / 286** HuggingFace synthetic-data cards declare DP (`scripts/wild_audit_honest.py`).
- **12 / 12** flagship real DP deployments document ε but **none is signed, none is
  machine-checkable** (`research/21`).
- Our pipeline emits a release that **passes RB1–RB14, is signed, and validates against the
  official MLCommons validator** (`scripts/build_release.py`) — the existence proof that the label
  Dibia proposed can actually be built and checked.

## The honest one-liner for the paper

*The field has the guarantee parameters, the leak phenomena, and empirical attacks; what it lacks —
and what Dibia et al. (2025) call for but do not build — is a signed, machine-checkable release
label a third party can verify from the artifact alone. We build it, fill its two gaps (signature,
operating range), and show every prominent real release fails it today.*

## Honest limits of this check

- One US web-index pass; not an exhaustive survey. A hostile reviewer may still surface a closer
  artifact-level checker — the framing above (implementation + two gaps) survives that better than
  any "we invented it" claim would.
- The specific 2022 metadata-leakage origin paper was named in a search summary but **not fetched**;
  fetch it before citing a 2022 source in the paper.
- Nothing here upgrades the mechanism side: our generators (AIM/MST) are integrations of published
  methods and must not be presented as novel.

Sources: [2405.10994](https://arxiv.org/pdf/2405.10994) ·
[2604.18352](https://arxiv.org/html/2604.18352) ·
[2507.15997](https://arxiv.org/html/2507.15997) ·
[2509.18014](https://arxiv.org/pdf/2509.18014) ·
[2508.21146](https://arxiv.org/pdf/2508.21146)
