.PHONY: help claims tables thesis install install-locked lock test lint format h1 h1-acs h2 h2-acs h3 h3-acs h2-analyse floor reproduce reproduce-all manifest figures demo serve data console console-build \
        console-install console-test security audit docker-build docker-up

help:
	@echo "SynthProof — commands"
	@echo ""
	@echo "  Python"
	@echo "    make install         Install the package with dev dependencies"
	@echo "    make install-locked  Install the EXACT versions behind the committed results"
	@echo "    make test            Run the test suite with coverage"
	@echo "    make lint            ruff + black checks (matches CI)"
	@echo "    make security        bandit SAST + pip-audit CVEs + npm audit"
	@echo "    make format          Format with black"
	@echo "    make data            Fetch UCI Adult and verify its SHA-256"
	@echo "    make h1              Run the H1 grid on UCI Adult (long)"
	@echo "    make h1-acs          Run the same grid on ACSIncome"
	@echo "    make floor           Measure the auditor's detection floor (long)"
	@echo "    make h2              Run the H2 subgroup-leakage study"
	@echo "    make h2-acs          Run the same subgroup study on ACSIncome"
	@echo "    make h3              Run the H3 allocation study on UCI Adult"
	@echo "    make h3-acs          Run the same allocation study on ACSIncome"
	@echo "    make h2-analyse      Re-analyse H2: FDR, equivalence, power"
	@echo "    make reproduce       Check results against the committed manifest"
	@echo "    make reproduce-all   Re-run every experiment, then check (very long)"
	@echo "    make figures         Regenerate every thesis figure from results/"
	@echo "    make demo            CLI end-to-end synthesis and audit"
	@echo "    make croissant       Emit a full release: CSV + signed sheet + Croissant record"
	@echo "    make croissant-validate  Check it with the official MLCommons validator"
	@echo ""
	@echo "  Console (needs Node 20+)"
	@echo "    make serve           Start the FastAPI service on :8000"
	@echo "    make console-install Install the console's npm dependencies"
	@echo "    make console         Start the console dev server on :5173"
	@echo "    make console-build   Build the console into synthproof/api/static"
	@echo "    make console-test    Run the console test suite (vitest)"
	@echo ""
	@echo "  For the live demo, run 'make serve' and 'make console' in two terminals."

install:
	pip install -e ".[dev]"

# The exact resolved dependency set the committed results were produced with. Use this, not
# `make install`, when the goal is to REPRODUCE rather than to develop.
install-locked:
	pip install -r requirements.lock
	pip install -e . --no-deps

lock:
	pip freeze --exclude-editable > requirements.lock

# Run ONE suite at a time. `mbi` enables a persistent JAX compilation cache and warns on
# every import that concurrent runs sharing that cache location are counterproductive;
# on 2026-08-23 two overlapping pytest processes crashed the interpreter outright
# (fatal error dump, no test summary). If you need the result, capture pytest's own exit
# code -- piping to `tail` returns tail's status and turns a crash into a silent pass.
test:
	python -m pytest

# Mirrors the CI job exactly, so a green local lint means a green pipeline.
lint:
	ruff check synthproof/ tests/ scripts/
	black --check synthproof/ tests/ scripts/

format:
	black synthproof/ tests/ scripts/

# The same scanners CI runs, so a finding shows up before the push rather than after.
security:
	@echo "== bandit (SAST) =="
	bandit -c pyproject.toml -r synthproof/ scripts/ -ll
	bandit -r tests/ -ll --skip B101
	@echo "== pip-audit (dependency CVEs) =="
	pip-audit --skip-editable --progress-spinner off
	@echo "== npm audit (console, production deps) =="
	cd web && npm audit --omit=dev --audit-level=moderate

# The task board's definition of done for M1.2 named this target; it now exists.
data:
	python -c "from synthproof.data.datasets import ADULT, fetch; \
	           print('verified ->', fetch(ADULT))"

# The H1 grid on UCI Adult -- the experiment the preregistration commits to. The toy
# sweep this replaces ran 100 independent rows and measured nothing.
h1:
	python -m scripts.run_h1

# The same protocol on ACSIncome. Same n, seeds, epsilon grid and structure column pair as
# Adult, so a difference between them is the data and not the protocol.
h1-acs:
	python -m scripts.run_h1 --dataset acs

# Measures what the auditor can actually see. Every eps_audited in this repo is
# uninterpretable without it.
floor:
	python -m scripts.run_detection_floor

# H2 -- per-subgroup leakage. Canaries are allocated EQUALLY across subgroups so rare
# groups get the same audit ceiling as common ones.
h2:
	python -m scripts.run_h2

# The same subgroup protocol on ACSIncome. NOTE: RAC1P has 9 levels against Adult's 5, so an
# equal split of the same fixed canary budget gives ACS a LOWER per-group ceiling (2.65 vs
# 3.27). That difference is reported, not corrected away.
h2-acs:
	python -m scripts.run_h2 --dataset acs

# H3 -- utility-weighted vs uniform budget allocation at fixed total epsilon. Weights are
# DECLARED public metadata, never measured from the table; deriving them from the data would
# be an uncharged query and would make every epsilon here a false statement.
h3:
	python -m scripts.run_h3

h3-acs:
	python -m scripts.run_h3 --dataset acs

# Re-analyses the committed H2 results with FDR control, TOST equivalence and a power
# statement. Reads results only -- runs no experiment.
h2-analyse:
	python -m scripts.analyse_h2

# Verify every published number against the committed manifest. `make reproduce-all` re-runs
# every experiment first; that is long, and it is what the thesis's reproducibility claim
# rests on.
reproduce:
	python -m scripts.reproduce

reproduce-all:
	python -m scripts.reproduce --run

manifest:
	python -m scripts.reproduce --update

# Every thesis figure, regenerated from the committed result files so a figure can never
# drift from the data behind it.
figures:
	python -m scripts.make_figures

# Fails if a chapter states one of the eight claims the novelty protocol killed.
# See docs/thesis/WRITING_NOTICE.md and research/08_novelty_verdict.md.
claims:
	python scripts/check_thesis_claims.py --all
	python scripts/check_citations.py

# Regenerates docs/thesis/ch07-tables.md from results/. Re-run after any experiment;
# a typed table drifts silently, a generated one cannot.
tables:
	python scripts/build_results_tables.py
	python scripts/build_implementation_evidence.py
	python scripts/build_argument_maps.py
	python scripts/build_api_reference.py

# Assembles ch01..ch08 into docs/thesis/THESIS.md and renders SynthProof-Thesis.pdf.
# The front matter carries a draft-status page naming every unwritten section, so an
# incomplete build cannot be mistaken for a finished one.
thesis:
	python scripts/build_thesis.py

demo:
	python -m synthproof.cli demo --rows 100 --eps 1.0

# A complete release: the synthetic table, the signed claim, and a Croissant record carrying
# it. Writes into build/release/ so it never collides with results/, which is under the
# reproducibility manifest.
croissant:
	python -m synthproof.cli keygen || true
	mkdir -p build/release
	python -m synthproof.cli run --rows 1200 --eps 1.0 --mechanism pairwise --sign --out build/release/sheet.json --synthetic-out build/release/release.csv --croissant build/release/release.croissant.json
	python -m synthproof.cli verify build/release/release.croissant.json --pubkey .keys/synthproof_ed25519.pub

# Conformance against the OFFICIAL MLCommons validator, in an isolated venv. Separate because
# mlcroissant pins a numpy that breaks jax/mbi/private-PGM and therefore real AIM. Exits 2 --
# not 0 -- when the env is absent, so an unrun check never looks like a passed one.
croissant-validate-setup:
	python scripts/validate_croissant.py --setup

croissant-validate:
	python scripts/validate_croissant.py build/release/release.croissant.json

serve:
	uvicorn synthproof.api.main:app --reload --host 0.0.0.0 --port 8000

console-install:
	cd web && npm install

console:
	cd web && npm run dev

console-build:
	cd web && npm run build

# The console's own test suite. Targets the hand-rolled SSE parser in src/lib/api.ts, which
# is the riskiest frontend code: a frame can straddle two network chunks, and mis-buffering
# drops pipeline stages silently rather than erroring.
console-test:
	cd web && npm test

docker-build:
	docker build -t synthproof:latest .

docker-up:
	docker-compose up --build
