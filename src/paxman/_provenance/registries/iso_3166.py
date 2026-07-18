"""ISO 3166-1 registry authority (kind="registry", multi-edition capable).

ISO 3166 assigns country codes; new editions rename or add entries. Paxman
pins the edition it *currently bundles* so replay can reproduce an artifact
against the edition that produced it (Concern 3).

Pre-release rule: Paxman recognizes exactly the latest edition it bundles.
This build bundles **ISO 3166-1:2024** only — it has no awareness of any
earlier edition (e.g. 2020), and pinning an unknown edition raises
`UnknownAuthorityEdition`. When a newer edition ships (say 2026), it is added
*alongside* 2024 as a new `Authority` constant + `_EDITIONS` entry; old 2024
artifacts keep replaying because 2024 stays bundled. No architecture change
is needed for that — the per-authority module, the edition `Selector`, and
the `Engine` binding already support multiple editions.

The bundled lookup table lives in `paxman._capabilities._iso3166` and is read
by the country/phone capabilities. `dataset` here carries an illustrative
sample of the edition's assigned values for provenance/inspection only.
"""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

#: ISO 3166-1:2024 — the single edition this Paxman build bundles in full.
ISO_3166_2024: Authority = Authority(
    name="ISO 3166-1",
    edition="2024",
    kind="registry",
    publisher="ISO",
    released_on="2024-01-01",
    lifecycle="active",
    supports_multiple_editions=True,
    dataset={"MY": "Malaysia", "US": "United States", "JP": "Japan"},
    checksum="iso3166-1:2024",
)

_EDITIONS: dict[str, Authority] = {
    "2024": ISO_3166_2024,
}

_LATEST = "2024"


def latest() -> Authority:
    """Return the active (only bundled) ISO 3166-1 edition."""
    return _EDITIONS[_LATEST]


def edition(edition_id: str) -> Authority:
    """Return a specific ISO 3166-1 edition by id (e.g. "2024").

    Raises `UnknownAuthorityEdition` for any edition Paxman does not bundle
    (it has no awareness of editions it has not shipped).
    """
    if edition_id not in _EDITIONS:
        raise UnknownAuthorityEdition(
            f"ISO 3166-1 has no edition {edition_id!r}; available: {sorted(_EDITIONS)!r}"
        )
    return _EDITIONS[edition_id]


#: Backwards-compatible single-name export (the active edition).
ISO_3166 = latest()

__all__ = ["ISO_3166", "ISO_3166_2024", "edition", "latest"]
