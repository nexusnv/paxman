# src/paxman/_capabilities/money/grammar.py
"""Money recognition grammar.

Recognizes a raw money string into structured parts, then parses the amount
into a canonical decimal string. The currency itself is NEVER guessed: it comes
from the contract (Law 3 — Never Guess; Law 7 — Explicit Over Clever). The
grammar only validates that any symbol/code present in the input matches the
contract currency.

Locked decisions (from the design spec, user-approved):
  Q1=A — currency-keyed separator convention (comma-decimal for a fixed set).
  Q2=A — negatives accepted, sign preserved (also parenthesized form).
  Q3=A — scientific notation normalized to plain decimal via Decimal.
  F1   — literal decimal places preserved (NO quantization/rounding).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

import attrs

from paxman._capabilities.money.contract import CanonicalMoneyContract
from paxman._errors import ContractError

# Currencies that conventionally use a COMMA as the decimal separator and a
# dot as the thousands separator (Q1=A). All others use the dot-decimal
# convention. This is a fixed deterministic table (Law 8a — no network).
_COMMA_DECIMAL_CURRENCIES: frozenset[str] = frozenset(
    {
        "EUR",
        "DKK",
        "NOK",
        "SEK",
        "CHF",
        "BRL",
        "RUB",
        "TRY",
        "PLN",
        "HUF",
        "CZK",
        "RON",
        "ILS",
        "ISK",
    }
)

# Symbol → ISO 4217 code map. Symbols are validated against the contract
# currency; an unrecognized or mismatched symbol is rejected.
_SYMBOL_TO_CODE: dict[str, str] = {
    "RM": "MYR",
    "$": "USD",
    "US$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "￥": "JPY",
    "S$": "SGD",
    "A$": "AUD",
    "C$": "CAD",
    "CHF": "CHF",
    "Rs": "INR",
    "₹": "INR",
    "R$": "BRL",
    "kr": "SEK",
    "zł": "PLN",
    "₪": "ILS",
    "₽": "RUB",
    "฿": "THB",
    "Rp": "IDR",
    "₱": "PHP",
    "₩": "KRW",
    "₴": "UAH",
}

# Code → symbol is just the reverse lookup convenience (may be empty).
_CODE_TO_SYMBOL: dict[str, str] = {v: k for k, v in _SYMBOL_TO_CODE.items()}

# A "pure amount" token before separator normalization. Captures optional
# sign, digits, optional thousands separators, optional decimal part.
_AMOUNT_RE = re.compile(r"^\s*([(+-]?)\s*([0-9][0-9.,\s]*?)\s*(?:\))?\s*$")


@attrs.frozen
class MoneyParts:
    """Structured parts of a recognized money string."""

    currency: str
    amount: str
    symbol: str | None = None
    code: str | None = None
    sign: str = ""


def _strip_amount_text(raw: str, contract: CanonicalMoneyContract) -> str:
    """Trim the raw input if strip_spaces is on; reject whitespace-only."""
    if contract.strip_spaces:
        text = raw.strip()
    else:
        text = raw
        if text != text.strip():
            raise ContractError("leading/trailing whitespace not allowed")
    if not text.strip():
        raise ContractError("empty money input")
    return text


def _detect_symbol(text: str, contract: CanonicalMoneyContract) -> tuple[str | None, str]:
    """Detect a leading currency symbol; validate it matches the contract.

    Returns (symbol_or_None, remaining_text). Raises ContractError on mismatch
    or when symbols are disallowed.
    """
    for sym in sorted(_SYMBOL_TO_CODE, key=len, reverse=True):
        if text.startswith(sym):
            if not contract.allow_symbol:
                raise ContractError("currency symbol not allowed by contract")
            code = _SYMBOL_TO_CODE[sym]
            if code != contract.currency:
                raise ContractError(
                    f"symbol {sym!r} denotes {code}, contract expects {contract.currency}"
                )
            return sym, text[len(sym) :].strip()
    return None, text


def _detect_code(text: str, contract: CanonicalMoneyContract) -> tuple[str | None, str]:
    """Detect a leading ISO code (3 letters); validate it matches contract.

    Returns (code_or_None, remaining_text). Raises ContractError on mismatch or
    when codes are disallowed.
    """
    m = re.match(r"^\s*([A-Za-z]{3})\b\s*(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    candidate = m.group(1).upper()
    rest = m.group(2)
    if not re.fullmatch(r"[A-Z]{3}", candidate):
        return None, text
    # Only treat as a code if it is a known ISO code AND matches contract.
    if candidate != contract.currency:
        # A code that is not the contract currency is a hard mismatch.
        if candidate in {
            "MYR",
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "SGD",
            "AUD",
            "CAD",
            "CHF",
        }:
            raise ContractError(
                f"code {candidate!r} does not match contract currency {contract.currency!r}"
            )
        # Otherwise it's not a currency code; leave the text alone.
        return None, text
    if not contract.allow_code:
        raise ContractError("currency code not allowed by contract")
    return candidate, rest


def recognize_money(raw: str, contract: CanonicalMoneyContract) -> MoneyParts:
    """Recognize a raw money string into structured parts.

    Args:
        raw: The raw input string.
        contract: The CanonicalMoneyContract (currency required).

    Returns:
        A MoneyParts with currency, amount, optional symbol/code, and sign.

    Raises:
        ContractError: on empty input, disallowed symbol/code, or mismatch.
    """
    text = _strip_amount_text(raw, contract)
    symbol, after_sym = _detect_symbol(text, contract)
    code, after_code = _detect_code(after_sym, contract)
    sign, amount_text = _split_sign(after_code)
    amount = amount_text.strip()
    if not amount or not re.search(r"[0-9]", amount):
        raise ContractError(f"no numeric amount found in {raw!r}")
    return MoneyParts(
        currency=contract.currency,
        amount=amount,
        symbol=symbol,
        code=code,
        sign=sign,
    )


def _split_sign(text: str) -> tuple[str, str]:
    """Extract a leading +/- or parenthesized negative sign.

    Q2=A: negatives accepted. Parenthesized form "(12.50)" means negative.
    Returns (sign, rest) where sign is "" or "-".
    """
    t = text.strip()
    if t.startswith("(") and t.endswith(")"):
        return "-", t[1:-1].strip()
    if t.startswith("-"):
        return "-", t[1:].strip()
    if t.startswith("+"):
        return "", t[1:].strip()
    return "", t


def parse_amount(amount: str, currency: str) -> str:
    """Parse a numeric amount string into the canonical decimal string (F1).

    Args:
        amount: The numeric portion (may contain thousands separators).
        currency: ISO 4217 code (drives the separator convention, Q1=A).

    Returns:
        Canonical decimal string via Decimal (exact, never float). Literal
        decimal places are preserved (F1). Scientific notation is normalized
        (Q3=A).

    Raises:
        ContractError: if the amount is not a valid number.
    """
    comma_decimal = currency in _COMMA_DECIMAL_CURRENCIES
    if comma_decimal:
        # "1.234,56" → "1234.56": remove dots (thousands), swap comma→dot.
        cleaned = amount.replace(".", "").replace(",", ".")
    else:
        # "1,234.56" → "1234.56": remove commas (thousands).
        cleaned = amount.replace(",", "")
    cleaned = cleaned.strip()
    if not cleaned:
        raise ContractError(f"empty amount in {amount!r}")
    if cleaned.count(".") > 1:
        raise ContractError(f"multiple decimal points in {amount!r}")
    # Scientific notation (Q3=A): normalize to a plain decimal string.
    if "e" in cleaned.lower():
        try:
            value = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ContractError(f"invalid amount {amount!r}") from exc
        if value == value.to_integral_value():
            return str(value.to_integral_value())
        return format(value, "f")
    # Reject any non-numeric residue (letters, stray symbols).
    if not re.fullmatch(r"[+-]?[0-9]+(\.[0-9]+)?", cleaned):
        raise ContractError(f"invalid amount {amount!r}")
    # F1 — literal decimal places preserved (no quantization/rounding).
    return cleaned
