# SynthProof API + console, built from source in three stages.
#
# The previous version declared `as builder` and then had no second stage, so it was
# single-stage despite the comment: `build-essential` -- a full compiler toolchain -- shipped
# in the final image. More seriously, it never built the web console. The console is a build
# artefact and is gitignored, so on a clean clone the image served an API with no UI at all,
# while the README promised a stranger could clone, follow it, and reach a working demo.

# ---------------------------------------------------------------- stage 1: the web console
# Built inside the image from web/ sources rather than copied from the host, so the result
# does not depend on whether whoever ran `docker build` happened to have run `npm run build`.
FROM node:20-slim AS console

WORKDIR /web

# Dependencies first, so a source-only change does not reinstall them.
COPY web/package.json web/package-lock.json* /web/
RUN npm ci --no-audit --no-fund

COPY web/ /web/
# vite writes to ../synthproof/api/console, so that path must exist relative to /web.
RUN mkdir -p /synthproof/api/console && npm run build

# ---------------------------------------------------------------- stage 2: python wheels
# build-essential lives here and is discarded with the stage, rather than shipping.
FROM python:3.11-slim AS wheels

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md requirements.lock /app/
COPY synthproof/ /app/synthproof/

# requirements.lock is applied as a CONSTRAINTS file: every runtime dependency resolves to the
# exact version the committed results were produced with, while the lock's dev-only tools
# (pytest, black, bandit ...) are not pulled into the image. Without it the image resolved
# pyproject's open ranges and could drift from the published numbers on any rebuild.
# `mbi` is a git URL, which a constraints file cannot carry; it is pinned by commit below.
RUN grep -v '^mbi ' requirements.lock > /tmp/constraints.txt \
    && pip wheel --no-cache-dir --wheel-dir /wheels -c /tmp/constraints.txt .

# private-PGM (`mbi`) has no PyPI release, so it is built from git -- pinned to the commit
# requirements.lock records, the one every committed AIM/MST result was produced with. Without
# it AIM, MST and fixed_workload are unregistered and the image cannot run the headline mechanism.
ARG MBI_COMMIT=78df3419f271ac2c1fa7929aa7adc910a583084f
RUN pip wheel --no-cache-dir --wheel-dir /wheels -c /tmp/constraints.txt \
    "mbi @ git+https://github.com/ryan112358/private-pgm.git@${MBI_COMMIT}"

# ---------------------------------------------------------------- stage 3: the runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels synthproof mbi \
    && rm -rf /wheels

COPY synthproof/ /app/synthproof/
COPY scripts/ /app/scripts/
# The console's demo presets read these. Without them every preset silently ran the toy table.
COPY demo_datasets/ /app/demo_datasets/
COPY results/gdp/ /app/results/gdp/

# The console, built in stage 1. Without this the container has an API and no UI.
COPY --from=console /synthproof/api/console /app/synthproof/api/console

# Run as a non-root user. The ledger volume is mounted at /app/.synthproof and must be
# writable by that user, so it is created and chowned before the drop.
RUN useradd --create-home --uid 10001 synthproof \
    && mkdir -p /app/.synthproof \
    && chown -R synthproof:synthproof /app
USER synthproof

EXPOSE 8000

# Library caches go to /tmp, so the container runs with a read-only root filesystem
# (`docker run --read-only --tmpfs /tmp`, exercised in CI): the only other writable path is the
# ledger volume.
ENV PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    XDG_CACHE_HOME=/tmp/.cache \
    SYNTHPROOF_TRUSTED_NETWORK=private

# SYNTHPROOF_TRUSTED_NETWORK=private: with no API key, the service answers only loopback and
# private (RFC 1918) addresses -- the host reaches a container over a Docker bridge -- and refuses
# the internet. Set SYNTHPROOF_API_KEY(S) to serve anyone else (synthproof/api/security.py).

# Liveness for Docker and Compose. Standard library only -- the slim image has no curl.
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=4 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"]

# All seven mechanisms are available, AIM, MST and fixed_workload included: private-PGM is
# built in stage 2 from the commit requirements.lock pins.
CMD ["uvicorn", "synthproof.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
