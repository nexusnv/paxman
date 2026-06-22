"""Dict DSL MONEY coverage — exercises the MONEY field type.

Paired with ``pydantic/with_money.py`` and ``json_schema/with_money.json``.

Features exercised:
- ``amount``: MONEY (required) — exercises the MONEY type with an
  ``iso_4217`` constraint and a ``currency-sensitive`` tag.
- ``notes``: STRING (required) — a simple accompanying string field.
"""

DICT_DSL_WITH_MONEY: dict[str, object] = {
    "id": "with-money-v1",
    "version": "1",
    "fields": [
        {
            "name": "amount",
            "type": "MONEY",
            "required": True,
            "description": "Monetary amount with ISO-4217 currency.",
            "tags": ["currency-sensitive"],
            "constraints": [
                {"kind": "iso_4217", "params": {}},
            ],
        },
        {
            "name": "notes",
            "type": "STRING",
            "required": True,
            "description": "Free-form notes accompanying the money value.",
        },
    ],
}
