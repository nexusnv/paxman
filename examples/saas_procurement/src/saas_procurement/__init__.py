"""Paxman reference example: CSV batch procurement pipeline."""

from saas_procurement.manifest import ManifestRow, load_manifest
from saas_procurement.pipeline import RunSummary, run_pipeline

__version__ = "0.1.0"
__all__ = ["ManifestRow", "RunSummary", "load_manifest", "run_pipeline"]
