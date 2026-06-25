"""Dict DSL receipt contract — the receipt use case.

Paired with ``pydantic/receipt.py`` and ``json_schema/receipt.json``.
"""

DICT_DSL_RECEIPT: dict[str, object] = {
    "id": "receipt-v1",
    "version": "1",
    "fields": [
        {
            "name": "merchant_name",
            "type": "STRING",
            "required": True,
            "description": "Legal name of the merchant.",
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 200}},
            ],
        },
        {
            "name": "total",
            "type": "MONEY",
            "required": True,
            "description": "Total transaction amount.",
            "tags": ["currency-sensitive"],
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
                    "params": {"values": ["USD", "EUR", "GBP", "JPY", "CHF"]},
                },
            ],
        },
        {
            "name": "transaction_date",
            "type": "DATE",
            "required": True,
        },
        {
            "name": "card_last4",
            "type": "STRING",
            "required": False,
            "description": "Last 4 digits of the payment card.",
            "constraints": [
                {"kind": "pattern", "params": {"regex": r"^\d{4}$"}},
            ],
        },
        {
            "name": "category",
            "type": "ENUM",
            "required": False,
            "default": "OTHER",
            "description": "Spending category.",
            "constraints": [
                {
                    "kind": "enum",
                    "params": {
                        "values": ["FOOD", "TRAVEL", "OFFICE", "OTHER"],
                    },
                },
            ],
        },
    ],
    "policy": {
        "confidence_floor": 0.80,
        "unresolved_acceptable": True,
    },
}
