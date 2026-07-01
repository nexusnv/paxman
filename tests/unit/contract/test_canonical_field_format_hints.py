"""Unit tests for ``CanonicalField.format_hints``."""

from __future__ import annotations

import pytest

from paxman.contract._format_hint import FormatHint
from paxman.contract.canonical import CanonicalField
from paxman.types import FieldType


def _make_field(**overrides: object) -> CanonicalField:
    base: dict[str, object] = {
        "id": "field_test_supplier",
        "path": "supplier",
        "name": "supplier",
        "type": FieldType.STRING,
        "required": True,
    }
    base.update(overrides)
    return CanonicalField(**base)  # type: ignore[arg-type]


class TestFormatHintsAttribute:
    def test_default_is_empty_tuple(self) -> None:
        f = _make_field()
        assert f.format_hints == ()

    def test_default_is_immutable(self) -> None:
        # CanonicalField is attrs.frozen(slots=True) — the default
        # tuple is shared across instances, which is fine because
        # tuples are immutable. Verify it is in fact a tuple.
        f = _make_field()
        assert isinstance(f.format_hints, tuple)

    def test_accepts_single_member(self) -> None:
        f = _make_field(format_hints=(FormatHint.CSV,))
        assert f.format_hints == (FormatHint.CSV,)

    def test_accepts_multiple_members(self) -> None:
        f = _make_field(format_hints=(FormatHint.JSON, FormatHint.XML))
        assert f.format_hints == (FormatHint.JSON, FormatHint.XML)

    def test_accepts_any_format_hint_member(self) -> None:
        # The validator is member-agnostic. Even if a future member
        # is added, the attribute accepts it. We simulate this by
        # iterating the enum.
        for member in FormatHint:
            f = _make_field(format_hints=(member,))
            assert f.format_hints == (member,)

    def test_preserves_repeated_members(self) -> None:
        # The validator does not auto-dedupe (attrs.frozen forbids
        # in-place mutation of self.format_hints). Repeated hints
        # are preserved as-given. Adapters are responsible for
        # canonical form; the field accepts whatever the adapter
        # produced.
        f = _make_field(format_hints=(FormatHint.CSV, FormatHint.CSV))
        assert f.format_hints == (FormatHint.CSV, FormatHint.CSV)

    def test_rejects_non_format_hint_values(self) -> None:
        with pytest.raises(TypeError, match="format_hints must be a tuple of FormatHint"):
            _make_field(format_hints=("csv",))  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="format_hints must be a tuple of FormatHint"):
            _make_field(format_hints=(FormatHint.CSV, "json"))  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="format_hints must be a tuple of FormatHint"):
            _make_field(format_hints=42)  # type: ignore[arg-type]

    def test_rejects_list_input(self) -> None:
        # The attribute is declared as a tuple; lists are rejected
        # to keep the type honest. Adapters convert lists to tuples
        # before constructing CanonicalField.
        with pytest.raises(TypeError, match="format_hints must be a tuple of FormatHint"):
            _make_field(format_hints=[FormatHint.CSV])  # type: ignore[arg-type]
