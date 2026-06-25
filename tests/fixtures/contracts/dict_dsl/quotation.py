"""Dict DSL quotation contract — the quotation use case.

Paired with ``pydantic/quotation.py`` and ``json_schema/quotation.json``.
"""

DICT_DSL_QUOTATION: dict[str, object] = {
    "id": "quotation-v1",
    "version": "1",
    "fields": [
        {
            "name": "quote_number",
            "type": "STRING",
            "required": True,
            "description": "Unique quote identifier.",
            "constraints": [
                {"kind": "pattern", "params": {"regex": r"^Q-\d{6}$"}},
            ],
        },
        {
            "name": "supplier_name",
            "type": "STRING",
            "required": True,
            "description": "Legal name of the supplier.",
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 500}},
            ],
        },
        {
            "name": "total_amount",
            "type": "MONEY",
            "required": True,
            "description": "Total quote amount.",
            "tags": ["currency-sensitive", "high-stakes"],
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
            ],
        },
        {
            "name": "currency_code",
            "type": "ENUM",
            "required": True,
            "description": "ISO-4217 currency code.",
            "tags": ["currency-sensitive"],
            "constraints": [
                {
                    "kind": "enum",
                    "params": {"values": ["USD", "EUR", "GBP", "JPY"]},
                },
            ],
        },
        {
            "name": "valid_until",
            "type": "DATE",
            "required": True,
            "description": "Quote expiration date.",
        },
        {
            "name": "notes",
            "type": "STRING",
            "required": False,
            "description": "Free-form notes accompanying the quote.",
            "constraints": [
                {"kind": "max_length", "params": {"max": 2000}},
            ],
        },
        {
            "name": "line_items",
            "type": "ARRAY",
            "required": False,
            "default": [],
            "description": "Individual quote line items.",
        },
    ],
    "policy": {
        "confidence_floor": 0.85,
        "unresolved_acceptable": True,
    },
}
