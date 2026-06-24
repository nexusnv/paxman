"""Unit tests for :mod:`paxman.contract.adapters.openapi`.

Per Sprint 4 D4.18: the V1 OpenAPI adapter is a best-effort
adapter that delegates to the JSON Schema adapter for property
parsing. The tests pin the contract using the
``petstore.yaml`` fixture.
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
    Path(__file__).parent.parent / "fixtures" / "contracts" / "openapi" / "petstore.yaml"
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
    # The real petstore vendor fixture has ``info.title: Swagger Petstore``.
    assert contract.id == "Swagger Petstore"
    field_paths = {f.path for f in contract.fields}
    assert "id" in field_paths
    assert "name" in field_paths
    assert "tag" in field_paths


def test_adapt_petstore_field_types() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    assert by_path["id"].type is FieldType.INTEGER
    assert by_path["name"].type is FieldType.STRING
    assert by_path["tag"].type is FieldType.STRING


def test_adapt_petstore_required_set() -> None:
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    assert by_path["id"].required is True
    assert by_path["name"].required is True
    # ``tag`` is optional in Pet.
    assert by_path["tag"].required is False


def test_adapt_petstore_no_constraints_on_basic_string() -> None:
    """The official petstore vendor fixture does not define length constraints."""
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    assert by_path["name"].type is FieldType.STRING
    # No min_length / max_length are specified in the fixture.
    assert not any(
        c.kind.value in ("min_length", "max_length") for c in by_path["name"].constraints
    )


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
    """Schemas with ``$ref`` are resolved and inlined by the adapter.

    The petstore vendor fixture uses ``$ref`` in its path responses
    (e.g. ``$ref: "#/components/schemas/Pets"``).  Component-schema
    fields stored inline are plain types (``tag`` is ``STRING``).
    """
    doc = _load_petstore()
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    # ``tag`` is defined inline as ``type: string`` (not a $ref).
    assert by_path["tag"].type is FieldType.STRING


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
    assert contract.id == "Swagger Petstore"


def test_adapt_accepts_3_1_x() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.1.0"
    contract = OpenApiAdapter().adapt(doc)
    assert contract.id == "Swagger Petstore"


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
    assert "Swagger Petstore" in exported["components"]["schemas"]


def test_export_rejects_non_canonical_contract() -> None:
    with pytest.raises(InvalidContractError, match="export expects CanonicalContract"):
        OpenApiAdapter().export("not a contract")  # type: ignore[arg-type]
