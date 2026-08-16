.PHONY: help install install-locked lock test lint format h1 h1-acs h2 h2-acs h3 h3-acs h2-analyse floor reproduce reproduce-all manifest figures demo serve data console console-build \
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

demo:
	python -m synthproof.cli demo --rows 100 --eps 1.0

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
