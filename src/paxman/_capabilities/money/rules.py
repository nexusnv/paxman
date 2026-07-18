# src/paxman/_capabilities/money/rules.py
"""Money Law 14 rule→provenance manifest + evidence helper.

Mirrors the IP sibling convention: the authoritative Law 14 surface is the
`_RULE_PROVENANCE` mapping (rule-name → provenance citation) plus the
`_evidence` helper that the canonicalizer consumes. Every emitted `Evidence`
carries a `provenance` citation sourced from `_RULE_PROVENANCE`. A separate
`get_money_rules` summary artifact is provided for human-readable
introspection (it is NOT the Law 14 surface).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from paxman._capabilities.money.contract import (
    MONEY_TABLE_VERSION,
    CanonicalMoneyContract,
)
from paxman._core.provenance import Evidence

# Law 14 rule→provenance manifest. Dispatch invariants (not_a_money_contract,
# not_a_string_value) are allow-listed with empty provenance (Law 14 §3.6):
# they describe a routing failure, not a canonical-form rule. Every
# canonical-form rule cites an authoritative source (mandate law or the
# approved money design spec).
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 §3.6 allow-list) ---
        "not_a_money_contract": "",
        "not_a_string_value": "",
        # missing_value is a canonical-form rejection (empty input), not a
        # routing failure, so it carries a real citation (Law 3 — Never Guess).
        "missing_value": "money design spec (empty input rejected — Law 3 Never Guess)",
        # --- recognition / canonicalization (mandate laws + design spec) ---
        "currency_from_contract": (
            f"MANDATE Law 3 (Never Guess) + Law 7 (Explicit Over Clever); "
            f"currency is an ISO 4217:2015 code ({MONEY_TABLE_VERSION})"
        ),
        "canonical_form": (
            f"money design spec M2 ('<ISO4217>:<amount>'); currency is an "
            f"ISO 4217:2015 code ({MONEY_TABLE_VERSION})"
        ),
        "symbol_validated": (
            "Unicode CLDR currency symbol data (frozen glyph→ISO 4217 code map); "
            "symbol recognized via the bundled symbol table and must match the "
            "contract currency (Law 3 — Never Guess)"
        ),
        "code_validated": (
            f"ISO 4217:2015 ({MONEY_TABLE_VERSION}); code must be a recognized "
            f"ISO 4217 code and match the contract currency"
        ),
        "trimmed_whitespace": "money design spec (strip_spaces policy)",
        "preserved_sign": "money design spec Q2=A (negatives preserved)",
        "parsed_decimal": (
            "Unicode CLDR currency number patterns (frozen comma-decimal "
            "convention table); money design spec Q1=A (Decimal, "
            "comma-decimal per currency)"
        ),
        "preserved_decimals": (
            "money design spec F1/Q3=A (no quantization; sci-notation normalized)"
        ),
        "unrecognized_format": (
            "money design spec (rejected: empty, malformed, or symbol/code "
            "mismatch — Law 3 Never Guess)"
        ),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])


def get_money_rules(contract: CanonicalMoneyContract) -> list[dict[str, Any]]:
    """Human-readable summary of the money canonicalization rules.

    NOTE: this is an introspection/summary artifact. The authoritative Law 14
    surface is `_RULE_PROVENANCE` + `_evidence`, consumed by the canonicalizer.
    """
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
                "Currency is taken from the contract; Paxman never guesses it "
                "(Law 3 — Never Guess; Law 7 — Explicit Over Clever)."
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
                "EUR/DKK/NOK/SEK/BRL/RUB/TRY/PLN/HUF/CZK/RON/CHE (Q1=A)."
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
