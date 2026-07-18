"""ISO 4217 registry authority (kind="registry", single bundled edition).

Currency codes are assigned by ISO; Paxman pins the edition it bundles. The
currency TABLE_VERSION lives in the money capability's contract module and is
read there; this authority records the edition for provenance + replay.
"""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

ISO_4217: Authority = Authority(
    name="ISO 4217",
    edition="iso4217:2015",
    kind="registry",
    publisher="ISO",
    released_on="2015-01-01",
    lifecycle="active",
    supports_multiple_editions=True,
    dataset=None,
    checksum="iso4217:2015",
)

_EDITIONS: dict[str, Authority] = {"iso4217:2015": ISO_4217}


def latest() -> Authority:
    """Return the (single) bundled ISO 4217 edition."""
    return ISO_4217


def edition(edition_id: str) -> Authority:
    """Return a specific ISO 4217 edition by id."""
    if edition_id != "iso4217:2015":
        raise UnknownAuthorityEdition(
            f"ISO 4217 has no edition {edition_id!r}; available: ['iso4217:2015']"
        )
    return ISO_4217


__all__ = ["ISO_4217", "edition", "latest"]
