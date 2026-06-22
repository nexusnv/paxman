"""All 9 V1 field types in a single model — the canonical coverage fixture.

Paired with ``json_schema/all_v1_types.json`` and ``dict_dsl/all_v1_types.py``.

Features exercised — exactly one field per V1 ``FieldType``:
- ``s``: STRING (``str``)
- ``i``: INTEGER (``int``)
- ``d``: DECIMAL (``float``)
- ``b``: BOOLEAN (``bool``)
- ``date``: DATE (``datetime.date``; V1 represents dates as ISO 8601 strings)
- ``e``: ENUM (``Literal['a', 'b', 'c']``)
- ``o``: OBJECT (``dict``)
- ``arr``: ARRAY (``list[int]``)
- ``m``: MONEY (``Money`` subclass from the Pydantic adapter)
"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, Field

from paxman.contract.adapters.pydantic import Money


class AllV1Types(BaseModel):
    """Contract with exactly one field per V1 ``FieldType``."""

    s: str = Field(..., description="STRING field.")
    i: int = Field(..., description="INTEGER field.")
    d: float = Field(..., description="DECIMAL field.")
    b: bool = Field(..., description="BOOLEAN field.")
    date: datetime.date = Field(..., description="DATE field (ISO 8601).")
    e: Literal["a", "b", "c"] = Field(..., description="ENUM field with three allowed values.")
    o: dict = Field(..., description="OBJECT field (arbitrary dict).")
    arr: list[int] = Field(..., description="ARRAY field of integers.")
    m: Money = Field(..., description="MONEY field (amount + ISO-4217 currency).")
