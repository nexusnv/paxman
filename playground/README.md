# Paxman Jupyter Lab Playground in Docker Container

> **Issue:** [#90](https://github.com/nexusnv/paxman/issues/90)

This directory contains a containerized **Jupyter Lab** playground for exploring Paxman interactively. The playground builds Paxman from source so the notebooks always match the working tree of the repository.

## Prerequisites

- **Docker** (recommended), or
- **Python 3.12 + `uv`** (host fallback, no Docker required)

## Build and run (Docker)

```bash
# From the repo root
make playground-build   # Build the Docker image (~2 min first time)
make playground-up      # Start the container (http://127.0.0.1:8888)
make playground-logs    # See the token to paste in the browser
```

Open `http://127.0.0.1:8888` and enter the token shown in the logs (default: `paxman-dev`).

To stop: `make playground-down`

## Build and run (host fallback, no Docker)

```bash
uv sync --project playground
uv run --project playground jupyter lab --ip=127.0.0.1 --port=8888 --no-browser --notebook-dir=playground/notebooks
```

## Notebooks

| # | Notebook | What you'll learn |
|---|---|---|
| 00 | Welcome | Navigation, version check |
| 01 | Basics + Contracts | Pydantic, JSON Schema, Dict DSL, OpenAPI |
| 02 | text_extraction | Free-text field extraction |
| 03 | regex_extraction | Pattern-based extraction |
| 04 | lookup | ID/code-based lookup, custom capabilities |
| 05 | inference | AI-powered inference (V1 stub) |
| 06 | validation | Constraint checking |
| 07 | Replay | Deterministic replay hash, `paxman.replay()` |
| 08 | Money and Decimal | First-class MONEY support |
| 09 | Full Pipeline | End-to-end invoice normalization |
| 10 | Budget and Policy | Cost control, PII protection |

## Adding a notebook

1. Name it `NN-topic-name.ipynb` (e.g., `11-capability-csv-extraction.ipynb`).
2. Follow the template: problem statement → imports → contract → sample input → normalize → inspect results → try-it-yourself.
3. Run the smoke test to catch internal-import leaks.
4. Open a PR.

**Important:** Keep notebooks 100% deterministic — no `datetime.now()`, no `random.*` without a seeded generator. Use `Decimal` for money literals.

## Troubleshooting

| Problem | Solution |
|---|---|
| Port 8888 in use | `JUPYTER_PORT=8889 make playground-up` |
| Outdated Paxman | `make playground-build && make playground-down && make playground-up` |
| Docker not running | Use the host fallback |
| Browser won't open | Check `make playground-logs` for the token |
| Image too large | First build pulls many deps; subsequent builds are incremental |

## Limitations

- **Single-user only** — loopback-bound by default. Not a multi-user JupyterHub.
- **V1 `inference` is a stub** (notebook 05). Real LLM-backed inference lands in V2 (issues [#50](https://github.com/nexusnv/paxman/issues/50), [#51](https://github.com/nexusnv/paxman/issues/51)).
- **Not a CI environment** — the playground is excluded from `make ci`.
- **Format extractor notebooks** (json_path, csv, xpath) are a separate follow-up.
