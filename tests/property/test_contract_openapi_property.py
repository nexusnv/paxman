"""Property tests for the OpenAPI adapter (V1.1.0).

Pins the round-trip and determinism contracts the design spec
requires (§5.2). Uses stdlib + hypothesis only.
"""

from __future__ import annotations

import typing
from copy import deepcopy

import hypothesis
import hypothesis.strategies as st
import pytest

from paxman.contract.adapters.openapi import OpenApiAdapter
from paxman.errors import InvalidContractError

pytestmark = [pytest.mark.property, pytest.mark.deterministic]


# --- minimal OpenAPI document strategy ------------------------------


# A simple, well-formed OpenAPI 3.0 document with one OBJECT schema
# and 1-3 properties. Bounded so property tests stay sub-second.
@st.composite
def _openapi_doc(draw: typing.Any) -> dict[str, typing.Any]:
    # Use identifier-style names that match CanonicalField.path's
    # validation pattern ([A-Za-z_][A-Za-z0-9_]*).
    prop_names = draw(
        st.lists(
            st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,9}", fullmatch=True),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )
    properties: dict[str, dict[str, typing.Any]] = {}
    for name in prop_names:
        kind = draw(st.sampled_from(["string", "integer", "number", "boolean"]))
        properties[name] = {"type": kind}
    return {
        "openapi": "3.0.3",
        "info": {"title": "Property Test"},
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "required": prop_names[:1],
                    "properties": properties,
                }
            }
        },
    }


# --- property tests --------------------------------------------------


@hypothesis.given(_openapi_doc())
@hypothesis.settings(max_examples=25, deadline=2000, derandomize=True)
def test_adapt_is_deterministic(doc: dict[str, typing.Any]) -> None:
    adapter = OpenApiAdapter()
    a = adapter.adapt(doc)
    b = adapter.adapt(deepcopy(doc))
    # Two independent adapts of identical input must produce equal
    # canonical contracts (field set, types, required flags).
    assert {f.path for f in a.fields} == {f.path for f in b.fields}
    assert {f.path: f.type for f in a.fields} == {f.path: f.type for f in b.fields}


@hypothesis.given(_openapi_doc())
@hypothesis.settings(max_examples=25, deadline=2000, derandomize=True)
def test_adapt_export_adapt_round_trip(doc: dict[str, typing.Any]) -> None:
    """adapt -> export -> adapt preserves the canonical content."""
    adapter = OpenApiAdapter()
    a = adapter.adapt(doc)
    exported = adapter.export(a)
    b = adapter.adapt(exported)
    # The envelope changes (3.0.3, paths={}, ...) but the canonical
    # content (field set, types) must be byte-equal.
    assert {f.path for f in a.fields} == {f.path for f in b.fields}
    assert {f.path: f.type for f in a.fields} == {f.path: f.type for f in b.fields}


def test_cycle_detection_raises_invalid_ref() -> None:
    """A -> B -> A cycle raises InvalidContractError, not RecursionError."""
    doc: dict[str, typing.Any] = {
        "openapi": "3.0.3",
        "info": {"title": "Cycle"},
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "properties": {"b": {"$ref": "#/components/schemas/B"}},
                },
                "B": {
                    "type": "object",
                    "properties": {"a": {"$ref": "#/components/schemas/A"}},
                },
            }
        },
    }
    adapter = OpenApiAdapter()
    with pytest.raises(InvalidContractError) as excinfo:
        adapter.adapt(doc)
    assert excinfo.value.error_code == "INVALID_REF"
    assert "cycle" in str(excinfo.value).lower()
