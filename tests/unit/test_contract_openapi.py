"""Unit tests for :mod:`paxman.contract.adapters.openapi`.

Per Sprint 4 D4.18: the V1 OpenAPI adapter is a best-effort
adapter that delegates to the JSON Schema adapter for property
parsing. The tests pin the contract using the
``petstore_3_0.yaml`` fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paxman.contract.adapters.openapi import OpenApiAdapter
from paxman.errors import InvalidContractError
from paxman.types import FieldType

pytestmark = pytest.mark.unit


# --- fixture loading -------------------------------------------------


_PETSTORE_PATH: Path = (
    Path(__file__).parent.parent / "fixtures" / "contracts" / "openapi" / "petstore_3_0.yaml"
)


def _load_petstore() -> dict:
    """Load the vendored petstore 3.0 YAML fixture."""
    import yaml

    with _PETSTORE_PATH.open() as f:
        result: dict = yaml.safe_load(f)
    return result


# --- basic adapt -----------------------------------------------------


def test_adapt_petstore_produces_canonical_contract() -> None:
    doc = _load_petstore()
    adapter = OpenApiAdapter()
    contract = adapter.adapt(doc)
    # The Petstore doc has ``info.title: Petstore``.
    assert contract.id == "Petstore"
    field_paths = {f.path for f in contract.fields}
    assert "id" in field_paths
    assert "name" in field_paths
    assert "tag" in field_paths
    assert "photoUrls" in field_paths
    assert "status" in field_paths


def test_adapt_petstore_field_types() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    assert by_path["id"].type is FieldType.INTEGER
    assert by_path["name"].type is FieldType.STRING
    assert by_path["tag"].type is FieldType.OBJECT  # inlined from Tag
    assert by_path["photoUrls"].type is FieldType.ARRAY
    assert by_path["status"].type is FieldType.ENUM


def test_adapt_petstore_required_set() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    assert by_path["id"].required is True
    assert by_path["name"].required is True
    assert by_path["photoUrls"].required is True
    assert by_path["status"].required is True
    # ``tag`` is optional in Pet.
    assert by_path["tag"].required is False


def test_adapt_petstore_name_constraints() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    kinds = [c.kind.value for c in by_path["name"].constraints]
    assert "min_length" in kinds
    assert "max_length" in kinds


def test_adapt_petstore_status_enum_values() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    enum = by_path["status"].enum_values
    assert enum is not None
    assert "available" in enum
    assert "pending" in enum
    assert "sold" in enum


# --- reject list (V2 features) --------------------------------------


def test_adapt_rejects_top_level_oneof() -> None:
    doc = _load_petstore()
    doc["oneOf"] = [{"$ref": "#/components/schemas/Pet"}]
    adapter = OpenApiAdapter()
    with pytest.raises(InvalidContractError, match="V2-only keyword"):
        adapter.adapt(doc)


def test_adapt_rejects_top_level_anyof() -> None:
    doc = _load_petstore()
    doc["anyOf"] = [{"$ref": "#/components/schemas/Pet"}]
    with pytest.raises(InvalidContractError, match="V2-only keyword"):
        OpenApiAdapter().adapt(doc)


def test_adapt_rejects_schema_level_allof() -> None:
    doc = _load_petstore()
    doc["components"]["schemas"]["Pet"]["allOf"] = [{"$ref": "#/components/schemas/Tag"}]
    with pytest.raises(InvalidContractError, match="V2-only keyword"):
        OpenApiAdapter().adapt(doc)


def test_adapt_rejects_discriminator() -> None:
    doc = _load_petstore()
    doc["components"]["schemas"]["Pet"]["discriminator"] = {"propertyName": "kind"}
    with pytest.raises(InvalidContractError, match="V2-only keyword"):
        OpenApiAdapter().adapt(doc)


# --- ref handling ---------------------------------------------------


def test_adapt_resolves_components_schemas_ref() -> None:
    """The petstore's ``tag: $ref: #/components/schemas/Tag`` is inlined."""
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    # The tag field is inlined as OBJECT (the JSON Schema
    # adapter sees the Tag schema and treats it as a generic
    # object with id + name).
    assert by_path["tag"].type is FieldType.OBJECT


def test_adapt_rejects_unresolvable_ref() -> None:
    doc = _load_petstore()
    doc["components"]["schemas"]["Pet"]["properties"]["missing"] = {
        "$ref": "#/components/schemas/DoesNotExist"
    }
    with pytest.raises(InvalidContractError, match="does not resolve"):
        OpenApiAdapter().adapt(doc)


def test_adapt_rejects_non_components_ref() -> None:
    doc = _load_petstore()
    doc["components"]["schemas"]["Pet"]["properties"]["bad"] = {
        "$ref": "https://example.com/schema.json"
    }
    with pytest.raises(InvalidContractError, match="not supported by the V1 adapter"):
        OpenApiAdapter().adapt(doc)


def test_adapt_rejects_non_string_ref() -> None:
    doc = _load_petstore()
    doc["components"]["schemas"]["Pet"]["properties"]["bad"] = {"$ref": 42}
    with pytest.raises(InvalidContractError, match="non-string"):
        OpenApiAdapter().adapt(doc)


# --- version handling -----------------------------------------------


def test_adapt_rejects_missing_openapi_field() -> None:
    with pytest.raises(InvalidContractError, match="missing the 'openapi'"):
        OpenApiAdapter().adapt({"info": {"title": "x"}, "components": {"schemas": {}}})


def test_adapt_rejects_unsupported_version() -> None:
    with pytest.raises(InvalidContractError, match="is not supported"):
        OpenApiAdapter().adapt(
            {"openapi": "2.0", "info": {"title": "x"}, "components": {"schemas": {}}}
        )


def test_adapt_accepts_3_0_x() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.0.0"
    contract = OpenApiAdapter().adapt(doc)
    assert contract.id == "Petstore"


def test_adapt_accepts_3_1_x() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.1.0"
    contract = OpenApiAdapter().adapt(doc)
    assert contract.id == "Petstore"


# --- input validation -----------------------------------------------


def test_adapt_rejects_non_dict() -> None:
    with pytest.raises(InvalidContractError, match="requires a dict"):
        OpenApiAdapter().adapt("not a dict")  # type: ignore[arg-type]


def test_adapt_rejects_empty_schemas() -> None:
    with pytest.raises(InvalidContractError, match="empty"):
        OpenApiAdapter().adapt(
            {
                "openapi": "3.0.3",
                "info": {"title": "Empty"},
                "components": {"schemas": {}},
            }
        )


# --- format_id / export ---------------------------------------------


def test_format_id() -> None:
    assert OpenApiAdapter().format_id == "openapi:3.x"


def test_export_round_trip() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    exported = OpenApiAdapter().export(contract)
    assert exported["openapi"] == "3.0.3"
    # The export uses the contract id as the schema key (since
    # the V1 model is one canonical contract per document).
    assert "Petstore" in exported["components"]["schemas"]


def test_export_rejects_non_canonical_contract() -> None:
    with pytest.raises(InvalidContractError, match="export expects CanonicalContract"):
        OpenApiAdapter().export("not a contract")  # type: ignore[arg-type]
