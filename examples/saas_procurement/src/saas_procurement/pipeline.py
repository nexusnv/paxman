"""Batch pipeline: reads a manifest, normalises each row, writes artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import attrs

import paxman
import paxman.contract.adapters.pydantic
from saas_procurement.contracts import CONTRACTS
from saas_procurement.manifest import load_manifest


@attrs.frozen
class RunSummary:
    """Summary of a batch run.

    Attributes:
        manifest_path: Path to the manifest that was processed.
        total_rows: Number of rows in the manifest.
        successful: Count of rows with SUCCESS or PARTIAL_SUCCESS status.
        unresolved: Count of rows with UNRESOLVED status.
        failed: Count of rows that raised an exception.
        artifact_paths: List of paths to written artifact JSON files.
    """

    manifest_path: str = attrs.field()
    total_rows: int = attrs.field()
    successful: int = attrs.field()
    unresolved: int = attrs.field()
    failed: int = attrs.field()
    artifact_paths: list[str] = attrs.field()


def _artifact_to_dict(artifact: Any) -> dict[str, Any]:
    """Convert an ExecutionArtifact to a JSON-serialisable dict.

    Args:
        artifact: A completed :class:`paxman.ExecutionArtifact`.

    Returns:
        A plain dict suitable for ``json.dumps``.
    """
    return {
        "paxman_version": artifact.paxman_version,
        "status": artifact.status.name,
        "normalized_data": artifact.normalized_data,
        "unresolved_fields": list(artifact.unresolved_fields),
        "replay_hash": artifact.replay_hash,
        "field_results": [
            {
                "field_path": fr.field_path,
                "value": fr.value,
                "confidence": fr.confidence.name,
                "status": fr.status.name,
            }
            for fr in artifact.field_results.values()
        ],
    }


def run_pipeline(manifest_path: Path, output_dir: Path) -> RunSummary:
    """Run the batch pipeline.

    Args:
        manifest_path: Path to the manifest CSV.
        output_dir: Directory to write artifacts to.  Created if
            missing.

    Returns:
        :class:`RunSummary` with counts and artifact paths.

    Raises:
        FileNotFoundError: If manifest or any input file is missing.
        ValueError: If a ``contract_name`` in the manifest is unknown.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_manifest(manifest_path)
    artifacts: list[str] = []
    successful = 0
    unresolved = 0
    failed = 0

    for row in rows:
        if not row.input_file.exists():
            raise FileNotFoundError(f"Input file missing: {row.input_file}")
        if row.contract_name not in CONTRACTS:
            raise ValueError(f"Unknown contract {row.contract_name!r} in row {row.id!r}")
        safe_row_id = Path(row.id).name
        if safe_row_id != row.id or ".." in row.id:
            raise ValueError(f"Invalid row id {row.id!r}")
        contract = CONTRACTS[row.contract_name]
        input_data = row.input_file.read_text(encoding="utf-8")
        try:
            artifact = paxman.normalize(input_data=input_data, contract=contract)
            artifact_path = output_dir / f"{safe_row_id}.json"
            artifact_path.write_text(
                json.dumps(_artifact_to_dict(artifact), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            artifacts.append(str(artifact_path))
            if artifact.status.name in ("SUCCESS", "PARTIAL_SUCCESS"):
                successful += 1
            elif artifact.status.name == "UNRESOLVED":
                unresolved += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            error_path = output_dir / f"{safe_row_id}.error.txt"
            error_path.write_text(str(exc), encoding="utf-8")

    summary = RunSummary(
        manifest_path=str(manifest_path),
        total_rows=len(rows),
        successful=successful,
        unresolved=unresolved,
        failed=failed,
        artifact_paths=artifacts,
    )
    (output_dir / "run_summary.json").write_text(
        json.dumps(attrs.asdict(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary
