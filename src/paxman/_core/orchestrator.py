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
place that produces ExecutionArtifacts.
"""
from __future__ import annotations

from typing import Any

import paxman as _paxman_version  # noqa: F401  (used to read __version__)

from paxman._contracts.contract import parse_contract
from paxman._core.artifact import ExecutionArtifact
from paxman._core.classification import ValidationResult, classify
from paxman._core.types import Evidence, Status, VersionStamp
from paxman._core.validation import validate as validate_value
from paxman._errors import ContractError, UnsupportedContractError


class _StubContract:
    """Minimal contract stand-in for unparseable contract specs."""

    def __init__(self, spec: object) -> None:
        self._spec = spec
        self.kind = "unknown"
        self.version = 0

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
        registry.freeze()

    # Stage 1: inspect — parse the contract Dict DSL.
    try:
        parsed_contract = parse_contract(contract)
    except ContractError:
        # An unparseable contract is a call that cannot proceed. The
        # contract is the truth (Law 5); a malformed contract is a
        # caller error, but the orchestrator maps unknown kinds to
        # Status.UNSUPPORTED (mandate Law 8 — fail informatively).
        return _build_artifact(
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
            parsed_contract=parsed_contract,
            status=Status.UNSUPPORTED,
            value=None,
            evidence=(
                Evidence(
                    rule="no_capability_claims",
                    detail=f"contract kind {parsed_contract.kind!r}, value type {type(input_data).__name__}",
                ),
            ),
        )

    if len(claimants) > 1:
        # Mandate §5.4: more than one claimant -> Status.AMBIGUOUS.
        return _build_artifact(
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
        try:
            validation = validate_value(capability_result.value, parsed_contract)
        except UnsupportedContractError:
            # Defensive: validation should never raise for a parsed
            # contract. If it does, treat as UNSUPPORTED.
            return _build_artifact(
                parsed_contract=parsed_contract,
                status=Status.UNSUPPORTED,
                value=None,
                evidence=(Evidence(rule="validation_unsupported_contract"),),
            )
    else:
        validation = ValidationResult(is_valid=True)

    # Stage 6: classify.
    final_status = classify(capability_result, validation)

    return _build_artifact(
        parsed_contract=parsed_contract,
        status=final_status,
        value=capability_result.value if final_status is Status.CANONICALIZED else None,
        evidence=capability_result.evidence,
    )


def _build_artifact(
    *,
    parsed_contract: object,
    status: Status,
    value: str | None,
    evidence: tuple[Evidence, ...],
) -> ExecutionArtifact:
    """Construct an ExecutionArtifact with the current VersionStamp."""
    from paxman import _orchestrator_runtime

    version_stamp = VersionStamp(
        paxman_version=_paxman_version.__version__,
        contract_version=parsed_contract.version,  # type: ignore[attr-defined]
        capabilities_hash=_orchestrator_runtime.default_registry.capabilities_hash(),
        configuration_version="0",
    )
    return ExecutionArtifact(
        status=status,
        value=value,
        evidence=evidence,
        contract=parsed_contract,  # type: ignore[arg-type]
        version_stamp=version_stamp,
    )
