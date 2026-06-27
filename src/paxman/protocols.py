"""Internal Protocol definitions for cross-cutting SPIs.

Defines the four structural protocols that govern extensibility points
throughout the paxman engine.  A public subset (``ContractAdapter``,
``Capability``, ``Heuristic``) is re-exported via ``paxman.api.protocols``.
``InferenceProvider`` is internal-only.

All protocols use ``typing.Protocol`` (PEP 544) so that concrete
implementations need not inherit from them -- they are satisfied
structurally.
"""

from typing import Protocol

__all__ = [
    "Capability",
    "ContractAdapter",
    "Heuristic",
    "InferenceProvider",
]


# ---------------------------------------------------------------------------
# ContractAdapter
# ---------------------------------------------------------------------------


class ContractAdapter(Protocol):
    """SPI: translate an external contract format to/from ``CanonicalContract``.

    Adapters are pure: same input always produces the same
    ``CanonicalContract``.  No I/O, no clock reads, no randomness.

    Public
        Re-exported in ``paxman.api.protocols``.
    """

    @property
    def format_id(self) -> str:
        """Stable identifier for the external format.

        Examples: ``'pydantic'``, ``'json_schema:draft-2020-12'``.
        """
        ...

    def adapt(self, external: object) -> object:
        """Translate an external contract into a ``CanonicalContract``.

        Args:
            external: The external contract object (e.g. a Pydantic model,
                a JSON-Schema dict, an OpenAPI spec).

        Returns:
            A ``CanonicalContract`` representing the same logical contract.

        Raises:
            paxman.errors.InvalidContractError: If *external* is malformed or
                cannot be translated.
        """
        ...

    def export(self, canonical: object) -> object:
        """Translate a ``CanonicalContract`` back into the external format.

        Args:
            canonical: The internal ``CanonicalContract`` to export.

        Returns:
            An object in the adapter's external format.

        Raises:
            paxman.errors.InvalidContractError: If the canonical contract
                cannot be represented in the target format.
        """
        ...


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


class Capability(Protocol):
    """SPI: an atomic operation producing candidates and evidence.

    Each capability executes one kind of extraction or inference step
    against a ``CapabilityContext`` and returns a ``CapabilityResult``
    containing candidates, evidence, and diagnostics.

    Capabilities **never** assign confidence.  Confidence is the sole
    responsibility of the ``Reconciler`` (ADR-0005).

    Public
        Re-exported in ``paxman.api.protocols``.
    """

    @property
    def spec(self) -> object:
        """Metadata describing the capability (``CapabilitySpec``).

        The spec is used by the planner to select and configure
        capabilities for each ``FieldPlan``.
        """
        ...

    def invoke(self, ctx: object) -> object:
        """Execute the capability against a ``CapabilityContext``.

        Args:
            ctx: A ``CapabilityContext`` carrying the input data, field
                metadata, and any configuration needed for execution.

        Returns:
            A ``CapabilityResult`` containing candidates, evidence, and
            diagnostics -- but **no** confidence values.
        """
        ...


# ---------------------------------------------------------------------------
# Heuristic
# ---------------------------------------------------------------------------


class Heuristic(Protocol):
    """SPI: a planner heuristic for customising plan synthesis.

    Heuristics allow callers to inject domain-specific logic into the
    planner's step-selection phase.  A heuristic receives a field
    descriptor and a context, and returns an ordered list of
    ``FieldPlanStep`` objects.

    Public
        Re-exported in ``paxman.api.protocols`` (post-V1).
    """

    def select(self, field: object, ctx: object) -> list[object]:
        """Return the ``FieldPlanStep`` list for a field.

        Args:
            field: A descriptor of the target field (name, type, constraints).
            ctx: Planner context providing access to the canonical contract
                and any resolved values so far.

        Returns:
            An ordered list of ``FieldPlanStep`` objects to execute for
            this field.  May be empty if the heuristic declines to act.
        """
        ...


# ---------------------------------------------------------------------------
# InferenceProvider
# ---------------------------------------------------------------------------


class InferenceProvider(Protocol):
    """SPI: a model provider behind the ``inference`` capability.

    Concrete implementations wrap external LLM or ML services (e.g.
    OpenAI, Anthropic, local models).  The ``inference`` capability
    delegates the actual completion call to a provider that satisfies
    this protocol.

    Internal
        Not re-exported.  Lives in ``paxman.capabilities.inference``.
    """

    def complete(self, request: object) -> object:
        """Send a ``CompletionRequest`` to the model provider.

        Args:
            request: A ``CompletionRequest`` describing the prompt,
                model parameters, and budget constraints.

        Returns:
            A ``Completion`` object containing the model response,
            token usage, and any provider-specific metadata.
        """
        ...
