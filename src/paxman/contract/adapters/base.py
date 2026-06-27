"""``ContractAdapter`` Protocol — the SPI for translating external contracts.

This is the **public SPI** for adding new contract adapters (per
``EXTENDING.md`` §1.2 and ``PACKAGE_STRUCTURE.md`` §3.3). The Protocol is
re-exported from :mod:`paxman.protocols` (where the canonical declaration
lives, with ``object`` placeholders). The version here is the **concrete
typed** version, used by adapter implementations and the registry.

Why two declarations?
---------------------

- :mod:`paxman.protocols` is a leaf module that defines the SPIs with
  ``object`` placeholders so the type system doesn't depend on the
  concrete :class:`CanonicalContract` (which lives in ``contract/``).
- This module redeclares the Protocol with concrete types so adapter
  authors get proper type-checking.

Both declarations are structurally compatible (PEP 544) — a class
satisfying the concrete Protocol also satisfies the abstract one.

Boundary
--------

This module imports from :mod:`paxman.contract.canonical` and
:mod:`paxman.errors`. It is the **only** module in ``contract/`` that the
:mod:`paxman.contract.registry` depends on, and is the import target for
every concrete adapter.
"""

from __future__ import annotations

import typing

from paxman.contract.canonical import CanonicalContract

__all__ = ["ContractAdapter"]


class ContractAdapter(typing.Protocol):
    """SPI: translate an external contract format to/from ``CanonicalContract``.

    Adapters are pure: the same input always produces the same
    :class:`CanonicalContract`. No I/O, no clock reads, no randomness.

    Implementations should be ``@attrs.frozen(slots=True)`` for
    immutability and type stability.

    See :mod:`paxman.protocols` for the abstract re-declaration; the
public ``paxman.api.protocols.ContractAdapter`` re-exports
this Protocol.
    """

    @property
    def format_id(self) -> str:
        """Stable identifier for the external format.

        Examples: ``'pydantic'``, ``'json_schema:draft-2020-12'``,
        ``'dict_dsl'``.

        Returns:
            A non-empty lowercase identifier string.
        """
        ...

    def adapt(self, external: object) -> CanonicalContract:
        """Translate an external contract into a :class:`CanonicalContract`.

        Args:
            external: The external contract object (e.g., a Pydantic model
                class, a JSON Schema dict, a Dict DSL dict).

        Returns:
            A :class:`CanonicalContract` representing the same logical
            contract.

        Raises:
            paxman.errors.InvalidContractError: If *external* is malformed
                or cannot be translated.
        """
        ...

    def export(self, canonical: CanonicalContract) -> object:
        """Translate a :class:`CanonicalContract` back into the external format.

        Args:
            canonical: The :class:`CanonicalContract` to export.

        Returns:
            An object in the adapter's external format (e.g., a Pydantic
            model class, a JSON Schema dict).

        Raises:
            paxman.errors.InvalidContractError: If the canonical contract
                cannot be represented in the target format.
        """
        ...
