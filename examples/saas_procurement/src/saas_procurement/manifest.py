"""CSV manifest schema and parser.

Manifest format (CSV)::

    id,input_file,contract_name
    invoice_acme,data/inputs/invoice_acme.txt,Invoice
    invoice_globex,data/inputs/invoice_globex.txt,Invoice
    quotation_initech,data/inputs/quotation_initech.txt,Quotation
"""

from __future__ import annotations

import csv
from pathlib import Path

import attrs

REQUIRED_COLUMNS: tuple[str, ...] = ("id", "input_file", "contract_name")


@attrs.frozen
class ManifestRow:
    """A single row from the manifest CSV.

    Attributes:
        id: Unique row identifier.
        input_file: Absolute path to the raw input file.
        contract_name: Name of the Pydantic contract to normalise against.
    """

    id: str = attrs.field()
    input_file: Path = attrs.field()
    contract_name: str = attrs.field()


def load_manifest(
    manifest_path: Path,
    base_dir: Path | None = None,
) -> list[ManifestRow]:
    """Load and validate a manifest CSV.

    Args:
        manifest_path: Path to the manifest CSV.
        base_dir: Base directory for resolving relative input_file
            paths.  Defaults to ``manifest_path.parent``.

    Returns:
        List of :class:`ManifestRow`.

    Raises:
        ValueError: If required columns are missing or rows are
            malformed.
    """
    base = base_dir or manifest_path.parent
    rows: list[ManifestRow] = []
    with open(manifest_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Manifest is empty: {manifest_path}")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"Manifest missing required columns: {missing}")
        for i, row in enumerate(reader):
            try:
                rows.append(
                    ManifestRow(
                        id=row["id"],
                        input_file=(base / row["input_file"]).resolve(),
                        contract_name=row["contract_name"],
                    )
                )
            except KeyError as e:
                raise ValueError(f"Manifest row {i} missing column: {e}") from e
    return rows
