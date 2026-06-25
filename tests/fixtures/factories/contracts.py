"""Contract factories — Pydantic, Dict DSL, JSON Schema, OpenAPI.

Per Sprint 7 D7.4 and ``docs/TEST_DATA.md`` §7.1, these factories
generate realistic-looking contract fixtures.

Factories:

- :class:`DictDSLInvoiceFactory` — a Dict DSL invoice contract.
- :class:`PydanticInvoiceFactory` — a Pydantic invoice model class.
- :class:`JsonSchemaInvoiceFactory` — a JSON Schema invoice.
- :class:`OpenAPIPetstoreFactory` — a minimal OpenAPI YAML spec.
"""

from __future__ import annotations

import factory

# Use the project-wide seed.
from tests.fixtures.factories import SEED  # noqa: F401


class DictDSLInvoiceFactory(factory.DictFactory):
    """A Dict DSL invoice contract (per :mod:`paxman.contract.dict_dsl`)."""

    id = factory.Faker("bothify", text="invoice-########")
    version = "1"
    fields = [
        {
            "name": "supplier_name",
            "type": "STRING",
            "required": True,
            "description": "Legal name of the supplier.",
        },
        {
            "name": "total_amount",
            "type": "MONEY",
            "required": True,
            "description": "Total invoice amount.",
            "constraints": [{"kind": "min_value", "params": {"min": 0}}],
        },
        {
            "name": "currency_code",
            "type": "ENUM",
            "required": True,
            "description": "ISO-4217 currency code.",
            "constraints": [
                {
                    "kind": "enum",
                    "params": {"values": ["USD", "EUR", "GBP", "JPY"]},
                }
            ],
        },
        {"name": "invoice_date", "type": "DATE", "required": True},
    ]
    policy = {"confidence_floor": 0.85, "unresolved_acceptable": False}


class PydanticInvoiceFactory(factory.Factory):
    """A Pydantic invoice model class (per :mod:`paxman.contract.pydantic`).

    Returns a Pydantic ``BaseModel`` *class* (not an instance). This
    is what callers pass to ``paxman.normalize()``.

    Example::

        Invoice = PydanticInvoiceFactory()
        artifact = paxman.normalize(input_data=text, contract=Invoice)
    """

    class Meta:
        model = type

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> type:  # type: ignore[override]
        from pydantic import BaseModel, Field
        import datetime

        class _Invoice(BaseModel):
            """Dynamically generated invoice model."""

            supplier_name: str = Field(..., min_length=1, max_length=500)
            total: float = Field(..., ge=0)
            currency: str = Field(..., pattern=r"^[A-Z]{3}$")
            invoice_date: datetime.date
            paid: bool = False

        _Invoice.__name__ = "GeneratedInvoice"
        _Invoice.__qualname__ = _Invoice.__name__
        return _Invoice


class JsonSchemaInvoiceFactory(factory.Factory):
    """A JSON Schema invoice (per :mod:`paxman.contract.json_schema`)."""

    class Meta:
        model = dict

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> dict[str, object]:  # type: ignore[override]
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"Invoice_{factory.Faker._get_faker().bothify('######')}",
            "type": "object",
            "properties": {
                "supplier_name": {"type": "string", "minLength": 1, "maxLength": 500},
                "total": {"type": "number", "minimum": 0},
                "currency": {"type": "string", "pattern": r"^[A-Z]{3}$"},
                "paid": {"type": "boolean", "default": False},
            },
            "required": ["supplier_name", "total", "currency"],
        }


_OPENAPI_YAML = """openapi: 3.0.0
info:
  title: Petstore (generated)
  version: 1.0.0
paths:
  /pets:
    get:
      summary: List pets
      responses:
        '200':
          description: OK
"""


class OpenAPIPetstoreFactory(factory.Factory):
    """A minimal OpenAPI 3.0 petstore spec (YAML string)."""

    class Meta:
        model = str

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        return _OPENAPI_YAML
