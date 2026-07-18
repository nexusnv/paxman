"""ITU-T E.164 registry authority (kind="registry", single bundled edition).

ITU-T E.164 defines the global Switched Telephone Network number structure;
Paxman cites the standard itself (the global shape rule), not a bundled
calling-code dataset. Single edition.
"""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

ITU_E164: Authority = Authority(
    name="ITU-T E.164",
    edition="ITU-T E.164",
    kind="registry",
    publisher="ITU-T",
    lifecycle="active",
    supports_multiple_editions=True,
    dataset=None,
    checksum="itu-e164",
)

_EDITIONS: dict[str, Authority] = {"ITU-T E.164": ITU_E164}


def latest() -> Authority:
    """Return the (single) ITU-T E.164 edition."""
    return ITU_E164


def edition(edition_id: str) -> Authority:
    """Return a specific ITU-T E.164 edition by id."""
    if edition_id != "ITU-T E.164":
        raise UnknownAuthorityEdition(
            f"ITU-T E.164 has no edition {edition_id!r}; available: ['ITU-T E.164']"
        )
    return ITU_E164


__all__ = ["ITU_E164", "edition", "latest"]
