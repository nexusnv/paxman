"""Unit tests for :mod:`paxman.capabilities.v1.case_normalization`.

V1 post-extraction cleanup transform that lower-/upper-/title-/
preserve-cases a pre-resolved string value. The capability
reads from ``ctx.config["value"]`` (the post-resolution input
pattern) and ``ctx.config["mode"]`` (the closed mode set).
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.case_normalization import CaseNormalizationCapability

pytestmark = pytest.mark.unit


# Sentinel for "key not present" — ``None`` is a valid value.
_UNSET: object = object()


def _ctx(value: object = _UNSET, mode: object = _UNSET, **extra: object) -> CapabilityContext:
    """Build a ``CapabilityContext`` for case_normalization tests.

    The capability ignores ``raw_input``; we pass an empty bytes
    object to satisfy the ``CapabilityContext`` invariant.
    """
    config: dict[str, object] = {}
    if value is not _UNSET:
        config["value"] = value
    if mode is not _UNSET:
        config["mode"] = mode
    config.update(extra)
    return CapabilityContext(
        raw_input=b"",
        field_path="supplier_name",
        field_type_name="STRING",
        config=config,
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is case_normalization@1.0, LOCAL_DETERMINISTIC, free."""
    cap = CaseNormalizationCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "case_normalization"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert spec.input_types == ("STRING",)
    assert spec.output_type == "STRING"


# --- happy path -----------------------------------------------------------


def test_lowers_ascii() -> None:
    """mode='lower' lowercases ASCII."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="ACME Corp", mode="lower"))
    assert [c.value for c in result.candidates] == ["acme corp"]
    ev = result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "case_normalization"
    assert ev.context["mode"] == "lower"
    assert ev.context["original_value"] == "ACME Corp"


def test_uppers_ascii() -> None:
    """mode='upper' uppercases ASCII."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="acme corp", mode="upper"))
    assert [c.value for c in result.candidates] == ["ACME CORP"]


def test_titles_ascii() -> None:
    """mode='title' title-cases ASCII."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="acme corp", mode="title"))
    assert [c.value for c in result.candidates] == ["Acme Corp"]


def test_preserve_returns_input_verbatim() -> None:
    """mode='preserve' is the explicit no-op identity."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="ACME Corp", mode="preserve"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_empty_string_preserved() -> None:
    """An empty value produces an empty value (no error, no diagnostic)."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="", mode="lower"))
    assert [c.value for c in result.candidates] == [""]
    assert result.diagnostics == ()


def test_unicode_lowered() -> None:
    """Unicode lower-casing works on non-ASCII (e.g., German sharp s)."""
    cap = CaseNormalizationCapability()
    # "STRAßE" -> "straße" under str.lower()
    result = cap.invoke(_ctx(value="STRAßE", mode="lower"))
    assert [c.value for c in result.candidates] == ["straße"]


def test_unicode_emoji_preserved() -> None:
    """Emoji is preserved through all modes; ASCII letters are cased per mode."""
    cap = CaseNormalizationCapability()
    # The emoji is preserved; ASCII letters are cased per mode.
    assert [c.value for c in cap.invoke(_ctx(value="acme 🎉 corp", mode="lower")).candidates] == [
        "acme 🎉 corp"
    ]
    assert [c.value for c in cap.invoke(_ctx(value="acme 🎉 corp", mode="upper")).candidates] == [
        "ACME 🎉 CORP"
    ]
    assert [c.value for c in cap.invoke(_ctx(value="acme 🎉 corp", mode="title")).candidates] == [
        "Acme 🎉 Corp"
    ]
    assert [
        c.value for c in cap.invoke(_ctx(value="ACME 🎉 CORP", mode="preserve")).candidates
    ] == ["ACME 🎉 CORP"]


# --- config validation ---------------------------------------------------


def test_missing_value_returns_error() -> None:
    """Missing config['value'] returns a CAPABILITY_INVOKE_FAILED diagnostic."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(mode="lower"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "value" in d.message


def test_missing_mode_returns_error() -> None:
    """Missing config['mode'] returns a CAPABILITY_INVOKE_FAILED diagnostic."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="ACME"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "mode" in d.message


def test_unknown_mode_returns_error() -> None:
    """An unknown mode is a hard error, not a silent no-op."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="ACME", mode="snake_case"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "snake_case" in d.message


def test_value_wrong_type_returns_error() -> None:
    """A non-string value is a hard error (no coercion from bytes/int/None)."""
    cap = CaseNormalizationCapability()
    for bad in (b"ACME", 123, None, 1.5, ["ACME"], {"x": "ACME"}):
        result = cap.invoke(_ctx(value=bad, mode="lower"))
        assert result.candidates == ()
        assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_mode_wrong_type_returns_error() -> None:
    """A non-string mode is a hard error."""
    cap = CaseNormalizationCapability()
    for bad in (1, None, ["lower"], {"mode": "lower"}):
        result = cap.invoke(_ctx(value="ACME", mode=bad))
        assert result.candidates == ()
        assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_empty_mode_string_returns_error() -> None:
    """An empty string mode is a hard error (caller almost certainly typo'd)."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="ACME", mode=""))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


# --- evidence shape ------------------------------------------------------


def test_evidence_includes_original_value_and_mode() -> None:
    """The EvidenceRef.context carries the original value and the mode."""
    cap = CaseNormalizationCapability()
    result = cap.invoke(_ctx(value="ACME Corp", mode="lower"))
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context == {"original_value": "ACME Corp", "mode": "lower"}
    assert ev.capability_version == "1.0"
    assert ev.field_path == "supplier_name"


def test_raw_input_is_not_read() -> None:
    """The capability must not consume ctx.raw_input; an arbitrary byte string is harmless."""
    cap = CaseNormalizationCapability()
    ctx = CapabilityContext(
        raw_input=b"this is intentionally weird and must not affect the result",
        field_path="supplier_name",
        field_type_name="STRING",
        config={"value": "ACME Corp", "mode": "lower"},
    )
    result = cap.invoke(ctx)
    assert [c.value for c in result.candidates] == ["acme corp"]


# --- determinism ---------------------------------------------------------


@pytest.mark.deterministic
def test_determinism() -> None:
    """Same value + same mode = same candidates, byte-equal."""
    cap = CaseNormalizationCapability()
    ctx = _ctx(value="ACME Corp", mode="lower")
    r1 = cap.invoke(ctx)
    r2 = cap.invoke(ctx)
    assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
    assert [c.evidence_refs[0].context for c in r1.candidates] == [
        c.evidence_refs[0].context for c in r2.candidates
    ]


# --- self-registration (ADR-0012) ----------------------------------------


def test_module_registers_on_import() -> None:
    """Importing the module registers the capability (ADR-0012).

    The hook is module-level: ``_register_on_import()`` runs at
    import time. The test calls the hook explicitly to be robust
    against test-suite ordering and the autouse registry-reset
    fixtures in other tests (the spec-registry test clears the
    registry between tests, so we cannot rely on the import-time
    side effect still being in effect at this point).
    """
    import paxman.capabilities.v1.case_normalization as mod
    from paxman.capabilities import registry

    assert hasattr(mod, "_register_on_import")
    assert callable(mod._register_on_import)
    mod._register_on_import()  # re-register explicitly for this test
    cap = registry.get("case_normalization", "1.0")
    assert isinstance(cap, CaseNormalizationCapability)
