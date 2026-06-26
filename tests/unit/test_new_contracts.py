"""Tests for the new dict_dsl receipt/quotation and pydantic receipt contracts.

Per Sprint 7 D7.2, this test verifies that the new contract
fixtures (added in Sprint 7) load, adapt, and normalize correctly.
"""

from __future__ import annotations

import pytest

import paxman

# Trigger auto-registration for adapters.
import paxman.contract.adapters.dict_dsl
import paxman.contract.adapters.pydantic
from paxman.artifact.artifact import ExecutionArtifact
from tests.fixtures.contracts.dict_dsl.quotation import DICT_DSL_QUOTATION
from tests.fixtures.contracts.dict_dsl.receipt import DICT_DSL_RECEIPT
from tests.fixtures.contracts.pydantic.receipt import Receipt

pytestmark = [pytest.mark.deterministic, pytest.mark.unit]


class TestNewContracts:
    """Tests for Sprint 7 new contract fixtures."""

    def test_dict_dsl_receipt_adapts(self) -> None:
        """The Dict DSL receipt contract adapts to a CanonicalContract."""
        artifact = paxman.normalize(input_data="merchant", contract=DICT_DSL_RECEIPT)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.contract_id == "receipt-v1"

    def test_dict_dsl_quotation_adapts(self) -> None:
        """The Dict DSL quotation contract adapts to a CanonicalContract."""
        artifact = paxman.normalize(input_data="Q-123456", contract=DICT_DSL_QUOTATION)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.contract_id == "quotation-v1"

    def test_pydantic_receipt_adapts(self) -> None:
        """The Pydantic receipt model adapts to a CanonicalContract."""
        artifact = paxman.normalize(input_data="merchant", contract=Receipt)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.contract_id == "Receipt"

    def test_dict_dsl_receipt_has_card_last4_pattern(self) -> None:
        """The Dict DSL receipt's ``card_last4`` field has a pattern constraint."""
        field = next(f for f in DICT_DSL_RECEIPT["fields"] if f["name"] == "card_last4")
        assert any(c["kind"] == "pattern" for c in field.get("constraints", [])), (
            f"card_last4 field is missing a 'pattern' constraint: {field}"
        )

    def test_dict_dsl_quotation_has_quote_number_pattern(self) -> None:
        """The Dict DSL quotation's ``quote_number`` field has a pattern constraint."""
        field = next(f for f in DICT_DSL_QUOTATION["fields"] if f["name"] == "quote_number")
        assert any(c["kind"] == "pattern" for c in field.get("constraints", [])), (
            f"quote_number field is missing a 'pattern' constraint: {field}"
        )
