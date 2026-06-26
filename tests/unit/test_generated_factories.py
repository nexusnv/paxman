"""Tests for the ``tests.fixtures.factories/`` programmatic fixture factories.

Per Sprint 7 D7.4, this test verifies that all factory_boy + faker
factories work and produce valid output. Each factory is invoked
once; the result is type-checked and (where applicable) validated
via :func:`paxman.normalize` to ensure end-to-end correctness.
"""

from __future__ import annotations

import pytest

from tests.fixtures.factories import SEED, reseed
from tests.fixtures.factories.artifacts import ExecutionArtifactFactory
from tests.fixtures.factories.candidates import CandidateFactory, EvidenceRefFactory
from tests.fixtures.factories.contracts import (
    DictDSLInvoiceFactory,
    JsonSchemaInvoiceFactory,
    OpenAPIPetstoreFactory,
    PydanticInvoiceFactory,
)
from tests.fixtures.factories.inputs import (
    InvoiceInputFactory,
    MultiPageInputFactory,
    QuotationInputFactory,
    ReceiptInputFactory,
)
from tests.fixtures.factories.policies import BudgetFactory, PolicyFactory

pytestmark = pytest.mark.unit


def test_deterministic_seed_recorded() -> None:
    """The default seed is recorded for reproducibility."""
    assert SEED == 0x70617821


def test_reseed_changes_random_state() -> None:
    """``reseed`` resets ``factory_boy``'s global random state.

    After ``reseed(seed)``, the next ``InvoiceInputFactory()`` call
    returns the same value as a previous call with the same seed.
    """
    reseed(42)
    a1 = InvoiceInputFactory()
    reseed(42)
    b1 = InvoiceInputFactory()
    # Same seed → same output.
    assert a1 == b1


def test_dict_dsl_invoice_factory() -> None:
    """``DictDSLInvoiceFactory`` produces a valid Dict DSL contract dict."""
    contract = DictDSLInvoiceFactory()
    assert isinstance(contract, dict)
    assert "id" in contract
    assert "fields" in contract
    assert len(contract["fields"]) >= 3


def test_pydantic_invoice_factory() -> None:
    """``PydanticInvoiceFactory`` produces a Pydantic ``BaseModel`` subclass.

    The factory must produce a model with the 5 documented invoice
    fields (``supplier_name``, ``total_amount``, ``currency_code``,
    ``invoice_date``, ``paid``) so the adapter-parity tests can
    normalize the same input against either Pydantic or Dict DSL and
    expect the same downstream contract shape. A factory that
    produced an empty model would pass the prior ``isinstance(type)``
    + ``hasattr(model_fields)`` check, which is why this test now
    asserts on the actual field set.
    """
    model_class = PydanticInvoiceFactory()
    # It's a class (Pydantic models are classes).
    assert isinstance(model_class, type)
    # It has pydantic attributes.
    assert hasattr(model_class, "model_fields")
    # It is a Pydantic BaseModel subclass (not just any class with
    # a ``model_fields`` attribute).
    from pydantic import BaseModel

    assert issubclass(model_class, BaseModel)
    # It carries the 5 documented invoice fields — not an empty
    # ``class Empty(BaseModel): pass``.
    field_names = set(model_class.model_fields.keys())
    expected_fields = {
        "supplier_name",
        "total_amount",
        "currency_code",
        "invoice_date",
        "paid",
    }
    assert expected_fields.issubset(field_names), (
        f"PydanticInvoiceFactory missing required fields: "
        f"{expected_fields - field_names}; got {field_names}"
    )
    # The class has the auto-generated name set by the factory.
    assert model_class.__name__ == "GeneratedInvoice"


def test_json_schema_invoice_factory() -> None:
    """``JsonSchemaInvoiceFactory`` produces a valid JSON Schema dict."""
    schema = JsonSchemaInvoiceFactory()
    assert isinstance(schema, dict)
    assert "$schema" in schema
    assert "properties" in schema


def test_openapi_petstore_factory() -> None:
    """``OpenAPIPetstoreFactory`` produces a valid OpenAPI YAML string."""
    spec = OpenAPIPetstoreFactory()
    assert isinstance(spec, str)
    assert "openapi: 3.0" in spec


def test_invoice_input_factory() -> None:
    """``InvoiceInputFactory`` produces a multi-line invoice text."""
    text = InvoiceInputFactory()
    assert "Supplier:" in text
    assert "Total:" in text
    assert "Invoice #" in text


def test_receipt_input_factory() -> None:
    """``ReceiptInputFactory`` produces a receipt text."""
    text = ReceiptInputFactory()
    assert "Merchant:" in text
    assert "Amount:" in text


def test_quotation_input_factory() -> None:
    """``QuotationInputFactory`` produces a quotation text."""
    text = QuotationInputFactory()
    assert "Quotation" in text
    assert "Quote #" in text


def test_multi_page_input_factory() -> None:
    """``MultiPageInputFactory`` produces a 3-page text."""
    text = MultiPageInputFactory()
    assert text.count("=== Page") == 3


def test_evidence_ref_factory() -> None:
    """``EvidenceRefFactory`` produces a valid ``EvidenceRef``."""
    from paxman.capabilities.result import EvidenceRef

    ref = EvidenceRefFactory()
    assert isinstance(ref, EvidenceRef)
    assert ref.capability_id
    assert ref.field_path


def test_candidate_factory() -> None:
    """``CandidateFactory`` produces a valid ``Candidate``."""
    from paxman.capabilities.result import Candidate

    cand = CandidateFactory()
    assert isinstance(cand, Candidate)
    assert cand.value is not None


def test_execution_artifact_factory() -> None:
    """``ExecutionArtifactFactory`` produces a valid ``ExecutionArtifact`` with a stable hash."""
    from paxman.artifact.artifact import ExecutionArtifact

    artifact = ExecutionArtifactFactory()
    assert isinstance(artifact, ExecutionArtifact)
    # Replay hash is non-empty (64 chars).
    assert len(artifact.replay_hash) == 64


def test_execution_artifact_factory_is_deterministic() -> None:
    """``ExecutionArtifactFactory`` produces byte-equal output for a fixed seed."""
    from tests.fixtures.factories import reseed

    reseed(SEED)
    a = ExecutionArtifactFactory()
    reseed(SEED)
    b = ExecutionArtifactFactory()
    # They have the same replay_hash (deterministic) but possibly
    # different IDs (because ExecutionArtifact uses UUID4 for id by
    # default). For pure replay testing, the replay_hash is what
    # matters.
    assert a.replay_hash == b.replay_hash


def test_budget_factory() -> None:
    """``BudgetFactory`` produces a valid ``Budget``."""
    from paxman.budget import Budget

    budget = BudgetFactory()
    assert isinstance(budget, Budget)
    assert budget.max_total_latency_ms is not None


def test_policy_factory() -> None:
    """``PolicyFactory`` produces a valid ``Policy``."""
    from paxman.budget import Policy

    policy = PolicyFactory()
    assert isinstance(policy, Policy)
    assert 0.0 <= policy.confidence_floor <= 1.0


def test_factory_input_runs_through_paxman() -> None:
    """An end-to-end smoke: factory-generated input + contract runs through ``paxman.normalize()``."""
    import paxman
    import paxman.contract.adapters.dict_dsl

    text = InvoiceInputFactory()
    contract = DictDSLInvoiceFactory()
    artifact = paxman.normalize(input_data=text, contract=contract)
    assert artifact is not None
    # The contract's id is the one from the factory.
    assert artifact.contract_id == contract["id"]
