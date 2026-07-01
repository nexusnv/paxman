# syntax=docker/dockerfile:1.7

# --- Stage 1: build paxman from source -----------------------------
FROM python:3.12-slim AS builder
WORKDIR /paxman-src

# Install uv (matches repo convention)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only what uv needs first (cache-friendly layer)
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Build a venv at /paxman-venv with all extras (so notebooks can use
# pydantic, jsonschema, openapi, defusedxml).
RUN uv sync --frozen --all-extras --python 3.12
# Move the venv to a stable absolute path for the runtime stage
RUN mv .venv /paxman-venv
# Install jupyterlab into the same venv so the runtime stage is one venv
RUN uv pip install --python /paxman-venv/bin/python "jupyterlab>=4.3,<5"

# --- Stage 2: runtime with Jupyter Lab ----------------------------
FROM python:3.12-slim
WORKDIR /home/jovyan

# Create non-root user (Jupyter convention)
RUN useradd -m -s /bin/bash jovyan
USER jovyan

# Copy the built venv and playground contents
COPY --from=builder --chown=jovyan:jovyan /paxman-venv /home/jovyan/.venv
COPY --chown=jovyan:jovyan playground /home/jovyan/playground

# Put venv on PATH
ENV PATH="/home/jovyan/.venv/bin:${PATH}"
ENV JUPYTER_PORT=8888

EXPOSE 8888

CMD ["jupyter", "lab", \
     "--ip=0.0.0.0", \
     "--port=8888", \
     "--no-browser", \
     "--notebook-dir=/home/jovyan/playground/notebooks"]
