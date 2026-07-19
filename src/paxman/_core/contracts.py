"""The generic contract interface owned by the core.

Mandate Law 5: the contract declares *what* the canonical form is. This
Protocol is structural only — it names no domain. Concrete contract
value-objects (CanonicalEmailContract, etc.) satisfy it structurally.
The public *union* `Contract` lives in `paxman/__init__.py`.
"""

from __future__ import annotations

from typing import Any, Protocol


class Contract(Protocol):
    """Structural shape every contract value-object satisfies."""

    kind: str
    version_field: int
    # Concern-3 escape hatch: a contract may pin a specific authority edition
    # for a single canonicalize call (same semantics as the per-domain
    # authority_override_field()). None means "no pin; use the engine binding".
    authority_override: Any | None

    def as_dict(self) -> dict[str, Any]: ...
