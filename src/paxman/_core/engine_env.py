"""The Engine — the execution-environment that binds authority editions.

An :class:`Engine` is an immutable mapping ``name -> Authority`` of the
*concrete, resolved* editions Paxman uses for one canonicalize call. It is the
Foundation layer (C) of the three-layer authority model:

- **Foundation (C):** ``Engine(authorities: Mapping[str, Authority])`` binds
  explicit concrete editions. This is what replay reconstructs — the artifact
  records exactly which editions produced it, so ``Engine.from_artifact``
  rebuilds them byte-for-byte (mandate Law 12, Concern 2).
- **Sugar (B):** ``Engine.with_authorities({name: "2024", ...})`` pins specific
  editions (a ``ComplianceProfile``), resolving each selector once. Only editions
  Paxman actually bundles are accepted; an unknown edition raises
  ``UnknownAuthorityEdition``.
- **Escape hatch (A):** a contract's ``authority_override`` can pin one
  authority for a single call (testing), layered on top of the engine.

``Engine.default()`` resolves every known authority to its active edition. The
public ``paxman.canonicalize`` uses ``Engine.default()`` so the zero-config
path is unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from paxman._core.artifact import ExecutionArtifact

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority
from paxman._provenance.registries import (
    cldr_edition,
    cldr_latest,
    iso3166_edition,
    iso3166_latest,
    iso4217_edition,
    iso4217_latest,
    itu_e164_edition,
    itu_e164_latest,
)
from paxman._provenance.selection import (
    Latest,
    NormalizedSelector,
    Selector,
    _normalize_selector,
)
from paxman._provenance.specs import _SPEC_RESOLVERS


class _Resolver(NamedTuple):
    """Resolution helpers + the active (default) edition for one authority."""

    latest: Callable[[], Authority]
    edition: Callable[[str], Authority]


#: name -> resolver for every authority the Engine can bind. Grammars come from
#: ``specs._SPEC_RESOLVERS``; registries from their per-module helpers.
_RESOLVERS: dict[str, _Resolver] = {
    **{name: _Resolver(r.latest, r.edition) for name, r in _SPEC_RESOLVERS.items()},
    "ISO 3166-1": _Resolver(iso3166_latest, iso3166_edition),
    "ISO 4217": _Resolver(iso4217_latest, iso4217_edition),
    "Unicode CLDR": _Resolver(cldr_latest, cldr_edition),
    "ITU-T E.164": _Resolver(itu_e164_latest, itu_e164_edition),
}

#: The default (active) edition of every bindable authority, resolved once.
_DEFAULT_AUTHORITIES: dict[str, Authority] = {name: r.latest() for name, r in _RESOLVERS.items()}

#: Older editions that are *retired* (no longer resolvable as "latest") but
#: may appear in historical artifacts. Replay of an artifact citing a retired
#: edition raises ``UnknownAuthorityEdition`` only when the edition id is not
#: among the known historical editions below.
_KNOWN_EDITIONS: dict[str, frozenset[str]] = {
    "ISO 3166-1": frozenset({"2024"}),
    "ISO 4217": frozenset({"iso4217:2015"}),
    "Unicode CLDR": frozenset({"cldr-45"}),
    "ITU-T E.164": frozenset({"ITU-T E.164"}),
}


class Engine:
    """An immutable binding of authority names to concrete editions.

    The map holds only concrete :class:`Authority` objects (never selectors).
    Construct via :meth:`default`, :meth:`with_authorities`, or
    :meth:`from_artifact`; the positional constructor binds explicit editions.
    """

    __slots__ = ("_authorities",)

    def __init__(self, authorities: Mapping[str, Authority]) -> None:
        # Copy to a tuple-backed dict so the binding is immutable in spirit and
        # the iteration order is stable (byte-stable replay hash).
        self._authorities: dict[str, Authority] = dict(authorities)

    @classmethod
    def default(cls) -> Engine:
        """Bind every known authority to its active (latest) edition."""
        return cls(dict(_DEFAULT_AUTHORITIES))

    @classmethod
    def with_authorities(cls, bindings: Mapping[str, Selector]) -> Engine:
        """Pin specific editions via a ``name -> Selector`` mapping.

        Each selector is resolved once: ``Latest`` -> the active edition,
        ``Edition(id)`` -> the concrete pinned edition. Unknown authority names
        or unknown edition ids raise :class:`UnknownAuthorityEdition`.
        """
        resolved: dict[str, Authority] = {}
        for name, selector in bindings.items():
            if name not in _RESOLVERS:
                raise UnknownAuthorityEdition(
                    f"cannot bind unknown authority {name!r}; known: {sorted(_RESOLVERS)!r}"
                )
            norm: NormalizedSelector = _normalize_selector(selector)
            if isinstance(norm, Latest):
                resolved[name] = _RESOLVERS[name].latest()
            else:
                resolved[name] = _RESOLVERS[name].edition(norm.edition_id)
        return cls(resolved)

    @classmethod
    def from_artifact(cls, authorities: tuple[Authority, ...]) -> Engine:
        """Rebuild an Engine from the editions recorded on an artifact.

        Replay reconstructs the exact production context: the recorded concrete
        editions are reused verbatim, so replay is byte-for-byte deterministic
        (mandate Law 12) even if a newer edition has since shipped. Recorded
        editions are merged over :meth:`default` so every bindable authority is
        always concretely bound — an artifact that fired only grammar rules (and
        thus recorded no registry authority) still resolves registry lookups
        against the active edition rather than silently falling back.
        """
        merged = dict(_DEFAULT_AUTHORITIES)
        merged.update({a.name: a for a in authorities})
        return cls(merged)

    def authority(self, name: str) -> Authority:
        """Return the concrete :class:`Authority` bound for ``name``.

        Capabilities read this for IoC (e.g. a registry's ``dataset``). Every
        bindable authority is always bound — :meth:`default` and
        :meth:`from_artifact` both seed the full roster — so a known name never
        silently falls back to a different edition. Only an unknown name raises.
        """
        bound = self._authorities.get(name)
        if bound is not None:
            return bound
        if name in _RESOLVERS:
            return _RESOLVERS[name].latest()
        raise UnknownAuthorityEdition(f"no authority bound for {name!r}")

    def override(self, name: str, selector: Selector) -> Engine:
        """Return a new Engine with ``name`` re-bound to ``selector``.

        Used by the per-contract ``authority_override`` escape hatch (testing).
        """
        norm: NormalizedSelector = _normalize_selector(selector)
        if name not in _RESOLVERS:
            raise UnknownAuthorityEdition(
                f"cannot override unknown authority {name!r}; known: {sorted(_RESOLVERS)!r}"
            )
        if isinstance(norm, Latest):
            resolved = _RESOLVERS[name].latest()
        else:
            resolved = _RESOLVERS[name].edition(norm.edition_id)
        new_map = dict(self._authorities)
        new_map[name] = resolved
        return Engine(new_map)

    def authorities(self) -> tuple[Authority, ...]:
        """The bound authorities, sorted by name for byte-stable serialization."""
        return tuple(sorted(self._authorities.values(), key=lambda a: a.name))

    def __repr__(self) -> str:
        return f"Engine({self.authorities()!r})"


def _verify_recorded_authorities(authorities: tuple[Authority, ...]) -> None:
    """Validate that recorded editions are still known (not fabricated).

    A recorded edition that is neither the active edition nor a known historical
    edition is rejected at replay time (mandate Law 12 — replay must not trust a
    stale or forged edition). This guards the artifact's integrity without
    forcing every historical edition to still be "latest".
    """
    for auth in authorities:
        known = _KNOWN_EDITIONS.get(auth.name)
        if known is None:
            # Authorities without a historical-edition roster (grammars, policy)
            # are validated structurally elsewhere; accept them.
            continue
        if auth.edition not in known:
            raise UnknownAuthorityEdition(
                f"artifact records retired/unknown edition {auth.edition!r} "
                f"for {auth.name!r}; known editions: {sorted(known)!r}"
            )


class ComplianceProfile:
    """Sugar over :meth:`Engine.with_authorities` for pinning editions.

    A compliance profile names the editions an organization has adopted;
    building an ``Engine`` from it pins exactly those editions for every
    canonicalize call, so artifacts are replay-deterministic against the
    adopted profile regardless of newer editions Paxman later bundles.
    """

    __slots__ = ("bindings",)

    def __init__(self, bindings: Mapping[str, Selector]) -> None:
        self.bindings = dict(bindings)

    def engine(self) -> Engine:
        """Build the pinned :class:`Engine` for this profile.

        Pins the named editions over :meth:`Engine.default` (the active
        roster), so every bindable authority remains concretely bound. This is
        the concrete form of the plan's ``ComplianceProfile.to_engine`` (the
        ``base`` merge parameter is always ``Engine.default`` here).
        """
        return Engine.with_authorities(self.bindings)


def canonicalize_with(
    input_data: object,
    contract: object,
    engine: Engine,
) -> ExecutionArtifact:
    """Canonicalize ``input_data`` against ``contract`` using a specific ``engine``.

    The Foundation entry point (C): binds explicit authority editions for one
    call. The zero-config ``paxman.canonicalize`` uses ``Engine.default()``.
    """
    from paxman._core.engine import canonicalize as _canonicalize

    return _canonicalize(input_data, contract, engine)
