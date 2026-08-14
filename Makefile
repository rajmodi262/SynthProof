.PHONY: help install test lint format h1 demo serve data console console-build \
        console-install security audit docker-build docker-up

help:
	@echo "SynthProof — commands"
	@echo ""
	@echo "  Python"
	@echo "    make install         Install the package with dev dependencies"
	@echo "    make test            Run the test suite with coverage"
	@echo "    make lint            ruff + black checks (matches CI)"
	@echo "    make security        bandit SAST + pip-audit CVEs + npm audit"
	@echo "    make format          Format with black"
	@echo "    make data            Fetch UCI Adult and verify its SHA-256"
	@echo "    make h1              Run the H1 grid on UCI Adult (long)"
	@echo "    make demo            CLI end-to-end synthesis and audit"
	@echo ""
	@echo "  Console (needs Node 20+)"
	@echo "    make serve           Start the FastAPI service on :8000"
	@echo "    make console-install Install the console's npm dependencies"
	@echo "    make console         Start the console dev server on :5173"
	@echo "    make console-build   Build the console into synthproof/api/static"
	@echo ""
	@echo "  For the live demo, run 'make serve' and 'make console' in two terminals."

install:
	pip install -e ".[dev]"

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

docker-build:
	docker build -t synthproof:latest .

docker-up:
	docker-compose up --build
