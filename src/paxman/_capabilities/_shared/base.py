"""Shared capability base (Finding D, narrow).

Every capability subclasses ``CapabilityBase`` so it inherits the uniform
post-canonicalization ``validate`` hook and a single import surface for the
``Capability`` Protocol. The orchestrator dispatches validation through the
resolved capability (``validation.validate`` -> ``capability.validate``), so
``_core`` never imports concrete contracts (goal 4: dependencies point
inward).

The ``canonicalize`` pipeline differs per domain (date does recognition
inside its resolver; money folds everything into ``canonicalize``; email
needs strict-mode pre-checks). Rather than force a single rigid skeleton
that would alter behavior (the over-abstraction trap in Finding D), each
domain implements ``can_handle`` / ``canonicalize`` directly and reuses the
shared ``_shared`` scaffolds (grammar, evidence, contract field). The
``engine`` parameter stays on the Protocol (uniformity is the scaling
mechanism — Finding C) and is threaded through, ignored by domains that do
not cite authorities.

Law 4: ``validate`` is a post-canonicalization policy check, never
interpretation. Default passes; the engine dispatches to it.
"""

from __future__ import annotations

from typing import Any

from paxman._core.classification import ValidationResult
from paxman._core.contracts import Contract


class CapabilityBase:
    """Base for capabilities: uniform ``validate`` hook + Protocol surface.

    Subclasses set ``name`` and implement ``can_handle`` / ``canonicalize``
    (and optionally ``validate`` for contract-specific strictness policy).
    """

    name: str

    def can_handle(self, contract: Contract, value: Any) -> bool:  # pragma: no cover
        """Return True if this capability canonicalizes the (contract, value) pair."""
        raise NotImplementedError

    def canonicalize(
        self, value: Any, contract: Contract, engine: Any | None = None
    ) -> object:  # pragma: no cover
        """Canonicalize ``value`` against ``contract`` (domain-specific)."""
        raise NotImplementedError

    def validate(self, value: str, contract: Contract) -> ValidationResult:
        """Post-canonicalization policy check (Law 4). Default: passes.

        Domains with strictness policy (e.g. email) override this. The
        orchestrator calls it after canonicalize; it must not interpret or
        guess (Law 4).
        """
        return ValidationResult(is_valid=True)
