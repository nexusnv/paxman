"""Safety regressions for truthful field-resolution outcomes.

These tests exercise the public pipeline rather than mocked subsystem
boundaries.  A document-level text payload is evidence about the document,
not evidence that it is the value of every string field in a contract.
"""

from __future__ import annotations

import paxman
import paxman.capabilities.v1  # Register built-in capabilities for this public-path test.
import paxman.contract.adapters.dict_dsl  # Register the Dict DSL adapter.


def test_plain_text_does_not_resolve_a_field_to_the_entire_document() -> None:
    """An unconfigured text field remains unresolved instead of using all input."""
    contract: dict[str, object] = {
        "id": "truthful-plain-text",
        "fields": [
            {
                "name": "supplier",
                "type": "STRING",
                "required": True,
            }
        ],
    }

    artifact = paxman.normalize(
        input_data="Supplier: ACME Corp\nTotal: 12",
        contract=contract,
    )

    assert artifact.status is paxman.Status.UNRESOLVED
    assert artifact.normalized_data == {}
    assert artifact.unresolved_fields == ["supplier"]
    assert artifact.field_results["supplier"].value is None
    assert artifact.field_results["supplier"].status is paxman.Status.UNRESOLVED
