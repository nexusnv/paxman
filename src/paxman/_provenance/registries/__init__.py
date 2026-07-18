"""Central registry of cited authorities — the single source of truth.

Every externally-maintained standard or data-set Paxman cites is declared
**once** in its dedicated package under ``paxman._provenance`` (``specs/`` for
grammars, ``registries/`` for data-sets, ``behaviour/`` for platform behavior,
``policy/`` for Paxman's own resolution rules). This package re-exports all of
them under their historical flat names so existing imports
(``from paxman._provenance import registries as R``) keep working, and exposes
the current-edition maps used by the replay staleness check.

Updating a bundled edition (e.g. adding ISO 3166-1:2026 alongside 2024) is one edit in one place,
propagating to every citing capability (mandate Law 14, Principle 4). The
registry holds **citation metadata** (which authority exists, which edition),
not domain knowledge (how to parse email) — capabilities keep their grammars,
tables, and rule logic.

The frozen edition strings are constants, never runtime lookups (mandate
Law 1). ``Authority`` is frozen (mandate Law 13).
"""

from __future__ import annotations

from paxman._provenance.behaviour import GOOGLE_HELP
from paxman._provenance.policy import (
    MANDATE,
    PAXMAN_SPEC_BOOLEAN,
    PAXMAN_SPEC_COUNTRY,
    PAXMAN_SPEC_DATE,
    PAXMAN_SPEC_EMAIL,
    PAXMAN_SPEC_GEOLOCATION,
    PAXMAN_SPEC_IP,
    PAXMAN_SPEC_MONEY,
    PAXMAN_SPEC_PHONE,
    PAXMAN_SPEC_URL,
    PAXMAN_VERSION,
)
from paxman._provenance.registries.cldr import (
    CLDR,
)
from paxman._provenance.registries.cldr import (
    edition as cldr_edition,
)
from paxman._provenance.registries.cldr import (
    latest as cldr_latest,
)
from paxman._provenance.registries.iso_3166 import (
    ISO_3166,
    ISO_3166_2024,
)
from paxman._provenance.registries.iso_3166 import (
    edition as iso3166_edition,
)
from paxman._provenance.registries.iso_3166 import (
    latest as iso3166_latest,
)
from paxman._provenance.registries.iso_4217 import (
    ISO_4217,
)
from paxman._provenance.registries.iso_4217 import (
    edition as iso4217_edition,
)
from paxman._provenance.registries.iso_4217 import (
    latest as iso4217_latest,
)
from paxman._provenance.registries.itu_e164 import (
    ITU_E164,
)
from paxman._provenance.registries.itu_e164 import (
    edition as itu_e164_edition,
)
from paxman._provenance.registries.itu_e164 import (
    latest as itu_e164_latest,
)
from paxman._provenance.specs import (
    IEEE_1003_1,
    ISO_8601,
    RFC_1035,
    RFC_2822,
    RFC_3339,
    RFC_3966,
    RFC_3986,
    RFC_4007,
    RFC_4122,
    RFC_4291,
    RFC_5321,
    RFC_5322,
    RFC_5952,
    WHATWG_URL,
)

#: Every authority re-exported by this package, in citation-declaration order.
#: Used to derive the current-edition maps without re-listing each name.
_ALL_AUTHORITIES: tuple = (
    RFC_5321,
    RFC_5322,
    RFC_3966,
    RFC_4122,
    RFC_4291,
    RFC_5952,
    RFC_4007,
    RFC_3986,
    RFC_3339,
    RFC_2822,
    RFC_1035,
    ISO_8601,
    WHATWG_URL,
    IEEE_1003_1,
    ISO_3166,
    ISO_3166_2024,
    ISO_4217,
    CLDR,
    ITU_E164,
    GOOGLE_HELP,
    PAXMAN_SPEC_EMAIL,
    PAXMAN_SPEC_DATE,
    PAXMAN_SPEC_MONEY,
    PAXMAN_SPEC_PHONE,
    PAXMAN_SPEC_URL,
    PAXMAN_SPEC_IP,
    PAXMAN_SPEC_GEOLOCATION,
    PAXMAN_SPEC_BOOLEAN,
    PAXMAN_SPEC_COUNTRY,
    MANDATE,
)


def current_spec_versions() -> dict[str, str]:
    """The editions of every grammar authority Paxman currently bundles.

    Used at replay time to detect a stale authority. Only the authorities an
    artifact's own evidence cited are compared (mandate Law 12 — the
    artifact's production context, not the global registry).
    """
    return {a.name: a.edition for a in _ALL_AUTHORITIES if a.kind == "grammar"}


def current_registry_versions() -> dict[str, str]:
    """The editions of every registry authority Paxman currently bundles.

    See :func:`current_spec_versions` for the Law 12 rationale.
    """
    return {a.name: a.edition for a in _ALL_AUTHORITIES if a.kind == "registry"}


__all__ = [
    "CLDR",
    "GOOGLE_HELP",
    "IEEE_1003_1",
    "ISO_3166",
    "ISO_3166_2024",
    "ISO_4217",
    "ISO_8601",
    "ITU_E164",
    "MANDATE",
    "PAXMAN_SPEC_BOOLEAN",
    "PAXMAN_SPEC_COUNTRY",
    "PAXMAN_SPEC_DATE",
    "PAXMAN_SPEC_EMAIL",
    "PAXMAN_SPEC_GEOLOCATION",
    "PAXMAN_SPEC_IP",
    "PAXMAN_SPEC_MONEY",
    "PAXMAN_SPEC_PHONE",
    "PAXMAN_SPEC_URL",
    "PAXMAN_VERSION",
    "RFC_1035",
    "RFC_2822",
    "RFC_3339",
    "RFC_3966",
    "RFC_3986",
    "RFC_4007",
    "RFC_4122",
    "RFC_4291",
    "RFC_5321",
    "RFC_5322",
    "RFC_5952",
    "WHATWG_URL",
    "cldr_edition",
    "cldr_latest",
    "iso3166_edition",
    "iso3166_latest",
    "iso4217_edition",
    "iso4217_latest",
    "itu_e164_edition",
    "itu_e164_latest",
]
