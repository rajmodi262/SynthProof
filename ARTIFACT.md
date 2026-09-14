# Artifact Evaluation — SynthProof

Written to the USENIX artifact-evaluation format. Every claim in the thesis is mapped to the
command that reproduces it, and every command has an expected output and a runtime.

**Badges this artifact is prepared for:** *Artifacts Available* (Zenodo DOI, see §7),
*Artifacts Functional* (§2–§4), and *Results Reproduced* (§5) for the subset of claims whose
runtime fits an evaluation window.

---

## 1. Abstract

SynthProof generates differentially private synthetic tabular data and reports both a formal
upper bound on privacy loss (ε_proved) and an empirical lower bound from canary auditing
(ε_audited). Its principal finding is negative and concerns the measurement rather than the
mechanisms: the ε a one-run audit can certify is bounded by the canary count alone.

The artifact contains the full pipeline, the experiment runners, the committed results, and a
reproducibility manifest that pins each result file to a commit and an environment.

---

## 2. Requirements

| | |
|---|---|
| **OS** | Linux, macOS, or Windows. CI runs Ubuntu; development was on Windows 11 |
| **Python** | **3.11 required.** `private-pgm` (real AIM) declares `>=3.11`. On 3.10 the AIM mechanism is skipped and its tests self-skip |
| **Node** | 20+, only for the web console. Not needed for any experimental claim |
| **RAM** | 8 GB. AIM's junction tree is bounded to 128 MB by default (`AIMGenerator(max_model_mb=...)`) |
| **GPU** | **None.** No component uses one |
| **Network** | Only to fetch UCI Adult on first run. Verified against a committed SHA-256 |
| **Disk** | ~500 MB including the venv |

No proprietary dependencies. All code MIT-licensed; UCI Adult is public.

---

## 3. Getting started (≈5 minutes)

```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
```

```bash
pip install -e ".[dev]"
```

Real AIM additionally needs private-PGM, which is not on PyPI:

```bash
pip install "git+https://github.com/ryan112358/private-pgm.git"
```

Smoke test — should print a Privacy Data Sheet and exit 0:

```bash
python -m synthproof.cli demo --rows 200 --eps 1.0
```

Full test suite (**expected: 228 passed, 1 skipped** — the skip is AIM without private-PGM):

```bash
make test
```

---

## 4. Functional check (≈10 minutes)

Each of these exercises a distinct subsystem end to end.

**Signing and third-party verification.** Demonstrates that a released sheet is tamper-evident.

```bash
python -m synthproof.cli keygen && python -m synthproof.cli run --eps 2.0 --mechanism pairwise --rows 300 --sign --out /tmp/sheet.json && python -m synthproof.cli verify /tmp/sheet.json --pubkey .keys/synthproof_ed25519.pub
```

Expect `VERIFIED`. Now edit any field in `/tmp/sheet.json` and re-run `verify`: expect
`FAILED` and exit code 1.

**Auditor controls.** The positive and negative controls that make every null result
trustworthy. Also enforced in CI as the `auditor-guard` job.

```bash
python -m pytest tests/test_detection_floor.py -q
```

**Accountant differential test.** Cross-checks composed ε against `autodp`, an independent
implementation.

```bash
python -m pytest tests/test_accounting_properties.py -q -k autodp
```

**Console** (optional, needs Node):

```bash
make serve
```

```bash
cd web && npm install && npm run dev
```

---

## 5. Claims mapped to commands

| # | Claim (thesis §) | Command | Expected | Runtime |
|---|---|---|---|---|
| C1 | Calibration never overspends; proved/target ≈ 0.92 (§4.4, §7.1) | `make test` then inspect the `calibration-guard` CI job, or run the inline script in `.github/workflows/ci.yml` | Passes across 24 configurations; no achieved ε exceeds its target | 1 min |
| C2 | Composed ε agrees with `autodp` to within 0.05% (§5) | `pytest tests/test_accounting_properties.py -k autodp` | 12 configurations pass at `rel=0.01` | 1 min |
| C3 | The auditor detects a verbatim release and does not fire on a shuffled one (§7.2) | `pytest tests/test_detection_floor.py -q` | 12 passed | 1 min |
| C4 | Detection floor and **audit ceiling** (§7.2) — the ceiling is a corollary of Steinke et al. (2023) Thm 2.1, and reporting it beside the measurement transfers limit-of-detection reporting from analytical chemistry (MIQE 2.0, Bustin et al., *Clinical Chemistry* 2025;71(6):634–651). Neither convention is ours | `make floor` | Reproduces `results/detection_floor.json`; floor at leak=1.0 is m=10, leak≤0.05 undetected at m=800 | ~25 min |
| C5 | H1: structured mechanisms preserve structure better, non-overlapping CIs (§7.3) | `make h1` | Reproduces `results/h1_all_families.json`, 75 cells | **~4 h** |
| C6 | **RETRACTED.** This row claimed a fixed fraction of the correlation signal was destroyed by canary contamination. **The effect is real; the figure does not replicate** — a dose-response run found the loss varies continuously with the canary fraction and does not sit at any single value. Report the fraction axis, never a percentage | `results/CANARY_DOSE_RESPONSE.md` records the run that superseded it | The contamination mechanism reproduces; no fixed figure does | 5 min |
| C7 | H2 is a bounded null; adversary needed accuracy 0.600 and reached 0.562 (§7.6) | `make h2` then `make h2-analyse` | Reproduces `results/h2_analysis.json` | ~5 min |
| C8 | Every published number matches its manifest | `make reproduce` | `REPRODUCED` | seconds |
| C9 | All figures derive from committed results | `make figures` | 8 figures in `docs/thesis/figures/` | 1 min |

**C5 is the long one.** Evaluators short of time should run C1–C4 and C7–C9 (C6 is retracted) (~35 minutes
total) and treat C5 as available-but-not-rerun. The grid is **resumable**: it checkpoints every
cell, so an interrupted run continues where it stopped rather than starting over.

---

## 6. Reproducibility notes, including what is *not* guaranteed

`make reproduce` compares every result file against `results/MANIFEST.json`, which pins the
commit, whether the tree was dirty, the interpreter and platform, the versions of the seven
packages whose value can change a number, the dataset checksums, and each runner's grid read
from the module itself.

**A manifest mismatch means something changed — not necessarily that a number was edited.**
Floating-point results can differ across BLAS builds and CPU architectures at a fixed seed.
Bitwise reproduction is expected on the same platform and *not* claimed across platforms.

Every experiment records its seeds. Nothing depends on wall-clock time or on network state
after the dataset is fetched.

---

## 7. Archival availability (Zenodo)

GitHub alone does not satisfy *Artifacts Available*; an archival DOI is required. These steps
need a browser and must be done by a maintainer:

1. Sign in to <https://zenodo.org> **with GitHub** and authorise the app.
2. Go to Zenodo → your profile → **GitHub**. Find `rajmodi262/SynthProof` and toggle it
   **on**. That installs a webhook on the repository.
3. In GitHub, cut a **Release** (not just a tag) from the existing tag `v1.0.0`, titled
   `SynthProof v1.0.0`, using `CHANGELOG.md` as the release notes.

   **Order matters: do step 2 first.** Zenodo archives only Releases published *after* its
   webhook is switched on. The `v1.0.0` tag was pushed on 2026-09-13 but no Release was
   created from it, precisely so that the first Release can be archived. Publishing it before
   the toggle means v1.0.0 is never archived and the DOI has to wait for a later release.
4. Zenodo archives the release automatically and mints **two** DOIs:
   - a **concept DOI**, which always resolves to the newest version — cite this in the thesis;
   - a **version DOI** for that specific release — cite this when a reader must see the exact
     code behind a number.
5. Add both to `CITATION.cff` (`doi:` and `identifiers:`) and to the README badge row.

Release notes: use `CHANGELOG.md` for v1.0.0 verbatim. It opens with the release's known gaps,
and those should stay first in the published notes too.

---

## 8. Known limitations

Stated here because an evaluator will find them, and because the project's standing rules
require capabilities that do not exist to be named rather than omitted.

> **Rewritten 2026-09-13.** The previous version of this list was written for v0.2.0 and had
> become false in three places: it said only UCI Adult was run, that attribute inference was not
> implemented, and that H3 was untested. An evaluator checking the repository would have found
> all three contradicted, which is worse than finding a limitation.

- **The audit ceiling disqualifies the headline comparison.** At the canary counts used, the
  instrument could not have certified the ε values being claimed. This is the project's main
  finding, not a caveat hidden here. Every sheet now carries a verdict saying so when it applies.
- **Three datasets.** UCI Adult, ACSIncome (CA 2018), and UCI Bank Marketing all carry the
  full preregistered 5 × 5 grid (75 cells each). The structure-ordering and utility-ordering
  findings do not all transfer across the three.
- **LiRA is not implemented**, and is declared absent in every sheet
  (`attacks_not_implemented`). Each release runs six attacks: canary audit, distance MIA,
  DOMIAS, exact-match risk, linkability and attribute inference. A seventh, the marginal-ratio
  adversary, is used in the adversary-comparison experiment, not per release.
- **H2 and H3 are nulls.** H2 is a bounded null at this scale; H3 replicated null on both census
  datasets, with no bootstrap CI excluding zero at any of five ε.
- **The ledger is tamper-evident, not tamper-proof.** A holder of the signing key can rewrite
  and re-sign. Key custody is an organisational control.
- **A signature proves origin, not truth.** Until 2026-09-13 the two demo capsules were
  hand-typed and signed, and verified as authentic. They are now built from real releases, and
  the verifier recomputes the audit ceiling from the declared audit.
- **The certificate attests the claim, not the execution.** Nothing proves the code that ran is
  the code that was audited; that requires a trusted execution environment.
- **`dp_accounting` is trusted**, mitigated by the `autodp` differential test.
- **`docker compose up` has not been executed** for v1.0.0, and real AIM is not available inside
  the image (private-pgm installs from git and is not a declared dependency).

---

## 9. Repository map

```
synthproof/
├── accounting/   accountant, calibration, discrete noise samplers
├── audit/        canary auditor, one-run Steinke auditor, detection floor,
│                 subgroup auditing, equivalence/power analysis
├── attacks/      distance-MIA baseline, DOMIAS, exact-match singling out
├── data/         schema, dataset wrapper, loaders, DP domain profiler
├── generators/   independent, copula, pairwise tree, AIM, leaky controls
├── evaluate/     downstream utility (TSTR/TRTR)
├── frontier/     experiment runner, checkpointing, data sheet exporter
├── ledger/       hash-chain ledger, Ed25519 signing
└── api/          FastAPI service behind the console
scripts/          experiment runners, figure generation, reproduce
results/          committed results, manifest, and their write-ups
docs/thesis/      chapters, data pack, figures, references.bib
web/              React console
```
