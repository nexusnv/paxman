"""JSON Schema invoice contract — the canonical invoice use case.

Paired with ``pydantic/invoice.py`` and ``dict_dsl/invoice.py``.

The ``JSON_SCHEMA_INVOICE`` constant exposes the JSON schema as a
``str`` (the on-disk JSON file's contents) so it can be passed
directly to ``paxman.normalize()``. The JSON Schema adapter parses
the string at adapt time.
"""

from __future__ import annotations

import json
import pathlib

#: The full path to the JSON schema file.
_SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "invoice.json"

#: The JSON schema (as a string) for the canonical invoice use case.
JSON_SCHEMA_INVOICE: str = _SCHEMA_PATH.read_text(encoding="utf-8")


def load_json_schema_invoice_dict() -> dict[str, object]:
    """Return the JSON Schema invoice as a parsed dict.

    Returns:
        The parsed JSON schema dictionary.
    """
    return json.loads(JSON_SCHEMA_INVOICE)
