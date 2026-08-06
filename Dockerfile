# Multi-stage Dockerfile for SynthProof API & Platform
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project definition
COPY pyproject.toml README.md /app/
COPY synthproof/ /app/synthproof/
COPY scripts/ /app/scripts/

# Install synthproof package
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "synthproof.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
