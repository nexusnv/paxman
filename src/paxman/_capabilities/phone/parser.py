"""ISO 3166-1 alpha-2 -> E.164 country code lookup (v1 frozen subset).

Mandate Law 5: the contract declares the country; this table is the
deterministic mapping from that declared policy to the E.164 prefix. No
inference, no dataset. Extending the table is a capability-version bump
(Law 8a) — the version rides on the artifact's VersionStamp.
"""

from __future__ import annotations

from typing import Mapping

from paxman._errors import ContractError

# Frozen subset of ITU-T E.164 country codes keyed by ISO 3166-1 alpha-2.
# v1 ships the most common calling regions; extend deliberately, never
# silently. Each entry cites ITU-T E.164 / ISO 3166-1.
_COUNTRY_TO_CC: Mapping[str, str] = {
    "US": "1",
    "CA": "1",
    "GB": "44",
    "DE": "49",
    "FR": "33",
    "IT": "39",
    "ES": "34",
    "NL": "31",
    "SE": "46",
    "AU": "61",
    "JP": "81",
    "KR": "82",
    "CN": "86",
    "IN": "91",
    "BR": "55",
    "MX": "52",
    "RU": "7",
}


def _cc_for_country(country: str) -> str:
    """Return the E.164 country code for an ISO 3166-1 alpha-2 code.

    Raises:
        ContractError: if `country` is not a known code in the v1 table.
            Unknown codes are a contract error at parse time, never a
            runtime guess (Law 3 — Never Guess).
    """
    cc = _COUNTRY_TO_CC.get(country.upper())
    if cc is None:
        raise ContractError(
            f"unknown country code: {country!r}; "
            f"supported: {sorted(_COUNTRY_TO_CC)}"
        )
    return cc
