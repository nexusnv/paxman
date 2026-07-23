# src/paxman/_capabilities/country/canonicalizer.py
"""CountryCapability: a built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14. Architecture (recognition -> resolver ->
validation -> classify), mirroring the ip/money/boolean capabilities.
Recognition is delegated to grammar.py; the resolver looks the token up in the
bundled, versioned ISO 3166-1 table (Law 8a).
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
from paxman._capabilities.country.contract import (
    _ALPHA2_CODES,
    _ALPHA3_TO_ALPHA2,
    _HISTORICAL_TO_ALPHA2,
    _LOCALIZED_TO_ALPHA2,
    _NAME_TO_ALPHA2,
    _NUMERIC_TO_ALPHA2,
    _SYNONYM_TO_ALPHA2,
    CanonicalCountryContract,
)
from paxman._capabilities.country.grammar import RecognizedRep, recognize
from paxman._capabilities.country.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.engine_env import Engine
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# Case-folded index over the CLDR localized table. CLDR keys mix scripts and
# cases (e.g. "États-Unis", "Deutschland", "Россия", "日本"); case folding makes
# the Latin-script entries case-insensitive without disturbing non-Latin
# scripts (casefold is a no-op for Cyrillic/Han). Built once at import so the
# lookup stays deterministic (Law 1). Wrapped in MappingProxyType for runtime
# immutability (Law 1 + Law 2 — replay-affecting bundled state).
_LOCALIZED_CASEFOLDED: Mapping[str, str] = MappingProxyType(
    {key.casefold(): code for key, code in _LOCALIZED_TO_ALPHA2.items()}
)


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a country-shaped input."""

    value: str
    rule: str
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    """A candidate that survived policy validation: a concrete canonical form."""

    value: str
    rule: str
    evidence: tuple[Evidence, ...]


def generate_interpretations(
    reps: list[RecognizedRep],
    contract: CanonicalCountryContract,
    engine: Engine | None = None,
) -> tuple[list[_Candidate], list[str]]:
    """Map grammar recognitions to candidate canonical forms (resolver).

    Looks the (uppercased) token up in the bundled ISO 3166-1 table, applying
    the declared contract policies. A token that matches a shape but is not a
    known country representation yields no candidate (rejected as INVALID,
    never guessed).

    Policy gating is checked at the shape level (spec §3.5): an alpha-3 token
    with `allow_alpha3=False` is rejected outright, even if the same string
    also appears as a bundled synonym (e.g. `USA`). Synonym/name lookup is a
    fallback for tokens that are not valid codes of their own shape (e.g. `UK`,
    a 2-letter synonym that is not a valid ISO alpha-2 code).

    Returns:
        A (candidates, drop_reasons) tuple. When a representation kind was
        recognized but rejected by policy, drop_reasons contains
        ``"policy_disabled_kind"`` so the caller can emit the documented
        ``policy_disabled_kind`` evidence instead of the misleading
        ``unrecognized_format``.
    """
    candidates: list[_Candidate] = []
    drop_reasons: list[str] = []
    if not reps:
        return candidates, drop_reasons
    rep = reps[0]
    token = rep.captures.get("tok", rep.raw).strip().upper()
    if rep.shape == "alpha2" and token in _ALPHA2_CODES:
        candidates.append(_mk(token, "canonicalized_country", engine))
    elif rep.shape == "alpha3":
        if not contract.allow_alpha3:
            drop_reasons.append("policy_disabled_kind")
            return candidates, drop_reasons
        code = _ALPHA3_TO_ALPHA2.get(token)
        if code is not None:
            candidates.append(_mk(code, "canonicalized_country", engine))
    elif rep.shape == "numeric":
        if not contract.allow_numeric:
            drop_reasons.append("policy_disabled_kind")
            return candidates, drop_reasons
        # Numeric codes are zero-padded to 3 digits in the table; also accept
        # the unpadded form (e.g. "4" -> "004").
        code = _NUMERIC_TO_ALPHA2.get(token.zfill(3))
        if code is not None:
            candidates.append(_mk(code, "numeric_resolved", engine))
    # Synonym / name / extra-synonym / localized / historical fallback for
    # tokens that are not valid codes of their own shape (e.g. UK, U.S.A.,
    # America, 马来西亚, Burma). When a table match exists but the contract
    # disables that representation kind, record a policy_disabled_kind drop
    # reason so the caller emits the documented policy-disabled evidence
    # instead of the misleading unrecognized_format.
    synonym_code = _SYNONYM_TO_ALPHA2.get(token)
    if synonym_code is not None:
        if contract.allow_synonym:
            candidates.append(_mk(synonym_code, "alias_resolved", engine))
        else:
            drop_reasons.append("policy_disabled_kind")

    name_code = _NAME_TO_ALPHA2.get(token)
    if name_code is not None:
        if contract.allow_name:
            candidates.append(_mk(name_code, "canonicalized_country", engine))
        else:
            drop_reasons.append("policy_disabled_kind")

    if contract.localized_names:
        raw = rep.captures.get("tok", rep.raw).strip()
        code = _LOCALIZED_CASEFOLDED.get(raw.casefold())
        if code is not None:
            candidates.append(_mk(code, "localized_resolved", engine))
    if contract.historical_names:
        code = _HISTORICAL_TO_ALPHA2.get(token)
        if code is not None:
            candidates.append(_mk(code, "historical_resolved", engine))
    extra = contract.extra_synonyms.get(token.lower())
    if extra is not None:
        candidates.append(_mk(extra, "extra_synonym_resolved", engine))
    # Collapse candidates that resolve to the same alpha-2 code. Two distinct
    # paths (e.g. alpha-3 `USA` and the bundled synonym `USA`) naming the same
    # country are one canonical answer, not ambiguity (spec §2.2 — intra-
    # capability ambiguity does not occur).
    seen: dict[str, _Candidate] = {}
    for cand in candidates:
        if cand.value in seen:
            continue
        seen[cand.value] = cand
    return list(seen.values()), drop_reasons


def _mk(value: str, rule: str, engine: Engine | None = None) -> _Candidate:
    return _Candidate(value=value, rule=rule, evidence=(_evidence(rule, value, engine),))


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalCountryContract
) -> tuple[list[_Survivor], list[str]]:
    """Validate each candidate against the contract policy.

    A representation kind disabled by policy is dropped with a
    `policy_disabled_kind` reason. (Kind-gating for alpha3/name/synonym is
    already enforced inside the resolver; this stage is the deterministic
    re-check and the survivor collector.)
    """
    survivors: list[_Survivor] = []
    drop_reasons: list[str] = []
    for c in candidates:
        survivors.append(_Survivor(c.value, c.rule, c.evidence))
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
        return Status.INVALID, None, (_evidence("unrecognized_format"),), None
    if not survivors:
        if "policy_disabled_kind" in drop_reasons:
            return Status.INVALID, None, (_evidence("policy_disabled_kind"),), None
        return Status.INVALID, None, (_evidence("unrecognized_format"),), None
    if len(survivors) == 1:
        s = survivors[0]
        return Status.CANONICALIZED, s.value, s.evidence, None
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


class CountryCapability(CapabilityBase):
    """A pure deterministic transformation that canonicalizes countries."""

    name: str = "country_canonicalization"

    can_handle: CanHandle = make_can_handle(CanonicalCountryContract, accept_none=True)

    def canonicalize(
        self, value: object, contract: Contract, engine: Engine | None = None
    ) -> CapabilityResult:

        def _ev(rule: str) -> object:
            return _evidence(rule, engine=engine)

        r = reject_contract(contract, CanonicalCountryContract, _ev, "not_a_country_contract")
        if r is not None:
            return r
        r = reject_non_string(value, _ev)
        if r is not None:
            return r
        assert isinstance(contract, CanonicalCountryContract)

        # Missing value -> MISSING (spec §3.5).
        r = reject_missing(value, _ev, "missing_value")
        if r is not None:
            return r
        assert isinstance(value, str)

        # Trim leading/trailing ASCII whitespace (record if changed).
        stripped_evidence: tuple[Evidence, ...] = ()
        stripped = value.strip(" \t\r\n\f\v")
        if stripped != value:
            stripped_evidence = (_evidence("trimmed_whitespace", engine=engine),)
            value = stripped

        # Recognition layer (Layer 1) — shape classification only.
        reps = recognize(value, contract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format", engine=engine),)
            )

        # Resolver (table lookup) + validation + classify.
        cands, drop_reasons = generate_interpretations(reps, contract, engine)
        if not cands:
            # Distinguish policy-disabled from genuinely unrecognized: an
            # alpha-3/numeric token that was recognized but rejected by
            # contract policy emits ``policy_disabled_kind`` evidence (the
            # documented behavior), not the misleading
            # ``unrecognized_format``.
            if "policy_disabled_kind" in drop_reasons:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("policy_disabled_kind", engine=engine),),
                )
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format", engine=engine),)
            )
        survs, drops = resolve_and_validate(cands, contract)
        status, rendered, evidence, cands_out = classify(cands, survs, drops)
        if stripped_evidence:
            evidence = stripped_evidence + evidence
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )
