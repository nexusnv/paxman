"""The normalize_document tool. Plug this into any agent framework."""

from __future__ import annotations

from typing import Any

import attrs

import paxman
import paxman.contract.adapters.pydantic


@attrs.frozen
class ToolCall:
    """A tool call from the agent."""

    tool_name: str
    arguments: dict[str, Any]


@attrs.frozen
class ToolResult:
    """The result of a tool call, returned to the agent."""

    tool_name: str
    success: bool
    payload: dict[str, Any]
    error: str | None = None


class NormalizeTool:
    """A tool that normalizes a document via paxman.normalize().

    Usage in any agent framework::

        tool = NormalizeTool(contract=ExtractedDocument)
        result = tool.run(input_data=raw_doc_text)
        # result.payload is the normalized dict with status, replay_hash, etc.
    """

    name: str = "normalize_document"

    def __init__(self, contract: Any) -> None:
        self._contract = contract

    def run(self, input_data: str, **kwargs: Any) -> ToolResult:
        """Run the normalization tool.

        Args:
            input_data: The raw document text to normalize.
            **kwargs: Forwarded to paxman.normalize() (e.g. budget, policy).

        Returns:
            ToolResult with success status and the artifact as payload.
        """
        try:
            artifact = paxman.normalize(
                input_data=input_data,
                contract=self._contract,
                **kwargs,
            )
            return ToolResult(
                tool_name=self.name,
                success=True,
                payload={
                    "status": artifact.status.name,
                    "normalized_data": artifact.normalized_data,
                    "unresolved_fields": artifact.unresolved_fields,
                    "replay_hash": artifact.replay_hash,
                },
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                payload={},
                error=str(exc),
            )
