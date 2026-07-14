"""Tests for the DateCapability (spec: .superpowers/specs/2026-07-15-...)."""

from __future__ import annotations

from paxman import Status
from paxman._capabilities.builtins.date import DateCapability
from paxman._contracts.contract import CanonicalDateContract


def _cap() -> DateCapability:
    return DateCapability()


def _contract(locale: str = "ISO") -> CanonicalDateContract:
    return CanonicalDateContract(locale=locale)


class TestDateCapability:
    def test_name_is_date_canonicalization(self) -> None:
        assert _cap().name == "date_canonicalization"

    def test_can_handle_accepts_date_contract_and_string(self) -> None:
        assert _cap().can_handle(_contract(), "2025-01-01") is True

    def test_can_handle_rejects_non_date_contract(self) -> None:
        assert _cap().can_handle("not a contract", "2025-01-01") is False  # type: ignore[arg-type]

    def test_can_handle_rejects_non_string_value(self) -> None:
        assert _cap().can_handle(_contract(), 12345) is False  # type: ignore[arg-type]

    def test_iso_date_canonicalizes(self) -> None:
        r = _cap().canonicalize("2025-01-01", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01"
        assert r.evidence[0].rule == "parsed_iso_date"
