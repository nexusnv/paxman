"""Authority edition selection (mandate Law 14 — verifiable editions).

A `Selector` names *which* edition of an authority an :class:`~paxman._core.engine_env.Engine`
should bind. ``Latest`` is the resolution strategy (never stored); ``Edition`` pins a
concrete edition id. The Engine resolves a selector once, to a concrete
:class:`~paxman._provenance.authority.Authority`, and that concrete object is what gets
recorded on the artifact and replayed.

This module is selection-only: it knows nothing about the Engine. Resolution against a
concrete registry happens in :mod:`paxman._core.engine_env`.
"""

from __future__ import annotations

from typing import Literal

import attrs

from paxman._provenance.authority import Authority


@attrs.frozen
class Latest:
    """Select the active edition of an authority.

    ``Latest`` is a *resolution strategy*, not an edition. It is resolved once
    (to a concrete ``Authority``) and never stored; the artifact records the
    resolved concrete edition, so replay is deterministic regardless of whether
    a newer edition has since been published.
    """


@attrs.frozen
class Edition:
    """Pin a concrete edition id of an authority (e.g. ``"2024"`` for ISO 3166-1).

    Used by :class:`~paxman._core.engine_env.Engine.with_authorities` to bind an
    organization's pinned edition for replay-deterministic canonicalization.
    """

    edition_id: str


#: A selection for one authority: either "use the latest", pin a concrete
#: :class:`Edition`, pass an already-resolved :class:`~paxman._provenance.authority.Authority`
#: verbatim, or ``None`` to leave the authority at its default (active) edition.
Selector = Authority | Literal["latest"] | Latest | Edition | None

#: A normalized selector after coercing the ``"latest"`` string / ``None`` to
#: :class:`Latest`, and unwrapping an :class:`Authority` to its concrete edition.
NormalizedSelector = Latest | Edition

#: The canonical form of a selector request, keyed by authority name.
AuthorityBindings = dict[str, Selector]


def _normalize_selector(selector: Selector) -> NormalizedSelector:
    """Coerce a user-facing selector to ``Latest`` / ``Edition``.

    The string ``"latest"`` becomes :class:`Latest`; ``None`` also means the
    active edition; any other bare string is treated as a concrete edition id
    (wrapped in :class:`Edition`); an :class:`Authority` is unwrapped to its
    concrete edition; an existing ``Latest`` / ``Edition`` is passed through.
    """
    if selector is None or selector == "latest":
        return Latest()
    if isinstance(selector, str):
        return Edition(selector)
    if isinstance(selector, Authority):
        return Edition(selector.edition)
    return selector
