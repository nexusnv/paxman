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


# ``pytest`` is already imported above; reference it under a short alias
# for the tests that need a pytest.raises in the middle of a function.
_pytest = pytest


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
    assert [c.value for c in cap.invoke(_ctx(raw, pointer="/refunded")).candidates] == ["false"]


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
    raw = '{"name": "日本語 🎉"}'.encode()
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


# --- additional coverage --------------------------------------------------


def test_root_only_pointer() -> None:
    """A pointer of ``/`` returns the whole document as a string."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": 1}'
    result = cap.invoke(_ctx(raw, pointer="/"))
    # The whole object can't be coerced to a string; expect type-mismatch.
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_json_pointer_unescape_sequences() -> None:
    """JSON-Pointer ~1 (slash) and ~0 (tilde) are unescaped per RFC 6901."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a/b": {"c~d": "found"}}'
    result = cap.invoke(_ctx(raw, pointer="/a~1b/c~0d"))
    assert [c.value for c in result.candidates] == ["found"]


def test_json_pointer_indexing_list() -> None:
    """A JSON-Pointer with an integer segment indexes into a list."""
    cap = JsonPathExtractionCapability()
    raw = b'["a", "b", "c"]'
    result = cap.invoke(_ctx(raw, pointer="/2"))
    assert [c.value for c in result.candidates] == ["c"]


def test_json_pointer_unicode_escape() -> None:
    """A non-ASCII JSON-Pointer segment is supported."""
    cap = JsonPathExtractionCapability()
    raw = '{"日本語": "value"}'.encode()
    result = cap.invoke(_ctx(raw, pointer="/日本語"))
    assert [c.value for c in result.candidates] == ["value"]


def test_jsonpath_root_only() -> None:
    """A JSONPath of ``$`` returns the whole document."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": 1}'
    result = cap.invoke(_ctx(raw, pointer="$"))
    # Whole object: cannot coerce to string.
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_jsonpath_object_wildcard() -> None:
    """``$.*`` expands an object's values."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": 1, "b": 2, "c": 3}'
    result = cap.invoke(_ctx(raw, pointer="$.*"))
    assert [c.value for c in result.candidates] == ["1", "2", "3"]


def test_jsonpath_keyed_index() -> None:
    """``$.key[N]`` indexes a list at a key."""
    cap = JsonPathExtractionCapability()
    raw = b'{"items": ["first", "second", "third"]}'
    result = cap.invoke(_ctx(raw, pointer="$.items[1]"))
    assert [c.value for c in result.candidates] == ["second"]


def test_jsonpath_bracket_star_wildcard() -> None:
    """``$.key[*]`` is rejected as unsupported syntax in V1.

    The V1 subset supports ``$.foo.*`` (dot-wildcard) but not
    ``$.key[*]`` (bracket-wildcard). This is documented in design
    spec #68 §5.1.
    """
    cap = JsonPathExtractionCapability()
    raw = b'{"items": ["a", "b", "c"]}'
    result = cap.invoke(_ctx(raw, pointer="$.items[*]"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "unsupported" in d.message.lower() or "index" in d.message.lower()


def test_jsonpath_wildcard_on_non_container() -> None:
    """A wildcard on a non-container value returns an error diagnostic."""
    cap = JsonPathExtractionCapability()
    raw = b'{"leaf": 42}'
    result = cap.invoke(_ctx(raw, pointer="$.leaf.*"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "expand" in result.diagnostics[0].message.lower()


def test_jsonpath_unsupported_syntax_no_dot() -> None:
    """A JSONPath that does not start with ``$.`` is rejected."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": 1}'
    result = cap.invoke(_ctx(raw, pointer="$foo"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_unsupported_syntax_does_not_start_with_slash_or_dollar() -> None:
    """A pointer that starts with neither ``/`` nor ``$`` is rejected."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": 1}'
    result = cap.invoke(_ctx(raw, pointer="foo.bar"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "unsupported" in d.message.lower()


def test_array_at_pointer_index_out_of_range() -> None:
    """An out-of-range array index returns a PATTERN_NO_MATCH diagnostic."""
    cap = JsonPathExtractionCapability()
    raw = b'["a", "b"]'
    result = cap.invoke(_ctx(raw, pointer="/5"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.PATTERN_NO_MATCH


def test_array_at_pointer_index_for_object() -> None:
    """An integer pointer segment on a dict is a PATTERN_NO_MATCH (key miss)."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": 1}'
    result = cap.invoke(_ctx(raw, pointer="/0"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.PATTERN_NO_MATCH


def test_resolve_pointer_rejects_empty_string_directly() -> None:
    """A direct call to _resolve_pointer with an empty string raises ValueError."""

    cap = JsonPathExtractionCapability()
    with _pytest.raises(ValueError, match="non-empty string"):
        cap._resolve_pointer({}, "")


def test_resolve_jsonpath_rejects_non_dollar_start() -> None:
    """A direct call to _resolve_jsonpath with non-``$`` raises ValueError."""

    cap = JsonPathExtractionCapability()
    with _pytest.raises(ValueError, match="must start with '\\$'"):
        cap._resolve_jsonpath({}, "foo.bar")


def test_resolve_jsonpath_rejects_non_dot_after_dollar() -> None:
    """A direct call to _resolve_jsonpath with ``$foo`` (no dot) raises ValueError."""

    cap = JsonPathExtractionCapability()
    with _pytest.raises(ValueError, match="unsupported JSONPath syntax"):
        cap._resolve_jsonpath({}, "$foo")


def test_resolved_wildcard_on_dict_with_no_string_values() -> None:
    """A wildcard on a dict whose values are all empty produces empty-string candidates."""
    cap = JsonPathExtractionCapability()
    raw = b'{"a": "", "b": "", "c": ""}'
    result = cap.invoke(_ctx(raw, pointer="$.*"))
    # Unlike csv_extraction, json_path_extraction returns empty-string matches
    # verbatim (the spec is about path resolution, not content filtering).
    assert [c.value for c in result.candidates] == ["", "", ""]


def test_walk_jsonpath_wildcard_on_non_container_raises() -> None:
    """A direct call to _walk_jsonpath with a wildcard on a scalar raises ValueError."""

    with _pytest.raises(ValueError, match="cannot expand"):
        JsonPathExtractionCapability._walk_jsonpath(42, ["*"], ("root",), [])


def test_walk_jsonpath_index_on_non_container_raises() -> None:
    """A direct call to _walk_jsonpath indexing a scalar raises ValueError."""

    with _pytest.raises(ValueError, match="cannot index"):
        JsonPathExtractionCapability._walk_jsonpath(42, ["0"], ("root",), [])


def test_walk_jsonpath_key_index_on_non_list_raises() -> None:
    """A direct call to _walk_jsonpath key[N] on a non-list raises ValueError."""

    with _pytest.raises(ValueError, match="expected list"):
        JsonPathExtractionCapability._walk_jsonpath({"key": "scalar"}, ["key[0]"], ("root",), [])


def test_coerce_list_raises_type_error() -> None:
    """A direct call to _coerce_to_string on a list raises TypeError."""

    with _pytest.raises(TypeError, match="cannot coerce"):
        JsonPathExtractionCapability._coerce_to_string([1, 2, 3])


def test_coerce_dict_raises_type_error() -> None:
    """A direct call to _coerce_to_string on a dict raises TypeError."""

    with _pytest.raises(TypeError, match="cannot coerce"):
        JsonPathExtractionCapability._coerce_to_string({"a": 1})


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
