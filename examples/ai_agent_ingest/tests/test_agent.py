"""Tests for the IngestionAgent loop."""

from __future__ import annotations

import pytest
from ai_agent_ingest.agent import IngestionAgent
from ai_agent_ingest.contracts import ExtractedDocument
from ai_agent_ingest.fake_llm import AgentDecision, FakeLLM
from ai_agent_ingest.tools import NormalizeTool


class AlwaysCallLLM:
    """An LLM that always requests a tool call — for max-iteration testing."""

    def decide(self, history: list[dict[str, object]]) -> AgentDecision:
        return AgentDecision(
            action="tool_call",
            tool_name="normalize_document",
            arguments={},
        )


class TestIngestionAgent:
    """Tests for the agent tool-calling loop."""

    def test_agent_calls_tool_then_answers(self, sample_document_text: str) -> None:
        tool = NormalizeTool(contract=ExtractedDocument)
        llm = FakeLLM(scripted_answer="Document normalized.")
        agent = IngestionAgent(llm=llm, tools=[tool])
        result = agent.run(input_data=sample_document_text)
        assert result["answer"] == "Document normalized."
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool_name"] == "normalize_document"

    def test_agent_handles_unknown_tool(self, sample_document_text: str) -> None:
        class UnknownToolLLM:
            def decide(self, history: list[dict[str, object]]) -> AgentDecision:
                return AgentDecision(
                    action="tool_call",
                    tool_name="nonexistent_tool",
                    arguments={},
                )

        agent = IngestionAgent(llm=UnknownToolLLM(), tools=[])
        with pytest.raises(ValueError, match="Unknown tool: nonexistent_tool"):
            agent.run(input_data=sample_document_text)

    def test_agent_max_iterations(self, sample_document_text: str) -> None:
        tool = NormalizeTool(contract=ExtractedDocument)
        agent = IngestionAgent(llm=AlwaysCallLLM(), tools=[tool])
        with pytest.raises(RuntimeError, match="Agent exceeded MAX_ITERATIONS"):
            agent.run(input_data=sample_document_text)

    def test_agent_includes_artifact_in_history(self, sample_document_text: str) -> None:
        tool = NormalizeTool(contract=ExtractedDocument)
        llm = FakeLLM(scripted_answer="Done.")
        agent = IngestionAgent(llm=llm, tools=[tool])
        result = agent.run(input_data=sample_document_text)
        tool_entry = result["tool_calls"][0]
        assert "result" in tool_entry
        artifact_payload = tool_entry["result"].payload
        assert "status" in artifact_payload
        assert "replay_hash" in artifact_payload
