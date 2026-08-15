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
| C4 | Detection floor and **audit ceiling** (§7.2) | `make floor` | Reproduces `results/detection_floor.json`; floor at leak=1.0 is m=10, leak≤0.05 undetected at m=800 | ~25 min |
| C5 | H1: structured mechanisms preserve structure better, non-overlapping CIs (§7.3) | `make h1` | Reproduces `results/h1_all_families.json`, 75 cells | **~4 h** |
| C6 | Canary contamination destroys 89% of the correlation signal (§7.4) | See `results/H1_RESULTS.md` §4; reproduce with `run_cell(..., separate_utility_fit=False)` vs `True` | corr 0.1014 → 0.0109 at 60 canaries | 5 min |
| C7 | H2 is a bounded null; adversary needed accuracy 0.600 and reached 0.562 (§7.6) | `make h2` then `make h2-analyse` | Reproduces `results/h2_analysis.json` | ~5 min |
| C8 | Every published number matches its manifest | `make reproduce` | `REPRODUCED` | seconds |
| C9 | All figures derive from committed results | `make figures` | 8 figures in `docs/thesis/figures/` | 1 min |

**C5 is the long one.** Evaluators short of time should run C1–C4 and C6–C9 (~35 minutes
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
3. In GitHub, cut a **Release** (not just a tag) — e.g. `v0.2.0`, titled
   `SynthProof v0.2.0 — auditor validation and the audit ceiling`.
4. Zenodo archives the release automatically and mints **two** DOIs:
   - a **concept DOI**, which always resolves to the newest version — cite this in the thesis;
   - a **version DOI** for that specific release — cite this when a reader must see the exact
     code behind a number.
5. Add both to `CITATION.cff` (`doi:` and `identifiers:`) and to the README badge row.

Suggested release notes:

> Auditor validation: detection floor and ceiling measured, with positive and negative
> controls enforced in CI. One-run (Steinke) auditor alongside the paired Clopper-Pearson
> estimator. H1 answered on UCI Adult with bootstrapped CIs; H2 reported as a bounded null with
> FDR control, equivalence testing and a power statement. Signed Privacy Data Sheet with a
> standalone verifier. Reproducibility manifest and per-cell grid checkpointing.

---

## 8. Known limitations

Stated here because an evaluator will find them, and because the project's standing rules
require capabilities that do not exist to be named rather than omitted.

- **One dataset.** UCI Adult only; ACS PUMS was not run. Every H1/H2 conclusion is
  single-dataset.
- **The audit ceiling disqualifies the headline comparison.** At the canary counts used, the
  instrument could not have certified the ε values being claimed. This is the project's main
  finding, not a caveat hidden here.
- **Three attacks, not four.** Shadow-model MIA and attribute inference are not implemented and
  are named as absent in the API, the console, and the thesis.
- **The ledger is tamper-evident, not tamper-proof.** A holder of the signing key can rewrite
  and re-sign. Key custody is an organisational control.
- **`dp_accounting` is trusted**, mitigated by the `autodp` differential test.
- **H3 untested.**

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
