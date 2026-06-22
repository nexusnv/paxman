"""Dict DSL all-9-types contract — one field per V1 ``FieldType``.

Paired with ``pydantic/all_v1_types.py`` and ``json_schema/all_v1_types.json``.

Features exercised — exactly one field per V1 ``FieldType``:
- ``s``: STRING
- ``i``: INTEGER
- ``d``: DECIMAL
- ``b``: BOOLEAN
- ``date``: DATE
- ``e``: ENUM (with ``enum`` constraint listing allowed values)
- ``o``: OBJECT
- ``arr``: ARRAY
- ``m``: MONEY (with ``iso_4217`` constraint)
"""

DICT_DSL_ALL_V1_TYPES: dict[str, object] = {
    "id": "all-v1-types-v1",
    "version": "1",
    "fields": [
        {
            "name": "s",
            "type": "STRING",
            "required": True,
            "description": "STRING field.",
        },
        {
            "name": "i",
            "type": "INTEGER",
            "required": True,
            "description": "INTEGER field.",
        },
        {
            "name": "d",
            "type": "DECIMAL",
            "required": True,
            "description": "DECIMAL field.",
        },
        {
            "name": "b",
            "type": "BOOLEAN",
            "required": True,
            "description": "BOOLEAN field.",
        },
        {
            "name": "date",
            "type": "DATE",
            "required": True,
            "description": "DATE field (ISO 8601).",
        },
        {
            "name": "e",
            "type": "ENUM",
            "required": True,
            "description": "ENUM field with three allowed values.",
            "constraints": [
                {"kind": "enum", "params": {"values": ["a", "b", "c"]}},
            ],
        },
        {
            "name": "o",
            "type": "OBJECT",
            "required": True,
            "description": "OBJECT field (arbitrary dict).",
        },
        {
            "name": "arr",
            "type": "ARRAY",
            "required": True,
            "description": "ARRAY field of integers.",
        },
        {
            "name": "m",
            "type": "MONEY",
            "required": True,
            "description": "MONEY field (amount + ISO-4217 currency).",
            "tags": ["currency-sensitive"],
            "constraints": [
                {"kind": "iso_4217", "params": {}},
            ],
        },
    ],
}
