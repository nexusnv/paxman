"""Integration test — format-aware executor auto-dispatch (issue #73).

End-to-end DoD: a CSV byte string + a Dict DSL contract whose
fields declare ``format_hints=["csv"]`` resolves to values
extracted by the ``csv_extraction`` capability, **without** the
caller calling ``paxman.capabilities.registry.register(...)``
(ADR-0012 self-registration is in effect).

Also pins the "default behavior unchanged" contract: a contract
without ``format_hints`` is dispatched exactly as on
``v1.1.0`` HEAD.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import paxman
import paxman.contract.adapters.dict_dsl  # self-registration

pytestmark = pytest.mark.integration


_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


def _load_csv() -> bytes:
    return (_FIXTURES_DIR / "inputs" / "sample_invoices.csv").read_bytes()


def test_normalize_resolves_csv_field_via_format_hint() -> None:
    """A CSV byte string + a contract whose fields declare
    ``format_hints=["csv"]`` resolves to values extracted by
    the ``csv_extraction`` capability."""
    contract_dict: dict[str, object] = {
        "id": "csv_with_format_hint",
        "version": "1.0",
        "fields": [
            {
                "name": "supplier",
                "type": "STRING",
                "required": True,
                "format_hints": ["csv"],
            },
        ],
    }
    csv_bytes = _load_csv()
    result = paxman.normalize(input_data=csv_bytes, contract=contract_dict)
    # The first row of the fixture is INV-001 / ACME Corp.
    # The contract has only the supplier field; csv_extraction
    # extracts the supplier column; validation accepts; reconciler
    # grades; artifact has normalized_data["supplier"] == "ACME Corp".
    assert "supplier" in result.normalized_data
    assert result.normalized_data["supplier"] == "ACME Corp"


def test_normalize_field_without_format_hint_unchanged() -> None:
    """Regression lock: a field without ``format_hints`` is
    dispatched exactly as on v1.1.0 HEAD. We use a contract
    with the same shape but no ``format_hints`` key, and
    assert the result is UNRESOLVED for the supplier field
    (the existing v1.1.0 behavior)."""
    contract_dict: dict[str, object] = {
        "id": "no_format_hint",
        "version": "1.0",
        "fields": [
            {"name": "supplier", "type": "STRING", "required": True},
            {"name": "amount", "type": "DECIMAL", "required": True},
            {"name": "currency_code", "type": "STRING", "required": True},
        ],
    }
    csv_bytes = _load_csv()
    result = paxman.normalize(input_data=csv_bytes, contract=contract_dict)
    # On v1.1.0 HEAD, the executor does not auto-dispatch; the
    # supplier field is UNRESOLVED. This pins the "default
    # behavior unchanged" contract.
    assert "supplier" in result.unresolved_fields
