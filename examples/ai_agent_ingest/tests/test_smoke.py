"""Smoke tests: imports work and demo runs."""

from __future__ import annotations

import subprocess
import sys


class TestImports:
    """Verify all public symbols are importable."""

    def test_imports(self) -> None:
        from ai_agent_ingest import FakeLLM, IngestionAgent, NormalizeTool, ToolResult

        assert IngestionAgent is not None
        assert FakeLLM is not None
        assert NormalizeTool is not None
        assert ToolResult is not None

    def test_version(self) -> None:
        from ai_agent_ingest import __version__

        assert __version__ == "0.1.0"

    def test_contracts_import(self) -> None:
        from ai_agent_ingest.contracts import CONTRACTS, ExtractedDocument

        assert "ExtractedDocument" in CONTRACTS
        assert ExtractedDocument is CONTRACTS["ExtractedDocument"]


class TestDemo:
    """Verify the demo __main__ runs without error."""

    def test_demo_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ai_agent_ingest"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Answer:" in result.stdout
        assert "Tool calls:" in result.stdout
        assert "Artifact payload:" in result.stdout
