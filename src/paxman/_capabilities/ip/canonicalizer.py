# src/paxman/_capabilities/ip/canonicalizer.py
"""IPCapability: a built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14.
Architecture (recognition → resolver → validation → classify), mirroring
the email/date/boolean capabilities. Recognition is delegated to the stdlib
`ipaddress` module, which is the deterministic authority for parse + canonical
form (RFC 4291 / RFC 5952 / RFC 4007).
"""

from __future__ import annotations

import ipaddress

import attrs

from paxman._capabilities.ip.contract import CanonicalIPContract
from paxman._capabilities.ip.grammar import RecognizedRep, recognize
from paxman._capabilities.ip.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


@attrs.frozen
class _Candidate:
    """A single enumerated reading of an IP-shaped input."""

    value: str
    family: str
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
    reps: list[RecognizedRep], contract: CanonicalIPContract
) -> list[_Candidate]:
    """Map grammar recognitions to candidate canonical forms (resolver).

    Delegates the actual parse + canonical formatting to the stdlib
    `ipaddress` module (RFC 4291 / RFC 5952 / RFC 4007). A malformed input
    raises `ipaddress.AddressValueError` here — caught by `canonicalize` and
    surfaced as `unrecognized_format` (INVALID), never guessed.
    """
    candidates: list[_Candidate] = []
    zone: str | None = reps[0].captures.get("zone")
    addr = reps[0].captures["addr"]
    is_zone = reps[0].shape == "ipv6_zone"
    try:
        if reps[0].shape == "ipv4":
            # The stdlib rejects leading zeros ("001"); strip them so an
            # equivalent dotted-decimal representation canonicalizes to the
            # same form (RFC 4291 §2.2 — no leading zeros in canonical text).
            normalized = ".".join(str(int(octet)) for octet in addr.split("."))
            parsed = ipaddress.IPv4Address(normalized)
            canonical = str(parsed)  # dotted-decimal, no leading zeros
            rule = "canonicalized_ipv4"
            source = "RFC 4291 §2.2"
        else:
            parsed = ipaddress.IPv6Address(addr)
            canonical = str(parsed)  # RFC 5952 lowercase compressed
            rule = "canonicalized_ipv6"
            source = "RFC 5952"
            if is_zone and zone is not None:
                if contract.preserve_zone_id:
                    canonical = f"{canonical}%{zone.lower()}"
                    rule = "canonicalized_ipv6_zone"
                    source = "RFC 4007 §11 + RFC 5952 §4.3"
                else:
                    # zone stripped by policy; canonical stays the bare addr
                    pass
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
        return []
    candidates.append(
        _Candidate(
            value=canonical,
            family=reps[0].shape,
            rule=rule,
            source=source,
            evidence=(_evidence(rule, f"{addr!r} -> {canonical!r}"),),
        )
    )
    return candidates


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalIPContract
) -> tuple[list[_Survivor], list[str]]:
    """Validate each candidate against the contract policy.

    An address family disabled by the contract's policy (ipv4 without
    allow_ipv4, or ipv6/ipv6_zone without allow_ipv6) is dropped with a
    `policy_disabled_family` reason.
    """
    survivors: list[_Survivor] = []
    drop_reasons: list[str] = []
    for c in candidates:
        is_ipv4 = c.family == "ipv4"
        is_ipv6 = c.family in ("ipv6", "ipv6_zone")
        if is_ipv4 and not contract.allow_ipv4:
            drop_reasons.append("policy_disabled_family")
            continue
        if is_ipv6 and not contract.allow_ipv6:
            drop_reasons.append("policy_disabled_family")
            continue
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
        if "policy_disabled_family" in drop_reasons:
            return Status.INVALID, None, (_evidence("policy_disabled_family"),), None
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


class IPCapability:
    """A pure deterministic transformation that canonicalizes IP addresses."""

    name: str = "ip_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalIPContract) and (
            value is None or isinstance(value, str)
        )

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        if not isinstance(contract, CanonicalIPContract):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_ip_contract"),)
            )
        if not (value is None or isinstance(value, str)):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_string_value"),)
            )

        # Missing value -> MISSING (spec §3.4).
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

        # Resolver (delegates to stdlib ipaddress) + validation + classify.
        cands = generate_interpretations(reps, contract)
        if not cands:
            # resolver rejected a malformed address (e.g. 999.1.1.1)
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
