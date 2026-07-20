"""EmailCapability: the first built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14:
- Law 4: rewrites known representations; does not interpret.
- Law 5: the contract declares the policy; the capability applies it.
- Law 7: the policy is explicit; no auto-detection.
- Law 8 + 8a: the capability is a pure function of (value, contract).
  No network, no time, no randomness, no filesystem.
- Law 11: the canonical form is a function of (value, contract). Two
  independent implementations must produce the same value.
- Law 14: every transformation rule has provenance. The rule→citation
  manifest is `_RULE_AUTHORITIES`; `Evidence.authority` is populated
  from it.

Architecture (recognition → resolver → validation → classify)
------------------------------------------------------------
The capability is split into four deterministic stages, mirroring the
date capability:

1. ``grammar.recognize`` (Layer 1) maps the raw input to the set of
   grammar shapes it could name, producing only RAW string captures.
2. ``generate_interpretations`` (resolver) assigns meaning to those
   captures and enumerates candidate canonical forms (including gmail
   provider-equivalence).
3. ``resolve_and_validate`` validates each candidate against the
   RFC 5322 §3.2.3 dot-atom local part and RFC 5321 §3.4 + RFC 1035
   §2.3.1 dot-atom domain grammar, dropping those that name no valid
   mailbox.
4. ``classify`` maps the surviving candidates to a canonicalization
   outcome (CANONICALIZED / AMBIGUOUS / INVALID), never guessing.

Surface-grammar gate
--------------------
Pre-Law 14, the capability silently accepted any string with one `@`
and non-empty local+domain parts as `CANONICALIZED`. The user-experiment
report (2026-07-14) surfaced this as silent canonical-form invention for
malformed inputs like `user@example.com@example.com`,
`user@-domain.com`, `user@[127.0.0.300]`.

Post-Law 14, the capability gate-checks the local part against RFC 5322
§3.2.3 `dot-atom` and the domain against RFC 5321 §3.4 + RFC 1035
§2.3.1. Inputs that fail the gate return `Status.INVALID` with a
`grammar_rejected` evidence rule. Quoted-string local parts
(`RFC 5322 §3.2.4`) and bracketed domain literals
(`RFC 5321 §3.4.1 IPv4 / §3.4.2 IPv6`) are out of v2.0.0 scope and
fail this gate; v2.x may extend the gate to admit them.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import attrs

from paxman._capabilities._shared.base import CapabilityBase
from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.email.grammar import recognize
from paxman._capabilities.email.parser import _validate_dot_atom_domain, _validate_dot_atom_local
from paxman._capabilities.email.rules import _evidence
from paxman._core.classification import ValidationResult
from paxman._core.contracts import Contract
from paxman._core.engine_env import Engine
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

_GMAIL_SUFFIX = "gmail.com"


@attrs.frozen
class _Candidate:
    """A single enumerated reading of an email-shaped input.

    ``value`` is the fully-reconstructed candidate mailbox
    (``local@domain``). ``rule`` / ``source`` carry the originating
    grammar's id and Law-14 provenance. ``evidence`` is the tuple of
    ``Evidence`` accumulated for the transformations that produced this
    candidate (lowercasing, provider-equivalence, etc.).
    """

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    """A candidate that survived validation: a concrete valid mailbox."""

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


def _is_gmail_family(domain: str) -> bool:
    """True when ``domain`` is a Gmail-family domain (case-insensitive).

    Covers only the exact ``gmail.com`` / ``googlemail.com`` domains.
    Tenant subdomains such as ``foo.gmail.com`` are distinct identities and
    must not be collapsed into ``gmail.com`` (Identity invariant).
    """
    d = domain.lower()
    return d == _GMAIL_SUFFIX or d == "googlemail.com"


def _lowercase_evidence(
    local: str, domain: str, contract: CanonicalEmailContract
) -> tuple[str, str, tuple[Evidence, ...]]:
    """Apply the contract's lowercase policy, returning the lowercased
    local/domain plus any accumulated evidence.
    """
    if not contract.lowercase:
        return local, domain, ()
    new_local = local.lower()
    new_domain = domain.lower()
    ev: tuple[Evidence, ...] = ()
    if new_local != local:
        ev = (*ev, _evidence("lowercased_local_part"))
    if new_domain != domain:
        ev = (*ev, _evidence("lowercased_domain"))
    return new_local, new_domain, ev


def provider_equivalence(
    local: str,
    domain: str,
    contract: CanonicalEmailContract,
    base_evidence: tuple[Evidence, ...],
    rule: str,
    source: str,
) -> list[_Candidate]:
    """Enumerate provider-equivalence candidates for a (local, domain) pair.

    For Gmail-family domains, the contract's ``provider_aliases`` policy
    decides whether to emit only the Gmail-canonical form (``"gmail"``) or
    both the literal form and the Gmail-canonical form (``"none"``).
    """
    if _is_gmail_family(domain):
        # Gmail treats dots in the local part as equivalent (john.doe ==
        # johndoe), but only for a VALID dotted local. A dot-invalid local
        # (leading/trailing/consecutive dots) is not a real Gmail address, so
        # we must not repair it into one -- the literal candidate fails the
        # dot-atom gate and the input is rejected (Identity: canonicalize
        # only, never guess or normalize).
        if not _validate_dot_atom_local(local):
            return [_Candidate(f"{local}@{domain}", rule, source, base_evidence)]
        gmail_local = local.replace(".", "")
        dot_ev = (_evidence("stripped_dots_in_local_part"),) if "." in local else ()
        if "+" in gmail_local:
            gmail_local = gmail_local.split("+", 1)[0]
            tag_ev: tuple[Evidence, ...] = (_evidence("stripped_plus_tag"),)
        else:
            tag_ev = ()
        gmail_domain = _GMAIL_SUFFIX
        syn_ev = (_evidence("domain_synonym_gmail"),) if domain != gmail_domain else ()
        if contract.provider_aliases == "gmail":
            return [
                _Candidate(
                    f"{gmail_local}@{gmail_domain}",
                    rule,
                    source,
                    base_evidence + syn_ev + dot_ev + tag_ev,
                )
            ]
        if contract.provider_aliases == "none":
            return [
                _Candidate(f"{local}@{domain}", rule, source, base_evidence),
                _Candidate(
                    f"{gmail_local}@{gmail_domain}",
                    rule,
                    source,
                    base_evidence + syn_ev + dot_ev + tag_ev,
                ),
            ]
    return [_Candidate(f"{local}@{domain}", rule, source, base_evidence)]


def generate_interpretations(
    reps: Sequence[object], contract: CanonicalEmailContract
) -> list[_Candidate]:
    """Map grammar recognitions to candidate canonical forms (resolver).

    Assigns meaning to the raw captures produced by
    :func:`grammar.recognize` and enumerates every candidate mailbox the
    declared policies permit (including Gmail provider-equivalence).
    """
    from paxman._capabilities.email.grammar import RecognizedRep

    candidates: list[_Candidate] = []
    for rep in reps:
        assert isinstance(rep, RecognizedRep)
        gid = rep.grammar_id
        if gid == "addr_spec":
            local = rep.captures["local"]
            domain = rep.captures["domain"]
            local, domain, ev = _lowercase_evidence(local, domain, contract)
            candidates.extend(
                provider_equivalence(local, domain, contract, ev, "addr_spec", rep.source)
            )
        elif gid == "ws_padded_addr_spec":
            local = rep.captures["local"]
            domain = rep.captures["domain"]
            if contract.strip_whitespace:
                raw = f"{local}@{domain}"
                collapsed = re.sub(r"[ \t\r\n\f\v]*([@.])[ \t\r\n\f\v]*", r"\1", raw)
                ws_ev: tuple[Evidence, ...] = ()
                if collapsed != raw:
                    ws_ev = (_evidence("collapsed_internal_whitespace"),)
                local, _, domain = collapsed.partition("@")
                local, domain, lower_ev = _lowercase_evidence(local, domain, contract)
                ws_ev = (*ws_ev, *lower_ev)
                candidates.extend(
                    provider_equivalence(
                        local, domain, contract, ws_ev, "ws_padded_addr_spec", rep.source
                    )
                )
            else:
                # Leave internal whitespace; the candidate will fail the
                # dot-atom gate in resolve_and_validate and be dropped.
                local, domain, ev = _lowercase_evidence(local, domain, contract)
                candidates.extend(
                    provider_equivalence(
                        local, domain, contract, ev, "ws_padded_addr_spec", rep.source
                    )
                )
        elif gid == "verbal_at_dot_addr_spec":
            local = rep.captures["local"]
            mid = rep.captures["mid"]
            tld = rep.captures["tld"]
            reconstructed = f"{local}@{mid}.{tld}"
            ev = (_evidence("deobfuscated_verbal_at_dot"),)
            local, domain, lower_ev = _lowercase_evidence(
                *reconstructed.partition("@")[0::2], contract
            )
            ev = (*ev, *lower_ev)
            candidates.extend(
                provider_equivalence(
                    local, domain, contract, ev, "verbal_at_dot_addr_spec", rep.source
                )
            )
        elif gid == "quoted_local_addr_spec":
            # RFC 5322 §3.2.4 quoted-string local parts are out of v2.0.0 scope:
            # we recognise the shape (Layer 1) but assign no meaning. Keep the
            # raw quoted value so it fails the dot-atom atext gate in
            # resolve_and_validate and is rejected with grammar_rejected,
            # rather than silently lowercasing an out-of-scope form into a hit.
            value = f"{rep.captures['local']}@{rep.captures['domain']}"
            candidates.append(_Candidate(value, "quoted_local_addr_spec", rep.source, ()))
    return candidates


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalEmailContract
) -> tuple[list[_Survivor], list[str]]:
    """Validate each candidate; drop those that name no valid mailbox."""
    survivors: list[_Survivor] = []
    drop_reasons: list[str] = []
    for c in candidates:
        local, _, domain = c.value.partition("@")
        if not _validate_dot_atom_local(local) or not _validate_dot_atom_domain(domain):
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
    form when the outcome is ``AMBIGUOUS`` (surface the ambiguity instead
    of guessing), and ``None`` otherwise.
    """
    # Collapse survivors that resolve to the same canonical string so
    # identical readings do not masquerade as AMBIGUOUS (spec §2.4 — surface
    # ambiguity only when readings genuinely differ).
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
    # >1 survivor -> AMBIGUOUS (Don't Guess). Surface every candidate and
    # the union of each survivor's derivation evidence, then mark the
    # ambiguity itself.
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


class EmailCapability(CapabilityBase):
    """A pure deterministic transformation that canonicalizes emails.

    `Capability` (from `paxman._capabilities.protocol`) is a structural
    Protocol — this class satisfies it by virtue of its `name` attribute
    and the `can_handle` / `canonicalize` methods, not by inheritance.

    Law 14 enforcement: every `Evidence` returned by `canonicalize`
    pulls its `authority` from `_RULE_AUTHORITIES` via the `_evidence`
    helper. Adding a new rule requires adding to the manifest; the
    manifest lookup will raise `KeyError` if a rule is constructed
    without one.
    """

    name: str = "email_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(
        self, value: object, contract: Contract, engine: Engine | None = None
    ) -> CapabilityResult:
        if not isinstance(contract, CanonicalEmailContract):
            # Structural typecheck: a non-email contract must not reach
            # this capability. Return INVALID as a defensive default;
            # the orchestrator maps it through classification.
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_an_email_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )

        # Strict-mode grammar check happens FIRST so a non-grammar input
        # is rejected before any rewriting (no partial canonicalization).
        if contract.strict:
            if re.search(r"\s", value):
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("strict_rejected_whitespace"),),
                )
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("strict_rejected_non_ascii"),),
                )

        # Step 1 (spec §1.3): strip leading/trailing ASCII whitespace only.
        # Unicode whitespace (e.g. non-breaking space) is intentionally left
        # intact so canonicalization stays deterministic across Python
        # versions and RFC-correct.
        stripped_evidence: tuple[Evidence, ...] = ()
        if contract.strip_whitespace:
            stripped = value.strip(" \t\r\n\f\v")
            if stripped != value:
                stripped_evidence = (_evidence("stripped_whitespace"),)
                value = stripped

        # Step 2: require an '@' with non-empty local and domain parts.
        if "@" in value:
            local, _, domain = value.partition("@")
            if not local or not domain:
                return CapabilityResult(
                    status=Status.INVALID, evidence=(_evidence("empty_local_or_domain"),)
                )

        # Step 3: recognition layer (Layer 1).
        reps = recognize(value, contract)
        if not reps:
            if "@" not in value:
                return CapabilityResult(
                    status=Status.INVALID, evidence=(_evidence("missing_at_sign"),)
                )
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format"),)
            )

        # Step 4: resolver + validation + classify.
        cands = generate_interpretations(reps, contract)
        survs, drops = resolve_and_validate(cands, contract)
        status, rendered, evidence, cands_out = classify(cands, survs, drops)
        if stripped_evidence:
            evidence = stripped_evidence + evidence
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )

    def validate(self, value: str, contract: object) -> ValidationResult:
        """Post-canonicalization policy check (Law 4) for emails.

        The canonical form has already been lowercased, stripped, and
        resolved, so this re-checks only the structural invariants that no
        valid mailbox may violate: a single ``@`` with non-empty local and
        domain parts, and (under ``strict``) ASCII-only with no internal
        whitespace. Inputs that reach here already passed the dot-atom gate
        in :func:`resolve_and_validate`, so this is a narrow policy guard
        restored from the email contract validation removed in Task 1.

        Args:
            value: The canonicalized email string (post-canonicalize).
            contract: A ``CanonicalEmailContract`` declaring the policy.

        Returns:
            A ``ValidationResult`` marking the value valid or invalid.
        """
        if "@" not in value:
            return ValidationResult(is_valid=False)
        local, _, domain = value.partition("@")
        if not local or not domain:
            return ValidationResult(is_valid=False)
        if isinstance(contract, CanonicalEmailContract) and contract.strict:
            if " " in local or " " in domain:
                return ValidationResult(is_valid=False)
            try:
                local.encode("ascii")
                domain.encode("ascii")
            except UnicodeEncodeError:
                return ValidationResult(is_valid=False)
        return ValidationResult(is_valid=True)
