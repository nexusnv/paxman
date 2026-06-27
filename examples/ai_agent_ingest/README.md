# AI Agent Ingest — Paxman Reference Example

> Framework-agnostic agent tool-calling loop calling `paxman.normalize()`.

## Problem statement

I'm an AI engineer building an agentic ingestion flow. I want to call Paxman
as a tool in my agent's loop, but I don't want to be locked into LangChain
or LlamaIndex.

## Why stdlib-only

This example has **zero framework deps** (just `paxman[pydantic]`). The
pattern works in any agent framework: replace `FakeLLM` with your real LLM,
and the tool interface stays the same.

## Install

```bash
cd examples/ai_agent_ingest
uv venv
uv pip install -e ".[dev]"
```

If Paxman is not yet on PyPI, install the parent project first:

```bash
uv pip install -e ../..
```

## Run

```bash
uv run python -m ai_agent_ingest
```

## Test

```bash
uv run pytest tests/ -v
```

## Expected output

```
Answer: Document normalized successfully.
Tool calls: 1
Artifact payload: {'status': 'SUCCESS', 'normalized_data': {...}, 'unresolved_fields': [...], 'replay_hash': '...'}
```

## What this example demonstrates

- **Agent tool-calling loop** — a `run()` method that iterates between LLM
  decisions and tool invocations.
- **Tool registration** — tools are registered by name; the agent dispatches
  to the right one.
- **Evidence-backed normalization** — `paxman.normalize()` returns an
  `ExecutionArtifact` with status, resolved data, and diagnostics.
- **Replay hash** — the artifact carries a deterministic `replay_hash` for
  later verification via `paxman.replay()`.

## How to adapt

### Porting `NormalizeTool` to LangChain

```python
from langchain.tools import BaseTool

class PaxmanNormalizeTool(BaseTool):
    name = "normalize_document"
    description = "Normalize a document against a contract using Paxman."

    def _run(self, input_data: str, **kwargs):
        import paxman
        from ai_agent_ingest.contracts import ExtractedDocument
        artifact = paxman.normalize(input_data=input_data, contract=ExtractedDocument)
        return {
            "status": artifact.status.name,
            "normalized_data": artifact.normalized_data,
            "replay_hash": artifact.replay_hash,
        }
```

### Porting to LlamaIndex

Subclass `FunctionTool` and wrap `NormalizeTool.run()` the same way.
The key point: **the tool's interface doesn't change** — only the
framework-specific wrapper does.

### Custom agents

Replace `FakeLLM` with a class that has a `decide(history)` method returning
an `AgentDecision`. Everything else stays the same.
