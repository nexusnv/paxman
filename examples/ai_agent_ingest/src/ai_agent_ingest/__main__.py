"""Demo: run the agent on a sample document."""

from ai_agent_ingest import FakeLLM, IngestionAgent, NormalizeTool
from ai_agent_ingest.contracts import ExtractedDocument

SAMPLE_DOC: str = """
ACME Corp
Invoice #INV-2026-0042
Total: $1,234.56 USD
"""

if __name__ == "__main__":
    tool = NormalizeTool(contract=ExtractedDocument)
    llm = FakeLLM(
        scripted_tool_args={"input_data": SAMPLE_DOC},
        scripted_answer="Document normalized successfully.",
    )
    agent = IngestionAgent(llm=llm, tools=[tool])
    result = agent.run(input_data=SAMPLE_DOC)
    print("Answer:", result["answer"])
    print("Tool calls:", len(result["tool_calls"]))
    if result["tool_calls"]:
        print("Artifact payload:", result["tool_calls"][0]["result"].payload)
    else:
        print("Artifact payload: none")
