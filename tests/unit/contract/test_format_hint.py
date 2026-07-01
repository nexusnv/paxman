"""Unit tests for ``paxman.contract._format_hint.FormatHint``."""

from __future__ import annotations

import enum

import pytest

from paxman.contract._format_hint import FormatHint, resolve_format_hint


class TestFormatHintEnum:
    def test_is_a_subclass_of_enum(self) -> None:
        assert issubclass(FormatHint, enum.Enum)

    def test_v110_members_present(self) -> None:
        # V1.1.0 ships exactly three members: CSV, JSON, XML.
        # Adding a new member must NOT break this assertion; the test
        # is permissive (>=) so the enum is genuinely additive.
        members = {m.name for m in FormatHint}
        assert {"CSV", "JSON", "XML"}.issubset(members)

    def test_value_is_lowercase_string(self) -> None:
        # The wire form is a lowercase string. Adapters pass the
        # string ``"csv"`` / ``"json"`` / ``"xml"``; the resolver
        # looks up ``FormatHint(value)``.
        for member in FormatHint:
            assert isinstance(member.value, str)
            assert member.value == member.value.lower()
            assert member.value == member.name.lower()

    def test_iteration_is_deterministic(self) -> None:
        # Two iterations must yield the same order. The enum is
        # insertion-ordered, so the first iteration defines the
        # canonical order. This is the order used by the planner
        # when sorting format-aware steps.
        first = list(FormatHint)
        second = list(FormatHint)
        assert first == second

    def test_member_agnostic_lookup_accepts_any_member(self) -> None:
        # resolve_format_hint must accept ANY FormatHint member, not
        # only the three V1.1.0 members. A future member added in
        # V1.2 / V2 must round-trip without changes to this function.
        for member in FormatHint:
            assert resolve_format_hint(member) is member
            assert resolve_format_hint(member.value) is member


class TestResolveFormatHint:
    def test_accepts_format_hint_member(self) -> None:
        assert resolve_format_hint(FormatHint.CSV) is FormatHint.CSV
        assert resolve_format_hint(FormatHint.JSON) is FormatHint.JSON
        assert resolve_format_hint(FormatHint.XML) is FormatHint.XML

    def test_accepts_lowercase_string(self) -> None:
        assert resolve_format_hint("csv") is FormatHint.CSV
        assert resolve_format_hint("json") is FormatHint.JSON
        assert resolve_format_hint("xml") is FormatHint.XML

    def test_accepts_uppercase_string(self) -> None:
        # Case-insensitive on input; canonical form is lowercase.
        assert resolve_format_hint("CSV") is FormatHint.CSV
        assert resolve_format_hint("Json") is FormatHint.JSON

    def test_rejects_unknown_string(self) -> None:
        # Unknown values raise ValueError with the offending input
        # in the message. The error code is not exposed at this
        # layer (this is internal); the adapter layer maps to
        # ``InvalidContractError`` with ``error_code="INVALID_FORMAT_HINT"``.
        with pytest.raises(ValueError, match="unknown format hint"):
            resolve_format_hint("pdf")  # not yet a member

    def test_rejects_non_string_non_enum(self) -> None:
        with pytest.raises(TypeError):
            resolve_format_hint(42)
        with pytest.raises(TypeError):
            resolve_format_hint(None)
        with pytest.raises(TypeError):
            resolve_format_hint(["csv"])


class TestFormatHintReexport:
    def test_importable_from_contract_package(self) -> None:
        # Re-exported through paxman.contract.__init__ for adapter use.
        from paxman.contract import FormatHint as TopLevel
        assert TopLevel is FormatHint
