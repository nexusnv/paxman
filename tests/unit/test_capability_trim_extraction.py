"""Unit tests for :mod:`paxman.capabilities.v1.trim_extraction`.

V1 post-extraction cleanup transform that strips leading/trailing
whitespace and common punctuation from a pre-resolved string
value. The capability reads from ``ctx.config["value"]`` (the
post-resolution input pattern) and an optional
``ctx.config["chars"]`` literal-character set.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.trim_extraction import _DEFAULT_CHARS, TrimExtractionCapability

pytestmark = pytest.mark.unit


# Sentinel for "key not present" — ``None`` is a valid value.
_UNSET: object = object()


def _ctx(value: object = _UNSET, chars: object = _UNSET, **extra: object) -> CapabilityContext:
    """Build a ``CapabilityContext`` for trim_extraction tests.

    The capability ignores ``raw_input``; we pass an empty bytes
    object to satisfy the ``CapabilityContext`` invariant.
    """
    config: dict[str, object] = {}
    if value is not _UNSET:
        config["value"] = value
    if chars is not _UNSET:
        config["chars"] = chars
    config.update(extra)
    return CapabilityContext(
        raw_input=b"",
        field_path="supplier_name",
        field_type_name="STRING",
        config=config,
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is trim_extraction@1.0, LOCAL_DETERMINISTIC, free."""
    cap = TrimExtractionCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "trim_extraction"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert spec.input_types == ("STRING",)
    assert spec.output_type == "STRING"


# --- happy path with default chars ---------------------------------------


def test_default_strips_leading_and_trailing_whitespace() -> None:
    """Default chars strip leading and trailing whitespace."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="  ACME Corp  "))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_default_strips_trailing_colon() -> None:
    """Default chars strip a trailing colon (common in invoice text)."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="ACME Corp:"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_default_strips_leading_and_trailing_punctuation() -> None:
    """Default chars strip the documented common-punctuation set.

    Note: ``[ACME]`` strips the brackets (the default set includes
    ``[`` and ``]``) and produces just ``ACME``. We test the strip
    with single punctuation on each side instead so the inner
    content is unambiguous.
    """
    cap = TrimExtractionCapability()
    for s in (": ACME Corp", "ACME Corp ;", "  ACME Corp ,  "):
        result = cap.invoke(_ctx(value=s))
        assert [c.value for c in result.candidates] == ["ACME Corp"], f"failed for {s!r}"


def test_default_strips_brackets() -> None:
    """The default set includes ``[`` and ``]``."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="[ACME]"))
    assert [c.value for c in result.candidates] == ["ACME"]


def test_default_strips_zero_width_and_bom() -> None:
    """Default chars strip zero-width spaces, ZWNJ, ZWJ, and BOM."""
    cap = TrimExtractionCapability()
    for s in (
        "\u200bACME Corp\u200b",  # ZWSP on both sides
        "\u200cACME Corp\u200d",  # ZWNJ + ZWJ
        "\ufeffACME Corp\ufeff",  # BOM on both sides
    ):
        result = cap.invoke(_ctx(value=s))
        assert [c.value for c in result.candidates] == ["ACME Corp"], f"failed for {s!r}"


def test_default_strips_newlines_and_tabs() -> None:
    """Default chars strip ``\\n``, ``\\r``, ``\\t``, and other ASCII whitespace."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="\n\tACME Corp\r\n"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_no_trim_needed_returns_value_unchanged() -> None:
    """A value with nothing to strip is returned unchanged (no-op identity)."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="ACME Corp"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]
    # stripped_count is 0
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["stripped_count"] == 0


def test_empty_string_returns_empty() -> None:
    """An empty value produces an empty value (no error, no diagnostic)."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value=""))
    assert [c.value for c in result.candidates] == [""]
    assert result.diagnostics == ()


def test_unicode_value_trimmed() -> None:
    """A unicode value is trimmed correctly."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="  ACME 株式会社  "))
    assert [c.value for c in result.candidates] == ["ACME 株式会社"]


# --- happy path with explicit chars --------------------------------------


def test_explicit_chars_strip_only_those() -> None:
    """chars='-' strips only dashes, not other whitespace."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="--ACME Corp--", chars="-"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_explicit_chars_does_not_strip_undocumented() -> None:
    """chars='-' does NOT strip whitespace that the default would have stripped.

    ``str.strip('-')`` only strips ``-`` from the boundary; the
    leading/trailing whitespace stays because ``-`` is the only
    char in the strip set, and ``str.strip`` cannot proceed past
    boundary chars that are not in the set.
    """
    cap = TrimExtractionCapability()
    # Value with leading/trailing whitespace + boundary ``-``:
    # the leading whitespace blocks the strip from doing anything.
    result = cap.invoke(_ctx(value="  -ACME Corp-  ", chars="-"))
    # The leading whitespace is not in ``-``, so the strip stops there.
    # The trailing whitespace is also not in ``-``. No stripping happens.
    assert [c.value for c in result.candidates] == ["  -ACME Corp-  "]


def test_explicit_chars_strips_when_boundary_matches() -> None:
    """chars='-' strips the boundary ``-`` when there is no leading whitespace."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="--ACME Corp--", chars="-"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_explicit_chars_handles_multi_char_set() -> None:
    """chars can be a multi-character string; each char is a literal to strip."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="abcACME Corpcba", chars="abc"))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


# --- config validation ---------------------------------------------------


def test_missing_value_returns_error() -> None:
    """Missing config['value'] returns a CAPABILITY_INVOKE_FAILED diagnostic."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx())
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "value" in d.message


def test_chars_wrong_type_returns_error() -> None:
    """A non-string chars is a hard error (the chars are literals, not a regex).

    Note: ``chars=None`` is **not** an error — it is the explicit
    signal to fall back to the default char set (per the spec).
    Only non-None, non-str values are errors.
    """
    cap = TrimExtractionCapability()
    for bad in (1, ["-"], {"x": "-"}, b"-"):
        result = cap.invoke(_ctx(value="--ACME--", chars=bad))
        assert result.candidates == ()
        assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_chars_none_falls_back_to_default() -> None:
    """``chars=None`` is the explicit signal to use the default char set.

    The default set includes both whitespace AND ``-``, so the
    leading/trailing whitespace and the boundary ``-`` are all
    stripped, leaving just ``ACME``.
    """
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="  --ACME--  ", chars=None))
    assert [c.value for c in result.candidates] == ["ACME"]
    # trimmed_chars in the evidence records the default set.
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["trimmed_chars"] == sorted(_DEFAULT_CHARS)


def test_chars_empty_string_returns_error() -> None:
    """An empty chars string is a hard error (caller almost certainly typo'd)."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="ACME", chars=""))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_value_wrong_type_returns_error() -> None:
    """A non-string value is a hard error (no coercion from bytes/int/None)."""
    cap = TrimExtractionCapability()
    for bad in (b"ACME", 123, None, 1.5, ["ACME"], {"x": "ACME"}):
        result = cap.invoke(_ctx(value=bad))
        assert result.candidates == ()
        assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


# --- evidence shape ------------------------------------------------------


def test_evidence_includes_original_and_trimmed_chars() -> None:
    """The EvidenceRef.context carries the original value, the trimmed-chars set, and a count."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="  ACME  "))
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["original_value"] == "  ACME  "
    assert ev.context["trimmed_chars"] == sorted(_DEFAULT_CHARS)
    assert ev.context["stripped_count"] == 4  # 2 leading + 2 trailing spaces
    assert ev.capability_version == "1.0"
    assert ev.field_path == "supplier_name"


def test_evidence_records_explicit_chars() -> None:
    """When chars is explicit, the evidence records exactly those chars."""
    cap = TrimExtractionCapability()
    result = cap.invoke(_ctx(value="--ACME--", chars="-"))
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["trimmed_chars"] == ["-"]
    assert ev.context["stripped_count"] == 4


def test_raw_input_is_not_read() -> None:
    """The capability must not consume ctx.raw_input."""
    cap = TrimExtractionCapability()
    ctx = CapabilityContext(
        raw_input=b"this is intentionally weird and must not affect the result",
        field_path="supplier_name",
        field_type_name="STRING",
        config={"value": "  ACME Corp  "},
    )
    result = cap.invoke(ctx)
    assert [c.value for c in result.candidates] == ["ACME Corp"]


# --- determinism ---------------------------------------------------------


@pytest.mark.deterministic
def test_determinism() -> None:
    """Same value + same chars = same candidates, byte-equal."""
    cap = TrimExtractionCapability()
    ctx = _ctx(value="  ACME Corp :", chars=" :")
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
    import paxman.capabilities.v1.trim_extraction as mod
    from paxman.capabilities import registry

    assert hasattr(mod, "_register_on_import")
    assert callable(mod._register_on_import)
    mod._register_on_import()  # re-register explicitly for this test
    cap = registry.get("trim_extraction", "1.0")
    assert isinstance(cap, TrimExtractionCapability)
