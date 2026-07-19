"""Date rule authority map and the Evidence builder.

Migrated from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._capabilities._shared.evidence import make_evidence
from paxman._provenance import Authority
from paxman._provenance import registries as R

_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # dispatch invariants (no authority — Law 14 §3.6 allow-list)
        "not_a_date_contract": None,
        "not_a_string_value": None,
        "empty_value": None,
        "unrecognized_format": None,
        # rejecting rules
        "numeric_format_requires_us_or_eu_locale": R.PAXMAN_SPEC_DATE.section(
            "ISO locale rejects slash forms; Law 7"
        ),
        "invalid_iso_format": R.ISO_8601.section("§5.2.1"),
        "invalid_calendar_date": R.ISO_8601.section("(Gregorian calendar validity)"),
        "ambiguous_two_digit_year": R.PAXMAN_SPEC_DATE.section(
            "2-digit year with no `two_digit_year` century policy; Don't Guess -> AMBIGUOUS"
        ),
        "ambiguous_naive_datetime": R.RFC_3339.section("§5.6 (unknown local offset convention)"),
        "invalid_epoch_value": R.IEEE_1003_1.section("(epoch seconds out of representable range)"),
        # transforming rules (success path)
        "parsed_iso_date": R.ISO_8601.section("§5.2.1"),
        "parsed_iso_datetime": R.RFC_3339,
        "parsed_us_numeric": R.PAXMAN_SPEC_DATE.section("(US MM/DD/YYYY reading)"),
        "parsed_eu_numeric": R.PAXMAN_SPEC_DATE.section("(EU DD/MM/YYYY reading)"),
        "parsed_rfc2822": R.RFC_2822.section("§3.3"),
        "parsed_unix_timestamp": Authority(
            "POSIX/IEEE 1003.1 + RFC 3339",
            "POSIX/IEEE 1003.1 (epoch seconds) + RFC 3339",
            "specification",
        ),
        "normalized_to_utc": R.RFC_3339.section("§4.1 (instant equivalence) + §4.2 (Z designator)"),
        "no_transformation_needed": R.ISO_8601.section(
            "§5.2.1 / RFC 3339 (input already canonical)"
        ),
        # multilingual enumeration model
        "parsed_text_month_date": R.PAXMAN_SPEC_DATE.section(
            "full/abbrev month name in declared language; Law 14 declared Paxman policy"
        ),
        "parsed_numeric_date": R.PAXMAN_SPEC_DATE.section(
            "numeric slash form enumerated per locale ordering; architectural discussion §2"
        ),
        "parsed_numeric_ymd_date": R.PAXMAN_SPEC_DATE.section(
            "year-first numeric slash, ISO 8601 slash ordering; fixed Y/M/D reading"
        ),
        "ambiguous_ordering": R.PAXMAN_SPEC_DATE.section(
            "MM/DD and DD/MM both survive under locale=ISO; Don't Guess -> AMBIGUOUS"
        ),
        "rejected_two_digit_year": R.PAXMAN_SPEC_DATE.section("`two_digit_year='reject'` policy"),
        "weekday_contradicts_date": R.PAXMAN_SPEC_DATE.section(
            "semantic validation: weekday must match calendar; architectural discussion §3 Stage 4"
        ),
    }
)


# Shared Law-14 closure bound to this capability's authority manifest.
_evidence = make_evidence(_RULE_AUTHORITIES)
