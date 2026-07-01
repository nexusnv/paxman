"""Unit tests for ``CapabilitySpec.format_hint``."""

from __future__ import annotations

import pytest

from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.contract._format_hint import FormatHint


def _make_spec(**overrides: object) -> CapabilitySpec:
    base: dict[str, object] = {
        "id": "csv_extraction",
        "version": "1.0",
        "tier": CapabilityTier.LOCAL_DETERMINISTIC,
        "input_types": ("STRING", "HTML_TEXT", "MIXED"),
        "output_type": "STRING",
        "cost_estimate": CostHint(),
    }
    base.update(overrides)
    return CapabilitySpec(**base)  # type: ignore[arg-type]


class TestFormatHintAttribute:
    def test_default_is_none(self) -> None:
        # The default is None: capabilities that do not consume
        # raw input bytes (cleanup transforms, lookup, inference,
        # validation) leave format_hint unset. This is the safe
        # default — the planner's select_format_aware only matches
        # when both the field and the cap declare a hint.
        spec = _make_spec()
        assert spec.format_hint is None

    def test_accepts_format_hint_member(self) -> None:
        spec = _make_spec(format_hint=FormatHint.CSV)
        assert spec.format_hint is FormatHint.CSV

    def test_accepts_any_format_hint_member(self) -> None:
        # The validator is member-agnostic. Iterating the enum
        # covers the V1.1.0 set AND any future member.
        for member in FormatHint:
            spec = _make_spec(format_hint=member)
            assert spec.format_hint is member

    def test_rejects_non_format_hint_values(self) -> None:
        with pytest.raises(TypeError, match="format_hint must be a FormatHint or None"):
            _make_spec(format_hint="csv")  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="format_hint must be a FormatHint or None"):
            _make_spec(format_hint=42)  # type: ignore[arg-type]

    def test_rejects_tuple(self) -> None:
        # A capability declares exactly one format_hint (or None).
        # A tuple is rejected to keep the contract honest: a
        # capability that handles multiple formats is two
        # capabilities, not one with multiple hints.
        with pytest.raises(TypeError, match="format_hint must be a FormatHint or None"):
            _make_spec(format_hint=(FormatHint.CSV, FormatHint.JSON))  # type: ignore[arg-type]


class TestExistingCapabilitiesUnchanged:
    """Every existing V1 capability must keep ``format_hint = None``
    unless Task 5 explicitly sets it. This test enumerates the
    built-in registry to pin the default."""

    def test_all_capabilities_have_format_hint(self) -> None:
        from paxman.capabilities.registry import all_capabilities

        for cap in all_capabilities().values():
            assert hasattr(cap.spec, "format_hint")
            # Most capabilities leave it None; the three V1.1.0
            # format extractors are the exception, set in Task 5.
            assert cap.spec.format_hint is None or isinstance(cap.spec.format_hint, FormatHint)
