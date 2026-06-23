"""Unit tests for :mod:`paxman.capabilities.v1.lookup`.

Per Sprint 4 D4.16: ``LookupCapability`` is a deterministic
in-memory dict lookup. The tests pin the contract that:

- A hit returns one ``Candidate`` with the mapped value.
- A miss returns no candidates + a ``PATTERN_NO_MATCH`` diagnostic.
- The capability rejects malformed configs with structured diagnostics.
- The capability supports a ``case_sensitive`` toggle.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.lookup import LookupCapability

pytestmark = pytest.mark.unit


def _ctx(
    raw_input: bytes = b"US",
    field_path: str = "country_name",
    field_type_name: str = "STRING",
    config: dict[str, object] | None = None,
) -> CapabilityContext:
    return CapabilityContext(
        raw_input=raw_input,
        field_path=field_path,
        field_type_name=field_type_name,
        config=config or {},
    )


# --- spec ------------------------------------------------------------


def test_spec() -> None:
    cap = LookupCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "lookup"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.STRUCTURED_LOOKUP
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)


# --- hit / miss ------------------------------------------------------


def test_hit_returns_candidate() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"US",
            config={"table": {"US": "United States", "DE": "Germany"}},
        )
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].value == "United States"
    # No diagnostic on a clean hit.
    assert result.diagnostics == ()


def test_miss_returns_no_candidate_with_diagnostic() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"ZZ",
            config={"table": {"US": "United States"}},
        )
    )
    assert result.candidates == ()
    assert any(d.code is DiagnosticCode.PATTERN_NO_MATCH for d in result.diagnostics)


def test_default_key_uses_raw_input() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"  DE  \n",
            config={"table": {"DE": "Germany"}},
        )
    )
    # Surrounding whitespace and trailing newline are stripped.
    assert len(result.candidates) == 1
    assert result.candidates[0].value == "Germany"


def test_explicit_key_overrides_raw_input() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"ZZ",
            config={"key": "FR", "table": {"FR": "France"}},
        )
    )
    assert result.candidates[0].value == "France"


# --- case sensitivity ------------------------------------------------


def test_case_sensitive_default() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"us",
            config={"table": {"US": "United States"}},
        )
    )
    assert result.candidates == ()


def test_case_insensitive() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"us",
            config={
                "table": {"US": "United States"},
                "case_sensitive": False,
            },
        )
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].value == "United States"


# --- malformed config -----------------------------------------------


def test_missing_table_returns_diagnostic() -> None:
    cap = LookupCapability()
    result = cap.invoke(_ctx(raw_input=b"US", config={}))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_non_dict_table_returns_diagnostic() -> None:
    cap = LookupCapability()
    result = cap.invoke(_ctx(raw_input=b"US", config={"table": "not a dict"}))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_non_string_value_returns_diagnostic() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(raw_input=b"US", config={"table": {"US": 42}})  # type: ignore[dict-item]
    )
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_empty_key_returns_diagnostic() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"",
            config={"table": {"US": "United States"}},
        )
    )
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_non_bool_case_sensitive_returns_diagnostic() -> None:
    cap = LookupCapability()
    result = cap.invoke(
        _ctx(
            raw_input=b"US",
            config={"table": {"US": "United States"}, "case_sensitive": "yes"},
        )
    )
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


# --- determinism ----------------------------------------------------


def test_same_input_same_output() -> None:
    """Lookup is deterministic: same input → same output, byte-for-byte."""
    cap = LookupCapability()
    table = {"US": "United States", "DE": "Germany", "FR": "France"}
    r1 = cap.invoke(_ctx(raw_input=b"DE", config={"table": table}))
    r2 = cap.invoke(_ctx(raw_input=b"DE", config={"table": table}))
    assert r1.candidates[0].value == r2.candidates[0].value


def test_empty_table_returns_no_candidates() -> None:
    cap = LookupCapability()
    result = cap.invoke(_ctx(raw_input=b"US", config={"table": {}}))
    assert result.candidates == ()
    assert any(d.code is DiagnosticCode.PATTERN_NO_MATCH for d in result.diagnostics)
