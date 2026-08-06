.PHONY: help install test lint format sweep demo serve docker-build docker-up

help:
	@echo "SynthProof Makefile Commands:"
	@echo "  make install      Install project in editable mode with dev dependencies"
	@echo "  make test         Run pytest unit and property test suite"
	@echo "  make lint         Run ruff and mypy code quality checks"
	@echo "  make format       Format code using black"
	@echo "  make sweep        Run experimental sweeps and update results/RESULTS.md"
	@echo "  make demo         Run CLI end-to-end synthesis and audit demo"
	@echo "  make serve        Start FastAPI backend service & Web Console"
	@echo "  make docker-up    Start Docker Compose services"

install:
	pip install -e ".[dev]"

test:
	python -m pytest

lint:
	ruff check synthproof/
	black --check synthproof/

format:
	black synthproof/ tests/ scripts/

sweep:
	python -m scripts.run_sweep

demo:
	python -m synthproof.cli demo --rows 100 --eps 1.0

serve:
	uvicorn synthproof.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t synthproof:latest .

docker-up:
	docker-compose up --build
