"""Date rule provenance map and the Evidence builder.

Migrated verbatim from ``paxman._capabilities.builtins.date``.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # dispatch invariants (no provenance — Law 14 §3.6 allow-list)
        "not_a_date_contract": "",
        "not_a_string_value": "",
        "empty_value": "",
        "unrecognized_format": "",
        # rejecting rules
        "numeric_format_requires_us_or_eu_locale": (
            "paxman spec/date (ISO locale rejects slash forms; Law 7)"
        ),
        "invalid_iso_format": "ISO 8601:2004 §5.2.1",
        "invalid_calendar_date": "ISO 8601:2004 (Gregorian calendar validity)",
        "ambiguous_two_digit_year": (
            "paxman spec/date (2-digit year with no `two_digit_year` century policy; "
            "Don't Guess -> AMBIGUOUS)"
        ),
        "ambiguous_naive_datetime": "RFC 3339 §5.6 (unknown local offset convention)",
        "invalid_epoch_value": "POSIX/IEEE 1003.1 (epoch seconds out of representable range)",
        # transforming rules (success path)
        "parsed_iso_date": "ISO 8601:2004 §5.2.1",
        "parsed_iso_datetime": "RFC 3339",
        "parsed_us_numeric": "paxman spec/date (US MM/DD/YYYY reading)",
        "parsed_eu_numeric": "paxman spec/date (EU DD/MM/YYYY reading)",
        "parsed_rfc2822": "RFC 2822 §3.3",
        "parsed_unix_timestamp": "POSIX/IEEE 1003.1 (epoch seconds) + RFC 3339",
        "normalized_to_utc": "RFC 3339 §4.1 (instant equivalence) + §4.2 (Z designator)",
        "no_transformation_needed": "ISO 8601:2004 §5.2.1 / RFC 3339 (input already canonical)",
        # multilingual enumeration model (spec 2026-07-16-date-multilang; Law 14 #3)
        "parsed_text_month_date": (
            "paxman spec/date (full/abbrev month name in declared language; "
            "Law 14 declared Paxman policy — no single RFC governs multilingual month names)"
        ),
        "parsed_numeric_date": (
            "paxman spec/date (numeric slash form enumerated per locale ordering; "
            "architectural discussion §2)"
        ),
        "ambiguous_ordering": (
            "paxman spec/date (MM/DD and DD/MM both survive under locale=ISO; "
            "Don't Guess -> AMBIGUOUS)"
        ),
        "rejected_two_digit_year": "paxman spec/date (`two_digit_year='reject'` policy)",
        "weekday_contradicts_date": (
            "paxman spec/date (semantic validation: weekday must match calendar; "
            "architectural discussion §3 Stage 4)"
        ),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an Evidence node for the given rule.

    Args:
        rule: The rule name; must be a key in ``_RULE_PROVENANCE``.
        detail: Optional human-readable detail string.

    Returns:
        An ``Evidence`` instance with provenance resolved from the map.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])
