"""Tests for the money rule manifest (mandate Law 14)."""

from __future__ import annotations

from paxman._capabilities.money.contract import Money
from paxman._capabilities.money.rules import get_money_rules


def test_rules_is_list_of_dicts() -> None:
    rules = get_money_rules(Money(currency="MYR"))
    assert isinstance(rules, list)
    assert rules
    assert all(isinstance(r, dict) for r in rules)


def test_rules_have_required_keys() -> None:
    rules = get_money_rules(Money(currency="MYR"))
    for r in rules:
        assert "id" in r
        assert "summary" in r
        assert "deterministic" in r


def test_rules_are_deterministic_flag_true() -> None:
    rules = get_money_rules(Money(currency="MYR"))
    assert all(r["deterministic"] is True for r in rules)


def test_rules_mention_currency_not_guessed() -> None:
    rules = get_money_rules(Money(currency="MYR"))
    joined = " ".join(r["summary"] for r in rules)
    assert "currency" in joined.lower()
    # Law 3 — Never Guess: the canonicalizer must not invent the currency.
    assert "never" in joined.lower() or "guess" in joined.lower()


def test_rules_count_matches_spec() -> None:
    # The design spec defines a fixed set of money canonicalization rules.
    rules = get_money_rules(Money(currency="MYR"))
    assert len(rules) == 8


def test_rule_ids_unique() -> None:
    rules = get_money_rules(Money(currency="MYR"))
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))


def test_rules_reflect_contract_policy() -> None:
    # When symbols are disallowed, a rule should note symbol rejection.
    rules = get_money_rules(Money(currency="MYR", allow_symbol=False))
    joined = " ".join(r["summary"] for r in rules)
    assert "symbol" in joined.lower()


def test_symbol_policy_flips_with_contract() -> None:
    from paxman._capabilities.money.rules import get_money_rules

    off = get_money_rules(Money(currency="MYR", allow_symbol=False))
    on = get_money_rules(Money(currency="MYR", allow_symbol=True))
    m3_off = next(r for r in off if r["id"] == "M3")["summary"]
    m3_on = next(r for r in on if r["id"] == "M3")["summary"]
    assert "rejected when allow_symbol is false" in m3_off
    assert "recognized only when allow_symbol is true" in m3_on


def test_authority_manifest_present() -> None:
    from paxman._capabilities.money.rules import _RULE_AUTHORITIES, _evidence

    assert "currency_from_contract" in _RULE_AUTHORITIES
    assert _RULE_AUTHORITIES["currency_from_contract"] is not None
    ev = _evidence("currency_from_contract", "MYR")
    assert ev.authority == _RULE_AUTHORITIES["currency_from_contract"]
    assert ev.rule == "currency_from_contract"
