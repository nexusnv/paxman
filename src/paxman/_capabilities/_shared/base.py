"""Shared capability base (Finding A + D).

Every capability subclasses ``CapabilityBase`` so it inherits the uniform
post-canonicalization ``validate`` hook and a single import surface for the
``Capability`` Protocol. The orchestrator dispatches validation through the
resolved capability (``validation.validate`` -> ``capability.validate``), so
``_core`` never imports concrete contracts (goal 4: dependencies point
inward).

The ``canonicalize`` pipeline differs per domain (date does recognition
inside its resolver; money folds everything into ``canonicalize``; email
needs strict-mode pre-checks). Rather than force a single rigid skeleton
that would alter behavior (the over-abstraction trap in Finding D), each
domain implements ``can_handle`` / ``canonicalize`` directly and reuses the
shared ``_shared`` scaffolds (grammar, evidence, contract field). The
``engine`` parameter stays on the Protocol (uniformity is the scaling
mechanism — Finding C) and is threaded through, ignored by domains that do
not cite authorities.

Finding A (dispatch boilerplate extraction): the ``make_can_handle`` factory
and the ``reject_contract`` / ``reject_non_string`` / ``reject_missing``
helpers below centralise the duplicated ``can_handle`` predicate and the
top-of-``canonicalize`` dispatch guards every capability repeated. They are
pure refactors — they preserve the exact ``Status``, evidence rule names,
``CapabilityResult`` shapes, and ``replay_hash`` of the inline code they
replace.

Law 4: ``validate`` is a post-canonicalization policy check, never
interpretation. Default passes; the engine dispatches to it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias, cast

from paxman._core.classification import ValidationResult
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# Shared type for a capability's can_handle predicate. Declared with `Any`
# params (not `Contract`) because mypy erases a @runtime_checkable
# Protocol used as a Callable parameter type when the Callable is
# produced by a factory and checked against the Capability Protocol;
# `Any` keeps both sides of the conformance check identical.
CanHandle = Callable[[Any, Any], bool]

# Shared type for a capability's declared output formats. Each capability
# enumerates the output formats it can produce (e.g. alpha2, alpha3, numeric
# for country). The default is an empty frozenset; subclasses override with
# their specific formats.
OutputFormats: TypeAlias = frozenset[str]

# Whitespace characters stripped by the canonicalizers' missing-value check
# (ASCII whitespace only — Unicode whitespace is intentionally left intact so
# canonicalization stays deterministic across Python versions).
WS = " \t\r\n\f\v"


def make_can_handle(contract_cls: type, *, accept_none: bool = False) -> Callable[[Any, Any], bool]:
    """Return a ``can_handle(self, contract, value)`` method for ``contract_cls``.

    The returned predicate claims the (contract, value) pair exactly when the
    contract is an instance of ``contract_cls`` and the value is a string (or,
    when ``accept_none`` is True, also ``None`` — so a missing value routes to
    ``Status.MISSING`` rather than ``Status.UNSUPPORTED``).
    """

    def can_handle(contract: Contract, value: Any) -> bool:
        if accept_none:
            return isinstance(contract, contract_cls) and (value is None or isinstance(value, str))
        return isinstance(contract, contract_cls) and isinstance(value, str)

    return cast(CanHandle, staticmethod(can_handle))


def reject_contract(
    contract: object,
    expected_cls: type,
    _evidence_fn: Callable[[str], object],
    rule: str,
) -> CapabilityResult | None:
    """Return ``CapabilityResult(INVALID, evidence=(_evidence_fn(rule),))`` or ``None``.

    Returns a rejecting ``CapabilityResult`` when ``contract`` is not an
    instance of ``expected_cls``; otherwise ``None`` (caller proceeds). The
    ``_evidence_fn`` closure is supplied by the caller so each capability cites
    its own evidence manifest (and, where relevant, its engine).
    """
    if not isinstance(contract, expected_cls):
        return CapabilityResult(
            status=Status.INVALID, evidence=(cast(Evidence, _evidence_fn(rule)),)
        )
    return None


def reject_non_string(
    value: object,
    _evidence_fn: Callable[[str], object],
    rule: str = "not_a_string_value",
) -> CapabilityResult | None:
    """Return ``CapabilityResult(INVALID, ...)`` for non-string, non-None values, else ``None``.

    Mirrors the inline guard every capability used: a value that is neither
    ``None`` nor a ``str`` is not this capability's to claim, so it returns
    ``Status.INVALID`` with the given evidence rule.
    """
    if not (value is None or isinstance(value, str)):
        return CapabilityResult(
            status=Status.INVALID, evidence=(cast(Evidence, _evidence_fn(rule)),)
        )
    return None


def reject_missing(
    value: object,
    _evidence_fn: Callable[[str], object],
    rule: str = "missing_value",
) -> CapabilityResult | None:
    """Return ``CapabilityResult(MISSING, ...)`` for None/whitespace-only values, else ``None``.

    Preserves the original missing-value guard: ``None`` or a string that is
    empty after stripping ``WS`` is reported as ``Status.MISSING``.
    """
    if value is None or (isinstance(value, str) and value.strip(WS) == ""):
        return CapabilityResult(
            status=Status.MISSING, evidence=(cast(Evidence, _evidence_fn(rule)),)
        )
    return None


class CapabilityBase:
    """Base for capabilities: uniform ``validate`` hook + Protocol surface.

    Subclasses set ``name`` and implement ``can_handle`` / ``_canonicalize``
    (and optionally ``validate`` for contract-specific strictness policy).

    The ``canonicalize`` method is a **template method** — it calls
    ``_canonicalize`` (domain-specific logic) and then ``_apply_output_format``
    (format conversion). Capabilities override ``_canonicalize``; format
    conversion is enforced by the base class and cannot be forgotten.
    """

    name: str

    # Declared as a CanHandle attribute (a Callable, not a method) so that
    # subclasses overriding it with `can_handle: CanHandle = make_can_handle(...)`
    # type-match exactly against both this base and the Capability Protocol.
    # A Protocol method `def can_handle(self, contract, value)` is satisfied
    # by this Callable attribute shape (self is bound away at the call site).
    can_handle: CanHandle

    # The set of output formats this capability can produce. Subclasses
    # override with their specific formats (e.g. frozenset({"alpha2", "alpha3"})).
    # The default is empty; the contract's output_format field must be one
    # of these at canonicalization time (validated at contract construction).
    supported_output_formats: OutputFormats = frozenset()

    def canonicalize(
        self, value: Any, contract: Contract, engine: Any | None = None
    ) -> CapabilityResult:
        """Template method: delegate to ``_canonicalize``, then apply format conversion.

        Capabilities must override ``_canonicalize``, NOT this method.
        Format conversion is applied automatically and cannot be forgotten.
        """
        result = self._canonicalize(value, contract, engine)
        return self._apply_output_format(result, contract, engine)

    def _canonicalize(
        self, value: Any, contract: Contract, engine: Any | None = None
    ) -> CapabilityResult:  # pragma: no cover
        """Domain-specific canonicalization logic. Override this in subclasses."""
        raise NotImplementedError

    def _apply_output_format(
        self, result: CapabilityResult, contract: Contract, engine: Any | None = None
    ) -> CapabilityResult:
        """Apply the contract's output_format to a canonicalization result.

        Default: no-op (single-format capabilities don't need to override).
        Capabilities with multiple output formats (country, date) override
        this to convert CANONICALIZED values and AMBIGUOUS candidates.
        """
        return result

    def validate(self, value: str, contract: Contract) -> ValidationResult:
        """Post-canonicalization policy check (Law 4). Default: passes.

        Domains with strictness policy (e.g. email) override this. The
        orchestrator calls it after canonicalize; it must not interpret or
        guess (Law 4).
        """
        return ValidationResult(is_valid=True)
