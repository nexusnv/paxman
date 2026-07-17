"""End-to-end exercise of the public Money canonicalization API."""

from __future__ import annotations

import pytest

from paxman import Money, canonicalize, parse_contract, replay
from paxman._capabilities.discovery import builtin_capabilities
from paxman._core.status import Status


@pytest.mark.integration
def test_public_api_canonicalize_and_replay() -> None:
    artifact = canonicalize("RM 12.50", Money(currency="MYR"))
    assert artifact.status is Status.CANONICALIZED
    assert artifact.value == "MYR:12.50"
    replayed = replay(artifact, Money(currency="MYR"))
    assert replayed == artifact
    assert replayed.canonical_bytes() == artifact.canonical_bytes()


@pytest.mark.integration
def test_dict_dsl_contract_round_trip() -> None:
    spec = {
        "kind": "canonical_money",
        "currency": "USD",
        "allow_symbol": True,
        "allow_code": True,
        "strip_spaces": True,
    }
    contract = parse_contract(spec)
    assert contract.kind == "canonical_money"
    artifact = canonicalize("USD 1,234.56", contract)
    assert artifact.value == "USD:1234.56"


@pytest.mark.integration
def test_money_is_registered_as_builtin() -> None:
    # The registry auto-loads built-ins on first canonicalize; money must be
    # among them (the 8th built-in).
    cap = builtin_capabilities()
    names = {c.name for c in cap}
    assert "money_canonicalization" in names


@pytest.mark.integration
def test_symbol_and_code_forms_agree() -> None:
    by_symbol = canonicalize("RM 10.00", Money(currency="MYR"))
    by_code = canonicalize("MYR 10.00", Money(currency="MYR"))
    by_plain = canonicalize("10.00", Money(currency="MYR"))
    assert by_symbol.value == by_code.value == by_plain.value == "MYR:10.00"


@pytest.mark.integration
def test_negative_forms_agree() -> None:
    by_minus = canonicalize("-5.00", Money(currency="MYR"))
    by_paren = canonicalize("(5.00)", Money(currency="MYR"))
    assert by_minus.value == by_paren.value == "MYR:-5.00"


@pytest.mark.integration
def test_eur_comma_decimal_end_to_end() -> None:
    artifact = canonicalize("1.234,56", Money(currency="EUR"))
    assert artifact.value == "EUR:1234.56"
    replayed = replay(artifact, Money(currency="EUR"))
    assert replayed.value == "EUR:1234.56"


@pytest.mark.integration
def test_invalid_input_is_reported_not_raised() -> None:
    artifact = canonicalize("€ 10.00", Money(currency="MYR"))
    assert artifact.status is Status.INVALID
    # Replay of an INVALID artifact is still safe and equal.
    assert replay(artifact, Money(currency="MYR")) == artifact


@pytest.mark.integration
def test_evidence_cites_law_14_rules() -> None:
    artifact = canonicalize("RM 12.50", Money(currency="MYR"))
    rules = {e.rule for e in artifact.evidence}
    assert "currency_from_contract" in rules
    assert "canonical_form" in rules
    # Every evidence carries provenance (Law 14).
    assert all(
        e.provenance
        for e in artifact.evidence
        if e.rule
        not in (
            "not_a_money_contract",
            "not_a_string_value",
            "missing_value",
        )
    )


@pytest.mark.integration
def test_disallowed_symbol_rejected() -> None:
    artifact = canonicalize("RM 10.00", Money(currency="MYR", allow_symbol=False))
    assert artifact.status is Status.INVALID
