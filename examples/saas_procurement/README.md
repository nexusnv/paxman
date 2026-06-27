# saas-procurement

CSV-batch invoice/quotation pipeline for SaaS procurement.

## Problem statement

I'm a SaaS team building procurement pipelines. I have a folder of raw
invoice files (PDF text dumps, email bodies, etc.) and a CSV manifest
listing which file goes to which contract. I want to normalize them in
batch, write artifacts to disk, and verify cross-run replay-hash
reproducibility.

## Install

```bash
cd examples/saas_procurement
uv venv
uv pip install -e ".[dev]"
```

If `paxman` is not yet published to PyPI, install the parent project
first:

```bash
uv pip install -e ../..
```

## Run

```bash
uv run python -m saas_procurement data/manifest.csv output/
```

## Test

```bash
uv run pytest tests/ -v
```

Includes the D10.7 cross-run replay_hash reproducibility test.

## Expected output

After a successful run the `output/` directory contains:

- `invoice_acme.json` — an ExecutionArtifact
- `invoice_globex.json` — an ExecutionArtifact
- `quotation_initech.json` — an ExecutionArtifact
- `run_summary.json` — batch run summary

## What this example demonstrates

- **CSV manifest parsing** — a simple `id,input_file,contract_name`
  manifest drives batch processing.
- **Batch normalize** — each manifest row is normalised via
  `paxman.normalize()` against a Pydantic contract.
- **On-disk artifact storage** — artifacts are written as
  JSON-serialised dicts.
- **Replay-hash determinism** — two independent runs on the same
  manifest produce byte-equal `replay_hash` values.

## The D10.7 fixture

This example's output is the D10.7 `replay_hash` reproducibility
fixture (per `docs/sprints/sprint-10-release.md` D10.19 + D10.7). The
`test_replay_hash.py` test verifies the artifact's `replay_hash` is
byte-equal across two independent runs.
