"""Integration test — format extractors invoked through the capability registry.

This test exercises the three V1.1.0 format extractors
(``json_path_extraction``, ``csv_extraction``, ``xpath_extraction``)
through the same public surface that downstream code uses
(``paxman.capabilities.registry.get`` and
``paxman.capabilities.base.CapabilityContext``).

Scope note: the V1.1.0 slice adds the three capabilities but does not
change the executor's capability-selection logic. A follow-up (filed
as a separate issue) is required to teach the executor to dispatch
format-aware input to the new extractors automatically. Until then,
callers wire the new capabilities explicitly via
:func:`paxman.capabilities.registry.register`. This integration
test verifies the slice's actual deliverable — the capabilities work
correctly through the public registry/contract surface — and
deliberately does not assert that the executor routes structured
inputs to the new extractors without explicit registration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import paxman
import paxman.contract.adapters.dict_dsl  # self-registration of the Dict DSL adapter
from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.registry import register
from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability
from paxman.capabilities.v1.json_path_extraction import JsonPathExtractionCapability
from paxman.capabilities.v1.xpath_extraction import XPathExtractionCapability
from tests.fixtures.contracts.dict_dsl.with_csv_extraction import (
    DICT_DSL_WITH_CSV_EXTRACTION,
)

pytestmark = pytest.mark.integration


_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture(autouse=True)
def _register_format_extractors() -> None:
    """Register the three V1.1.0 format extractors for the test session.

    Per the V1 registry contract (see Oracle review for issue #70), only
    ``lookup`` self-registers on import. The three new LOCAL_DETERMINISTIC
    extractors must be registered explicitly by the caller.
    """
    register(CsvExtractionCapability(), replace=True)
    register(JsonPathExtractionCapability(), replace=True)
    register(XPathExtractionCapability(), replace=True)


def _load_csv() -> bytes:
    return (_FIXTURES_DIR / "inputs" / "sample_invoices.csv").read_bytes()


def test_csv_extractor_is_in_registry() -> None:
    """The registered csv_extraction spec is reachable via the registry."""
    spec = paxman.capabilities.registry.get_latest("csv_extraction").spec
    assert spec.id == "csv_extraction"
    assert spec.version == "1.0"
    assert spec.tier.value == 1  # LOCAL_DETERMINISTIC
    assert spec.deterministic is True


def test_csv_extractor_invokes_against_csv_input() -> None:
    """A direct invoke() against the CSV fixture produces 4 non-empty suppliers."""
    cap = paxman.capabilities.registry.get_latest("csv_extraction")
    csv_bytes = _load_csv()
    ctx = CapabilityContext(
        raw_input=csv_bytes,
        field_path="supplier",
        field_type_name="STRING",
        config={"column": "supplier"},
    )
    result = cap.invoke(ctx)
    # Row 3 (INV-003) has an empty supplier and is silently skipped.
    assert [c.value for c in result.candidates] == [
        "ACME Corp",
        "Globex",
        "Initech",
        "Soylent",
    ]
    # Every candidate carries the format-specific evidence.
    for candidate in result.candidates:
        ev = candidate.evidence_refs[0]
        assert ev.capability_id == "csv_extraction"
        assert ev.context["csv_column"] == "supplier"
        assert isinstance(ev.context["row_index"], int)
        assert ev.context["header"] == [
            "invoice_id",
            "supplier",
            "amount",
            "currency",
        ]


def test_json_path_extractor_invokes_against_csv_input() -> None:
    """json_path_extraction can extract from a JSON-encoded CSV row.

    The CSV file is not JSON, but we serialize a row to JSON to exercise
    the extractor through the same public surface. The format-specific
    capability works on any JSON, not on the contract's field type.
    """
    cap = paxman.capabilities.registry.get_latest("json_path_extraction")
    json_bytes = b'{"supplier": "ACME Corp", "amount": 1234.56}'
    ctx = CapabilityContext(
        raw_input=json_bytes,
        field_path="supplier",
        field_type_name="STRING",
        config={"pointer": "/supplier"},
    )
    result = cap.invoke(ctx)
    assert [c.value for c in result.candidates] == ["ACME Corp"]
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["json_pointer"] == "/supplier"


def test_xpath_extractor_invokes_against_xml_input() -> None:
    """xpath_extraction works on XML, not CSV. We pass a synthetic XML doc."""
    cap = paxman.capabilities.registry.get_latest("xpath_extraction")
    xml_bytes = b"<root><supplier>ACME Corp</supplier></root>"
    ctx = CapabilityContext(
        raw_input=xml_bytes,
        field_path="supplier",
        field_type_name="STRING",
        config={"xpath": "/root/supplier"},
    )
    result = cap.invoke(ctx)
    assert [c.value for c in result.candidates] == ["ACME Corp"]
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["xpath"] == "/root/supplier"


def test_normalize_artifact_has_stable_replay_hash() -> None:
    """normalize() on the CSV input produces a stable replay_hash.

    The artifact's replay_hash is byte-equal across two runs of the
    same input, even though the slice does not yet wire the new
    extractors into the executor (the fields stay unresolved, but
    the artifact is still deterministic).
    """
    csv_bytes = _load_csv()

    first = paxman.normalize(input_data=csv_bytes, contract=DICT_DSL_WITH_CSV_EXTRACTION)
    second = paxman.normalize(input_data=csv_bytes, contract=DICT_DSL_WITH_CSV_EXTRACTION)
    assert first.replay_hash == second.replay_hash
    assert len(first.replay_hash) == 64  # SHA-256 hex
