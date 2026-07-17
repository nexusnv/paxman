# src/paxman/_capabilities/money/rules.py
"""Money Law 14 rule manifest.

Mandate Law 14 requires every capability to document its canonicalization
rules. This module returns a declarative, contract-aware manifest of the
money canonicalization rules as a list of dicts. The manifest is plain data
(no attrs, mirroring the IP sibling's manifest style) so it can be inspected,
serialized, and asserted against without executing the canonicalizer.
"""

from __future__ import annotations

from typing import Any

from paxman._capabilities.money.contract import CanonicalMoneyContract


def get_money_rules(contract: CanonicalMoneyContract) -> list[dict[str, Any]]:
    """Return the Law 14 rule manifest for the money capability.

    The manifest is a list of rule dicts, each with ``id``, ``summary``, and
    ``deterministic`` keys. The summaries encode the locked money design
    decisions and the two-part nature of money (currency + amount). Where a
    rule depends on contract policy, the summary is rendered contract-aware.

    Args:
        contract: the money contract whose policy shapes the manifest.

    Returns:
        A list of exactly eight rule dicts, each ``deterministic`` set to True.
    """
    currency = contract.currency
    symbol_policy = (
        "recognized only when allow_symbol is true"
        if contract.allow_symbol
        else "rejected when allow_symbol is false"
    )
    code_policy = (
        "recognized only when allow_code is true"
        if contract.allow_code
        else "rejected when allow_code is false"
    )
    return [
        {
            "id": "M1",
            "summary": (
                f"Currency is taken from the contract ({currency}); "
                "Paxman never guesses it (Law 3 — Never Guess; "
                "Law 7 — Explicit Over Clever)."
            ),
            "deterministic": True,
        },
        {
            "id": "M2",
            "summary": (
                "The canonical form is a single string '<ISO4217>:<amount>' "
                "concatenating the contract currency and the canonical amount."
            ),
            "deterministic": True,
        },
        {
            "id": "M3",
            "summary": (
                "Input symbols ($/€/£/¥/RM) are "
                f"{symbol_policy} and must match the contract currency; "
                "otherwise the input is rejected (ContractError)."
            ),
            "deterministic": True,
        },
        {
            "id": "M4",
            "summary": (
                "Input ISO codes (e.g. MYR) are "
                f"{code_policy} and must match the contract currency; "
                "otherwise the input is rejected (ContractError)."
            ),
            "deterministic": True,
        },
        {
            "id": "M5",
            "summary": (
                "Whitespace around the amount is trimmed only when "
                "strip_spaces is true; otherwise surrounding whitespace is "
                "rejected."
            ),
            "deterministic": True,
        },
        {
            "id": "M6",
            "summary": (
                "Negatives are preserved (leading '-' or parenthesized "
                "'(...)'); the sign is carried into the canonical amount (Q2=A)."
            ),
            "deterministic": True,
        },
        {
            "id": "M7",
            "summary": (
                "Amounts are parsed exactly with Decimal (never float); "
                "thousands separators are stripped and the decimal separator "
                "follows the currency-keyed convention, comma-decimal for "
                "EUR/DKK/NOK/SEK/CHF/BRL/RUB/TRY/PLN/HUF/CZK/RON/ILS/ISK (Q1=A)."
            ),
            "deterministic": True,
        },
        {
            "id": "M8",
            "summary": (
                "Literal decimal places are preserved (no rounding or "
                "quantization); scientific notation is normalized to plain "
                "decimal (F1, Q3=A)."
            ),
            "deterministic": True,
        },
    ]
