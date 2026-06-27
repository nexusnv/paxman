"""Shared test fixtures for saas_procurement tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from saas_procurement import run_pipeline

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MANIFEST_PATH = _DATA_DIR / "manifest.csv"


@pytest.fixture()
def sample_manifest_path() -> Path:
    """Path to the sample manifest CSV."""
    return MANIFEST_PATH


@pytest.fixture()
def tmp_output_dir(tmp_path: Path) -> Path:
    """A temporary output directory for pipeline runs."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture()
def sample_artifact_dict(sample_manifest_path: Path, tmp_path: Path) -> dict:
    """Run the pipeline once and return the invoice_acme artifact as a dict.

    This fixture is useful for tests that need a pre-computed artifact
    without re-running the full pipeline.
    """
    import json

    output_dir = tmp_path / "artifact_output"
    output_dir.mkdir()
    run_pipeline(sample_manifest_path, output_dir)
    artifact_path = output_dir / "invoice_acme.json"
    return json.loads(artifact_path.read_text(encoding="utf-8"))
