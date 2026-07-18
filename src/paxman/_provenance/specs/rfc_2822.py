"""RFC 2822 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_2822 = Authority(
    name="RFC 2822",
    kind="grammar",
    edition="RFC 2822 (Internet Message Format)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 2822 (Internet Message Format)": RFC_2822}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_2822


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 2822 (Internet Message Format)":
        raise UnknownAuthorityEdition(
            f"RFC 2822 is a grammar authority with a single edition "
            f"'RFC 2822 (Internet Message Format)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_2822


__all__ = ["RFC_2822", "edition", "latest"]
