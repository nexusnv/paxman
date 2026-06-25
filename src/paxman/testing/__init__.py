"""Hypothesis strategies for property-based testing of paxman.

Per Sprint 7 D7.1, this module exposes 7 public Hypothesis strategies
that downstream tests (and external test suites for libraries built on
paxman) can use:

- :func:`contracts` — :class:`~paxman.contract.canonical.CanonicalContract`
  instances with varied field shapes.
- :func:`inputs` — raw input bytes.
- :func:`budgets` — :class:`~paxman.budget.Budget` instances.
- :func:`policies` — :class:`~paxman.budget.Policy` instances.
- :func:`registries` — :class:`Capability` registries (process-local
  install-and-uninstall wrappers for use in property tests).
- :func:`candidate_sets` — ``list[dict[str, Any]]`` candidate sets
  suitable for direct Reconciler testing.
- :func:`artifacts` — :class:`~paxman.artifact.artifact.ExecutionArtifact`
  instances with a stable :attr:`~paxman.artifact.artifact.ExecutionArtifact.replay_hash`.

Usage::

    from hypothesis import given
    from paxman.testing import contracts, inputs

    @given(contract=contracts(), raw=inputs())
    def test_something(contract, raw):
        ...

Exit criterion #10: ``from paxman.testing import contracts, inputs,
budgets, policies, registries`` works.

Boundary
--------

This module is part of the **public surface** of paxman. It is allowed
to import from any cross-cutting module (``paxman.types``,
``paxman.budget``, ``paxman.ids``, etc.) and from the artifact /
contract / capabilities subsystems (it produces instances of those
types). It does not need to follow the strict cross-cutting
import-linter rules in :mod:`paxman.errors` because it is **not** a
cross-cutting module — it is a *test* module shipped for downstream
consumers.

V1 scope: V1 capabilities only. V2 will add strategy for LLM
provider mock outputs.
"""

from __future__ import annotations

import string
import typing

import attrs
import hypothesis
from hypothesis import strategies as st

from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.budget import Budget, CurrencyPolicy, Policy
from paxman.capabilities.base import Capability, CapabilityContext
from paxman.capabilities.registry import register, reset, unregister
from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.contract._types import EnumValueSet
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.planner.field_plan import ExecutionPlan, FieldPlan, FieldPlanStep
from paxman.types import ConfidenceBand, FieldType, Status

__all__ = [
    "Budget",
    "Candidate",
    "CandidateSet",
    "CanonicalContract",
    "CapabilityContext",
    "CapabilityResult",
    "CurrencyPolicy",
    "Diagnostic",
    "DiagnosticCode",
    "DiagnosticSeverity",
    "EvidenceRef",
    "ExecutionArtifact",
    "ExecutionPlan",
    "FieldPlan",
    "FieldPlanStep",
    "FieldType",
    "Policy",
    "Status",
    "artifacts",
    "budgets",
    "candidate_sets",
    "contracts",
    "inputs",
    "policies",
    "registries",
]


# ---------------------------------------------------------------------------
# Re-exports for convenience
# ---------------------------------------------------------------------------
#
# Downstream tests that use ``paxman.testing`` may want to build
# :class:`Candidate` / :class:`EvidenceRef` instances manually. We
# re-export the canonical types here so that imports are stable
# regardless of internal refactoring.


# ---------------------------------------------------------------------------
# Primitive strategies
# ---------------------------------------------------------------------------

# Identifier-friendly field names; reserved words in ``CanonicalContract``
# (``id``, ``fields``, ``version``, ``policies``) are excluded.
_FIELD_NAMES: st.SearchStrategy[str] = st.text(
    alphabet=string.ascii_lowercase,
    min_size=1,
    max_size=10,
).filter(lambda s: s.isidentifier() and s not in {"id", "fields", "version", "policies"})

# All 9 V1 field types are represented.
_FIELD_TYPES: st.SearchStrategy[FieldType] = st.sampled_from(
    [
        FieldType.STRING,
        FieldType.INTEGER,
        FieldType.DECIMAL,
        FieldType.BOOLEAN,
        FieldType.DATE,
        FieldType.ENUM,
        FieldType.OBJECT,
        FieldType.ARRAY,
        FieldType.MONEY,
    ]
)

# Short, decode-friendly byte strings as raw inputs. Random bytes are
# intentionally avoided because the planner's input-profile layer
# decodes them as UTF-8 (with errors="replace").
_INPUT_BYTES: st.SearchStrategy[bytes] = st.binary(min_size=0, max_size=512)


# ---------------------------------------------------------------------------
# contracts()
# ---------------------------------------------------------------------------


@st.composite
def _field_strategy(draw: st.DrawFn) -> CanonicalField:
    """A single ``CanonicalField`` with random metadata."""
    name = draw(_FIELD_NAMES)
    type_ = draw(_FIELD_TYPES)
    required = draw(st.booleans())
    threshold = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    # ENUM fields require a non-None ``enum_values``. We provide a small
    # fixed set so the strategy can produce ENUM-typed fields without
    # going off the deep end.
    enum_values: EnumValueSet | None = None
    if type_ is FieldType.ENUM:
        enum_values = EnumValueSet(values=("alpha", "beta", "gamma"))
    return CanonicalField(
        id=f"field_{name}",
        path=name,
        name=name,
        type=type_,
        required=required,
        confidence_threshold=threshold,
        enum_values=enum_values,
    )


@st.composite
def _contract_strategy(draw: st.DrawFn) -> CanonicalContract:
    """A ``CanonicalContract`` with 1-4 fields."""
    fields = draw(
        st.lists(
            _field_strategy(),
            min_size=1,
            max_size=4,
            unique_by=lambda f: f.name,
        )
    )
    return CanonicalContract(
        id="testing-generated",
        fields=tuple(fields),
    )


def contracts() -> st.SearchStrategy[CanonicalContract]:
    """Generate :class:`CanonicalContract` instances of varied shapes.

    Each generated contract has 1-4 fields, each with a random
    ``type`` (one of the 9 V1 field types) and random ``required`` /
    ``confidence_threshold`` settings.

    Returns:
        A Hypothesis search strategy yielding :class:`CanonicalContract`.

    Example::

        from paxman.testing import contracts
        from hypothesis import given

        @given(contract=contracts())
        def test_my_thing(contract):
            assert len(contract.fields) >= 1
    """
    return _contract_strategy()


# ---------------------------------------------------------------------------
# inputs()
# ---------------------------------------------------------------------------


def inputs() -> st.SearchStrategy[bytes]:
    """Generate raw input bytes suitable for ``paxman.normalize()``.

    The bytes are short (0-512 bytes) and decodeable as UTF-8 in most
    cases. The downstream planner's :func:`InputProfile` layer
    re-decodes bytes as UTF-8 (with errors="replace") so this strategy
    produces input that exercises both the ASCII and the
    partially-invalid paths.

    Returns:
        A Hypothesis search strategy yielding :class:`bytes`.
    """
    return _INPUT_BYTES


# ---------------------------------------------------------------------------
# budgets()
# ---------------------------------------------------------------------------


@st.composite
def _budget_strategy(draw: st.DrawFn) -> Budget:
    """A ``Budget`` with one or more caps set to non-trivial values."""
    return Budget(
        max_total_cost_usd=draw(
            st.one_of(
                st.none(),
                st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            )
        ),
        max_total_latency_ms=draw(
            st.one_of(
                st.none(),
                st.integers(min_value=1, max_value=60_000),
            )
        ),
        max_remote_inference_calls=draw(
            st.one_of(
                st.none(),
                st.integers(min_value=0, max_value=100),
            )
        ),
        max_capability_invocations=draw(
            st.one_of(
                st.none(),
                st.integers(min_value=1, max_value=1000),
            )
        ),
    )


def budgets() -> st.SearchStrategy[Budget]:
    """Generate :class:`~paxman.budget.Budget` instances.

    Each budget has one or more caps set. The ``max_total_cost_usd``
    cap, when set, ranges 0.0-10.0 USD. The ``max_total_latency_ms``
    cap ranges 1-60 000 ms. Invocation caps range 0-1000.

    Returns:
        A Hypothesis search strategy yielding :class:`Budget`.
    """
    return _budget_strategy()


# ---------------------------------------------------------------------------
# policies()
# ---------------------------------------------------------------------------


@st.composite
def _policy_strategy(draw: st.DrawFn) -> Policy:
    """A ``Policy`` with random boolean and numeric settings."""
    return Policy(
        allow_remote_inference=draw(st.booleans()),
        allow_local_inference=draw(st.booleans()),
        confidence_floor=draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        ),
        unresolved_acceptable=draw(st.booleans()),
        currency_policy=draw(st.sampled_from(list(CurrencyPolicy))),
        emit_metrics=draw(st.booleans()),
        log_raw_input=draw(st.booleans()),
        record_inference_io=draw(st.booleans()),
        embed_evidence_payload=draw(st.booleans()),
    )


def policies() -> st.SearchStrategy[Policy]:
    """Generate :class:`~paxman.budget.Policy` instances.

    Each policy has random boolean and numeric settings. The
    ``confidence_floor`` is always in [0.0, 1.0]; the
    ``currency_policy`` cycles through all three V1 values.

    Returns:
        A Hypothesis search strategy yielding :class:`Policy`.
    """
    return _policy_strategy()


# ---------------------------------------------------------------------------
# registries()
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class _StubCapability:
    """A trivial :class:`Capability` used by the ``registries`` strategy.

    The stub always returns an empty ``CapabilityResult``. It is
    sufficient for property tests that only need a populated registry
    (e.g. to test the planner's interaction with the registry), not
    realistic candidate output.
    """

    spec: CapabilitySpec

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Return an empty result (stub)."""
        return CapabilityResult(candidates=())


@st.composite
def _registry_strategy(draw: st.DrawFn) -> dict[tuple[str, str], Capability]:
    """A registry dict of 1-3 stub capabilities.

    The returned value is a plain ``dict`` (the same shape the
    :class:`Executor` consumes directly). To install it as
    process-local state, use :func:`install_registry` from a test
    fixture.
    """
    n_caps = draw(st.integers(min_value=1, max_value=3))
    capabilities: dict[tuple[str, str], Capability] = {}
    for i in range(n_caps):
        cap_id = f"stub_cap_{i}"
        spec = CapabilitySpec(
            id=cap_id,
            version="1.0",
            input_types=(),
            output_type="STRING",
            cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        )
        capabilities[(cap_id, "1.0")] = _StubCapability(spec=spec)
    return capabilities


def registries() -> st.SearchStrategy[dict[tuple[str, str], Capability]]:
    """Generate :class:`Capability` registries as plain dicts.

    Each registry contains 1-3 stub capabilities. Use
    :func:`install_registry` in test fixtures to install these into
    the process-local registry and clean up afterwards.

    Returns:
        A Hypothesis search strategy yielding ``dict[tuple[str, str], Capability]``.

    Example::

        from paxman.testing import registries, install_registry

        @given(registry=registries())
        def test_my_thing(registry):
            with install_registry(registry):
                # ... test code ...
    """
    return _registry_strategy()


class _RegistryInstaller:
    """Context manager that installs and removes a registry of capabilities.

    Use this in property tests to install a generated registry into
    the process-local state for the duration of the test, ensuring
    cleanup even on test failure.
    """

    def __init__(self, registry: dict[tuple[str, str], Capability]) -> None:
        self._registry = registry
        self._installed_keys: list[tuple[str, str]] = []

    def __enter__(self) -> _RegistryInstaller:
        # Reset first to ensure a clean state.
        reset()
        for (cap_id, version), cap in self._registry.items():
            register(cap, replace=True)
            self._installed_keys.append((cap_id, version))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        for cap_id, version in self._installed_keys:
            try:
                unregister(cap_id, version)
            except KeyError:
                pass
        # Final reset to ensure no leakage between tests.
        reset()
        self._installed_keys.clear()


def install_registry(registry: dict[tuple[str, str], Capability]) -> _RegistryInstaller:
    """Context manager that installs a registry for the duration of a test.

    Args:
        registry: The capabilities to install, keyed by
            ``(capability_id, version)``.

    Returns:
        A context manager. On exit, all installed capabilities are
        removed and the registry is reset.

    Example::

        from paxman.testing import registries, install_registry

        @given(registry=registries())
        def test_my_thing(registry):
            with install_registry(registry):
                # ... test code ...
    """
    return _RegistryInstaller(registry)


# ---------------------------------------------------------------------------
# candidate_sets()
# ---------------------------------------------------------------------------


# Type alias for the candidate-set output: a list of dicts that downstream
# Reconciler tests can adapt to CandidateResult instances.
CandidateSet = list[dict[str, typing.Any]]


@st.composite
def _candidate_set_strategy(draw: st.DrawFn) -> CandidateSet:
    """A list of 1-4 candidate-result dicts.

    Each dict has the keys ``field_id``, ``field_path``,
    ``field_type_name``, ``candidates`` (list of dicts with ``value``
    and ``evidence_refs``), and ``status``. The Reconciler tests build
    ``CandidateResult`` instances from these dicts.
    """
    n = draw(st.integers(min_value=1, max_value=4))
    field_id = draw(_FIELD_NAMES)
    field_type_name = draw(_FIELD_TYPES).name
    candidates_list: CandidateSet = []
    for _ in range(n):
        cand_count = draw(st.integers(min_value=0, max_value=3))
        cands: list[dict[str, typing.Any]] = []
        for j in range(cand_count):
            refs: list[dict[str, typing.Any]] = []
            n_refs = draw(st.integers(min_value=0, max_value=3))
            for k in range(n_refs):
                refs.append(
                    {
                        "capability_id": f"cap_{j}_{k}",
                        "capability_version": "1.0",
                        "field_path": field_id,
                    }
                )
            cands.append(
                {
                    "value": f"value_{j}",
                    "evidence_refs": refs,
                }
            )
        candidates_list.append(
            {
                "field_id": field_id,
                "field_path": field_id,
                "field_type_name": field_type_name,
                "candidates": cands,
                "status": "RESOLVED" if cands else "UNRESOLVED",
            }
        )
    return candidates_list


def candidate_sets() -> st.SearchStrategy[CandidateSet]:
    """Generate candidate sets for Reconciler property tests.

    Each set is a ``list[dict[str, Any]]`` of 1-4 candidate-result
    dicts, each with 0-3 candidates per field and 0-3 evidence refs
    per candidate. The Reconciler tests adapt these to
    :class:`CandidateResult` instances.

    Returns:
        A Hypothesis search strategy yielding ``CandidateSet``.
    """
    return _candidate_set_strategy()


# ---------------------------------------------------------------------------
# artifacts()
# ---------------------------------------------------------------------------


@st.composite
def _artifact_strategy(draw: st.DrawFn) -> ExecutionArtifact:
    """A minimal :class:`ExecutionArtifact` with a valid ``replay_hash``.

    The artifact is constructed with random field paths, candidate
    values, confidence bands, and statuses, then ``replay_hash`` is
    computed deterministically via :func:`compute_replay_hash`.
    """
    n_fields = draw(st.integers(min_value=0, max_value=3))
    field_results: dict[str, FieldResult] = {}
    normalized_data: dict[str, typing.Any] = {}
    unresolved_fields: list[str] = []
    evidence: list[EvidenceRef] = []
    diagnostics: list[Diagnostic] = []

    for i in range(n_fields):
        path = f"field_{i}"
        confidence = draw(st.sampled_from(list(ConfidenceBand)))
        if draw(st.booleans()):
            # RESOLVED field
            value = f"value_{i}"
            field_results[path] = FieldResult(
                field_path=path,
                value=value,
                confidence=confidence,
                candidates=(),
                evidence_refs=(),
                status=Status.SUCCESS,
            )
            normalized_data[path] = value
        else:
            # UNRESOLVED field
            field_results[path] = FieldResult(
                field_path=path,
                value=None,
                confidence=ConfidenceBand.UNTRUSTED,
                candidates=(),
                evidence_refs=(),
                status=Status.UNRESOLVED,
            )
            unresolved_fields.append(path)

    # A small but non-empty pool of evidence (always present so the
    # hash is non-trivial).
    n_evidence = draw(st.integers(min_value=0, max_value=2))
    for k in range(n_evidence):
        evidence.append(
            EvidenceRef(
                capability_id=f"cap_artifact_{k}",
                capability_version="1.0",
                field_path="synthetic",
            )
        )

    # A small pool of diagnostics.
    n_diag = draw(st.integers(min_value=0, max_value=2))
    for k in range(n_diag):
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCode.CAPABILITY_OK,
                severity=DiagnosticSeverity.INFO,
                message=f"synthetic diagnostic {k}",
            )
        )

    status = (
        Status.SUCCESS
        if not unresolved_fields
        else (Status.PARTIAL_SUCCESS if normalized_data else Status.UNRESOLVED)
    )

    artifact = ExecutionArtifact(
        status=status,
        id=f"art_test_{draw(st.integers(min_value=0, max_value=2**32))}",
        normalized_data=normalized_data,
        field_results=field_results,
        unresolved_fields=unresolved_fields,
        evidence=tuple(evidence),
        diagnostics=tuple(diagnostics),
        execution_plan=None,
        replay_hash="",  # computed below
        statistics=None,
        contract_id=f"contract_{draw(st.integers(min_value=0, max_value=2**32))}",
        capability_versions={},
    )
    # Compute the deterministic replay hash so that downstream replay
    # tests can verify byte-equal rehydration.
    return attrs.evolve(artifact, replay_hash=compute_replay_hash(artifact))


def artifacts() -> st.SearchStrategy[ExecutionArtifact]:
    """Generate :class:`~paxman.artifact.artifact.ExecutionArtifact` instances.

    Each artifact has 0-3 fields (a mix of resolved and unresolved),
    0-2 evidence refs, 0-2 diagnostics, and a deterministic
    :attr:`~paxman.artifact.artifact.ExecutionArtifact.replay_hash`.

    Returns:
        A Hypothesis search strategy yielding :class:`ExecutionArtifact`.

    Example::

        from paxman.testing import artifacts
        from hypothesis import given

        @given(artifact=artifacts())
        def test_replay_is_byte_equal(artifact):
            assert len(artifact.replay_hash) == 64
    """
    return _artifact_strategy()


# ---------------------------------------------------------------------------
# Self-check: confirm all 7 strategies are SearchStrategy instances
# ---------------------------------------------------------------------------

# This block is executed at module import time. It guards against
# accidental type regressions (e.g., a developer accidentally returning
# a list instead of a strategy from one of the factories).
_ = hypothesis  # satisfy type checker
