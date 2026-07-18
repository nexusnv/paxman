"""The orchestrator — the pipeline Paxman owns (mandate Law 6).

The pipeline walks six stages:
  1. inspect         parse the contract Dict DSL
  2. resolve         find the capability / capabilities that claim
                     (contract, value)
  3. execute         run the capability's canonicalize method
  4. canonicalize    (the orchestrator itself, producing the canonical
                     value via the capability — the step name is
                     inherited from the pipeline diagram)
  5. validate        policy-check the canonical value
  6. classify        map (capability_result, validation) -> Status and
                     build the ExecutionArtifact

The orchestrator is pure: same input, contract, frozen registry, and
Paxman version -> same artifact (mandate Law 1). It is the only
place that produces ExecutionArtifacts. Mandate Law 6 (pipeline
boundaries): users contribute capabilities, never the pipeline itself.

This module is `paxman._core.engine` (renamed from `paxman._core.orchestrator`
in the additive architecture migration); the import paths it uses now point
at the capability-owned packages and the `_dsl` parser registry.
"""

from __future__ import annotations

from typing import Any

import paxman as _paxman_version  # used to read __version__
from paxman._capabilities.discovery import builtin_capabilities
from paxman._core.artifact import ExecutionArtifact, _ContractLike
from paxman._core.classification import ValidationResult, classify
from paxman._core.provenance import Evidence
from paxman._core.result import VersionStamp
from paxman._core.status import Status
from paxman._core.validation import validate as validate_value
from paxman._dsl.parser import parse_contract
from paxman._errors import CanonicalizationError, ContractError, UnsupportedContractError
from paxman._registry.capability_registry import CapabilityRegistry


class _StubContract:
    """Minimal contract stand-in for unparseable contract specs.

    Satisfies the `_ContractLike` Protocol structurally (provides
    `as_dict()` and a read-only `version` property). The orchestrator
    hands a `_StubContract` to `_build_artifact` when the caller's
    contract could not be parsed, so the resulting artifact still has
    a serializable contract representation.
    """

    def __init__(self, spec: object) -> None:
        self._spec = spec
        self.kind = "unknown"
        self._version = 0

    @property
    def version_field(self) -> int:
        # Law 12: preserve the contract schema version for replayability.
        return self._version

    def as_dict(self) -> dict[str, object]:
        if isinstance(self._spec, dict):
            return dict(self._spec)
        return {"kind": "unknown"}


def canonicalize(input_data: object, contract: Any) -> ExecutionArtifact:
    """The single entry point that produces an ExecutionArtifact.

    Mandate Law 1 + §2: deterministic, total on supported inputs,
    idempotent, totality-preserving on rejection. The contract is the
    truth (Law 5); the algorithm is Paxman's (Law 6); failures are
    informative (Law 8).
    """
    # Lazy import to avoid a circular import at module load.
    from paxman import _orchestrator_runtime

    registry = _orchestrator_runtime.default_registry
    if not registry.is_frozen:
        # Lazy built-in loading (spec §2.4, MANDATE §4.3 + Law 8a).
        # Runs BEFORE freeze so the capability set is fixed at resolve
        # time (Law 1: the capability set is part of the determinism
        # invariant). The import is inside this branch (not at module
        # top) to keep 'import paxman' side-effect-free and to avoid a
        # potential circular import between the capability packages and
        # the contract module.
        registry.load_builtins(builtin_capabilities())
        registry.freeze()

    # Stage 1: inspect — parse the contract Dict DSL.
    try:
        parsed_contract: _ContractLike = parse_contract(contract)
    except ContractError:
        # An unparseable contract is a call that cannot proceed. The
        # contract is the truth (Law 5); a malformed contract is a
        # caller error, but the orchestrator maps unknown kinds to
        # Status.UNSUPPORTED (mandate Law 8 — fail informatively).
        return _build_artifact(
            registry=registry,
            parsed_contract=_StubContract(contract),
            status=Status.UNSUPPORTED,
            value=None,
            evidence=(
                Evidence(
                    rule="unparseable_contract",
                    detail=str(contract),
                ),
            ),
        )

    # Stage 2: resolve — find the claimants.
    claimants = registry.resolve_all(parsed_contract, input_data)

    if not claimants:
        return _build_artifact(
            registry=registry,
            parsed_contract=parsed_contract,
            status=Status.UNSUPPORTED,
            value=None,
            evidence=(
                Evidence(
                    rule="no_capability_claims",
                    detail=(
                        f"contract kind {parsed_contract.kind!r}, "
                        f"value type {type(input_data).__name__}"
                    ),
                ),
            ),
        )

    if len(claimants) > 1:
        # Mandate §5.4: more than one claimant -> Status.AMBIGUOUS.
        return _build_artifact(
            registry=registry,
            parsed_contract=parsed_contract,
            status=Status.AMBIGUOUS,
            value=None,
            evidence=(
                Evidence(
                    rule="multiple_claimants",
                    detail="claimants: " + ", ".join(c.name for c in claimants),
                ),
            ),
        )

    # Exactly one claimant.
    capability = claimants[0]
    capability_result = capability.canonicalize(input_data, parsed_contract)

    # Stage 3+4: execute + canonicalize. The capability did both.
    # Stage 5: validate.
    if capability_result.status is Status.CANONICALIZED:
        # A CANONICALIZED capability result is required to carry a
        # non-None value (mandate Law 2 — the canonical value is the
        # whole point of canonicalization). An explicit check (not an
        # assert) is used so the invariant holds even under `python -O`,
        # where asserts are stripped.
        if capability_result.value is None:
            raise CanonicalizationError("CANONICALIZED capability result must carry a value")
        try:
            validation = validate_value(capability_result.value, parsed_contract)
        except UnsupportedContractError:
            # Defensive: validation should never raise for a parsed
            # contract. If it does, treat as UNSUPPORTED.
            return _build_artifact(
                registry=registry,
                parsed_contract=parsed_contract,
                status=Status.UNSUPPORTED,
                value=None,
                evidence=(Evidence(rule="validation_unsupported_contract"),),
            )
    else:
        validation = ValidationResult(is_valid=True)

    # Stage 6: classify.
    final_status = classify(capability_result, validation)

    # Contract (result.py): candidates are exclusive to AMBIGUOUS; drop otherwise.
    return _build_artifact(
        registry=registry,
        parsed_contract=parsed_contract,
        status=final_status,
        value=capability_result.value if final_status is Status.CANONICALIZED else None,
        evidence=capability_result.evidence,
        candidates=capability_result.candidates if final_status is Status.AMBIGUOUS else None,
    )


def _build_artifact(
    *,
    registry: CapabilityRegistry,
    parsed_contract: _ContractLike,
    status: Status,
    value: str | None,
    evidence: tuple[Evidence, ...],
    candidates: tuple[str, ...] | None = None,
) -> ExecutionArtifact:
    """Construct an ExecutionArtifact with the current VersionStamp.

    The `registry` is passed in (not read from a global) so the function
    is testable in isolation and so a future orchestrator variation can
    use a non-default registry without monkey-patching.

    The ``spec_versions`` / ``registry_versions`` maps are populated from
    the authorities actually cited in this artifact's evidence (mandate Law
    12 — the context that *produced* the artifact). Only the authorities
    this artifact fired enter the maps; an artifact that triggers only RFC
    5321 rules must not fail replay because RFC 1035 (cited elsewhere by
    the same capability) was revised.
    """
    spec_versions: dict[str, str] = {}
    registry_versions: dict[str, str] = {}
    for ev in evidence:
        authority = ev.authority
        if authority is None:
            continue
        if authority.kind == "specification":
            spec_versions[authority.name] = authority.edition
        elif authority.kind == "data-set":
            registry_versions[authority.name] = authority.edition
    version_stamp = VersionStamp(
        paxman_version=_paxman_version.__version__,
        # Law 12: stamp the contract schema version (not the capability policy).
        contract_version=parsed_contract.version_field,
        capabilities_hash=registry.capabilities_hash(),
        configuration_version="0",
        spec_versions=spec_versions,
        registry_versions=registry_versions,
    )
    return ExecutionArtifact(
        status=status,
        value=value,
        evidence=evidence,
        contract=parsed_contract,
        version_stamp=version_stamp,
        candidates=candidates,
    )
