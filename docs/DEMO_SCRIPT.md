# Demo script — 8 minutes, five commands

Every command here was run end to end and produces the output shown. Print this page and keep
it in front of you.

> **Executed end to end on 2026-09-13**, all six steps including the tamper, on Windows /
> Python 3.11. The outputs below are copied from that run. Two things it caught: the `demo/`
> folder this script depends on **did not exist in the repository**, so the rehearsed path
> could not be rehearsed; and a JAX warning printed on every command, immediately above the
> output the audience is meant to read. Both fixed.

**Before you start**

```bash
cd SynthProof
python -m scripts.setup_demo               # builds demo/ok.csv and demo/patients.csv
export SYNTHPROOF_KEY_DIR=demo/keys        # Windows: set SYNTHPROOF_KEY_DIR=demo\keys
python -m synthproof.cli keygen --key-dir demo/keys
```

`setup_demo.py` writes the two CSVs this script uses, deterministically (fixed seeds):

* `ok.csv` — 3,000 rows of real UCI Adult (a normal table)
* `patients.csv` — 2,000 synthetic rows with an `mrn` identifier column, an age, and a
  diagnosis that depends on age, so there is real structure to preserve

**This runs with the network off**, once UCI Adult is in the local cache. Nothing in the five
steps reaches the internet: every command reads a local CSV. Build `demo/` while you still
have wifi, then unplug and rehearse.

The through-line of the whole demo, and the sentence to open with:

> "Most synthetic data tools accept your file and give you something back. Ours is about
> whether the privacy claim on that output is actually true — so a lot of what you're about to
> see is the system refusing to overclaim."

---

## Step 1 — a normal release (90 seconds)

```bash
python -m synthproof.cli run --input demo/ok.csv --out demo/sheet.json --eps 1.0
```

Output ends with:

```
Requested eps=1.000  ->  proved eps=0.912  (ratio 0.912; calibration never overspends)

  An adversary who already knows every other record can improve a guess about whether any
  one person is in this dataset from 50 in 100 to at most 71 in 100 (epsilon = 0.91).
  NOTE: domain_source=inferred-nonprivate. The bounds and category domains here were read
  from your data and were not charged.
```

**Say:**

> "Two things. First, we asked for epsilon 1 and delivered 0.91 — the calibration never
> overspends, which sounds obvious but an earlier version of this asked for 8 and quietly
> delivered 70.
>
> Second, epsilon is not interpretable to anyone outside this field, so we print what it
> means: an adversary's guess goes from 50-in-100 to at most 71-in-100. That framing is from a
> USENIX Security 2023 study with 963 participants — odds beat every other way of explaining
> it.
>
> And the last line is the system telling on itself. We didn't give it a schema, so it read
> the column ranges out of the data — which leaks. It says so on every run."

---

## Step 2 — the same thing at a loose budget (60 seconds)

```bash
python -m synthproof.cli run --input demo/ok.csv --out demo/s8.json --eps 8.0
```

```
  ... from 50 in 100 to at most 100 in 100 (epsilon = 7.36).
  NOTE: the audit ceiling at 30 canaries is 2.25, below the proved eps of 7.36. An audited
  eps of 0.00 means the auditor COULD NOT have detected this budget -- not that nothing leaked.
```

**Say:**

> "At epsilon 8 the honest statement is 100-in-100. That's what epsilon 8 buys you, and most
> papers use it without saying that.
>
> The second line is our main methodological point. Empirical privacy auditing has a ceiling —
> with 30 canaries the most you can ever certify is about 2.25. So an audited epsilon of zero
> next to a proved epsilon of 7.36 means *the instrument couldn't see it*, not that nothing
> leaked. We report the ceiling next to the number so nobody can read it the wrong way. This
> disqualifies our own headline comparison, and we say so in the thesis."

---

## Step 3 — the refusal (90 seconds) ← **the most important step**

```bash
python -m synthproof.cli run --input demo/patients.csv --out demo/x.json --eps 1.0
```

```
R2 REFUSE [mrn]: Declared domain has 2000 levels over 2000 rows (100% of the table). A column
with roughly one level per record is a direct identifier; releasing its domain releases the
individuals.
    -> Drop 'mrn', or replace it with a coarser public grouping.
```

**Say:**

> "This is a patient table with a medical record number. It's refused, with the column named
> and a remedy.
>
> This matters because it used to succeed. We measured it: real MRNs came out verbatim in the
> synthetic output — six of two thousand at epsilon 1, thirteen at epsilon 8. The 'synthetic'
> data contained real patient identifiers.
>
> The check reads only the declared schema and the row count — never the data. A check that
> reads the data to decide whether the data is safe would be the exact defect it's meant to
> prevent."

If asked *"so I can't upload any database?"* — **say no, clearly**:

> "No. Single table, no multi-table, and it refuses identifier columns, free text, tables under
> 500 rows, and tables with no categorical target. Understanding an unknown table is itself a
> query against sensitive data — you either declare the schema, use a public code book, or pay
> epsilon for it. SmartNoise and Tumult require the same thing for the same reason."

---

## Step 4 — sign it, then verify it (90 seconds)

```bash
python -m synthproof.cli run --input demo/ok.csv --out demo/signed.json --eps 1.0 --sign
python -m synthproof.cli verify demo/signed.json --pubkey demo/keys/synthproof_ed25519.pub
```

```
VERIFIED
  dataset      ok  (3000 rows)
  eps proved   0.9122542470732562
  ledger head  e33781a44586ee8d...

This proves the sheet came from the holder of that key and is unaltered.
It does not prove the numbers in it are correct.
```

**Say:**

> "A third party with just this file and our public key can check it. Note the last line — we
> refuse to claim more than the signature gives you. It proves origin and integrity. It does
> not prove the numbers are right, because whoever holds the key can sign anything."

---

## Step 5 — break it (60 seconds) ← **the one they remember**

Edit `demo/signed.json` in any text editor. Change `total_proved_eps` from `0.912` to `0.01` —
a lie in your favour. Save. Then:

```bash
python -m synthproof.cli verify demo/signed.json --pubkey demo/keys/synthproof_ed25519.pub
```

```
FAILED
Signature does not verify. Either the sheet was altered after signing, or it was not signed
by this key.
```

**Say:**

> "I just claimed a hundred times better privacy than we delivered, and it's caught.
>
> The same applies to the ledger. Editing an entry is detected, and so is deleting the last
> few — which is the interesting case, because hash chaining alone does *not* catch truncation.
> A shortened chain is still internally consistent, so an operator could delete the entries
> recording a budget overspend and still pass. We found that by attacking our own ledger, and
> fixed it with a signed head that commits to the chain's length."

---

## Close (30 seconds)

```bash
make reproduce
```

```
REPRODUCED: every result file matches the committed manifest.
```

> "Every number in the thesis regenerates from a committed manifest at a fixed seed."

---

## If something breaks

* **Any command errors** — you have `demo/sheet.json` and `demo/signed.json` from the dry run.
  Open them and talk through the fields. The data sheet *is* the artefact.
* **Wrong Python** — use `.venv311/Scripts/python.exe -m synthproof.cli ...` explicitly. The
  project needs 3.11; a bare `python` may be 3.10.
* **`verify` says FAILED when it should pass** — you tampered the file in step 5 and didn't
  regenerate it. Re-run the `--sign` command.
* **You lose the thread** — go back to the one sentence: *this project is about whether the
  privacy claim is true, and most of what it does is refuse to overclaim.*

---

## The three questions you will be asked

**"What's actually new here?"**

> "The integration is engineering — DP synthesis and one-run auditing both exist. Our
> contribution is two negative results about the measurement instruments: the audit ceiling,
> which disqualifies the proved-vs-audited comparison at these budgets, and evidence that the
> structure metric's choice of column pair changes which mechanism looks best."

**"Your hypotheses mostly returned nulls. Isn't that a failure?"**

> "All three were registered in git before any result existed, and every deviation is declared
> in a table in Chapter 6. H1 held on Adult and did not transfer to our second dataset. H2 and
> H3 are nulls on both. We report the ceiling alongside each null so you can tell a bounded
> effect from an absence of evidence — that distinction is the point of the project."

**"Can this be used on real hospital data?"**

> "No, and the README says so. No cross-session budget enforcement, authentication is a single
> shared key rather than real identity, single-table only. What it is, is an honest instrument
> for checking whether a DP release delivers the epsilon it claims."

---

### Measurement convention — the ceiling is borrowed, and attributed

The audit ceiling reported beside every ε_audited is `log(r / ln(1/α))`, a one-line corollary
of Steinke, Nasr & Jagielski (NeurIPS 2023, arXiv:2305.08846) Thm 2.1 — **not a result of
ours** — and the same quantity is already named *maximum auditable epsilon* by Annamalai,
Ganev & De Cristofaro (USENIX Sec 2024, arXiv:2405.10994) §2.2.

Reporting it alongside the measurement is a transfer of **limit-of-detection (LoD) reporting**
from analytical chemistry, where **MIQE 2.0** (Bustin et al., *Clinical Chemistry*
2025;71(6):634–651) mandates LoD/LLOQ disclosure and a laboratory reports *"Not Detected,
< LOD"* rather than zero. The transfer is the claim; the convention is not our invention.

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](MEASUREMENT_CONVENTIONS.md).

---

## If it breaks in the room — the fallback ladder

Rehearsed 2026-09-13. Work **down** this ladder; each rung needs strictly less than the one
above it. Do not debug in front of a panel — drop a rung and keep talking.

| # | If this fails… | Fall back to | Needs |
|---|---|---|---|
| 1 | The five CLI commands above | The **web console** — `START_PROTOTYPE.bat`, HR preset (600 rows, ~4 s) | Python env + browser |
| 2 | The backend will not start | The **offline capsule** — `OPEN_OFFLINE_CAPSULE.bat` | **A browser. Nothing else** |
| 3 | The capsule will not open | The **standalone pitch deck** — `02_Presentations_and_Pitches/SynthProof-Pitch.html`, verified self-contained with **no external references** | A browser |
| 4 | Nothing runs at all | This document plus `results/RESULTS.md`, read aloud from the printed copy | Paper |

**Rung 2 is the one to trust.** The capsule is a single HTML file that recomputes SHA-256
digests and checks an Ed25519 signature in the browser via WebCrypto, with no server, no
network and no Python. It is also the best artefact in the project, so falling to it is not a
downgrade — consider opening with it.

Three things that actually go wrong, and what to do:

- **No network.** Nothing in the five steps needs it, but `scripts/setup_demo.py` downloads
  UCI Adult on a cold cache. **Build `demo/` before you travel**, then verify with the wifi
  off.
- **The 400-row preset "fails".** It does not — it *refuses*, by design, and that is the S3
  contribution. Say so before someone else reads it as a crash. The CLI exits 1 on a refusal,
  which is correct, and a shell that stops on errors will halt there.
- **The smallest table is the slowest.** A toy table with independent columns is the worst
  case, because the attack suite finds nothing and works hardest doing it. A UI run against
  one was still going after nine minutes. Use the 600-row HR preset for anything timed.

### Rehearse it like this

```bash
cd SynthProof
python -m scripts.setup_demo        # while you still have wifi
# ... turn the wifi off, then run all five steps and the tamper
```

The tamper step is the one to have done with your own hands at least once: edit
`total_proved_eps` in `demo/signed.json` to `0.01`, re-run `verify`, and watch it print
`FAILED` and exit 1.
