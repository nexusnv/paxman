"""ISO 8601 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
ISO_8601 = Authority(
    name="ISO 8601",
    kind="grammar",
    edition="iso8601:2004",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"iso8601:2004": ISO_8601}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return ISO_8601


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "iso8601:2004":
        raise UnknownAuthorityEdition(
            f"ISO 8601 is a grammar authority with a single edition "
            f"'iso8601:2004'; requested edition {edition_id!r} is not valid."
        )
    return ISO_8601


__all__ = ["ISO_8601", "edition", "latest"]
