# src/paxman/_capabilities/money/rules.py
"""Money Law 14 rule→authority manifest + evidence helper.

Migrated from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158). The
authoritative Law 14 surface is the `_RULE_AUTHORITIES` mapping
(rule-name → Authority) plus the `_evidence` helper that the
canonicalizer consumes. Every emitted `Evidence` carries an `authority`
citation sourced from `_RULE_AUTHORITIES`. A separate `get_money_rules`
summary artifact is provided for human-readable introspection (it is NOT
the Law 14 surface).

The bundled dataset editions (ISO 4217, Unicode CLDR) are declared once
in the central registry (`paxman._provenance.registries`) and referenced
here by import — they are no longer interpolated as strings.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from paxman._capabilities._shared.evidence import make_evidence_for
from paxman._capabilities.money.contract import CanonicalMoneyContract
from paxman._provenance import Authority
from paxman._provenance import registries as R

# Composite authorities used by single money rules that cite more than one
# source.
_CURRENCY_FROM_CONTRACT = Authority(
    "MANDATE + ISO 4217",
    "MANDATE Law 3 (Never Guess) + Law 7 (Explicit Over Clever); currency is an ISO 4217:2015 code",
    "specification",
)
_CANONICAL_FORM = Authority(
    "paxman spec/money + ISO 4217",
    "money design spec M2 ('<ISO4217>:<amount>'); currency is an ISO 4217:2015 code",
    "policy",
)
_SYMBOL_VALIDATED = Authority(
    "Unicode CLDR + ISO 4217",
    "Unicode CLDR currency symbol data (frozen glyph→ISO 4217 code map) + "
    "contract currency match (Law 3 — Never Guess)",
    "data-set",
)
_CODE_VALIDATED = R.ISO_4217.section(
    "code must be a recognized ISO 4217 code and match the contract currency"
)
_PARSED_DECIMAL = Authority(
    "Unicode CLDR + money design spec",
    "Unicode CLDR currency number patterns (frozen comma-decimal convention) + "
    "money design spec Q1=A (Decimal, comma-decimal per currency)",
    "data-set",
)

# Law 14 rule→authority manifest. Dispatch invariants (not_a_money_contract,
# not_a_string_value) are allow-listed with ``None`` authority (Law 14
# §3.6): they describe a routing failure, not a canonical-form rule. Every
# canonical-form rule cites an authoritative source (mandate law or the
# approved money design spec).
_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # --- dispatch invariants (no authority — Law 14 §3.6 allow-list) ---
        "not_a_money_contract": None,
        "not_a_string_value": None,
        # missing_value is a canonical-form rejection (empty input), not a
        # routing failure, so it carries a real citation (Law 3 — Never Guess).
        "missing_value": Authority(
            "money design spec",
            "empty input rejected — Law 3 Never Guess",
            "policy",
        ),
        # --- recognition / canonicalization (mandate laws + design spec) ---
        "currency_from_contract": _CURRENCY_FROM_CONTRACT,
        "canonical_form": _CANONICAL_FORM,
        "symbol_validated": _SYMBOL_VALIDATED,
        "code_validated": _CODE_VALIDATED,
        "trimmed_whitespace": R.PAXMAN_SPEC_MONEY.section("strip_spaces policy"),
        "preserved_sign": R.PAXMAN_SPEC_MONEY.section("design spec Q2=A (negatives preserved)"),
        "parsed_decimal": _PARSED_DECIMAL,
        "preserved_decimals": R.PAXMAN_SPEC_MONEY.section(
            "design spec F1/Q3=A (no quantization; sci-notation normalized)"
        ),
        "unrecognized_format": R.PAXMAN_SPEC_MONEY.section(
            "rejected: empty, malformed, or symbol/code mismatch — Law 3 Never Guess"
        ),
    }
)


# Rules whose authority cites the ISO 4217 registry. When an engine binds a
# non-default ISO 4217 edition, the recorded authority must reflect that
# edition (Concern 3 — replay is deterministic against the pinned edition).
_ISO_4217_RULES = frozenset({"code_validated"})


# Engine-aware evidence closure: registry-citing rules re-resolve their
# authority from the engine's bound ISO 4217 edition (Concern 3). Money is
# engine-aware (trial architecture, citing ISO 4217) — mirroring country.
_evidence = make_evidence_for(_RULE_AUTHORITIES, "ISO 4217", registry_rules=_ISO_4217_RULES)


def get_money_rules(contract: CanonicalMoneyContract) -> list[dict[str, Any]]:
    """Human-readable summary of the money canonicalization rules.

    NOTE: this is an introspection/summary artifact. The authoritative Law 14
    surface is `_RULE_AUTHORITIES` + `_evidence`, consumed by the canonicalizer.
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
