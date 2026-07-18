"""The `Authority` value object — structured provenance (mandate Law 14).

Paxman v2 previously carried a free-form `provenance: str` on every
`Evidence` entry. That form could not answer the question the mandate
actually cares about: *which edition* of an externally-maintained
authority produced this canonical form? When RFC 5321 is revised or ISO
3166 releases a new edition, a free-form string cannot be compared for
staleness.

`Authority` is a frozen value object naming exactly one cited source and
the edition Paxman bundled. Every `Evidence` entry now carries an
`authority: Authority | None` instead of a `provenance` string.
"""

from __future__ import annotations

from typing import Literal

import attrs

from paxman._errors import PaxmanError

#: The four Law 14 provenance categories.
#:
#: - ``specification``: externally maintained documents/standards
#:   (RFC 5322, ISO 8601, RFC 4122, ...).
#: - ``data-set``: externally maintained data-sets (ISO 3166, ISO 4217,
#:   ITU-T E.164, CLDR, IANA TZDB).
#: - ``platform-behaviour``: documented platform behavior, distinct from
#:   Paxman policy (Law 14 source #2 — e.g. Google Help URLs). Carries
#:   `retrieved_at`.
#: - ``policy``: Paxman-defined; internally versioned to the paxman
#:   capability version that introduced the policy.
AuthorityKind = Literal["specification", "data-set", "platform-behaviour", "policy"]


@attrs.frozen
class Authority:
    """One cited source and the edition Paxman bundled (mandate Law 14).

    Frozen (mandate Law 13): an ``Authority`` is constant metadata, never
    a runtime lookup (mandate Law 1). Capabilities reference these by
    import from the central registry in ``paxman._provenance.registries``;
    they do not re-declare citation strings inline.

    Attributes:
        name: The authority identity, e.g. ``"RFC 5321"``,
            ``"ISO 3166-1"``, ``"Google Help"``, ``"paxman spec/email"``.
        version: The exact edition bundled, e.g. ``"§2.4"``,
            ``"iso3166-1:2020"``, ``"retrieved 2026-07-14"``. For Paxman
            policy authorities this is the introducing capability version.
        kind: One of the four :data:`AuthorityKind` categories.
        retrieved_at: Only for ``kind="platform-behaviour"`` — the date
            the documented platform behavior was captured.
    """

    name: str
    version: str
    kind: AuthorityKind
    retrieved_at: str | None = None
    # The bundled edition this authority represents — constant across every
    # `.section()` citation of the same authority. Used as the version-stamp
    # value so replay can detect a *stale edition* regardless of which
    # section a rule cited. Defaults to `version` for base authorities;
    # `.section()` preserves it.
    edition: str = ""

    def __attrs_post_init__(self) -> None:
        # When an authority is declared without an explicit `edition`, the
        # `version` is the edition (base authorities describe their own
        # edition). Sectioned derivations set `version` to the section while
        # `edition` is preserved via `attrs.evolve`.
        if not self.edition:
            object.__setattr__(self, "edition", self.version)
        # `retrieved_at` is meaningful only for documented platform behavior;
        # a spec / data-set / policy authority must not carry a retrieval
        # date, and a platform-behaviour authority must record when the
        # behavior was captured (mandate Law 14 — the citation is verifiable).
        if self.kind == "platform-behaviour" and self.retrieved_at is None:
            raise PaxmanError(f"platform-behaviour authority {self.name!r} requires retrieved_at")
        if self.kind != "platform-behaviour" and self.retrieved_at is not None:
            raise PaxmanError(f"{self.kind} authority {self.name!r} must not carry retrieved_at")

    def section(self, section: str) -> Authority:
        """Return a derived ``Authority`` citing a specific section.

        The `name`, `kind`, and `edition` are preserved; `version` becomes
        the given section string (e.g. ``"§2.4"``). Used when a rule cites
        one authority at a particular location. The edition identity (the
        `edition`, keyed by `name`) is unchanged, so the artifact's version
        map still detects a stale edition regardless of section.
        """
        return attrs.evolve(self, version=section)

    def retrieved(self, retrieved_at: str) -> Authority:
        """Return a derived ``Authority`` with a captured ``retrieved_at``.

        Only meaningful for ``kind="platform-behaviour"``.
        """
        if self.kind != "platform-behaviour":
            raise PaxmanError(
                f"retrieved() is only valid for platform-behaviour authorities, not {self.kind!r}"
            )
        return attrs.evolve(self, retrieved_at=retrieved_at)
