"""UUIDCapability: the second built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14:
- Law 4: rewrites known representations; does not interpret.
- Law 5: the contract declares the policy; the capability applies it.
- Law 7: the policy is explicit; no auto-detection.
- Law 8 + 8a: the capability is a pure function of (value, contract).
  No network, no time, no randomness, no filesystem.
- Law 11: the canonical form is a function of (value, contract). Two
  independent implementations must produce the same value.
- Law 14: every transformation rule has provenance. The rule→citation
  manifest is `_RULE_PROVENANCE`; `Evidence.provenance` is populated
  from it.

Architecture (recognition → resolver → validation → classify)
------------------------------------------------------------
The capability is split into four deterministic stages, mirroring the
email capability:

1. ``grammar.recognize`` (Layer 1) maps the raw input to the set of
   grammar shapes it could name, producing only RAW string captures.
2. ``generate_interpretations`` (resolver) assigns meaning to those
   captures and enumerates candidate canonical forms.
3. ``resolve_and_validate`` validates each candidate against the
   RFC 4122 §3 canonical form and the contract's version policy,
   dropping those that name no valid canonical uuid.
4. ``classify`` maps the surviving candidates to a canonicalization
   outcome (CANONICALIZED / AMBIGUOUS / INVALID), never guessing.

UUID has exactly one canonical form, so the resolver emits exactly one
candidate and classify always sees 0 or 1 survivor (never >1). The
generic classify structure is retained so the architecture matches
email/date.
"""

from __future__ import annotations

import attrs

from paxman._capabilities.uuid.contract import CanonicalUUIDContract
from paxman._capabilities.uuid.grammar import RecognizedRep, recognize
from paxman._capabilities.uuid.parser import CANONICAL_CHARS, CANONICAL_LENGTH, HYPHEN_POSITIONS
from paxman._capabilities.uuid.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a uuid-shaped input.

    ``value`` is the fully-reconstructed candidate canonical form.
    ``rule`` / ``source`` carry the originating grammar's id and Law-14
    provenance. ``evidence`` is the tuple of ``Evidence`` accumulated for
    the transformations that produced this candidate.
    """

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    """A candidate that survived validation: a concrete valid canonical uuid."""

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


def generate_interpretations(
    reps: list[RecognizedRep], contract: CanonicalUUIDContract
) -> list[_Candidate]:
    """Map grammar recognitions to candidate canonical forms (resolver).

    Assigns meaning to the raw captures produced by
    :func:`grammar.recognize` and enumerates every candidate canonical
    form the declared policies permit. The recognised form is already
    canonical, so the only evidence is ``no_transformation_needed``.
    """
    candidates: list[_Candidate] = []
    for rep in reps:
        gid = rep.grammar_id
        if gid == "canonical_uuid":
            candidates.append(
                _Candidate(
                    rep.captures["value"],
                    "canonical_uuid",
                    rep.source,
                    (_evidence("no_transformation_needed"),),
                )
            )
    return candidates


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalUUIDContract
) -> tuple[list[_Survivor], list[str]]:
    """Validate each candidate; drop those that name no valid canonical uuid."""
    survivors: list[_Survivor] = []
    drop_reasons: list[str] = []
    for c in candidates:
        # Defensive re-check: the grammar already guarantees the canonical
        # form, but re-validate against the contract constants so the
        # invariant holds even if the grammar is loosened.
        if len(c.value) != CANONICAL_LENGTH:
            drop_reasons.append("grammar_rejected")
            continue
        valid = True
        for i, ch in enumerate(c.value):
            if ch not in CANONICAL_CHARS:
                valid = False
                break
            if ch == "-" and i not in HYPHEN_POSITIONS:
                valid = False
                break
            if ch != "-" and i in HYPHEN_POSITIONS:
                valid = False
                break
        if not valid:
            drop_reasons.append("grammar_rejected")
            continue
        # Version-nibble policy: the first hex digit of the third group
        # (RFC 4122 §4.1.3) must match the contract's version policy.
        version_nibble = c.value[14]
        if contract.version != "any" and version_nibble != contract.version:
            drop_reasons.append("version_mismatch")
            continue
        survivors.append(_Survivor(c.value, c.rule, c.source, c.evidence))
    return survivors, drop_reasons


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome.

    Returns a 4-tuple ``(status, value, evidence, candidates)``. The
    ``candidates`` element is the sorted tuple of every surviving canonical
    form when the outcome is ``AMBIGUOUS`` (surface the ambiguity instead
    of guessing), and ``None`` otherwise.
    """
    if not candidates:
        return Status.INVALID, None, (_evidence("unrecognized_format"),), None
    if not survivors:
        reason = drop_reasons[0] if drop_reasons else "grammar_rejected"
        return Status.INVALID, None, (_evidence(reason),), None
    if len(survivors) == 1:
        s = survivors[0]
        return Status.CANONICALIZED, s.value, s.evidence, None
    # >1 survivor -> AMBIGUOUS (Don't Guess). Structurally present for
    # architecture parity with email; UUID never reaches this branch.
    merged: list[Evidence] = []
    for survivor in survivors:
        for ev in survivor.evidence:
            if ev not in merged:
                merged.append(ev)
    merged.append(_evidence("ambiguous_provider_equivalence"))
    return (
        Status.AMBIGUOUS,
        None,
        tuple(merged),
        tuple(sorted({s.value for s in survivors})),
    )


class UUIDCapability:
    """A pure deterministic transformation that canonicalizes UUIDs.

    The capability accepts only the RFC 4122 §3 canonical form (36
    lowercase hex chars, 8-4-4-4-12). Inputs in any other form
    (32-hex without hyphens, braced, URN, uppercase, with extra
    whitespace) are `Status.INVALID` with an `unrecognized_format` rule.

    Law 14 enforcement: every `Evidence` returned by `canonicalize`
    pulls its `provenance` from `_RULE_PROVENANCE` via the `_evidence`
    helper. Adding a new rule requires adding to the manifest; the
    manifest lookup will raise `KeyError` if a rule is constructed
    without one.
    """

    name: str = "uuid_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalUUIDContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        # Defensive type-check (mirrors email's pattern).
        if not isinstance(contract, CanonicalUUIDContract):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_uuid_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )

        # Step 1 (Layer 1): recognition. UUID does NOT strip whitespace —
        # leading/trailing whitespace is rejected (current behaviour).
        reps = recognize(value, contract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("unrecognized_format"),),
            )

        # Step 2: resolver + validation + classify.
        cands = generate_interpretations(reps, contract)
        survs, drops = resolve_and_validate(cands, contract)
        status, rendered, evidence, cands_out = classify(cands, survs, drops)
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )
