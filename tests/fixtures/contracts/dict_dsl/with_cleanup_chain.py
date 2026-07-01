"""Dict DSL contract that exercises the full cleanup-transform chain.

The contract mirrors a minimal invoice shape so the integration
test can exercise the ``regex_extraction`` → ``case_normalization``
→ ``trim_extraction`` chain end-to-end against a real Dict DSL
contract on the ``sample_invoices.csv`` fixture.

Paired fixtures: ``tests/fixtures/inputs/sample_invoices.csv``,
``tests/integration/capabilities/test_cleanup_transforms_chain.py``.

Features exercised:

- ``supplier``: STRING with ``min_length`` constraint; the
  integration test wires a chain of three capabilities for this
  field at the planner layer:
  ``regex_extraction`` (extract a candidate) →
  ``case_normalization`` (normalize the case) →
  ``trim_extraction`` (strip leading/trailing junk).
- ``amount``: DECIMAL with ``min_value`` constraint.
- ``currency_code``: ENUM with ``iso_4217`` constraint.

The contract itself is field-type and constraint symmetric with
``tests/fixtures/contracts/dict_dsl/with_csv_extraction.py`` so
the two integration tests can share their assertion patterns
without coupling.
"""

DICT_DSL_WITH_CLEANUP_CHAIN: dict[str, object] = {
    "id": "with-cleanup-chain-v1",
    "version": "1",
    "fields": [
        {
            "name": "supplier",
            "type": "STRING",
            "required": True,
            "description": (
                "The supplier's legal name (cleaned up via the full "
                "regex_extraction -> case_normalization -> trim_extraction chain)."
            ),
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 200}},
            ],
        },
        {
            "name": "amount",
            "type": "DECIMAL",
            "required": True,
            "description": "Invoice amount as a decimal.",
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
            ],
        },
        {
            "name": "currency_code",
            "type": "ENUM",
            "required": True,
            "description": "ISO-4217 currency code.",
            "constraints": [
                {
                    "kind": "enum",
                    "params": {
                        "values": ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"],
                    },
                },
                {"kind": "iso_4217", "params": {}},
            ],
        },
    ],
    "policy": {
        "confidence_floor": 0.0,
        "unresolved_acceptable": True,
    },
}
