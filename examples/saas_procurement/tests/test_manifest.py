"""Tests for the CSV manifest parser."""

from __future__ import annotations

from pathlib import Path

import pytest
from saas_procurement.manifest import load_manifest


class TestLoadManifest:
    """Tests for :func:`load_manifest`."""

    def test_load_manifest_basic(self, sample_manifest_path: Path) -> None:
        """Loading the sample manifest returns 3 rows."""
        rows = load_manifest(sample_manifest_path)
        assert len(rows) == 3

    def test_load_manifest_resolves_paths(self, sample_manifest_path: Path) -> None:
        """Input file paths are resolved relative to the manifest directory."""
        rows = load_manifest(sample_manifest_path)
        base = sample_manifest_path.parent
        for row in rows:
            assert row.input_file.is_absolute()
            # The resolved path should live under the data/ directory.
            assert str(base) in str(row.input_file)

    def test_load_manifest_missing_column(self, tmp_path: Path) -> None:
        """A manifest missing a required column raises ValueError."""
        bad_manifest = tmp_path / "bad.csv"
        bad_manifest.write_text("id,input_file\nfoo,bar.txt\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing required columns"):
            load_manifest(bad_manifest)

    def test_load_manifest_empty(self, tmp_path: Path) -> None:
        """An empty manifest raises ValueError."""
        empty_manifest = tmp_path / "empty.csv"
        empty_manifest.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            load_manifest(empty_manifest)

    def test_load_manifest_row_values(self, sample_manifest_path: Path) -> None:
        """Row values are correctly parsed."""
        rows = load_manifest(sample_manifest_path)
        assert rows[0].id == "invoice_acme"
        assert rows[0].contract_name == "Invoice"
        assert rows[1].id == "invoice_globex"
        assert rows[2].id == "quotation_initech"
        assert rows[2].contract_name == "Quotation"
