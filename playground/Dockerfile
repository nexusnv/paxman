# Playground Dockerfile — boots a JupyterLab with Paxman installed editable.
#
# Build context is the REPO ROOT (see playground/docker-compose.yml `build.context`),
# so the entire paxman source tree is available to COPY in. This Dockerfile itself
# lives in playground/ for discoverability.
FROM quay.io/jupyter/scipy-notebook:python-3.11

# Disable the upstream notebook idle-cull / first-run noise we don't need for a
# local playground; keep the base image's jovyan user and toolchain intact.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PAXMAN_PLAYGROUND=1

# Bring in the project (pyproject.toml, src/, uv.lock, README, quickstart).
# Editable install so the playground always reflects the source it was built from.
WORKDIR /opt/paxman
COPY pyproject.toml uv.lock* ./
COPY src ./src
COPY README.md quickstart.py ./

# Install runtime deps (attrs) + paxman editable. We deliberately do NOT pull the
# full dev/test extra groups — this is a learning environment, not a CI runner.
RUN pip install --no-cache-dir -e . && \
    python -c "import paxman; print('paxman', paxman.__version__, 'importable')"

# Notebooks are bind-mounted at runtime (see compose) into the jovyan home so
# edits are live and persist on the host. Default there for `docker compose up`.
WORKDIR /home/jovyan/playground
