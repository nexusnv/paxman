"""Tests for the NormalizeTool."""

from __future__ import annotations

from ai_agent_ingest.contracts import ExtractedDocument
from ai_agent_ingest.tools import NormalizeTool


class TestNormalizeTool:
    """Tests for NormalizeTool behavior."""

    def test_tool_name(self) -> None:
        tool = NormalizeTool(contract=ExtractedDocument)
        assert tool.name == "normalize_document"

    def test_normalize_tool_success(self, sample_document_text: str) -> None:
        tool = NormalizeTool(contract=ExtractedDocument)
        result = tool.run(input_data=sample_document_text)
        assert result.success is True
        assert result.tool_name == "normalize_document"
        assert "status" in result.payload
        assert "replay_hash" in result.payload
        assert result.error is None

    def test_normalize_tool_invalid_contract(self) -> None:
        tool = NormalizeTool(contract="not_a_real_contract")
        result = tool.run(input_data="some text")
        assert result.success is True
        assert result.payload["status"] == "INVALID_CONTRACT"

    def test_normalize_tool_catches_exception(self) -> None:
        from unittest.mock import patch

        tool = NormalizeTool(contract=ExtractedDocument)
        with patch("ai_agent_ingest.tools.paxman.normalize", side_effect=RuntimeError("boom")):
            result = tool.run(input_data="text")
        assert result.success is False
        assert "boom" in (result.error or "")
