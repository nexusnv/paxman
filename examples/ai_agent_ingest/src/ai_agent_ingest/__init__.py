"""Paxman reference example: stdlib-only agent tool-calling loop."""

from ai_agent_ingest.agent import IngestionAgent
from ai_agent_ingest.fake_llm import FakeLLM
from ai_agent_ingest.tools import NormalizeTool, ToolResult

__version__: str = "0.1.0"
__all__: list[str] = ["FakeLLM", "IngestionAgent", "NormalizeTool", "ToolResult"]
