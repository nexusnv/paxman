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

    def as_dict(self) -> dict[str, Any]: ...
