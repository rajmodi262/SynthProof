# Paste this into the NEW Claude account's first message

(Open the session in `D:\03_Study\CAPSTONE\SynthProof`. Copy everything between the lines.)

---

You are taking over an in-progress B.Tech capstone project called **SynthProof**. Before doing ANY
work, fully onboard yourself by scanning the project. Do not write code, change files, or answer
substantive questions until you have finished the scan and given me the summary at the end.

**Step 1 — Read the two handoff files first, in full:**
1. `HANDOFF_FULL_MEMORY.md` (repo root) — the structured memory: what the project is, the honesty
   rules, findings with verified numbers, git state, the two publishable directions, the paper
   status, traps, and next steps.
2. `ACTIVITY_LOG_FULL.md` (repo root) — the complete chronological action log (~11,800 events across
   26 days). Skim it, and grep it whenever you need the exact command or moment something was done.

**Step 2 — Read the project's own guidance and honesty rules:**
- `CLAUDE.md` (the running research context and the standing honesty rules).
- `research/08_novelty_verdict.md` (the canonical novelty verdict: "integration, not invention").
- `docs/design/PUBLIC_RELEASE_BOUNDARY.md` (the release-boundary spec, findings D1–D5).
- `research/11_pivot_scout_2026-09-03.md`, `research/11_selection_accounting.md`, and
  `research/12_boundary_prior_art.md`, `research/15_standards_gap_analysis.md`,
  `research/16_real_dp_release_case_study.md`, `research/imputation_audit/` (K3_FINDINGS.md,
  PREREGISTRATION.md, RESULTS.md), `research/accountant_crosscheck/README.md`.

**Step 3 — Scan the actual project (run these and read what matters):**
- Repo layout: list `synthproof/`, `synthproof/audit/`, `synthproof/generators/`,
  `synthproof/accounting/`, `synthproof/frontier/`, `synthproof/ledger/`, `synthproof/data/`,
  `synthproof/api/`, `tests/`, `scripts/`, `results/`, `research/`, `docs/`, `web/`, `paper/`.
- Git: run `git rev-parse --abbrev-ref HEAD`, `git log --oneline -15`, and `git status --short`.
  Note that a LOT of work is UNCOMMITTED on branch `fix/selection-accounting` (base master
  `ab0107e`) — the boundary auditor, the cross-check fix, the imputation modules, the whole web
  redesign, the paper, and research docs live only in the working tree.
- Read the key source files: `synthproof/audit/boundary.py` (the boundary-audit tool),
  `synthproof/accounting/differential.py` (the second-accountant cross-check),
  `synthproof/frontier/certificate.py` (the Privacy Data Sheet), `synthproof/data/imputation.py` and
  `missingness.py`, and skim the generators (`aim.py`, `independent.py`, `dpvae.py`).
- Read `paper/synthproof_ieee.tex` (the IEEE paper) and `SynthProof_Synopsis_Level2_FILLED.docx`
  location if present.
- Environment: the Python venv is `.venv311\Scripts\python.exe` (Python 3.11). Quality gates are
  `ruff check`, `black --check`, `mypy synthproof`, `python scripts/check_thesis_claims.py --all`,
  `python scripts/check_citations.py`; tests via `python -m pytest -q`; web via `cd web && npm run
  build`. There is also a top-level folder `..\Antigravity_Prompts\` with agent handoff briefs.

**Non-negotiable rules you inherit (from the honesty protocol):**
- Never fabricate a number or a citation. Every citation must be fetched/verified before use; mark
  anything unverified as `[UNVERIFIED]`. Copy numbers from files, never invent them.
- Prefix reasoning with `INFERENCE:` and uncertainty with `CONFIDENCE: low/med/high + why`.
- Be adversarial: try to kill claims before accepting them. Assistant output (including any prior
  agent's) has fabricated citations and one invalid measurement before — always verify.
- **Do NOT mention AI anywhere in the paper or the synopsis**, and do not add an AI-disclosure line.
- Operational: the AIM mechanism uses ~9 GB of virtual memory per run — run only ONE AIM process at
  a time on a 16 GB machine. Heavy re-runs go in an isolated git worktree.
- `dropna` (complete-case deletion) is NOT a DP bug — never claim it is. The clique-selection
  confound is RETRACTED — do not build on it.

**Step 4 — Report back before doing anything else.** After the scan, give me:
(a) a 10-line summary of what the project is and its current state;
(b) the two publishable directions and their status;
(c) the list of uncommitted work and anything that looks at risk;
(d) any discrepancies you found between the handoff and the actual files (trust the files, flag the
    gap);
(e) then ask me what I want to work on. Do not start work until I answer.

---
