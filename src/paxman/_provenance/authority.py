"""The `Authority` value object — structured, multi-edition provenance (Law 14).

Paxman v2 previously carried a free-form `provenance: str` on every `Evidence`
entry. That form could not answer the question the mandate actually cares
about: *which edition* of an externally-maintained authority produced this
canonical form? When RFC 5321 is revised or ISO 3166 releases a new edition, a
free-form string cannot be compared for staleness, and replay cannot reproduce
the artifact against the edition that originally produced it.

`Authority` is a frozen value object naming exactly one cited source, its
**concrete resolved edition**, and (for registries) the bundled dataset. Every
`Evidence` entry carries an `authority: Authority | None` instead of a string.

Authority kinds (the abstraction from the design discussion, replacing the old
specification/data-set split):

- ``grammar`` — a specification that defines a grammar/algorithm (RFC 5322,
  ISO 8601, RFC 4122, RFC 4291, …). Compiled into the capability's algorithm;
  `supports_multiple_editions=False` (selecting an edition is rejected).
- ``registry`` — an externally-maintained data-set of assigned values (ISO
  3166, ISO 4217, CLDR, ITU-T E.164, IANA TZDB). `supports_multiple_editions=True`;
  the engine can bind a specific edition.
- ``normative_standard`` — an editioned body of requirements (ISO 9001).
  Multiple editions are concurrently valid during transition; `True`.
- ``taxonomy`` — an annually-released classification (UNSPSC). `True`.
- ``platform-behaviour`` — documented platform behavior (Google Help), distinct
  from Paxman policy. Carries `retrieved_at`. `False`.
- ``policy`` — Paxman-defined; internally versioned to the capability version.
  `False`.

The engine resolves symbolic selectors (``Latest``, ``Edition(id)``) to a
concrete `Authority` *before* canonicalization; the artifact records only
concrete editions, never a symbolic selector (see `selection.py`).
"""

from __future__ import annotations

from typing import Any, Literal

import attrs

# NOTE: `PaxmanError` is imported lazily inside `__attrs_post_init__` rather than
# at module top-level. Importing `paxman._errors` triggers the `paxman` package
# __init__, which imports the capabilities, which import `paxman._provenance`
# (this package) — a circular import that would leave `authority` partially
# initialized. Laziness breaks that cycle.

#: The authority kinds. See the module docstring for the semantics of each.
AuthorityKind = Literal[
    "grammar",
    "registry",
    "normative_standard",
    "taxonomy",
    "platform-behaviour",
    "policy",
]

#: Lifecycle status of a concrete edition.
AuthorityLifecycle = Literal["active", "superseded", "retired"]


@attrs.frozen
class Authority:
    """One cited source and the concrete edition Paxman bundled (mandate Law 14).

    Frozen (mandate Law 13): an ``Authority`` is constant metadata, never a
    runtime lookup (mandate Law 1). Capabilities reference these by import from
    the central registry modules (``paxman._provenance.specs``,
    ``paxman._provenance.registries``, …); they do not re-declare citation
    strings inline.

    Attributes:
        name: The authority identity, e.g. ``"RFC 5321"``, ``"ISO 3166-1"``,
            ``"Google Help"``, ``"paxman spec/email"``.
        kind: One of the six :data:`AuthorityKind` categories.
        edition: The **concrete resolved edition id** this authority represents,
            e.g. ``"2024"`` for ISO 3166, ``"RFC 5321 (SMTP)"`` for a grammar.
            NEVER a symbolic selector like ``"latest"``. Used as the
            version-stamp value so replay can reload the exact edition.
        version: The descriptive version/section string. For a base authority
            this mirrors ``edition``; ``section()`` overrides it with the cited
            section (e.g. ``"§2.4"``) while preserving ``edition``.
        publisher: The issuing body, e.g. ``"ISO"``, ``"IANA"``, ``"Unicode"``.
        released_on: ISO date the edition was published (optional).
        lifecycle: ``active`` / ``superseded`` / ``retired``.
        checksum: sha256 (or similar) of the bundled dataset for this edition;
            ``None`` for grammar/policy authorities that carry no dataset.
        retrieved_at: Only for ``kind="platform-behaviour"`` — the date the
            documented platform behavior was captured.
        supports_multiple_editions: Whether the engine may bind a non-default
            edition for this authority. ``False`` for grammar/policy/
            platform-behaviour (compiled into the algorithm); ``True`` for
            registry/normative_standard/taxonomy.
        dataset: The frozen lookup table bundled for THIS edition (registries
            only). Capabilities read it via the engine; they do not embed it.
    """

    name: str
    edition: str
    kind: AuthorityKind = "grammar"
    version: str = ""
    publisher: str | None = None
    released_on: str | None = None
    lifecycle: AuthorityLifecycle = "active"
    checksum: str | None = None
    retrieved_at: str | None = None
    supports_multiple_editions: bool = False
    dataset: Any = None

    def __attrs_post_init__(self) -> None:
        from paxman._errors import PaxmanError

        # When an authority is declared without an explicit `version`, the
        # `edition` is the descriptive version (base authorities describe their
        # own edition). Sectioned derivations set `version` to the section while
        # `edition` is preserved (the version-stamp key) via `attrs.evolve`.
        if not self.version:
            object.__setattr__(self, "version", self.edition)
        # `retrieved_at` is meaningful only for documented platform behavior;
        # a spec / data-set / policy authority must not carry a retrieval date,
        # and a platform-behaviour authority must record when the behavior was
        # captured (mandate Law 14 — the citation is verifiable).
        if self.kind == "platform-behaviour" and self.retrieved_at is None:
            raise PaxmanError(f"platform-behaviour authority {self.name!r} requires retrieved_at")
        if self.kind != "platform-behaviour" and self.retrieved_at is not None:
            raise PaxmanError(f"{self.kind} authority {self.name!r} must not carry retrieved_at")

    def section(self, section: str) -> Authority:
        """Return a derived ``Authority`` citing a specific section.

        The `name`, `kind`, `edition`, and all edition metadata are preserved;
        `version` becomes the given section string (e.g. ``"§2.4"``). Used when a
        rule cites one authority at a particular location. The edition identity
        (the `edition`, keyed by `name`) is unchanged, so the artifact's version
        map still detects a stale edition regardless of section.
        """
        return attrs.evolve(self, version=section)

    def retrieved(self, retrieved_at: str) -> Authority:
        """Return a derived ``Authority`` with a captured ``retrieved_at``.

        Only meaningful for ``kind="platform-behaviour"``.
        """
        if self.kind != "platform-behaviour":
            from paxman._errors import PaxmanError

            raise PaxmanError(
                f"retrieved() is only valid for platform-behaviour authorities, not {self.kind!r}"
            )
        return attrs.evolve(self, retrieved_at=retrieved_at)

    @property
    def provenance(self) -> str:
        """Deprecated alias for the structured ``authority`` citation.

        ``Authority`` no longer carries a free-form ``provenance`` string (it
        carries structured fields). Accessing this property raises an
        informative error rather than returning a silently-wrong value.
        """
        raise AttributeError(
            "Authority no longer carries a 'provenance' string; it carries "
            "structured edition/version/kind fields (mandate Law 14)."
        )
