"""Dict DSL contract that uses ``csv_extraction`` for the supplier field.

The contract mirrors a minimal invoice shape so the integration test can
exercise the full ``paxman.normalize()`` pipeline against a real CSV input.

Paired fixtures: ``tests/fixtures/inputs/sample_invoices.csv``.

Features exercised:

- ``supplier``: STRING with ``min_length`` constraint; the integration
  test wires ``csv_extraction`` for this field at the planner layer.
- ``amount``: DECIMAL with ``min_value`` constraint.
- ``currency_code``: ENUM with ``iso_4217`` constraint.
"""

DICT_DSL_WITH_CSV_EXTRACTION: dict[str, object] = {
    "id": "with-csv-extraction-v1",
    "version": "1",
    "fields": [
        {
            "name": "supplier",
            "type": "STRING",
            "required": True,
            "description": "The supplier's legal name (extracted from CSV).",
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
