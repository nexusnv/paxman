# src/paxman/_capabilities/country/canonicalizer.py
"""CountryCapability: a built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14. Architecture (recognition -> resolver ->
validation -> classify), mirroring the ip/money/boolean capabilities.
Recognition is delegated to grammar.py; the resolver looks the token up in the
bundled, versioned ISO 3166-1 table (Law 8a).
"""

from __future__ import annotations

import attrs

from paxman._capabilities.country.contract import (
    _ALPHA2_CODES,
    _ALPHA3_TO_ALPHA2,
    _HISTORICAL_TO_ALPHA2,
    _LOCALIZED_TO_ALPHA2,
    _NAME_TO_ALPHA2,
    _NUMERIC_TO_ALPHA2,
    _SYNONYM_TO_ALPHA2,
    CLDR_VERSION,
    COUNTRY_TABLE_VERSION,
    CanonicalCountryContract,
)
from paxman._capabilities.country.grammar import RecognizedRep, recognize
from paxman._capabilities.country.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a country-shaped input."""

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    """A candidate that survived policy validation: a concrete canonical form."""

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


def generate_interpretations(
    reps: list[RecognizedRep], contract: CanonicalCountryContract
) -> list[_Candidate]:
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
    """
    candidates: list[_Candidate] = []
    rep = reps[0]
    token = rep.captures.get("tok", rep.raw).strip().upper()
    if rep.shape == "alpha2" and token in _ALPHA2_CODES:
        candidates.append(_mk(token, "canonicalized_country", "ISO 3166-1:2020 (alpha-2)"))
    elif rep.shape == "alpha3":
        if not contract.allow_alpha3:
            return []
        code = _ALPHA3_TO_ALPHA2.get(token)
        if code is not None:
            candidates.append(
                _mk(code, "canonicalized_country", "ISO 3166-1:2020 (alpha-3->alpha-2)")
            )
    elif rep.shape == "numeric":
        if not contract.allow_numeric:
            return []
        # Numeric codes are zero-padded to 3 digits in the table; also accept
        # the unpadded form (e.g. "4" -> "004").
        code = _NUMERIC_TO_ALPHA2.get(token.zfill(3))
        if code is not None:
            candidates.append(_mk(code, "numeric_resolved", "ISO 3166-1:2020 (numeric->alpha-2)"))
    # Synonym / name / extra-synonym / localized / historical fallback for
    # tokens that are not valid codes of their own shape (e.g. UK, U.S.A.,
    # America, 马来西亚, Burma).
    if contract.allow_synonym:
        code = _SYNONYM_TO_ALPHA2.get(token)
        if code is not None:
            candidates.append(
                _mk(code, "alias_resolved", f"paxman spec/country §3.3 ({COUNTRY_TABLE_VERSION})")
            )
    if contract.allow_name:
        code = _NAME_TO_ALPHA2.get(token)
        if code is not None:
            candidates.append(_mk(code, "canonicalized_country", "ISO 3166-1:2020 (name->alpha-2)"))
    if contract.localized_names:
        code = _LOCALIZED_TO_ALPHA2.get(rep.captures.get("tok", rep.raw).strip())
        if code is not None:
            candidates.append(_mk(code, "localized_resolved", f"Unicode CLDR ({CLDR_VERSION})"))
    if contract.historical_names:
        code = _HISTORICAL_TO_ALPHA2.get(token)
        if code is not None:
            candidates.append(
                _mk(code, "historical_resolved", "paxman policy/country: historical name map")
            )
    extra = contract.extra_synonyms.get(token.lower())
    if extra is not None:
        candidates.append(
            _mk(extra, "extra_synonym_resolved", "paxman spec/country §1.2 (extra_synonyms)")
        )
    # Collapse candidates that resolve to the same alpha-2 code. Two distinct
    # paths (e.g. alpha-3 `USA` and the bundled synonym `USA`) naming the same
    # country are one canonical answer, not ambiguity (spec §2.2 — intra-
    # capability ambiguity does not occur).
    seen: dict[str, _Candidate] = {}
    for cand in candidates:
        if cand.value in seen:
            continue
        seen[cand.value] = cand
    return list(seen.values())


def _mk(value: str, rule: str, source: str) -> _Candidate:
    return _Candidate(value=value, rule=rule, source=source, evidence=(_evidence(rule, value),))


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
        survivors.append(_Survivor(c.value, c.rule, c.source, c.evidence))
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


class CountryCapability:
    """A pure deterministic transformation that canonicalizes countries."""

    name: str = "country_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalCountryContract) and (
            value is None or isinstance(value, str)
        )

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        if not isinstance(contract, CanonicalCountryContract):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_country_contract"),)
            )
        if not (value is None or isinstance(value, str)):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_string_value"),)
            )

        # Missing value -> MISSING (spec §3.5).
        if value is None or value.strip(" \t\r\n\f\v") == "":
            return CapabilityResult(status=Status.MISSING, evidence=(_evidence("missing_value"),))

        # Trim leading/trailing ASCII whitespace (record if changed).
        stripped_evidence: tuple[Evidence, ...] = ()
        stripped = value.strip(" \t\r\n\f\v")
        if stripped != value:
            stripped_evidence = (_evidence("trimmed_whitespace"),)
            value = stripped

        # Recognition layer (Layer 1) — shape classification only.
        reps = recognize(value, contract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format"),)
            )

        # Resolver (table lookup) + validation + classify.
        cands = generate_interpretations(reps, contract)
        if not cands:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format"),)
            )
        survs, drops = resolve_and_validate(cands, contract)
        status, rendered, evidence, cands_out = classify(cands, survs, drops)
        if stripped_evidence:
            evidence = stripped_evidence + evidence
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )
