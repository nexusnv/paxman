"""Tests for the UUID() factory and the CanonicalUUIDContract parse path."""

from __future__ import annotations

import pytest

from paxman._contracts.contract import UUID, CanonicalUUIDContract, parse_contract
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
