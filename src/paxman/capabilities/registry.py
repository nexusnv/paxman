"""Capability registry — versioned lookup of :class:`Capability` instances.

The :class:`CapabilityRegistry` is the **single entry point** the
planner uses to discover capabilities. It is keyed by
``(capability_id, version)`` so the same capability id may be
registered under multiple versions (e.g., ``text_extraction@1.0``
and ``text_extraction@1.1``).

Per ``PACKAGE_STRUCTURE.md`` §2, the registry is the only way to
obtain a capability — subsystems MUST NOT import
``paxman.capabilities.v1.*`` directly.

Public surface
--------------

- :func:`register` — register a :class:`Capability` (process-local).
- :func:`unregister` — remove by ``(id, version)``.
- :func:`get` — look up by ``(id, version)``; raise on miss.
- :func:`get_latest` — look up by id, return the latest version.
- :func:`all_capabilities` — read-only snapshot of all registered.
- :func:`reset` — clear the registry (test-only helper).

Process-local state
-------------------

The registry is **process-local**, matching the contract adapter
registry in :mod:`paxman.contract.registry`. There is no global state
shared across processes; this is intentional.
"""

from __future__ import annotations

import sys
import types

from paxman.capabilities.base import Capability
from paxman.capabilities.spec import CapabilitySpec
from paxman.errors import InvalidContractError

__all__ = [
    "all_capabilities",
    "get",
    "get_latest",
    "register",
    "reset",
    "unregister",
]


#: The internal capability table. Keyed by ``(id, version)``; values
#: are :class:`Capability` instances. Insertion-ordered (Python dict
#: guarantees this since 3.7) for deterministic iteration.
_capabilities: dict[tuple[str, str], Capability] = {}


def register(capability: Capability, *, replace: bool = False) -> None:
    """Register a :class:`Capability` in the registry.

    Args:
        capability: The capability to register. Must expose a
            :class:`CapabilitySpec` via its ``spec`` property whose
            ``id`` and ``version`` are used as the key.
        replace: If ``True``, replace any existing capability with
            the same ``(id, version)``. Defaults to ``False``
            (idempotent registration is a no-op when the same
            instance is already registered, but raises on conflict).

    Raises:
        InvalidContractError: If *capability* is malformed (no
            ``spec`` / ``invoke`` attributes, or the spec's ``id``
            / ``version`` are not non-empty strings), or if a
            different instance with the same ``(id, version)`` is
            already registered and ``replace=False``.
        TypeError: If *capability* is not a :class:`Capability`.
    """
    if not hasattr(capability, "spec") or not hasattr(capability, "invoke"):
        raise TypeError(
            f"capability must implement spec and invoke, got {type(capability).__name__}"
        )
    spec = capability.spec
    if not isinstance(spec, CapabilitySpec):
        raise TypeError(f"capability.spec must be a CapabilitySpec, got {type(spec).__name__}")
    key = (spec.id, spec.version)
    existing = _capabilities.get(key)
    if existing is not None and existing is not capability and not replace:
        raise InvalidContractError(
            f"capability for id={spec.id!r}, version={spec.version!r} is already registered",
            error_code="CAPABILITY_ALREADY_REGISTERED",
            context={
                "capability_id": spec.id,
                "capability_version": spec.version,
                "existing_type": type(existing).__name__,
                "new_type": type(capability).__name__,
            },
        )
    _capabilities[key] = capability


def unregister(capability_id: str, version: str) -> bool:
    """Remove a registered capability.

    Args:
        capability_id: The capability's id.
        version: The capability's version.

    Returns:
        ``True`` if a capability was removed; ``False`` if no
        capability was registered for the given ``(id, version)``.

    Examples:
        >>> unregister("nonexistent", "1.0")
        False
    """
    return _capabilities.pop((capability_id, version), None) is not None


def get(capability_id: str, version: str) -> Capability:
    """Return the capability registered for ``(id, version)``.

    Args:
        capability_id: The capability's id (e.g., ``"regex_extraction"``).
        version: The capability's version (e.g., ``"1.0"``).

    Returns:
        The registered :class:`Capability`.

    Raises:
        InvalidContractError: If no capability is registered for
            ``(id, version)``. The error code is
            ``"CAPABILITY_NOT_FOUND"``.

    Examples:
        >>> get("nonexistent", "1.0")
        Traceback (most recent last):
        ...
        paxman.errors.InvalidContractError: ...
    """
    try:
        return _capabilities[(capability_id, version)]
    except KeyError as e:
        raise InvalidContractError(
            f"no capability registered for id={capability_id!r}, version={version!r}",
            error_code="CAPABILITY_NOT_FOUND",
            context={"capability_id": capability_id, "capability_version": version},
        ) from e


def get_latest(capability_id: str) -> Capability:
    """Return the latest-version capability registered for *capability_id*.

    "Latest" is determined by :func:`_version_key`, which parses
    semver triples; the maximum wins. If no semver version is
    registered, the most recently registered version wins
    (fallback for non-semver versions like ``"1.0-rc"``).

    The tie-break is the **insertion index** (descending) so that,
    when multiple non-semver versions are registered, the most
    recently registered one is preferred. Without this secondary
    key, Python's stable sort would preserve insertion order, which
    is the opposite of "latest."

    Args:
        capability_id: The capability's id.

    Returns:
        The latest registered :class:`Capability` for the id.

    Raises:
        InvalidContractError: If no capability is registered for
            *capability_id* at all.
    """
    matches = [
        (i, version, cap)
        for i, ((cid, version), cap) in enumerate(_capabilities.items())
        if cid == capability_id
    ]
    if not matches:
        raise InvalidContractError(
            f"no capability registered for id={capability_id!r}",
            error_code="CAPABILITY_NOT_FOUND",
            context={"capability_id": capability_id},
        )
    # Sort by (semver key descending, insertion index descending). The
    # secondary key ensures that non-semver versions (all sharing
    # the same ``(-1,)`` semver key) prefer the most recently
    # registered one.
    matches.sort(key=lambda ivc: (_version_key(ivc[1]), ivc[0]), reverse=True)
    return matches[0][2]


def _version_key(version: str) -> tuple[int, ...]:
    """Return a sortable key for a semver string.

    Args:
        version: A semver string (e.g., ``"1.2.3"``).

    Returns:
        A tuple of non-negative integers (e.g., ``(1, 2, 3)``).
        Non-semver versions sort before all semver versions (the
        leading ``(-1,)`` ensures that).
    """
    parts = version.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (-1,)


def all_capabilities() -> types.MappingProxyType[tuple[str, str], Capability]:
    """Return a read-only snapshot of all registered capabilities.

    The returned mapping is a **point-in-time snapshot**: subsequent
    registrations (or unregistrations) do not affect it. Without
    the copy, :class:`types.MappingProxyType` would be a live
    view of :data:`_capabilities` (read-only but reflecting
    future mutations), defeating the "snapshot" contract.

    Self-healing: if the registry is empty, the V1 ``lookup``
    capability (the only V1 capability that self-registers on
    import) is re-registered. This protects against test-only
    :func:`reset` calls that wipe the registry mid-test-suite
    and would otherwise leave the planner with no capabilities
    at all.

    Returns:
        A read-only mapping of ``(id, version)`` → :class:`Capability`,
        in registration order.

    Examples:
        >>> sorted(all_capabilities().keys())  # doctest: +SKIP
        [('regex_extraction', '1.0'), ('text_extraction', '1.0')]
    """
    if not _capabilities:
        _bootstrap_v1_capabilities()
    return types.MappingProxyType(dict(_capabilities))


def _bootstrap_v1_capabilities() -> None:
    """Re-register the V1 built-in capabilities.

    Called automatically by :func:`all_capabilities` when the
    registry is empty. Ensures that test fixtures which use
    :func:`reset` to clear the registry do not break subsequent
    :func:`paxman.normalize` calls.

    Only the V1 capabilities that **self-register on import** are
    re-registered here. The rest (text_extraction,
    regex_extraction, inference, validation) are not part of the
    default registry; they must be registered explicitly by the
    user. This matches the original behaviour: importing
    ``paxman.capabilities.v1`` only registers ``lookup``.

    The bootstrap is a no-op if the V1 module has not been
    imported yet (in which case the user has explicitly opted
    out of V1 capabilities).
    """
    # Defer the import to call time. Using ``sys.modules`` first lets
    # us short-circuit when the V1 module is not yet imported (avoids
    # triggering the import cycle at static analysis time, which
    # pyright reports as an error).
    lookup_module = sys.modules.get("paxman.capabilities.v1.lookup")
    if lookup_module is None:
        # V1 module not available; nothing to bootstrap.
        return
    # Re-register the V1 capabilities that self-register on import.
    # The lookup capability's ``_register_on_import`` hook only runs
    # once at module load, so we re-do it here after a ``reset()``.
    register(lookup_module.LookupCapability(), replace=True)


def reset() -> None:
    """Remove all registered capabilities.

    This is a **test-only helper**. Production code must not call
    :func:`reset`; the registry is process-local and should be
    populated by the application's startup logic.
    """
    _capabilities.clear()
