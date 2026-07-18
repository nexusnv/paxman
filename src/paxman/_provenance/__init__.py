"""Structured provenance for Paxman v2 (mandate Law 14).

Public surface of the ``_provenance`` package:

- :class:`Authority` — a frozen value object naming one cited source and
  the edition Paxman bundled.
- :class:`Evidence` — one evidence entry carrying an
  ``authority: Authority | None``.
- :func:`_evidence` / :func:`_evidence_from_args` — shared helpers that
  build ``Evidence`` from a capability manifest or an explicit authority.
"""

from __future__ import annotations

from paxman._provenance.authority import Authority, AuthorityKind
from paxman._provenance.evidence import (
    Evidence,
    RuleAuthorities,
    _evidence,
    _evidence_from_args,
)

__all__ = [
    "Authority",
    "AuthorityKind",
    "Evidence",
    "RuleAuthorities",
    "_evidence",
    "_evidence_from_args",
]
