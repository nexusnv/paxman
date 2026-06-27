"""The agent loop. Framework-agnostic; works with any LLM."""

from __future__ import annotations

from typing import Any

from ai_agent_ingest.fake_llm import AgentDecision
from ai_agent_ingest.tools import ToolResult


class IngestionAgent:
    """An agent that ingests documents using a tool-calling loop.

    The loop::

        1. Ask LLM what to do
        2. If LLM says "tool_call", call the tool, observe the result
        3. If LLM says "final_answer", return the answer
        4. Otherwise: error

    Usage::

        agent = IngestionAgent(llm=FakeLLM(...), tools=[NormalizeTool(...)])
        result = agent.run(input_data=raw_doc)
    """

    MAX_ITERATIONS: int = 5

    def __init__(self, llm: Any, tools: list[Any]) -> None:
        self._llm = llm
        self._tools: dict[str, Any] = {t.name: t for t in tools}
        self._history: list[dict[str, Any]] = []

    def run(self, input_data: str) -> dict[str, Any]:
        """Run the agent loop.

        Args:
            input_data: The raw document text to process.

        Returns:
            Dict with the final answer, tool call history, and the artifact.

        Raises:
            ValueError: If the LLM requests an unknown tool or action.
            RuntimeError: If the agent exceeds MAX_ITERATIONS.
        """
        self._history = [{"role": "user", "content": input_data}]
        for _ in range(self.MAX_ITERATIONS):
            decision: AgentDecision = self._llm.decide(self._history)
            if decision.action == "final_answer":
                return {
                    "answer": decision.answer,
                    "history": list(self._history),
                    "tool_calls": [h for h in self._history if h.get("role") == "tool"],
                }
            if decision.action == "tool_call":
                tool = self._tools.get(decision.tool_name or "")
                if tool is None:
                    raise ValueError(f"Unknown tool: {decision.tool_name}")
                arguments = decision.arguments or {}
                if "input_data" not in arguments:
                    arguments = {**arguments, "input_data": input_data}
                result: ToolResult = tool.run(**arguments)
                self._history.append({"role": "tool", "tool_name": tool.name, "result": result})
                continue
            raise ValueError(f"Unknown action: {decision.action}")
        raise RuntimeError(f"Agent exceeded MAX_ITERATIONS ({self.MAX_ITERATIONS})")
