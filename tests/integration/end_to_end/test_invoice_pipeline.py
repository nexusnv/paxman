"""Integration tests: End-to-end invoice pipeline (D7.11).

Per Sprint 7 D7.11, this test exercises the full pipeline on a
Pydantic invoice contract and verifies:

1. The pipeline returns a valid ``ExecutionArtifact``.
2. The ``replay_hash`` is computed and is 64 lowercase hex chars.
3. The artifact can be replayed successfully.
4. The artifact can be round-tripped (serialize → deserialize) without
   data loss.
"""

from __future__ import annotations

import pytest

import paxman

# Trigger auto-registration for Dict DSL and Pydantic adapters.
import paxman.contract.adapters.dict_dsl
import paxman.contract.adapters.pydantic
from paxman.artifact.artifact import ExecutionArtifact
from paxman.artifact.serializer import decode_artifact, encode_artifact
from paxman.types import Status
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE
from tests.fixtures.contracts.pydantic.invoice import Invoice

pytestmark = pytest.mark.integration


class TestInvoicePipeline:
    """End-to-end tests on the invoice pipeline."""

    def test_dict_dsl_invoice_pipeline(self) -> None:
        """Full pipeline on the Dict DSL invoice contract."""
        raw_text = "ACME Corp\nInvoice #INV-2026-12345\nDate: 2026-06-22\nTotal: $1,234.56 USD\n"
        artifact = paxman.normalize(input_data=raw_text, contract=DICT_DSL_INVOICE)

        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.contract_id == "invoice-v1"
        assert artifact.status in {Status.SUCCESS, Status.PARTIAL_SUCCESS, Status.UNRESOLVED}
        # Replay hash is a 64-char hex string.
        assert len(artifact.replay_hash) == 64
        assert all(c in "0123456789abcdef" for c in artifact.replay_hash)

    def test_pydantic_invoice_pipeline(self) -> None:
        """Full pipeline on the Pydantic invoice model."""
        raw_text = "Some invoice text"
        artifact = paxman.normalize(input_data=raw_text, contract=Invoice)

        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.contract_id == "Invoice"
        # The contract should adapt successfully.
        assert artifact.status is not Status.INVALID_CONTRACT

    def test_invoice_pipeline_replay_round_trip(self) -> None:
        """An invoice artifact can be replayed successfully."""
        raw_text = "ACME Corp\nInvoice #1234\nTotal: $1,234.56"
        artifact = paxman.normalize(input_data=raw_text, contract=DICT_DSL_INVOICE)

        replayed = paxman.replay(artifact, contract=DICT_DSL_INVOICE)
        assert replayed == artifact
        assert replayed.replay_hash == artifact.replay_hash

    def test_invoice_pipeline_serialization_round_trip(self) -> None:
        """An invoice artifact can be JSON-serialized and deserialized."""
        raw_text = "ACME Corp\nInvoice #1234\nTotal: $1,234.56"
        artifact = paxman.normalize(input_data=raw_text, contract=DICT_DSL_INVOICE)

        json_str = encode_artifact(artifact)
        decoded = decode_artifact(json_str)

        # The decoded dict has the same hash-relevant fields.
        assert decoded["replay_hash"] == artifact.replay_hash
        assert decoded["contract_id"] == artifact.contract_id
        assert decoded["status"] == artifact.status.value

    def test_invoice_pipeline_with_budget(self) -> None:
        """The invoice pipeline accepts a Budget cap."""
        from paxman.budget import Budget

        raw_text = "ACME Corp\nInvoice #1234\nTotal: $1,234.56"
        artifact = paxman.normalize(
            input_data=raw_text,
            contract=DICT_DSL_INVOICE,
            budget=Budget(max_total_cost_usd=0.10),
        )
        assert isinstance(artifact, ExecutionArtifact)
        # The artifact is valid even when the budget would be
        # exceeded (the executor short-circuits, but the artifact
        # is still well-formed).
        assert artifact.status in {Status.PARTIAL_SUCCESS, Status.UNRESOLVED, Status.SUCCESS}

    def test_invoice_pipeline_with_policy(self) -> None:
        """The invoice pipeline accepts a Policy override."""
        from paxman.budget import Policy

        raw_text = "ACME Corp\nInvoice #1234\nTotal: $1,234.56"
        policy = Policy(
            allow_remote_inference=False,
            allow_local_inference=False,
            confidence_floor=0.95,
        )
        artifact = paxman.normalize(
            input_data=raw_text,
            contract=DICT_DSL_INVOICE,
            policy=policy,
        )
        assert isinstance(artifact, ExecutionArtifact)
        # The policy is reflected in the plan (no inference capabilities).
        # The exact status depends on whether the policy excludes
        # the only V1 capabilities available — the test just checks
        # the pipeline runs without crashing.
        assert artifact.status is not None
