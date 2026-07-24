"""The Capability Protocol — the only extension point of Paxman v2.

Mandate §5.1: a capability transforms, it does not orchestrate. The
Protocol deliberately omits control-flow verbs (`next`, `execute`,
`pipeline`, `stage`, `context switching`, `branching`).

The Protocol is `@runtime_checkable` so the registry can validate
duck-typing at register time.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from paxman._capabilities._shared.base import CanHandle, OutputFormats

# Law 4 (capability boundaries): a capability transforms (contract,
# value); it does not orchestrate. Law 8a (pure functions):
# canonicalize is a pure (value, contract) -> result transform.
from paxman._core.contracts import Contract
from paxman._core.engine_env import Engine
from paxman._core.result import CapabilityResult


@runtime_checkable
class Capability(Protocol):
    """A pure deterministic transformation that answers
    'Can I canonicalize this value, given this contract?'

    Optional hook — ``validate(value, contract) -> ValidationResult``:
    a capability MAY define this method to enforce contract-specific
    strictness policy after canonicalization (mandate Law 4). It is not
    part of the runtime-checked Protocol surface (so existing capabilities
    remain valid without it); the orchestrator dispatches to it via
    duck-typing. The default behavior when absent is "always valid". The
    method must not interpret or guess (Law 4).
    """

    name: str

    # can_handle is a Callable attribute (not a method) matching CanHandle.
    # This keeps the Protocol's surface identical to what subclasses assign
    # (`can_handle: CanHandle = make_can_handle(...)`), so mypy's
    # conformance check sees two identical Callable shapes.
    can_handle: CanHandle

    # The set of output formats this capability can produce (e.g.
    # frozenset({"alpha2", "alpha3", "numeric"}) for country). Each
    # capability declares its supported formats; the contract's
    # `output_format` field must be one of these.
    supported_output_formats: OutputFormats

    def canonicalize(
        self, value: Any, contract: Contract, engine: Engine | None = None
    ) -> CapabilityResult: ...
