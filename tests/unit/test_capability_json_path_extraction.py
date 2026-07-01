"""Unit tests for :mod:`paxman.capabilities.v1.json_path_extraction`.

V1 deterministic capability that resolves a JSON-Pointer or a
documented subset of JSONPath against the raw input parsed as JSON.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode, DiagnosticSeverity
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.json_path_extraction import JsonPathExtractionCapability

pytestmark = pytest.mark.unit


def _ctx(raw: bytes = b"", pointer: str | None = None) -> CapabilityContext:
    cfg: dict = {}
    if pointer is not None:
        cfg["pointer"] = pointer
    return CapabilityContext(
        raw_input=raw,
        field_path="supplier_name",
        field_type_name="STRING",
        config=cfg,
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is json_path_extraction@1.0, LOCAL_DETERMINISTIC, free."""
    cap = JsonPathExtractionCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "json_path_extraction"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert "STRING" in spec.input_types
    assert "MIXED" in spec.input_types


# --- happy path -----------------------------------------------------------


def test_resolves_simple_pointer_to_string() -> None:
    """A simple JSON-Pointer returns the value at that path."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b'{"supplier": "ACME"}', pointer="/supplier"))
    assert [c.value for c in result.candidates] == ["ACME"]
    ev = result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "json_path_extraction"
    assert ev.capability_version == "1.0"
    assert ev.context["json_pointer"] == "/supplier"


def test_resolves_nested_pointer() -> None:
    """A nested JSON-Pointer walks the path."""
    cap = JsonPathExtractionCapability()
    raw = b'{"invoice": {"supplier": {"name": "ACME Corp"}}}'
    result = cap.invoke(_ctx(raw, pointer="/invoice/supplier/name"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_resolves_array_index() -> None:
    """An integer segment indexes into a JSON array."""
    cap = JsonPathExtractionCapability()
    raw = b'{"items": ["first", "second", "third"]}'
    result = cap.invoke(_ctx(raw, pointer="/items/1"))
    assert [c.value for c in result.candidates] == ["second"]


def test_resolves_numbers() -> None:
    """Integers coerce to their string form."""
    cap = JsonPathExtractionCapability()
    raw = b'{"qty": 42, "ratio": 0.5}'
    assert [c.value for c in cap.invoke(_ctx(raw, pointer="/qty")).candidates] == ["42"]
    assert [c.value for c in cap.invoke(_ctx(raw, pointer="/ratio")).candidates] == ["0.5"]


def test_resolves_boolean() -> None:
    """Booleans coerce to the literal 'true' / 'false'."""
    cap = JsonPathExtractionCapability()
    raw = b'{"paid": true, "refunded": false}'
    assert [c.value for c in cap.invoke(_ctx(raw, pointer="/paid")).candidates] == ["true"]
    assert [c.value for c in cap.invoke(_ctx(raw, pointer="/refunded")).candidates] == [
        "false"
    ]


def test_resolves_null() -> None:
    """null coerces to the literal 'null'."""
    cap = JsonPathExtractionCapability()
    raw = b'{"void": null}'
    assert [c.value for c in cap.invoke(_ctx(raw, pointer="/void")).candidates] == ["null"]


def test_wildcard_produces_multiple_candidates() -> None:
    """JSONPath wildcard produces one candidate per value."""
    cap = JsonPathExtractionCapability()
    raw = b'{"items": ["a", "b", "c"]}'
    result = cap.invoke(_ctx(raw, pointer="$.items.*"))
    assert [c.value for c in result.candidates] == ["a", "b", "c"]


def test_unicode_input() -> None:
    """Multi-byte unicode is supported."""
    cap = JsonPathExtractionCapability()
    raw = '{"name": "日本語 🎉"}'.encode("utf-8")
    result = cap.invoke(_ctx(raw, pointer="/name"))
    assert [c.value for c in result.candidates] == ["日本語 🎉"]


# --- failure modes --------------------------------------------------------


def test_missing_pointer_in_config() -> None:
    """Missing config['pointer'] returns an error diagnostic."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b'{"a": 1}', pointer=None))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert d.severity is DiagnosticSeverity.ERROR
    assert "pointer" in d.message


def test_empty_pointer() -> None:
    """Empty config['pointer'] returns an error diagnostic."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b'{"a": 1}', pointer=""))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_invalid_json() -> None:
    """Malformed input returns an error diagnostic (not an exception)."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b"not json {", pointer="/foo"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "json" in d.message.lower()


def test_path_not_found() -> None:
    """A valid JSON but missing path returns a PATTERN_NO_MATCH diagnostic."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b'{"a": 1}', pointer="/missing"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.PATTERN_NO_MATCH


def test_unsupported_pointer_syntax() -> None:
    """JSONPath filter expressions are out of scope for V1."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b'{"items": [1,2,3]}', pointer="$.items[?(@>1)]"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "unsupported" in d.message.lower()


def test_empty_input() -> None:
    """Empty raw_input returns an error diagnostic."""
    cap = JsonPathExtractionCapability()
    result = cap.invoke(_ctx(b"", pointer="/foo"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_object_leaf_emits_type_mismatch() -> None:
    """A resolved object/array at the leaf is an error (cannot coerce)."""
    cap = JsonPathExtractionCapability()
    raw = b'{"supplier": {"nested": "object"}}'
    result = cap.invoke(_ctx(raw, pointer="/supplier"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "coerce" in d.message.lower() or "cannot" in d.message.lower()


# --- determinism ----------------------------------------------------------


@pytest.mark.deterministic
def test_determinism() -> None:
    """Same input + same pointer = same candidates, byte-equal."""
    cap = JsonPathExtractionCapability()
    ctx = _ctx(b'{"a": 1, "b": [1, 2, 3]}', pointer="/b")
    r1 = cap.invoke(ctx)
    r2 = cap.invoke(ctx)
    assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
    assert [c.evidence_refs[0].context for c in r1.candidates] == [
        c.evidence_refs[0].context for c in r2.candidates
    ]
