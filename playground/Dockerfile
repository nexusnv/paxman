# syntax=docker/dockerfile:1.7

# --- Stage 1: build paxman from source -----------------------------
FROM python:3.12-slim AS builder
WORKDIR /paxman-src

# Pin the uv base to a specific release tag (builds are reproducible
# even with --frozen lockfile resolution). Bump on intentional upgrades.
COPY --from=ghcr.io/astral-sh/uv:0.5.10 /uv /usr/local/bin/uv

# Copy only what uv needs first (cache-friendly layer)
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Build a venv at /opt/paxman-venv with all extras (so notebooks can use
# pydantic, jsonschema, openapi, defusedxml).
RUN uv sync --frozen --all-extras --python 3.12
RUN mv .venv /opt/paxman-venv

# Install JupyterLab using playground/pyproject.toml as the single
# source of truth for the version range. Excludes the dev group so
# pytest and friends stay out of the runtime image.
COPY playground/pyproject.toml playground/uv.lock /pg/
RUN uv export --frozen --no-hashes --no-group dev --project /pg \
    | uv pip install --python /opt/paxman-venv/bin/python -r -

# --- Stage 2: runtime with Jupyter Lab ----------------------------
FROM python:3.12-slim

# Create non-root user (Jupyter convention). WORKDIR is set after
# user creation so the home dir is owned by jovyan, not root.
RUN useradd -m -s /bin/bash jovyan

# Copy the built venv to the same absolute path so shebangs remain valid
COPY --from=builder --chown=jovyan:jovyan /opt/paxman-venv /opt/paxman-venv
COPY --chown=jovyan:jovyan playground /home/jovyan/playground

USER jovyan
WORKDIR /home/jovyan

# Put venv on PATH (consistent absolute path preserves shebangs)
ENV PATH="/opt/paxman-venv/bin:${PATH}"
ENV JUPYTER_PORT=8888

EXPOSE 8888

CMD ["sh", "-c", "exec jupyter lab \
     --ip=0.0.0.0 \
     --port=${JUPYTER_PORT} \
     --no-browser \
     --notebook-dir=/home/jovyan/playground/notebooks"]
