# src/paxman/_capabilities/boolean/canonicalizer.py
"""BooleanCapability: a built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14.
Architecture (recognition → resolver → validation → classify), mirroring
the email/date capabilities.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

import attrs

from paxman._capabilities._shared.base import (
    CanHandle,
    CapabilityBase,
    make_can_handle,
    reject_contract,
    reject_missing,
    reject_non_string,
)
from paxman._capabilities._shared.grammar import Provenance
from paxman._capabilities.boolean.contract import CanonicalBooleanContract
from paxman._capabilities.boolean.grammar import RecognizedRep, recognize
from paxman._capabilities.boolean.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.engine_env import Engine
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# Token -> canonical mapping (declared Paxman policy, spec §3.2). Immutable so
# the canonical vocabulary cannot be mutated at runtime (mandate Law 1).
_TOKEN_TO_CANONICAL: Mapping[str, str] = MappingProxyType(
    {
        "true": "true",
        "t": "true",
        "yes": "true",
        "y": "true",
        "on": "true",
        "enabled": "true",
        "1": "true",
        "false": "false",
        "f": "false",
        "no": "false",
        "n": "false",
        "off": "false",
        "disabled": "false",
        "0": "false",
    }
)
_NUMERIC_TOKENS = frozenset({"1", "0"})


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a boolean-shaped input."""

    value: str
    token: str
    rule: str
    provenance: Provenance
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    """A candidate that survived policy validation: a concrete canonical form."""

    value: str
    rule: str
    provenance: Provenance
    evidence: tuple[Evidence, ...]


def generate_interpretations(
    reps: list[RecognizedRep], contract: CanonicalBooleanContract
) -> list[_Candidate]:
    """Map grammar recognitions to candidate canonical forms (resolver)."""
    candidates: list[_Candidate] = []
    for rep in reps:
        token = rep.captures["token"].lower()
        canonical = _TOKEN_TO_CANONICAL[token]
        candidates.append(
            _Candidate(
                value=canonical,
                token=token,
                rule="matched_boolean_token",
                provenance=rep.provenance,
                evidence=(_evidence("matched_boolean_token", f"{token!r} -> {canonical!r}"),),
            )
        )
    return candidates


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalBooleanContract
) -> tuple[list[_Survivor], list[str]]:
    """Validate each candidate against the contract policy.

    A token disabled by the contract's policy (numeric without
    accept_numeric, or word without accept_words) is dropped with a
    `policy_disabled_token` reason.
    """
    survivors: list[_Survivor] = []
    drop_reasons: list[str] = []
    for c in candidates:
        # An already-canonical input ("true"/"false") is always valid: it is
        # the *result* of canonicalization, never a gated user token. Accepting
        # it unconditionally preserves idempotence (mandate Law 2) even when
        # the contract disables word or numeric inputs.
        if c.token == c.value:
            survivors.append(_Survivor(c.value, c.rule, c.provenance, c.evidence))
            continue
        is_numeric = c.token in _NUMERIC_TOKENS
        if is_numeric and not contract.accept_numeric:
            drop_reasons.append("policy_disabled_token")
            continue
        if not is_numeric and not contract.accept_words:
            drop_reasons.append("policy_disabled_token")
            continue
        survivors.append(_Survivor(c.value, c.rule, c.provenance, c.evidence))
    return survivors, drop_reasons


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome.

    Returns a 4-tuple (status, value, evidence, candidates).
    """
    if not candidates:
        return Status.INVALID, None, (_evidence("unrecognized_token"),), None
    if not survivors:
        if "policy_disabled_token" in drop_reasons:
            return Status.INVALID, None, (_evidence("policy_disabled_token"),), None
        return Status.INVALID, None, (_evidence("unrecognized_token"),), None
    if len(survivors) == 1:
        s = survivors[0]
        return Status.CANONICALIZED, s.value, s.evidence, None
    # Defensive: boolean never yields >1 survivor, but surface ambiguity if it ever does.
    merged: list[Evidence] = []
    for survivor in survivors:
        for ev in survivor.evidence:
            if ev not in merged:
                merged.append(ev)
    return (
        Status.AMBIGUOUS,
        None,
        tuple(merged),
        tuple(sorted({s.value for s in survivors})),
    )


class BooleanCapability(CapabilityBase):
    """A pure deterministic transformation that canonicalizes booleans."""

    name: str = "boolean_canonicalization"

    can_handle: CanHandle = make_can_handle(CanonicalBooleanContract, accept_none=True)

    supported_output_formats: frozenset[str] = frozenset({"truefalse"})

    def _canonicalize(
        self, value: object, contract: Contract, engine: Engine | None = None
    ) -> CapabilityResult:
        """Canonicalize a boolean-shaped input into "true" or "false".

        The pipeline (recognition → resolver → validation → classify):
        - a non-boolean contract returns INVALID (not_a_boolean_contract);
        - a non-None/non-str value returns INVALID (not_a_string_value);
        - None or whitespace-only input returns MISSING (missing_value);
        - leading/trailing ASCII whitespace is trimmed (trimmed_whitespace);
        - Layer 1 recognition matches the boolean token grammar; an unmatched
          input returns INVALID (unrecognized_token);
        - the resolver maps the token to its canonical form, policy validation
          drops tokens disabled by accept_numeric/accept_words
          (policy_disabled_token), and classify emits the final Status.
        """
        r = reject_contract(contract, CanonicalBooleanContract, _evidence, "not_a_boolean_contract")
        if r is not None:
            return r
        r = reject_non_string(value, _evidence)
        if r is not None:
            return r
        assert isinstance(contract, CanonicalBooleanContract)

        # Missing value -> MISSING (spec §3.3).
        r = reject_missing(value, _evidence, "missing_value")
        if r is not None:
            return r
        assert isinstance(value, str)

        # Trim leading/trailing ASCII whitespace (record if changed).
        stripped_evidence: tuple[Evidence, ...] = ()
        stripped = value.strip(" \t\r\n\f\v")
        if stripped != value:
            stripped_evidence = (_evidence("trimmed_whitespace"),)
            value = stripped

        # Recognition layer (Layer 1).
        reps = recognize(value, contract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_token"),)
            )

        # Resolver + validation + classify.
        cands = generate_interpretations(reps, contract)
        survs, drops = resolve_and_validate(cands, contract)
        status, rendered, evidence, cands_out = classify(cands, survs, drops)
        if stripped_evidence:
            evidence = stripped_evidence + evidence
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )
