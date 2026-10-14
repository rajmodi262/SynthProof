# SynthProof — live demo runbook

**Every step below was rehearsed end to end on 2026-10-14 against v1.3.0.** Keys exist in
`.keys/` and the API serves a pre-built console needing no npm. **Before the demo, run the
"Restore" command in section 3 once** -- it creates `build/release/`, which section 3 needs and
which is not kept between machines.

**Total runtime: 8 minutes.** Cut to the ⭐ items if you get 4.

---

## 0. Start it — ONE command

```bash
cd D:\03_Study\CAPSTONE\SynthProof && .venv311\Scripts\python.exe -m uvicorn synthproof.api.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** — the console is served by the API itself. No npm, no second
process, no build step. Verified: all seven mechanisms available, including real AIM and MST.
Use a browser window at least **1280 px wide**: narrower, the run controls move below the 3D
chamber (scroll down to them).

**Leave that terminal running.** Open a SECOND terminal for the CLI parts below.

---

## 1. ⭐ The system refuses (45 s) — open with this

Most projects show what their tool *does*. Open by showing what it **won't** do.

```bash
.venv311\Scripts\python.exe -m synthproof.cli run --rows 200 --eps 1.0 --sign --out nul
```

It refuses:

```
R1 REFUSE: 200 rows is below the 500-row floor. Protecting one record among this few
requires noise that leaves nothing to release; the output would be noise carrying a
certificate.
```

**Say:** "It read only the schema and the row count — it never touched a cell — and it still
said no. A gate that reads your data to decide whether it's safe to read your data has already
lost."

---

## 2. ⭐ A real release, live (2 min)

In the **console** at http://127.0.0.1:8000 — click the **⚡ HR Attrition (fastest)** preset
(the toy table is the slow path), keep `pairwise`, ε = 1.0, and press **Run release & compute
proof**. It finishes in about ten seconds.

Fourteen stages stream live over SSE. Point at these three as they go past:

| Stage | What to say |
|---|---|
| `budget` | "profile 0.000 + synthesis 1.000. This table's domain is declared publicly, so learning it costs nothing and the whole budget goes to synthesis. A table with no declared domain would be charged for it." |
| `fit` | "+1.000 ε — every charge goes through the accountant; the sheet lists them." |
| `audit` | "Audited ε is about **0.0**, and beside it a ceiling of **2.97**." |

The **Audit Range** panel now states the ceiling beside the result, in words: the instrument
cannot report above ε ≈ 2.97 at this canary count, so an audited value near zero is not evidence
that nothing leaked. The correlation matrix is **measured** from the run; the tradeoff curve beside it is
labelled an illustrative model — do not present it as data.

**The line that lands:** "That zero is not good news and we refuse to present it as good news.
At 60 canaries our auditor could not report above 2.97 even against a release that was 100%
copied training data. The gap was guaranteed before the mechanism ran. We report the ceiling
next to the number so nobody can misread it."

**If asked where the convention comes from:** analytical chemistry. MIQE 2.0 (Bustin et al.,
*Clinical Chemistry* 2025;71(6):634-651) mandates limit-of-detection reporting, and a lab
writes *"Not Detected, < LOD"* rather than zero. The ceiling itself is a corollary of Steinke
et al. Thm 2.1. **Neither is ours** -- the transfer into a privacy artefact is."

---

## 3. ⭐⭐ The tamper demo — THE moment (90 s)

This is your best 90 seconds. Run it live.

```bash
.venv311\Scripts\python.exe -m synthproof.cli verify build\release\release.croissant.json --pubkey .keys\synthproof_ed25519.pub
```

→ `VERIFIED`, signature and all mirrored fields agree.

Now tamper with **only the human-visible epsilon**, leaving the signed payload untouched:

```bash
.venv311\Scripts\python.exe -c "import json;p='build/release/release.croissant.json';r=json.load(open(p));r['dp:epsilonProved']=0.01;json.dump(r,open(p,'w'),indent=2);print('epsilon display changed to 0.01')"
```

Verify again:

```bash
.venv311\Scripts\python.exe -m synthproof.cli verify build\release\release.croissant.json --pubkey .keys\synthproof_ed25519.pub
```

```
FAILED
SIGNATURE VALID, RECORD UNTRUSTWORTHY.
  dp:epsilonProved: record says 0.01, signed sheet says 0.9999580768688316
```

**Say:** "The signature is still perfectly valid. We didn't touch the signed bytes. We changed
the number a human reads — and a human is who gets fooled. We found this building it: a
signature over an embedded payload does not protect the layer above it. So we cross-check every
mirrored field, and refuse."

**Restore before the next demo:**

```bash
.venv311\Scripts\python.exe -m synthproof.cli run --rows 1200 --eps 1.0 --mechanism pairwise --sign --out build\release\sheet.json --synthetic-out build\release\release.csv --croissant build\release\release.croissant.json
```

---

## 4. External validation — MLCommons (45 s)

```bash
.venv311\Scripts\python.exe scripts\validate_croissant.py build\release\release.croissant.json
```

```
VALIDATED
  conformsTo  http://mlcommons.org/croissant/1.1
  warnings    0
```

**Say:** "That's not our checker. That's MLCommons' official validator — Croissant is what
NeurIPS requires datasets to ship with. Our DP release loads in standard tooling **and** carries
a signed privacy claim. Croissant has an ecosystem and no attestation; we had attestation and no
ecosystem. This is the join."

---

## 5. The ledger tamper (45 s)

In the console there's a **ledger tamper** button. Press it. The chain fails verification and
names the failure mode.

**Say:** "Hash chaining catches modification, insertion and reordering — but not truncation, because
a shortened chain is internally consistent. We found that in our own audit. The head now commits
to `(entry_count, tip_hash)`, so deleting the entries that record an overspend is detectable.
Nine attacks stopped, fourteen tests, each run against live SQLite."

---

## 6. Intellectual honesty — the pre-flight power analysis (45 s)

```bash
.venv311\Scripts\python.exe -m synthproof.cli audit-power --eps 7.36 --canaries 60
```

**Say:** "This answers, *before* you spend a day auditing, whether your audit could possibly
certify the epsilon you want. We built it because we ran that exact experiment and wasted the
run. Certifying ε costs canaries exponential in ε — ε = 7.36 needs about 4,700."

---

## 7. If they ask "what's new?" — the 30-second answer

> "Eight of our claims are dead. We killed them ourselves with an adversarial literature
> protocol — dual-sided assurance, privacy labels, release gating, all occupied, four of them by
> one group about two years ahead of us.
>
> What survives is integration. Dibia et al. 2025 got DP experts to agree on what a release
> should disclose — and proposed no signing, and no way to report the limits of an empirical
> privacy metric. One of their own experts called that omission *privacy theater*. We ship both,
> inside a record MLCommons validates.
>
> And our own pipeline leaked outside its epsilon until we audited it: the published run seed
> let anyone holding every other record rebuild a release and test membership — 15 of 15 exact
> matches. The boundary checker we built for that is what we would hand a regulator."

(Do **not** use the old "the benchmark measured clique selection" line: our own 175-fit
ablation retracted it. See `results/SELECTION_ABLATION.md`.)

**Volunteering the kills first is the strongest move available.** It proves the protocol was
real. Nobody can ambush you with a paper you already cited against yourself.

---

## Numbers you should have cold

| | |
|---|---|
| Tests / coverage | **1,082 tests**, coverage above the **94%** CI gate; CI green on Python 3.11-3.13 |
| Datasets | 11 benchmarks (Adult, ACSIncome, Bank, Diabetes 130, Texas, SF Fire and five UCI), 5 seeds, bootstrapped CIs |
| Mechanisms | 7, incl. **real AIM and MST** over private-PGM |
| H1 on Adult, eps 8 | AIM 0.0105 and pairwise 0.0283 both beat independent 0.0947; **AIM vs pairwise overlap** |
| Attacks | 5 per release, covering **all three EDPB risks**; **LiRA** offline: control AUC 1.0, no DP mechanism reliably attacked |
| Ledger | **9 attacks stopped**; head verifies across restarts; spends attributed per API key |
| Reproducibility | `make reproduce` passes, manifest pins 12 files |
| Croissant | MLCommons validator, **0 warnings** |

---

## If something breaks

| Problem | Do this |
|---|---|
| Port 8000 busy | `--port 8010`, open `127.0.0.1:8010` |
| Console blank | Hard-refresh (Ctrl+Shift+R). Endpoints still demo fine via CLI |
| API won't start | Skip it — **sections 1, 3, 4, 6 are pure CLI** and need no server |
| Everything breaks | `..\01_Thesis_and_Deliverables\SynthProof-Defence-Pack.pdf` — 28 pp, 45 Q&A, every headline number verified against `results/` at build. (The old cinematic deck in `..\archive\` predates the corrected numbers; do not show it.) |

**Nothing in sections 1, 3, 4 or 6 needs the API.** If the server dies mid-demo, keep going in
the terminal.

---

## Do not claim, under any questioning

- ❌ "We're the first to ship both bounds" — occupied, USENIX Sec 2024
- ❌ "We invented the privacy label" — Dibia et al. 2025
- ❌ "The audit ceiling is our finding" — corollary of Steinke et al. Thm 2.1
- ❌ "Canary auditing can't confirm tight bounds" — Ganev et al. Apr 2026 do exactly that with a
  Gaussian-DP estimator. Ours can't. Say *ours*
- ❌ "Our refusal gate is novel" — say **unrefuted**; the SDC Handbook was unreachable
- ❌ Any ratio of ε_audited to ε_proved — the comparison is retracted
- ❌ "AIM beats pairwise on Adult" — the intervals overlap since the D1 re-run
- ❌ "The benchmark measured clique selection" — retracted by our own ablation
- ❌ Anything read off the console's tradeoff curve — it is an illustrative model, not data

Every one of these is in `research/08_novelty_verdict.md` if pressed.
