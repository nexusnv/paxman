"""Date contract value object and domain-type factory.

Migrated from ``paxman._contracts.contract`` as part of the additive
reorganisation into ``paxman._capabilities.date``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, cast

import attrs

from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
    strip_authority_override,
)
from paxman._capabilities.date.i18n import SUPPORTED_LANGUAGES
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

# The century policy for 2-digit years (spec §3.2). ``None`` means no century
# policy is declared, so a 2-digit year enumerates every plausible century
# (Don't Guess -> AMBIGUOUS). ``"pivot:YYYY"`` expands ``YY`` via a pivot year.
TwoDigitYearPolicy = Literal["reject", "require_four_digit_year"] | str

_DATE_OUTPUT_FORMATS_ALLOWED = frozenset({"iso", "compact"})


def _validate_output_format_date(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported date formats."""
    if not isinstance(value, str) or value not in _DATE_OUTPUT_FORMATS_ALLOWED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_DATE_OUTPUT_FORMATS_ALLOWED)}, "
            f"got {value!r}"
        )


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
    output_format: Literal["iso", "compact"] = attrs.field(
        default="iso", validator=_validate_output_format_date
    )
    kind: str = "canonical_date"
    version_field: int = 1

    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, object]:
        """Return the Dict DSL form of this contract (round-trips via parse_contract)."""
        return strip_authority_override(
            {
                "kind": self.kind,
                "locale": self.locale,
                "language": self.language,
                "two_digit_year": self.two_digit_year,
                "output_format": self.output_format,
                "version_field": self.version_field,
                "include_grammar": self.include_grammar,
                "exclude_grammar": self.exclude_grammar,
            }
        )


def Date(
    *,
    locale: Literal["ISO", "US", "EU"] = "ISO",
    language: str = "en",
    two_digit_year: TwoDigitYearPolicy | None = None,
    output_format: Literal["iso", "compact"] = "iso",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalDateContract:
    """Domain-type sugar: declare a date contract in user vocabulary.

    ``locale`` defaults to ``"ISO"`` (spec §3.3 / Flag B) so callers that do
    not care about slash ordering need not state it; a *provided* locale is
    still honored exactly (Law 7 — no auto_detect of the input, only a fixed
    default). ``language`` selects the month/weekday-name table (default
    ``"en"``); ``two_digit_year`` selects the century policy (default ``None``,
    i.e. Don't Guess -> AMBIGUOUS for 2-digit years). ``output_format``
    selects the canonical output form (default ``"iso"`` for ``YYYY-MM-DD``;
    ``"compact"`` for ``YYYYMMDD``).
    """
    return _build_date(
        {
            "locale": locale,
            "language": language,
            "two_digit_year": two_digit_year,
            "output_format": output_format,
            "include_grammar": include_grammar,
            "exclude_grammar": exclude_grammar,
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
    if two_digit_year is not None and not isinstance(two_digit_year, str):
        raise ContractError(f"invalid two_digit_year: {two_digit_year!r}; expected string")
    _validate_two_digit_year(two_digit_year)
    output_format = spec.get("output_format", "iso")
    if not isinstance(output_format, str) or output_format not in _DATE_OUTPUT_FORMATS_ALLOWED:
        raise ContractError(
            f"output_format must be one of {sorted(_DATE_OUTPUT_FORMATS_ALLOWED)}, "
            f"got {output_format!r}"
        )
    authority_override = _authority_override_from_spec(spec)
    output_format = cast(Literal["iso", "compact"], output_format)
    inc = cast(Iterable[str], spec.get("include_grammar", ()))
    exc = cast(Iterable[str], spec.get("exclude_grammar", ()))
    return CanonicalDateContract(
        locale=locale,
        language=language,
        two_digit_year=two_digit_year,
        output_format=output_format,
        include_grammar=tuple(inc),
        exclude_grammar=tuple(exc),
        authority_override=authority_override,
    )


register_contract("canonical_date", _build_date)
