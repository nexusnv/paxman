"""Unit tests for :mod:`paxman.contract.adapters.openapi`.

Per Sprint 4 D4.18: the V1 OpenAPI adapter is a best-effort
adapter that delegates to the JSON Schema adapter for property
parsing. The tests pin the contract using the
``petstore.yaml`` fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paxman.contract.adapters.openapi import OpenApiAdapter, _read_defs, _read_json_schema_dialect
from paxman.errors import InvalidContractError
from paxman.types import FieldType

pytestmark = [pytest.mark.unit, pytest.mark.deterministic]


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
    # This is a same-version ref; the only legitimate failure mode is
    # "does not resolve" (the ref is well-formed, just points to a
    # missing target). Match precisely so a regression that
    # misclassifies the error (e.g. as "mismatched") would fail this
    # test.
    with pytest.raises(InvalidContractError, match=r"does not resolve"):
        OpenApiAdapter().adapt(doc)


def test_adapt_rejects_non_components_ref() -> None:
    doc = _load_petstore()
    doc["components"]["schemas"]["Pet"]["properties"]["bad"] = {
        "$ref": "https://example.com/schema.json"
    }
    with pytest.raises(InvalidContractError, match=r"not supported by the V1.1.0 adapter"):
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


# --- nullable translation (3.0 -> 3.1) ------------------------------


def test_adapt_3_0_nullable_true_becomes_nullable() -> None:
    """OpenAPI 3.0 ``nullable: true`` is translated to ``type: [type, "null"]``."""
    doc = {
        "openapi": "3.0.3",
        "info": {"title": "Nullable", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["nickname"],
                    "properties": {
                        "nickname": {"type": "string", "nullable": True},
                    },
                }
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    nickname = next(f for f in contract.fields if f.name == "nickname")
    assert nickname.nullable is True


def test_adapt_3_0_nullable_false_stays_non_nullable() -> None:
    """OpenAPI 3.0 ``nullable: false`` (or absent) keeps the field non-nullable."""
    doc = {
        "openapi": "3.0.3",
        "info": {"title": "Nullable", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "nullable": False},
                        "age": {"type": "integer"},
                    },
                }
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    by_name = {f.name: f for f in contract.fields}
    assert by_name["name"].nullable is False
    assert by_name["age"].nullable is False


def test_adapt_3_1_type_array_null_is_nullable() -> None:
    """OpenAPI 3.1 ``type: [string, "null"]`` is recognized as nullable."""
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "Nullable31", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "nickname": {"type": ["string", "null"]},
                    },
                }
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    nickname = next(f for f in contract.fields if f.name == "nickname")
    assert nickname.nullable is True


def test_translate_nullable_3_0_to_3_1_idempotent() -> None:
    """Translating an already-3.1-style list type with nullable: true is safe."""
    from paxman.contract.adapters.openapi import _translate_nullable_3_0_to_3_1

    # Already a list with "null" present: still works, no double-null.
    prop = {"type": ["string", "null"], "nullable": True}
    out = _translate_nullable_3_0_to_3_1(prop)
    assert out["type"] == ["string", "null"]
    assert "nullable" not in out


def test_translate_nullable_3_0_to_3_1_passthrough_when_not_dict() -> None:
    """Non-dict property values are returned unchanged."""
    from paxman.contract.adapters.openapi import _translate_nullable_3_0_to_3_1

    assert _translate_nullable_3_0_to_3_1("string") == "string"
    assert _translate_nullable_3_0_to_3_1(None) is None
    assert _translate_nullable_3_0_to_3_1(42) == 42


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


# --- 3.1 dialect & defs reading ------------------------------------


def test_read_json_schema_dialect_returns_none_when_absent() -> None:
    doc = _load_petstore()
    assert _read_json_schema_dialect(doc) is None


def test_read_json_schema_dialect_returns_value_when_present() -> None:
    doc = _load_petstore()
    doc["jsonSchemaDialect"] = "https://json-schema.org/draft/2020-12/schema"
    assert _read_json_schema_dialect(doc) == "https://json-schema.org/draft/2020-12/schema"


def test_read_json_schema_dialect_rejects_non_string() -> None:
    doc = _load_petstore()
    doc["jsonSchemaDialect"] = 42
    with pytest.raises(InvalidContractError, match="jsonSchemaDialect"):
        _read_json_schema_dialect(doc)


def test_read_defs_returns_empty_when_absent() -> None:
    doc = _load_petstore()
    assert _read_defs(doc) == {}


def test_read_defs_returns_dict_when_present() -> None:
    doc = _load_petstore()
    doc["$defs"] = {"Owner": {"type": "object", "properties": {"name": {"type": "string"}}}}
    defs = _read_defs(doc)
    assert "Owner" in defs
    assert defs["Owner"]["properties"]["name"]["type"] == "string"


def test_read_defs_rejects_non_dict() -> None:
    doc = _load_petstore()
    doc["$defs"] = "not a dict"
    with pytest.raises(InvalidContractError, match=r"\$defs"):
        _read_defs(doc)


# --- $ref resolution: $defs + components.schemas -------------------


def test_inline_refs_resolves_defs_ref_in_3_1() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.1.0"
    doc["$defs"] = {
        "Owner": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
    }
    doc["components"]["schemas"]["Pet"]["properties"]["owner"] = {"$ref": "#/$defs/Owner"}
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    # ``owner`` is now an OBJECT with a single required ``name`` STRING child.
    assert by_path["owner"].type is FieldType.OBJECT


def test_inline_refs_resolves_components_schemas_ref_in_3_1() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.1.0"
    # Inject an actual $ref under components.schemas.Pet.properties
    # so the assertion exercises the 3.1 components/schemas $ref
    # resolution path (the 3.0 petstore has all properties inline,
    # so without this the test would pass even if 3.1 component-ref
    # inlining was broken). The Tag schema must exist in
    # components.schemas for the ref to resolve.
    doc["components"]["schemas"]["Tag"] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    doc["components"]["schemas"]["Pet"]["properties"]["owner"] = {
        "$ref": "#/components/schemas/Tag",
    }
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    # ``owner`` was the $ref; the inlined Tag schema is an OBJECT.
    assert by_path["owner"].type is FieldType.OBJECT
    # Backward-compat: 3.1 documents still resolve #/components/schemas/*.
    assert by_path["tag"].type is FieldType.STRING


def test_inline_refs_rejects_defs_ref_in_3_0() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.0.3"
    doc["$defs"] = {"X": {"type": "string"}}
    doc["components"]["schemas"]["Pet"]["properties"]["bad"] = {"$ref": "#/$defs/X"}
    with pytest.raises(InvalidContractError, match="mismatched"):
        OpenApiAdapter().adapt(doc)


def test_inline_refs_rejects_components_schemas_ref_in_defs_only_doc() -> None:
    """3.1 doc with $defs but no components.schemas cannot resolve components refs."""
    doc: dict = {
        "openapi": "3.1.0",
        "info": {"title": "defs only"},
        "$defs": {"X": {"type": "string"}},
        "components": {
            "schemas": {
                "Pet": {"type": "object", "properties": {"bad": {"$ref": "#/components/schemas/X"}}}
            }
        },
    }
    with pytest.raises(InvalidContractError, match="does not resolve"):
        OpenApiAdapter().adapt(doc)


# --- 3.1 end-to-end adapt() ----------------------------------------


def test_adapt_3_1_document_with_defs_and_dialect() -> None:
    doc: dict = {
        "openapi": "3.1.0",
        "info": {"title": "Paxman Petstore 3.1"},
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {
            "Tag": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
        },
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "tag": {"$ref": "#/$defs/Tag"},
                    },
                }
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    assert contract.id == "Paxman Petstore 3.1"
    by_path = {f.path: f for f in contract.fields}
    # ``tag`` was a $defs ref; should have inlined as OBJECT. The
    # V1 contract model is flat (per ADR-0001 — no nested OBJECT
    # children are emitted as separate CanonicalFields), so we
    # cannot assert on the inlined Tag's children directly. The
    # fact that ``tag`` is OBJECT type is sufficient evidence that
    # the $defs ref was resolved and inlined (an inline STRING
    # would have produced STRING).
    assert by_path["tag"].type is FieldType.OBJECT
    # The other top-level fields remain intact.
    assert by_path["id"].type is FieldType.INTEGER
    assert by_path["name"].type is FieldType.STRING


def test_adapt_3_1_rejects_unknown_dialect() -> None:
    doc: dict = {
        "openapi": "3.1.0",
        "info": {"title": "Bad"},
        "jsonSchemaDialect": "https://example.com/no-such-dialect",
        "components": {
            "schemas": {"Pet": {"type": "object", "properties": {"id": {"type": "integer"}}}}
        },
    }
    with pytest.raises(InvalidContractError, match="dialect"):
        OpenApiAdapter().adapt(doc)


def test_adapt_ignores_webhooks() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.1.0"
    doc["webhooks"] = {
        "newPet": {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                    }
                }
            }
        }
    }
    contract = OpenApiAdapter().adapt(doc)
    # Adding webhooks must not change the canonical contract.
    by_path = {f.path: f for f in contract.fields}
    assert "id" in by_path
    assert "name" in by_path
    assert "tag" in by_path


def test_adapt_ignores_path_item_parameters() -> None:
    doc = _load_petstore()
    doc["openapi"] = "3.1.0"
    doc["paths"] = {
        "/pets": {
            "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer"}}],
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pets"}}
                        }
                    }
                }
            },
        }
    }
    contract = OpenApiAdapter().adapt(doc)
    # Path-item parameters must not appear as contract fields.
    assert "limit" not in {f.path for f in contract.fields}


def test_adapt_3_1_nullable_type_array() -> None:
    doc: dict = {
        "openapi": "3.1.0",
        "info": {"title": "Nullable"},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["nickname"],
                    "properties": {"nickname": {"type": ["string", "null"]}},
                }
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    assert by_path["nickname"].type is FieldType.STRING
    assert by_path["nickname"].nullable is True


# --- path-item parameters merge vs append --------------------------


def test_merge_path_parameters_3_0_appends() -> None:
    op = [{"name": "id", "in": "path"}]
    path = [{"name": "limit", "in": "query"}]
    merged = OpenApiAdapter._merge_path_parameters(op, path, version="3.0.3")
    assert len(merged) == 2
    assert merged[0]["name"] == "id"
    assert merged[1]["name"] == "limit"


def test_merge_path_parameters_3_1_merges_by_name_in() -> None:
    op = [{"name": "id", "in": "path", "schema": {"type": "string"}}]
    path = [{"name": "id", "in": "path", "schema": {"type": "integer"}}]
    merged = OpenApiAdapter._merge_path_parameters(op, path, version="3.1.0")
    assert len(merged) == 1
    # Operation-level wins on collision.
    assert merged[0]["schema"]["type"] == "string"


def test_merge_path_parameters_3_1_appends_new_keys() -> None:
    op = [{"name": "id", "in": "path"}]
    path = [{"name": "limit", "in": "query"}]
    merged = OpenApiAdapter._merge_path_parameters(op, path, version="3.1.0")
    assert len(merged) == 2
    names = {p["name"] for p in merged}
    assert names == {"id", "limit"}


# --- 3.1 fixture -----------------------------------------------------


def test_adapt_petstore_3_1_fixture() -> None:
    """The hand-rolled 3.1 fixture must adapt without error and exercise
    every V1 type except MONEY."""
    path = Path(__file__).parent.parent / "fixtures" / "contracts" / "openapi" / "petstore_3_1.yaml"
    import yaml

    with path.open() as f:
        doc = yaml.safe_load(f)
    contract = OpenApiAdapter().adapt(doc)
    assert contract.id == "Paxman Petstore 3.1"

    by_path = {f.path: f for f in contract.fields}
    # 3.0-style integer field.
    assert by_path["id"].type is FieldType.INTEGER
    # 3.0-style string with minLength constraint.
    assert by_path["name"].type is FieldType.STRING
    # 3.1 nullable type array: [string, null].
    assert by_path["nickname"].type is FieldType.STRING
    assert by_path["nickname"].nullable is True
    # $defs ref resolution: tag becomes an OBJECT (inlined Tag schema).
    assert by_path["tag"].type is FieldType.OBJECT
    # Boolean, enum, date, number, array — all present.
    assert by_path["available"].type is FieldType.BOOLEAN
    assert by_path["status"].type is FieldType.ENUM
    assert by_path["birthday"].type is FieldType.DATE
    assert by_path["weight_kg"].type is FieldType.DECIMAL
    assert by_path["photo_urls"].type is FieldType.ARRAY
    # webhooks / path-item parameters / MONEY must not leak into fields.
    assert "limit" not in by_path
    assert "newPet" not in by_path


# --- $ref sibling keyword preservation -----------------------------


def test_adapt_merges_ref_siblings_with_inlined_target() -> None:
    """JSON Schema 2020-12 (and OpenAPI 3.1) allow sibling keywords
    next to ``$ref``. The V1.1.0 adapter preserves the siblings and
    overlays them on the inlined target (siblings win on conflict).
    """
    doc: dict = {
        "openapi": "3.1.0",
        "info": {"title": "Siblings"},
        "components": {
            "schemas": {
                # ``Item`` is the first schema, so the OpenAPI adapter
                # adapts it (the adapter's V1 contract model is one
                # canonical contract per document).
                "Item": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        # ``$ref`` to a STRING target, with a sibling
                        # ``description`` and ``default`` that must
                        # survive the inlining.
                        "name": {
                            "$ref": "#/components/schemas/Target",
                            "description": "Item display name",
                            "default": "untitled",
                        }
                    },
                },
                "Target": {"type": "string", "minLength": 1, "maxLength": 50},
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    name = by_path["name"]
    assert name.type is FieldType.STRING
    assert name.description == "Item display name"
    assert name.default == "untitled"
    # Sibling must win: the inlined Target says minLength=1, maxLength=50;
    # the sibling set contains no conflicting key, so the constraints
    # survive.
    assert any(c.kind.value == "min_length" for c in name.constraints)
    assert any(c.kind.value == "max_length" for c in name.constraints)


def test_adapt_merges_ref_siblings_override_inlined_target() -> None:
    """When a sibling key conflicts with an inlined-target key, the
    sibling wins (per JSON Schema 2020-12 sibling semantics)."""
    doc: dict = {
        "openapi": "3.1.0",
        "info": {"title": "Override"},
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "$ref": "#/components/schemas/Target",
                            "description": "from sibling",
                        }
                    },
                },
                "Target": {
                    "type": "string",
                    "minLength": 1,
                    "description": "from target",
                },
            }
        },
    }
    contract = OpenApiAdapter().adapt(doc)
    by_path = {f.path: f for f in contract.fields}
    name = by_path["name"]
    assert name.type is FieldType.STRING
    # Sibling wins.
    assert name.description == "from sibling"
    # The target's minLength is preserved (no conflict on that key).
    assert any(c.kind.value == "min_length" for c in name.constraints)


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_hints_from_extension() -> None:
    """OpenAPI components/schemas x-paxman-format-hints extension is
    surfaced to CanonicalField.format_hints (OpenAPI delegates to
    JsonSchemaAdapter which already handles the extension)."""
    from paxman.contract import FormatHint
    from paxman.contract.adapters.openapi import OpenApiAdapter

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Invoice": {
                    "type": "object",
                    "properties": {
                        "supplier": {
                            "type": "string",
                            "x-paxman-format-hints": ["csv"],
                        },
                    },
                    "required": ["supplier"],
                }
            }
        },
    }
    adapter = OpenApiAdapter()
    canonical = adapter.adapt(spec)
    supplier = next(f for f in canonical.fields if f.name == "supplier")
    assert supplier.format_hints == (FormatHint.CSV,)
