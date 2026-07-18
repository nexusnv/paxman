"""Date contract value object and domain-type factory.

Migrated from ``paxman._contracts.contract`` as part of the additive
reorganisation into ``paxman._capabilities.date``.
"""

from __future__ import annotations

from typing import Any, Literal

import attrs

from paxman._capabilities.date.i18n import SUPPORTED_LANGUAGES
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

# The century policy for 2-digit years (spec §3.2). ``None`` means no century
# policy is declared, so a 2-digit year enumerates every plausible century
# (Don't Guess -> AMBIGUOUS). ``"pivot:YYYY"`` expands ``YY`` via a pivot year.
TwoDigitYearPolicy = Literal["reject", "require_four_digit_year"] | str


@attrs.frozen
class CanonicalDateContract:
    """The date contract (MANDATE §4: the contract is the user's language).

    ``locale`` declares the numeric slash ordering policy. It defaults to
    ``"ISO"`` (spec §3.3 / Flag B): a *provided* locale is honored exactly, but
    an *absent* locale falls back to ``"ISO"`` rather than raising. ``"ISO"``
    enumerates both ``MM/DD`` and ``DD/MM`` orderings (so ambiguous slash forms
    report ``AMBIGUOUS`` instead of being guessed). ``language`` declares the
    month/weekday-name reading policy (default ``"en"``); ``two_digit_year``
    declares the century policy (default ``None``).
    """

    locale: Literal["ISO", "US", "EU"] = "ISO"
    language: str = "en"
    two_digit_year: TwoDigitYearPolicy | None = None
    kind: str = "canonical_date"
    version_field: int = 1

    authority_override: Any = attrs.field(
        default=None,
        repr=False,
    )

    def as_dict(self) -> dict[str, object]:
        """Return the Dict DSL form of this contract (round-trips via parse_contract)."""
        return {
            "kind": self.kind,
            "locale": self.locale,
            "language": self.language,
            "two_digit_year": self.two_digit_year,
            "version_field": self.version_field,
        }


def Date(
    *,
    locale: Literal["ISO", "US", "EU"] = "ISO",
    language: str = "en",
    two_digit_year: TwoDigitYearPolicy | None = None,
    authority_override: Any | None = None,
) -> CanonicalDateContract:
    """Domain-type sugar: declare a date contract in user vocabulary.

    ``locale`` defaults to ``"ISO"`` (spec §3.3 / Flag B) so callers that do
    not care about slash ordering need not state it; a *provided* locale is
    still honored exactly (Law 7 — no auto_detect of the input, only a fixed
    default). ``language`` selects the month/weekday-name table (default
    ``"en"``); ``two_digit_year`` selects the century policy (default ``None``,
    i.e. Don't Guess -> AMBIGUOUS for 2-digit years).
    """
    return _build_date(
        {
            "locale": locale,
            "language": language,
            "two_digit_year": two_digit_year,
            "authority_override": authority_override,
        }
    )


def _validate_two_digit_year(policy: TwoDigitYearPolicy | None) -> None:
    """Validate a ``two_digit_year`` policy string against the allowed forms."""
    if policy is None:
        return
    if policy in ("reject", "require_four_digit_year"):
        return
    if isinstance(policy, str) and policy.startswith("pivot:"):
        pivot_str = policy.split(":", 1)[1]
        # Strictly a 4-digit year: reject signs, leading zeros tricks,
        # underscores, and wrong lengths at contract-build time.
        if not (pivot_str.isdigit() and len(pivot_str) == 4):
            raise ContractError(f"invalid two_digit_year pivot: {policy!r}; expected 'pivot:YYYY'")
        return
    raise ContractError(
        f"invalid two_digit_year: {policy!r}; "
        "allowed: 'reject', 'require_four_digit_year', or 'pivot:YYYY'"
    )


def _build_date(spec: dict[str, object]) -> CanonicalDateContract:
    locale = spec.get("locale", "ISO")
    if locale not in {"ISO", "US", "EU"}:
        raise ContractError(f"invalid or missing locale: {locale!r}; allowed: ['ISO', 'US', 'EU']")
    language = spec.get("language", "en")
    if language not in SUPPORTED_LANGUAGES:
        raise ContractError(
            f"unsupported language: {language!r}; allowed: {sorted(SUPPORTED_LANGUAGES)}"
        )
    two_digit_year = spec.get("two_digit_year", None)
    _validate_two_digit_year(two_digit_year)
    authority_override = spec.get("authority_override", None)
    return CanonicalDateContract(
        locale=locale,
        language=language,
        two_digit_year=two_digit_year,
        authority_override=authority_override,
    )


register_contract("canonical_date", _build_date)
