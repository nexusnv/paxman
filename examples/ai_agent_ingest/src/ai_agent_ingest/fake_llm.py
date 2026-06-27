"""A stub LLM that returns scripted tool calls. Replace with your real LLM."""

from __future__ import annotations

from typing import Any

import attrs


@attrs.frozen
class AgentDecision:
    """A decision from the LLM: either call a tool or produce a final answer."""

    action: str
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    answer: str | None = None


class FakeLLM:
    """A scripted LLM that always calls normalize_document then answers.

    Real usage: subclass this and override ``decide()`` to call
    OpenAI/Anthropic/etc. The agent loop doesn't care which LLM is
    plugged in.
    """

    def __init__(
        self,
        scripted_tool_args: dict[str, Any] | None = None,
        scripted_answer: str = "Done.",
    ) -> None:
        self._scripted_tool_args = scripted_tool_args or {}
        self._scripted_answer = scripted_answer
        self._call_count: int = 0

    def decide(self, history: list[dict[str, Any]]) -> AgentDecision:
        """Return a scripted decision based on call count.

        Args:
            history: The conversation history so far.

        Returns:
            An AgentDecision — tool_call on first invocation, final_answer after.
        """
        self._call_count += 1
        if self._call_count == 1:
            return AgentDecision(
                action="tool_call",
                tool_name="normalize_document",
                arguments=self._scripted_tool_args,
            )
        return AgentDecision(action="final_answer", answer=self._scripted_answer)
