"""The generic contract interface owned by the core.

Mandate Law 5: the contract declares *what* the canonical form is. This
Protocol is structural only — it names no domain. Concrete contract
value-objects (CanonicalEmailContract, etc.) satisfy it structurally.
The public *union* `Contract` lives in `paxman/__init__.py`.
"""

from __future__ import annotations

from typing import Any, Protocol


class Contract(Protocol):
    """Structural shape every contract value-object satisfies.

    All members are read-only properties: the concrete ``Canonical*Contract``
    types are ``@attrs.frozen``, and mypy's attrs plugin types frozen fields
    as read-only. A Protocol with settable variables would not match.
    """

    @property
    def kind(self) -> str:
        raise NotImplementedError

    @property
    def version_field(self) -> int:
        raise NotImplementedError

    @property
    def authority_override(self) -> Any | None:
        raise NotImplementedError

    def as_dict(self) -> dict[str, Any]:
        raise NotImplementedError
