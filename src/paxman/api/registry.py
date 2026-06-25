"""Public registry API for adapters and capabilities.

Provides the top-level :func:`register_adapter`,
:func:`register_capability`, :func:`get_adapter`, and
:func:`get_capability` functions that wrap the process-local
registries in :mod:`paxman.contract.registry` and
:mod:`paxman.capabilities.registry`.
"""

from paxman.capabilities.base import Capability
from paxman.capabilities.registry import get_latest as _get_latest_capability
from paxman.capabilities.registry import register as _register_capability
from paxman.contract.adapters.base import ContractAdapter
from paxman.contract.registry import get_adapter as _get_adapter
from paxman.contract.registry import register as _register_adapter
from paxman.errors import InvalidContractError

__all__ = [
    "get_adapter",
    "get_capability",
    "register_adapter",
    "register_capability",
]


def register_adapter(adapter: ContractAdapter) -> None:
    """Register a :class:`ContractAdapter` globally.

    Registered adapters are available for contract detection and
    adaptation in :func:`paxman.normalize`.

    Args:
        adapter: The adapter instance to register. Must implement the
            :class:`ContractAdapter` protocol (``format_id``, ``adapt``,
            ``export``).

    Raises:
        paxman.errors.InvalidContractError: If an adapter with the
            same ``format_id`` is already registered.
        TypeError: If *adapter* does not implement the protocol.

    Examples:
        >>> from paxman.contract.adapters.base import ContractAdapter
        >>> class MyAdapter:
        ...     format_id = "my_format"
        ...     def adapt(self, external): ...
        ...     def export(self, canonical): ...
        >>> register_adapter(MyAdapter())  # doctest: +SKIP
    """
    _register_adapter(adapter)


def register_capability(capability: Capability) -> None:
    """Register a :class:`Capability` globally.

    Registered capabilities are discovered by the planner and
    invoked by the executor during :func:`paxman.normalize`.

    Args:
        capability: The capability instance to register. Must implement
            the :class:`Capability` protocol (``spec`` property and
            ``invoke`` method).

    Raises:
        paxman.errors.InvalidContractError: If a capability with the
            same ``(id, version)`` is already registered.
        TypeError: If *capability* does not implement the protocol.

    Examples:
        >>> from paxman.capabilities.base import Capability
        >>> class MyCapability:
        ...     @property
        ...     def spec(self): ...
        ...     def invoke(self, ctx): ...
        >>> register_capability(MyCapability())  # doctest: +SKIP
    """
    _register_capability(capability)


def get_adapter(format_id: str) -> ContractAdapter | None:
    """Look up a registered adapter by ``format_id``.

    Args:
        format_id: The adapter's format identifier (e.g. ``"pydantic"``,
            ``"dict_dsl"``).

    Returns:
        The registered :class:`ContractAdapter`, or ``None`` if no
        adapter is registered for *format_id*.

    Examples:
        >>> adapter = get_adapter("pydantic")
        >>> adapter is not None
        True
    """
    try:
        return _get_adapter(format_id)
    except InvalidContractError:
        return None


def get_capability(capability_id: str) -> Capability | None:
    """Look up a registered capability by ``capability_id``.

    Returns the latest registered version of the capability.

    Args:
        capability_id: The capability's id (e.g. ``"regex_extraction"``,
            ``"text_extraction"``).

    Returns:
        The latest registered :class:`Capability`, or ``None`` if no
        capability is registered for *capability_id*.

    Examples:
        >>> cap = get_capability("regex_extraction")
        >>> cap is not None
        True
    """
    try:
        return _get_latest_capability(capability_id)
    except InvalidContractError:
        return None
