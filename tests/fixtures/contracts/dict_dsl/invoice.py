"""Dict DSL invoice contract — the canonical invoice use case.

Paired with ``pydantic/invoice.py`` and ``json_schema/invoice.json``.

Based on Example 2 of the Dict DSL specification
(``docs/specs/dict-dsl-spec.md``).

Features exercised:
- ``supplier_name``: STRING with ``min_length`` + ``max_length`` constraints
  and a ``pii`` tag.
- ``currency_code``: ENUM with ``iso_4217`` constraint and a
  ``currency-sensitive`` tag.
- ``total_amount``: MONEY with ``min_value`` constraint and
  ``currency-sensitive`` + ``high-stakes`` tags.
- ``invoice_date``: DATE (required).
- ``line_items``: ARRAY (optional, default ``[]``).
- ``paid``: BOOLEAN (optional, default ``False``).
- Contract-level ``policy`` with ``confidence_floor`` and
  ``unresolved_acceptable``.
"""

DICT_DSL_INVOICE: dict[str, object] = {
    "id": "invoice-v1",
    "version": "1",
    "fields": [
        {
            "name": "supplier_name",
            "type": "STRING",
            "required": True,
            "description": "Legal name of the supplier.",
            "tags": ["pii"],
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 500}},
            ],
        },
        {
            "name": "currency_code",
            "type": "ENUM",
            "required": True,
            "description": "ISO-4217 currency code for the invoice.",
            "tags": ["currency-sensitive"],
            "constraints": [
                {
                    "kind": "enum",
                    "params": {"values": ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"]},
                },
                {"kind": "iso_4217", "params": {}},
            ],
        },
        {
            "name": "total_amount",
            "type": "MONEY",
            "required": True,
            "description": "Total invoice amount.",
            "tags": ["currency-sensitive", "high-stakes"],
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
            ],
        },
        {
            "name": "invoice_date",
            "type": "DATE",
            "required": True,
        },
        {
            "name": "line_items",
            "type": "ARRAY",
            "required": False,
            "default": [],
            "description": "Individual line items on the invoice.",
        },
        {
            "name": "paid",
            "type": "BOOLEAN",
            "required": False,
            "default": False,
        },
    ],
    "policy": {
        "confidence_floor": 0.85,
        "unresolved_acceptable": False,
    },
}
