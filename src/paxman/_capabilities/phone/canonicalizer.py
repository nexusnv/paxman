# src/paxman/_capabilities/phone/canonicalizer.py
"""Phone canonicalizer: resolver + validator + classifier (Layer 2/3/4).

recognition (grammar.py) -> generate_interpretations (resolver) ->
resolve_and_validate (validator) -> classify.
"""

from __future__ import annotations

import re

import attrs

from paxman._capabilities.phone.contract import CanonicalPhoneContract
from paxman._capabilities.phone.grammar import RecognizedRep, recognize
from paxman._capabilities.phone.parser import _cc_for_country
from paxman._capabilities.phone.rules import _evidence
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# Strip everything that is not a digit when expanding a national number.
_NON_DIGIT = re.compile(r"\D")


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a phone-shaped input.

    ``value`` is the fully-reconstructed candidate E.164 string. ``rule`` /
    ``source`` carry the originating grammar's id and Law-14 provenance.
    ``evidence`` is the tuple of ``Evidence`` accumulated for the
    transformations that produced this candidate.
    """

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    """A candidate that survived validation: a concrete valid E.164 number."""

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


def generate_interpretations(
    reps: list[RecognizedRep], contract: CanonicalPhoneContract
) -> list[_Candidate]:
    """Map grammar recognitions to candidate canonical forms (resolver).

    Assigns meaning to the raw captures produced by
    :func:`grammar.recognize` and enumerates every candidate E.164 form the
    declared `country` policy permits.
    """
    cc = _cc_for_country(contract.country)
    candidates: list[_Candidate] = []
    for rep in reps:
        if rep.grammar_id == "e164":
            # Already global; reassemble (idempotent — reproduces input).
            # ``cc_first`` is only the first digit of the country code; the
            # remaining digits live in ``national``. Reassembling reproduces
            # the original E.164 string byte-for-byte.
            candidates.append(
                _Candidate(
                    f"+{rep.captures['cc_first']}{rep.captures['national']}",
                    "e164",
                    rep.source,
                    (_evidence("no_transformation_needed"),),
                )
            )
        else:
            # national or digits_only: strip separators, prepend declared cc.
            national = _NON_DIGIT.sub("", rep.captures["national"])
            candidates.append(
                _Candidate(
                    f"+{cc}{national}",
                    rep.grammar_id,
                    rep.source,
                    (_evidence("cc_prepended"),),
                )
            )
    return candidates


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalPhoneContract
) -> tuple[list[_Survivor], list[str]]:
    """Validate each candidate against the E.164 global shape rule.

    Drops candidates that name no valid global number (RFC 3966 §3 /
    ITU-T E.164: total digits 1-15, country code first digit 1-9, national
    part non-empty).
    """
    survivors: list[_Survivor] = []
    drop_reasons: list[str] = []
    for c in candidates:
        body = c.value[1:]  # strip leading '+'
        if not body or not body.isascii() or not body.isdigit():
            drop_reasons.append("grammar_rejected")
            continue
        if len(body) > 15:
            drop_reasons.append("grammar_rejected")
            continue
        if body[0] == "0":  # leading-zero country code is invalid
            drop_reasons.append("grammar_rejected")
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
    form when the outcome is ``AMBIGUOUS`` (surface the ambiguity instead of
    guessing), and ``None`` otherwise.

    Note: for phone the three grammars are mutually exclusive by construction
    (``e164`` requires a leading ``+``; ``national`` requires at least one
    separator; ``digits_only`` requires no separator), so recognition yields
    at most one ``RecognizedRep`` and therefore at most one canonical
    survivor. The ``AMBIGUOUS`` branch is thus unreachable through the real
    pipeline for v1 and is retained defensively for parity with the other
    capabilities. Paxman never guesses between competing forms.
    """
    seen: set[str] = set()
    unique: list[_Survivor] = []
    for survivor in survivors:
        if survivor.value not in seen:
            seen.add(survivor.value)
            unique.append(survivor)
    survivors = unique

    if not candidates:
        return Status.INVALID, None, (_evidence("unrecognized_format"),), None
    if not survivors:
        return Status.INVALID, None, (_evidence("grammar_rejected"),), None
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


class PhoneCapability:
    """A pure deterministic transformation that canonicalizes phone numbers.

    ``Capability`` (from ``paxman._capabilities.protocol``) is a structural
    Protocol — this class satisfies it by virtue of its ``name`` attribute
    and the ``can_handle`` / ``canonicalize`` methods, not by inheritance.

    Law 14 enforcement: every ``Evidence`` returned by ``canonicalize`` pulls
    its ``authority`` from ``_RULE_AUTHORITIES`` via the ``_evidence`` helper.
    """

    name: str = "phone_canonicalization"

    def can_handle(self, contract: object, value: object) -> bool:
        return isinstance(contract, CanonicalPhoneContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: object) -> CapabilityResult:
        if not isinstance(contract, CanonicalPhoneContract):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_phone_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )

        reps = recognize(value, contract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("unrecognized_format"),),
            )

        cands = generate_interpretations(reps, contract)
        survs, _drops = resolve_and_validate(cands, contract)
        status, rendered, evidence, cands_out = classify(cands, survs, _drops)
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )
