# src/paxman/_capabilities/money/canonicalizer.py
"""MoneyCapability: a built-in capability of Paxman v2.

Mandate Laws 3, 5, 7, 8a, 11, 14. The currency is taken from the contract
(Law 3 — Never Guess; Law 7 — Explicit Over Clever); the grammar only validates
that any symbol/code present in the input matches the contract currency. The
canonical form is "<ISO4217>:<amount>" where the amount is the canonical decimal
string from `parse_amount` (F1 literal decimals, Q1/Q2/Q3 applied).
"""

from __future__ import annotations

from paxman._capabilities._shared.base import CapabilityBase
from paxman._capabilities.money.contract import CanonicalMoneyContract
from paxman._capabilities.money.grammar import parse_amount, recognize_money
from paxman._capabilities.money.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.engine_env import Engine
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status
from paxman._errors import ContractError


class MoneyCapability(CapabilityBase):
    """A pure deterministic transformation that canonicalizes money strings."""

    name: str = "money_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        """Return True if this capability canonicalizes the given contract.

        Accepts a CanonicalMoneyContract with a string (or None) value.
        """
        return isinstance(contract, CanonicalMoneyContract) and (
            value is None or isinstance(value, str)
        )

    def canonicalize(
        self, value: object, contract: Contract, engine: Engine | None = None
    ) -> CapabilityResult:
        """Canonicalize a money string into "<ISO4217>:<amount>".

        Args:
            value: The raw money string (or None).
            contract: The CanonicalMoneyContract (currency required).

        Returns:
            A CapabilityResult with status CANONICALIZED and the canonical form,
            or INVALID when the input cannot be deterministically resolved
            (empty, malformed, or a symbol/code that does not match the contract).
        """
        if not isinstance(contract, CanonicalMoneyContract):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_money_contract", engine=engine),)
            )
        if not (value is None or isinstance(value, str)):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_string_value", engine=engine),)
            )

        # Missing/whitespace-only value -> INVALID (spec: empty input rejected).
        if value is None or value.strip(" \t\r\n\f\v") == "":
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("missing_value", engine=engine),)
            )

        # Track whether surrounding whitespace was stripped (record if changed).
        # Only strip when the contract policy allows it (Law 7 — policy is the
        # truth). When strip_spaces is False, preserve the original value and let
        # the grammar reject surrounding whitespace without emitting
        # trimmed_whitespace evidence for a transformation the contract forbids.
        stripped_evidence: tuple = ()
        if contract.strip_spaces:
            stripped = value.strip(" \t\r\n\f\v")
            if stripped != value:
                stripped_evidence = (_evidence("trimmed_whitespace", engine=engine),)
                value = stripped

        # Recognition layer (Layer 1) — shape classification + symbol/code
        # validation. A malformed or mismatched input raises ContractError here
        # (never guessed) and is surfaced as INVALID.
        try:
            parts = recognize_money(value, contract)
        except ContractError:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format", engine=engine),)
            )

        # Parse the amount into the canonical decimal string (F1/Q1/Q2/Q3).
        # When the input was our own canonical form (re-feed), `parts.canonical`
        # is True so the parser skips the currency separator convention.
        try:
            parsed = parse_amount(parts.amount, contract.currency, parts.canonical)
        except ContractError:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format", engine=engine),)
            )

        # Compose the canonical form "<ISO4217>:<sign><amount>".
        canonical = f"{contract.currency}:{parts.sign}{parsed}"

        evidence: list[Evidence] = list(stripped_evidence)
        evidence.append(
            _evidence("currency_from_contract", f"currency={contract.currency}", engine=engine)
        )
        if parts.symbol is not None:
            evidence.append(_evidence("symbol_validated", f"symbol={parts.symbol}", engine=engine))
        if parts.code is not None:
            evidence.append(_evidence("code_validated", f"code={parts.code}", engine=engine))
        if parts.sign:
            evidence.append(_evidence("preserved_sign", f"sign={parts.sign}", engine=engine))
        evidence.append(_evidence("parsed_decimal", f"amount={parts.amount}", engine=engine))
        if "." in parts.amount or "e" in parts.amount.lower() or "E" in parts.amount:
            evidence.append(
                _evidence("preserved_decimals", f"amount={parts.amount}", engine=engine)
            )
        evidence.append(_evidence("canonical_form", f"{value!r} -> {canonical!r}", engine=engine))

        return CapabilityResult(
            status=Status.CANONICALIZED, value=canonical, evidence=tuple(evidence)
        )
