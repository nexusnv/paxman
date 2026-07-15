"""Tests for the UUID() factory and the CanonicalUUIDContract parse path."""

from __future__ import annotations

import typing

import pytest

from paxman._capabilities.uuid.contract import (
    UUID,
    CanonicalUUIDContract,
)
from paxman._dsl.parser import parse_contract
from paxman._errors import ContractError


class TestUUIDFactory:
    def test_uuid_factory_default(self) -> None:
        assert UUID() == CanonicalUUIDContract()

    def test_uuid_factory_version(self) -> None:
        assert UUID(version="4") == CanonicalUUIDContract(version="4")

    def test_parse_contract_dict(self) -> None:
        result = parse_contract({"kind": "canonical_uuid", "version": "4"})
        assert result == CanonicalUUIDContract(version="4")

    def test_parse_contract_unknown_version_raises(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"kind": "canonical_uuid", "version": "9"})
        assert parse_contract({"kind": "canonical_uuid"}) == CanonicalUUIDContract(version="any")

    def test_uuid_factory_invalid_version_raises(self) -> None:
        # attrs does not validate Literal at runtime, so the contract's
        # __attrs_post_init__ must reject unknown versions loudly (Law 7 —
        # explicit over clever; never a silent INVALID for every input).
        invalid_version: typing.Any = "99"
        with pytest.raises(ContractError):
            UUID(version=invalid_version)

    def test_parse_contract_non_string_version_raises(self) -> None:
        # A malformed (non-string) version must raise ContractError, not
        # crash with TypeError during the membership check (CodeRabbit #19).
        with pytest.raises(ContractError):
            parse_contract({"kind": "canonical_uuid", "version": ["4"]})
