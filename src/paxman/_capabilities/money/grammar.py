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


@attrs.frozen
class MoneyParts:
    """Structured parts of a recognized money string."""

    currency: str
    amount: str
    symbol: str | None = None
    code: str | None = None
    sign: str = ""
    canonical: bool = False


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


def _detect_code(text: str, contract: CanonicalMoneyContract) -> tuple[str | None, str, bool]:
    """Detect a leading ISO code (3 letters); validate it matches contract.

    Accepts the optional canonical ":" delimiter immediately after a matching
    code so the emitted canonical form ("ISO4217:amount") is itself a valid
    input (idempotence: canonicalize(canonicalize(x)) == canonicalize(x)).

    Returns (code_or_None, remaining_text). Raises ContractError on mismatch or
    when codes are disallowed.
    """
    # Match a 3-letter code optionally followed by the canonical ":" delimiter
    # (e.g. "USD:12.50"). The delimiter is consumed only when present; when it
    # is, the remainder is the canonical amount (always dot-decimal) and we
    # signal that so the parser does not re-apply the currency's separator
    # convention (idempotence: canonicalize(canonicalize(x)) == canonicalize(x)).
    m = re.match(r"^\s*([A-Za-z]{3})(?::\s*)?(.*)$", text, re.DOTALL)
    if not m:
        return None, text, False
    candidate = m.group(1).upper()
    rest = m.group(2)
    if not re.fullmatch(r"[A-Z]{3}", candidate):
        return None, text, False
    # The contract currency is the ONLY valid code. Any other leading 3-letter
    # token is rejected — Paxman never guesses the currency (Law 3).
    if candidate != contract.currency:
        raise ContractError(
            f"code {candidate!r} does not match contract currency {contract.currency!r}"
        )
    if not contract.allow_code:
        raise ContractError("currency code not allowed by contract")
    canonical = bool(m.group(0)[: m.end(1) + 1].endswith(":"))
    return candidate, rest, canonical


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
    # Split the sign FIRST so a sign outside the symbol/code is handled
    # correctly (e.g. "-RM 5.00" or "RM 5.00-"). Symbol/code detection then
    # runs on the unsigned remainder (Law 7 — Explicit Over Clever).
    sign, unsigned_text = _split_sign(text)
    symbol, after_sym = _detect_symbol(unsigned_text, contract)
    code, after_code, canonical = _detect_code(after_sym, contract)
    amount = after_code.strip()
    if not amount or not re.search(r"[0-9]", amount):
        raise ContractError(f"no numeric amount found in {raw!r}")
    # Centralize the sign: an inner sign (e.g. "RM -5.00") is combined with
    # the outer sign so a negative is a negative regardless of placement (Q2=A).
    # A SECOND sign marker (e.g. "-12.50-", "+-12.50", "(-12.50)") is
    # contradictory/ambiguous and must be rejected — Paxman never guesses among
    # multiple interpretations (MANDATE: ambiguous input -> non-success).
    inner_sign, amount = _split_sign(amount)
    if inner_sign != "" and sign != "":
        raise ContractError(f"multiple/contradictory sign markers in {raw!r}")
    final_sign = "-" if (sign == "-" or inner_sign == "-") else ""
    return MoneyParts(
        currency=contract.currency,
        amount=amount,
        symbol=symbol,
        code=code,
        sign=final_sign,
        canonical=canonical,
    )


def _split_sign(text: str) -> tuple[str, str]:
    """Extract a leading +/-, trailing minus, or parenthesized negative sign.

    Q2=A: negatives accepted. Parenthesized form "(12.50)" means negative; a
    trailing minus ("12.50-") is also a negative. Returns (sign, rest) where
    sign is "" or "-".
    """
    t = text.strip()
    if t.startswith("(") and t.endswith(")"):
        return "-", t[1:-1].strip()
    if t.startswith("-"):
        return "-", t[1:].strip()
    if t.startswith("+"):
        return "", t[1:].strip()
    if t.endswith("-"):
        return "-", t[:-1].strip()
    return "", t


def _validate_thousands(segments: list[str], sep_name: str, raw: str) -> None:
    """Reject ambiguous thousands grouping (mandate: never guess).

    Every segment except possibly the first must be exactly 3 digits. The
    first segment may be 1-3 digits. A segment that violates this is
    ambiguous (Paxman must not guess the separator role) and is rejected.
    """
    for i, seg in enumerate(segments):
        if not seg:
            raise ContractError(f"ambiguous {sep_name} grouping in {raw!r}")
        if i == 0:
            if not (1 <= len(seg) <= 3) or not seg.isdigit():
                raise ContractError(f"ambiguous {sep_name} grouping in {raw!r}")
        else:
            if len(seg) != 3 or not seg.isdigit():
                raise ContractError(f"ambiguous {sep_name} grouping in {raw!r}")


def parse_amount(amount: str, currency: str, canonical: bool = False) -> str:
    """Parse a numeric amount string into the canonical decimal string (F1).

    Args:
        amount: The numeric portion (may contain thousands separators).
        currency: ISO 4217 code (drives the separator convention, Q1=A).
        canonical: when True, `amount` is already in canonical dot-decimal
            form (a re-feed of this capability's own output). Skip the currency
            separator convention and parse the plain decimal directly so the
            canonical form is idempotent
            (canonicalize(canonicalize(x)) == canonicalize(x)).

    Returns:
        Canonical decimal string via Decimal (exact, never float). Literal
        decimal places are preserved (F1) for plain AND scientific input, and
        scientific notation is normalized to a plain decimal (Q3=A).

    Raises:
        ContractError: if the amount is not a valid number, or if a thousands
        separator forms an ambiguous (non-3-digit) grouping.
    """
    comma_decimal = currency in _COMMA_DECIMAL_CURRENCIES

    if canonical:
        # Re-feed of our own canonical output: always dot-decimal, no thousands
        # separators, no currency-specific convention. Parse the exact decimal.
        cleaned = amount.strip()
        if not cleaned:
            raise ContractError(f"empty amount in {amount!r}")
        try:
            value = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ContractError(f"invalid amount {amount!r}") from exc
        plain = format(value, "f")
        return plain

    # Split off a scientific-notation exponent (Q3=A) so the mantissa's
    # separators can be validated independently of the "E". The mantissa is the
    # part BEFORE the exponent; trailing-zero width (F1) is measured on it, not
    # on the post-exponent value.
    exponent_part = ""
    mantissa = amount
    for _i, _ch in enumerate(amount):
        if _ch in "eE":
            mantissa, exponent_part = amount[:_i], amount[_i:]
            break
    base = mantissa

    if comma_decimal:
        # EUR etc.: DOT is the thousands sep, COMMA is the decimal sep.
        if "," in base:
            integer_part, _, frac_part = base.partition(",")
            if not frac_part.isdigit():
                raise ContractError(f"invalid amount {amount!r}")
        else:
            integer_part = base
        if "." in integer_part:
            _validate_thousands(integer_part.split("."), "thousands", amount)
        cleaned = base.replace(".", "").replace(",", ".") + exponent_part
    else:
        # USD/MYR etc.: COMMA is the thousands sep, DOT is the decimal sep.
        if "." in base:
            integer_part, _, frac_part = base.partition(".")
            if not frac_part.isdigit():
                raise ContractError(f"invalid amount {amount!r}")
        else:
            integer_part = base
        if "," in integer_part:
            _validate_thousands(integer_part.split(","), "thousands", amount)
        cleaned = base.replace(",", "") + exponent_part
    cleaned = cleaned.strip()
    if not cleaned:
        raise ContractError(f"empty amount in {amount!r}")

    # Parse exactly with Decimal (never float). Reject non-numeric residue.
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ContractError(f"invalid amount {amount!r}") from exc

    # F1/Q3: preserve the literal fractional-digit count of the INPUT mantissa
    # (not the post-exponent value) and always emit a plain decimal string
    # (no "E"). E.g. "1.25E+2" keeps 2 places -> "125.00"; "1.5e3" -> "1500.0";
    # "1e-2" -> "0.01" (the "E-2" dot must NOT be counted as a decimal point).
    decimal_sep = "," if comma_decimal else "."
    if decimal_sep in mantissa:
        mantissa_frac = len(mantissa.rsplit(decimal_sep, 1)[1])
    else:
        mantissa_frac = 0
    plain = format(value, "f")
    if mantissa_frac:
        if "." not in plain:
            plain += "." + ("0" * mantissa_frac)
        else:
            existing_frac = len(plain.rsplit(".", 1)[1])
            plain += "0" * max(0, mantissa_frac - existing_frac)
    return plain
