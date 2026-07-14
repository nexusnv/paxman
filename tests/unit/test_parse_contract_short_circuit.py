"""Tests for parse_contract accepting CanonicalEmailContract instances.

Spec §2.3: parse_contract short-circuits on the EXACT type
CanonicalEmailContract (not the parent Contract alias) so future
multi-field contract types (InvoiceContract, the north star) are NOT
silently absorbed. The dict-DSL path is unchanged.
"""

from __future__ import annotations

import pytest

from paxman import Email
from paxman._contracts.contract import CanonicalEmailContract, parse_contract
from paxman._errors import ContractError


class TestParseContractShortCircuit:
    def test_accepts_canonical_email_contract_instance(self) -> None:
        contract = CanonicalEmailContract()
        result = parse_contract(contract)
        assert result == contract

    def test_accepts_email_factory_result(self) -> None:
        contract = Email()
        result = parse_contract(contract)
        assert result == contract
        assert isinstance(result, CanonicalEmailContract)

    def test_preserves_provider_aliases_from_factory(self) -> None:
        contract = Email(provider_aliases="gmail")
        result = parse_contract(contract)
        assert result.provider_aliases == "gmail"

    def test_preserves_strict_from_factory(self) -> None:
        contract = Email(strict=True)
        result = parse_contract(contract)
        assert result.strict is True

    def test_rejects_non_contract_non_dict(self) -> None:
        # The dict-DSL path's existing ContractError must still fire
        # for anything that is neither a CanonicalEmailContract nor a
        # dict. Law 8: fail informatively.
        with pytest.raises(ContractError):
            parse_contract("not a contract")

    def test_rejects_dict_with_unknown_kind(self) -> None:
        # Regression guard: the dict-DSL path is unchanged.
        with pytest.raises(ContractError):
            parse_contract({"kind": "unknown_kind"})

    def test_accepts_dict_with_valid_kind(self) -> None:
        # Regression guard: the dict-DSL happy path still works.
        result = parse_contract({"kind": "canonical_email"})
        assert isinstance(result, CanonicalEmailContract)
        assert result.lowercase is True

    def test_short_circuit_is_exact_type_not_parent(self) -> None:
        # If a future contributor introduces a multi-field
        # InvoiceContract by subclassing CanonicalEmailContract, that
        # is their problem to solve with their own dispatch. The
        # short-circuit here must NOT accept subclasses silently —
        # but a frozen attrs class cannot be subclassed anyway
        # (frozen+slots blocks subclassing with new fields). The
        # exact-type check is the spec mandate (§2.3) regardless.
        # We assert the type is EXACTLY CanonicalEmailContract.
        contract = Email()
        assert type(parse_contract(contract)) is CanonicalEmailContract
