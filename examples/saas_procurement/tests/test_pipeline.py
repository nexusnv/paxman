"""Tests for the batch pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from saas_procurement import run_pipeline


class TestPipeline:
    """Tests for :func:`run_pipeline`."""

    def test_pipeline_runs(
        self,
        sample_manifest_path: Path,
        tmp_output_dir: Path,
    ) -> None:
        """Running the pipeline produces 3 artifact JSON files."""
        summary = run_pipeline(sample_manifest_path, tmp_output_dir)
        assert summary.total_rows == 3
        # At least one artifact should be written per row.
        json_files = list(tmp_output_dir.glob("*.json"))
        # Expect: invoice_acme.json, invoice_globex.json,
        # quotation_initech.json, run_summary.json
        assert len(json_files) >= 4

    def test_pipeline_creates_output_dir(
        self,
        sample_manifest_path: Path,
        tmp_path: Path,
    ) -> None:
        """The output directory is created if it does not exist."""
        output_dir = tmp_path / "nonexistent" / "nested" / "output"
        assert not output_dir.exists()
        run_pipeline(sample_manifest_path, output_dir)
        assert output_dir.exists()

    def test_pipeline_writes_summary(
        self,
        sample_manifest_path: Path,
        tmp_output_dir: Path,
    ) -> None:
        """A run_summary.json is written to the output directory."""
        run_pipeline(sample_manifest_path, tmp_output_dir)
        summary_path = tmp_output_dir / "run_summary.json"
        assert summary_path.exists()
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary_data["total_rows"] == 3
        assert "successful" in summary_data
        assert "unresolved" in summary_data
        assert "failed" in summary_data

    def test_pipeline_handles_missing_input(
        self,
        tmp_path: Path,
    ) -> None:
        """A manifest referencing a non-existent input file raises FileNotFoundError."""
        manifest = tmp_path / "manifest.csv"
        manifest.write_text(
            "id,input_file,contract_name\nbad_row,inputs/does_not_exist.txt,Invoice\n",
            encoding="utf-8",
        )
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Input file missing"):
            run_pipeline(manifest, output_dir)

    def test_pipeline_handles_unknown_contract(
        self,
        tmp_path: Path,
    ) -> None:
        """A manifest with an unknown contract_name raises ValueError."""
        input_file = tmp_path / "inputs" / "some.txt"
        input_file.parent.mkdir(parents=True)
        input_file.write_text("some data", encoding="utf-8")
        manifest = tmp_path / "manifest.csv"
        manifest.write_text(
            "id,input_file,contract_name\nbad_row,inputs/some.txt,NoSuchContract\n",
            encoding="utf-8",
        )
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        with pytest.raises(ValueError, match="Unknown contract"):
            run_pipeline(manifest, output_dir)
