"""Adapter registry — lookup of :class:`ContractAdapter` by ``format_id``.

Adapters register themselves at import time via :func:`register`. The
public :func:`get_adapter` and :func:`all_adapters` are the lookup API.
The :func:`adapt` convenience function dispatches an external contract to
the right adapter.

The registry is **process-local**. There is no global state shared across
processes; this is intentional. The public ``register_adapter`` API (per
``EXTENDING.md`` §1.3 step 4) lands in Sprint 6 with the rest of ``api/``.

Boundary
--------

This module is a leaf within ``contract/``. It imports from
:mod:`paxman.contract.adapters.base` (the Protocol) and from
:mod:`paxman.errors`. It does not import from any other subsystem.
"""

from __future__ import annotations

import types

from paxman.contract.adapters.base import ContractAdapter
from paxman.contract.canonical import CanonicalContract
from paxman.errors import InvalidContractError

__all__ = [
    "adapt",
    "all_adapters",
    "get_adapter",
    "register",
    "unregister",
]


#: The internal adapter table. Keyed by ``format_id``; values are
#: :class:`ContractAdapter` instances. Insertion-ordered (Python dict
#: guarantees this since 3.7) for deterministic iteration.
_adapters: dict[str, ContractAdapter] = {}


def register(adapter: ContractAdapter, *, replace: bool = False) -> None:
    """Register a :class:`ContractAdapter` in the registry.

    Args:
        adapter: The :class:`ContractAdapter` to register. Its
            ``format_id`` is the key.
        replace: If ``True``, replace any existing adapter with the same
            ``format_id``. Defaults to ``False`` (idempotent registration
            is a no-op when the same instance is already registered, but
            raises on conflict).

    Raises:
        InvalidContractError: If *adapter* is not a valid
            :class:`ContractAdapter` (i.e., its ``format_id`` is not a
            non-empty string), or if an adapter with the same
            ``format_id`` is already registered and ``replace=False``.
        TypeError: If *adapter* is missing ``format_id`` / ``adapt`` /
            ``export`` attributes.

    Examples:
        >>> class MyAdapter:
        ...     @property
        ...     def format_id(self) -> str: return "my_format"
        ...     def adapt(self, external): return external
        ...     def export(self, canonical): return canonical
        >>> register(MyAdapter())  # doctest: +SKIP
    """
    if (
        not hasattr(adapter, "format_id")
        or not hasattr(adapter, "adapt")
        or not hasattr(adapter, "export")
    ):
        raise TypeError(
            f"adapter must implement format_id, adapt, and export; got {type(adapter).__name__}"
        )
    fmt = adapter.format_id
    if not isinstance(fmt, str) or not fmt:
        raise InvalidContractError(
            f"adapter format_id must be a non-empty string, got {fmt!r}",
            error_code="INVALID_ADAPTER",
            context={"adapter_type": type(adapter).__name__, "format_id": repr(fmt)},
        )
    # Oracle review F14: SPI requires lowercase format_id (per
    # ``ContractAdapter.format_id`` docstring). Reject mixed/upper case.
    if fmt != fmt.lower():
        raise InvalidContractError(
            f"adapter format_id must be lowercase, got {fmt!r}",
            error_code="INVALID_ADAPTER",
            context={"adapter_type": type(adapter).__name__, "format_id": repr(fmt)},
        )
    existing = _adapters.get(fmt)
    if existing is not None and existing is not adapter and not replace:
        raise InvalidContractError(
            f"adapter for format {fmt!r} is already registered",
            error_code="ADAPTER_ALREADY_REGISTERED",
            context={
                "format_id": fmt,
                "existing_type": type(existing).__name__,
                "new_type": type(adapter).__name__,
            },
        )
    _adapters[fmt] = adapter


def unregister(format_id: str) -> bool:
    """Remove a registered adapter.

    Args:
        format_id: The format identifier to unregister.

    Returns:
        ``True`` if an adapter was removed; ``False`` if no adapter was
        registered for *format_id*.

    Examples:
        >>> unregister("nonexistent")
        False
    """
    return _adapters.pop(format_id, None) is not None


def get_adapter(format_id: str) -> ContractAdapter:
    """Return the adapter registered for *format_id*.

    Args:
        format_id: The format identifier (e.g., ``"pydantic"``,
            ``"json_schema:draft-2020-12"``, ``"dict_dsl"``).

    Returns:
        The registered :class:`ContractAdapter`.

    Raises:
        InvalidContractError: If no adapter is registered for
            *format_id*. The error code is ``"ADAPTER_NOT_FOUND"``.

    Examples:
        >>> get_adapter("nonexistent")  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        paxman.errors.InvalidContractError: ...
    """
    try:
        return _adapters[format_id]
    except KeyError as e:
        raise InvalidContractError(
            f"no adapter registered for format {format_id!r}",
            error_code="ADAPTER_NOT_FOUND",
            context={"format_id": format_id},
        ) from e


def all_adapters() -> types.MappingProxyType[str, ContractAdapter]:
    """Return a read-only snapshot of all registered adapters.

    Returns:
        A read-only mapping of ``format_id`` → :class:`ContractAdapter`,
        in registration order.

    Examples:
        >>> sorted(all_adapters().keys())  # doctest: +SKIP
        ['dict_dsl', 'json_schema:draft-2020-12', 'pydantic']
    """
    return types.MappingProxyType(_adapters)


def adapt(external: object, format_id: str | None = None) -> CanonicalContract:
    """Adapt *external* to a :class:`CanonicalContract` via the registry.

    Convenience function: looks up the adapter by *format_id* and calls
    its ``adapt()`` method. No type-based inference is performed in V1
    (the type-inference path is reserved for the future ``register_adapter``
    public API in Sprint 6).

    Args:
        external: The external contract object.
        format_id: Explicit :class:`ContractAdapter` ``format_id``.

    Returns:
        The :class:`CanonicalContract` produced by the adapter.

    Raises:
        InvalidContractError: If *format_id* is ``None``, no adapter is
            found for *format_id*, or the adapter fails to translate.
    """
    if format_id is None:
        raise InvalidContractError(
            "format_id is required; pass it explicitly",
            error_code="ADAPTER_NOT_FOUND",
            context={"external_type": type(external).__name__},
        )
    adapter = get_adapter(format_id)
    return adapter.adapt(external)
