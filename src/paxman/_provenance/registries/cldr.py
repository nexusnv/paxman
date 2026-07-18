"""Unicode CLDR registry authority (kind="registry", single bundled edition).

CLDR provides localized country names; Paxman pins the edition it bundles.
The localized-name TABLE lives in the country capability's tables; this
authority records the edition for provenance + replay.
"""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

CLDR: Authority = Authority(
    name="Unicode CLDR",
    edition="cldr-45",
    kind="registry",
    publisher="Unicode",
    released_on="2024-01-01",
    lifecycle="active",
    supports_multiple_editions=True,
    dataset=None,
    checksum="cldr-45",
)

_EDITIONS: dict[str, Authority] = {"cldr-45": CLDR}


def latest() -> Authority:
    """Return the (single) bundled CLDR edition."""
    return CLDR


def edition(edition_id: str) -> Authority:
    """Return a specific CLDR edition by id."""
    if edition_id != "cldr-45":
        raise UnknownAuthorityEdition(f"CLDR has no edition {edition_id!r}; available: ['cldr-45']")
    return CLDR


__all__ = ["CLDR", "edition", "latest"]
