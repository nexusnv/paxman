"""Tests for the contract Dict DSL parser and the contract value objects."""
from __future__ import annotations

import pytest

from paxman._contracts.contract import (
    CanonicalEmailContract,
    Contract,
    parse_contract,
)
from paxman._errors import ContractError


class TestParseCanonicalEmail:
    def test_minimal_dict(self) -> None:
        c = parse_contract({"kind": "canonical_email"})
        assert isinstance(c, CanonicalEmailContract)
        assert c.lowercase is True
        assert c.strip_whitespace is True
        assert c.provider_aliases == "none"
        assert c.strict is False
        assert c.version == 1

    def test_full_dict(self) -> None:
        c = parse_contract(
            {
                "kind": "canonical_email",
                "lowercase": False,
                "strip_whitespace": False,
                "provider_aliases": "gmail",
                "strict": True,
            }
        )
        assert c.lowercase is False
        assert c.strip_whitespace is False
        assert c.provider_aliases == "gmail"
        assert c.strict is True

    def test_unknown_kind_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"kind": "unknown"})

    def test_non_dict_input_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract("not a dict")  # type: ignore[arg-type]

    def test_missing_kind_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"lowercase": True})

    def test_invalid_provider_aliases_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract(
                {"kind": "canonical_email", "provider_aliases": "outlook"}
            )


class TestCanonicalEmailContract:
    def test_as_dict_round_trip(self) -> None:
        original = {"kind": "canonical_email", "provider_aliases": "gmail"}
        c = parse_contract(original)
        d = c.as_dict()
        assert d["kind"] == "canonical_email"
        assert d["provider_aliases"] == "gmail"
        # Round-trip
        c2 = parse_contract(d)
        assert c2 == c

    def test_is_frozen(self) -> None:
        c = parse_contract({"kind": "canonical_email"})
        with pytest.raises(Exception):  # attrs.FrozenInstanceError
            c.lowercase = False  # type: ignore[misc]

    def test_equality(self) -> None:
        a = parse_contract({"kind": "canonical_email", "provider_aliases": "gmail"})
        b = parse_contract({"kind": "canonical_email", "provider_aliases": "gmail"})
        assert a == b
