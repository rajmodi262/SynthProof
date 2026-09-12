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
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY synthproof/ /app/synthproof/

RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# ---------------------------------------------------------------- stage 3: the runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels synthproof \
    && rm -rf /wheels

COPY synthproof/ /app/synthproof/
COPY scripts/ /app/scripts/

# The console, built in stage 1. Without this the container has an API and no UI.
COPY --from=console /synthproof/api/console /app/synthproof/api/console

# Run as a non-root user. The ledger volume is mounted at /app/.synthproof and must be
# writable by that user, so it is created and chowned before the drop.
RUN useradd --create-home --uid 10001 synthproof \
    && mkdir -p /app/.synthproof \
    && chown -R synthproof:synthproof /app
USER synthproof

EXPOSE 8000

# NOTE: real AIM is NOT available in this image. private-pgm (`mbi`) installs from git and is
# not in the dependency set, so the AIM mechanism is unregistered here and the console offers
# only `independent` and `pairwise`. This is the same gap that hid real AIM from CI until
# 2026-09-12. It is stated rather than silently tolerated; installing it requires a git
# dependency in the image, which is a deliberate decision, not a default.
CMD ["uvicorn", "synthproof.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
