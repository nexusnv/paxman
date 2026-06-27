"""Planner heuristic chain — the 7-step ordering per `ARCHITECTURE.md` §4.2.

Per `ADR-0002` (Rule-Based Planner), the planner evaluates a fixed
7-step heuristic chain in order:

1. **Explicit evidence** — input already contains the value
   (detected by inspecting the :class:`InputProfile`; per Oracle M7
   this is a *planner rule* on the profile, not a
   ``text_extraction`` capability invocation).
2. **Local deterministic extraction** — ``regex_extraction``,
   ``validation`` (and any other ``LOCAL_DETERMINISTIC``-tier
   capability).
3. **Structured lookup** — ``lookup`` (``STRUCTURED_LOOKUP`` tier).
4. **Derived computation** — formula over resolved fields (V2).
5. **Local inference** — ``inference`` with a local model
   (``LOCAL_INFERENCE`` tier).
6. **Remote inference** — ``inference`` with a remote provider
   (``REMOTE_INFERENCE`` tier).
7. ``UNRESOLVED`` — terminal; no capability selected.

This module exposes the **chain builder** + per-step selection
functions. The top-level :func:`paxman.planner.planner.plan` is
the entry point.

The chain is **deterministic**: for the same canonical contract,
input profile, budget, policy, and capability registry, the planner
emits the same plan. See ``docs/specs/capability-cost-model.md``
§5 for the determinism invariants.

V1 simplification
----------------

- **Step 1 (Explicit Evidence):** V1 implements this as a
  short-circuit: for ``STRING`` fields, the planner emits a
  single ``text_extraction`` step (the planner treats "the input
  already has the text" as a synonym for "we can pull it out via
  text_extraction") when the profile is non-empty and has density
  > 0.1. For non-``STRING`` fields, the planner short-circuits
  to ``True`` only if the input is text-shaped
  (``"text"``, ``"html"``, ``"pdf_text"``, ``"email"``); for
  binary / CSV / JSON inputs, the planner does NOT emit a
  ``text_extraction`` step (it would be wrong to assume the
  binary blob is the source).
- **Step 4 (Derived Computation):** V2 feature. V1 skips this step.
- **Step 5 (Local Inference):** V1 has no local-inference provider
  in the registry; this step is always empty unless the caller
  registers a custom one.

Policy-driven exclusions
------------------------

- If ``Policy.allow_remote_inference=False`` → step 6 is dropped.
- If ``Policy.allow_local_inference=False`` → step 5 is dropped.
- If ``Budget.max_total_cost_usd < 0.001`` → both steps 5 and 6
  are dropped (``inference``'s minimum USD cost is 0.001).
"""

from __future__ import annotations

import typing

from paxman.budget import Budget, Policy
from paxman.capabilities.registry import all_capabilities
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier
from paxman.contract.canonical import CanonicalField
from paxman.planner.field_plan import FieldPlan, FieldPlanStep
from paxman.planner.input_profile import InputProfile
from paxman.planner.policies import EffectivePolicy
from paxman.planner.scoring import score_capability

__all__ = [
    "build_capability_chain",
    "has_explicit_evidence",
    "select_local_deterministic",
    "select_local_inference",
    "select_remote_inference",
    "select_structured_lookup",
]


def has_explicit_evidence(
    field: CanonicalField,
    profile: InputProfile,
) -> bool:
    """Return ``True`` if the input already contains the field's value.

    Per the [Sprint 3 — Planner & capabilities](https://github.com/nexusnv/paxman/wiki/Internal-Development/Sprints/Sprint-03---Planner-and-capabilities) (Oracle M7) and ``ARCHITECTURE.md`` §4.2, "explicit evidence"
    in step 1 is a **planner rule** that inspects the
    :class:`InputProfile`. It does NOT require a
    ``text_extraction`` capability invocation.

    V1 implementation (two-tier rule):

    - For ``STRING`` fields, return ``True`` if the profile is
      non-empty and has density > 0.1. The planner emits a
      ``text_extraction`` step (V1's "the input is the source").
    - For non-``STRING`` fields (e.g., ``INTEGER``, ``MONEY``,
      ``DATE``), return ``True`` **only** if the profile's
      ``input_type`` is text-shaped (``"text"``, ``"html"``,
      ``"pdf_text"``, ``"email"``). The rationale: a non-string
      value is most reliably resolved by passing the text
      payload through a downstream capability; a binary /
      structured / CSV / JSON profile means the planner cannot
      identify "the input is the source" without running a
      capability, so the heuristic short-circuits to ``False``.

    Args:
        field: The :class:`CanonicalField`.
        profile: The :class:`InputProfile`.

    Returns:
        ``True`` if the planner can short-circuit step 1 with a
        ``text_extraction`` step, ``False`` otherwise.
    """
    from paxman.types import FieldType

    if profile.is_empty:
        return False
    if profile.density <= 0.1:
        return False
    if field.type in (FieldType.STRING,):
        return True
    # Non-STRING fields: only short-circuit if the input is text-shaped.
    if profile.input_type in ("html", "text", "pdf_text", "email"):
        return True
    return False


def _specs_by_tier(
    tier: CapabilityTier,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> list[CapabilitySpec]:
    """Return all registered capability specs in *tier*, sorted by score.

    Args:
        tier: The :class:`CapabilityTier` to filter by.
        registry: A mapping of ``(id, version)`` → capability. If
            ``None`` (default), uses the global
            :func:`all_capabilities`.

    Returns:
        A list of :class:`CapabilitySpec`, sorted by ascending
        :func:`score_capability`. Ties (identical score) are broken
        by ``capability_id`` lexicographic ascending (per
        ``docs/specs/capability-cost-model.md`` §7 EC5).
    """
    if registry is None:
        registry = all_capabilities()
    out: list[tuple[float, str, CapabilitySpec]] = []
    for _key, cap in registry.items():
        spec_obj = getattr(cap, "spec", None)
        if not isinstance(spec_obj, CapabilitySpec):
            continue
        if spec_obj.tier is tier:
            score = score_capability(spec_obj)
            out.append((score, spec_obj.id, spec_obj))
    out.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in out]


def select_local_deterministic(
    field: CanonicalField,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> list[FieldPlanStep]:
    """Step 2: local deterministic capabilities for *field*.

    Returns the list of :class:`FieldPlanStep` records for
    ``LOCAL_DETERMINISTIC``-tier capabilities that accept
    ``field.type`` as an input type. Empty if none.

    Args:
        field: The :class:`CanonicalField`.
        registry: Optional capability registry (defaults to global).

    Returns:
        A list of :class:`FieldPlanStep` records, sorted by
        ascending score (i.e., the cheapest first).
    """
    specs = _specs_by_tier(CapabilityTier.LOCAL_DETERMINISTIC, registry)
    out: list[FieldPlanStep] = []
    for spec in specs:
        if _accepts_field_type(spec, field):
            out.append(
                FieldPlanStep(
                    capability_id=spec.id,
                    capability_version=spec.version,
                    config={},
                    note=f"local-deterministic tier={spec.tier.value}",
                )
            )
    return out


def select_structured_lookup(
    field: CanonicalField,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> list[FieldPlanStep]:
    """Step 3: structured-lookup capabilities for *field*.

    Returns the list of :class:`FieldPlanStep` records for
    ``STRUCTURED_LOOKUP``-tier capabilities that accept
    ``field.type``. V1's ``lookup`` is in Sprint 4; this returns
    an empty list in V1.
    """
    specs = _specs_by_tier(CapabilityTier.STRUCTURED_LOOKUP, registry)
    out: list[FieldPlanStep] = []
    for spec in specs:
        if _accepts_field_type(spec, field):
            out.append(
                FieldPlanStep(
                    capability_id=spec.id,
                    capability_version=spec.version,
                    config={},
                    note=f"structured-lookup tier={spec.tier.value}",
                )
            )
    return out


def select_local_inference(
    field: CanonicalField,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> list[FieldPlanStep]:
    """Step 5: local-inference capabilities for *field*.

    V1 has no local-inference provider in the registry; this
    returns an empty list unless the caller has registered a custom
    one.
    """
    specs = _specs_by_tier(CapabilityTier.LOCAL_INFERENCE, registry)
    out: list[FieldPlanStep] = []
    for spec in specs:
        if _accepts_field_type(spec, field):
            out.append(
                FieldPlanStep(
                    capability_id=spec.id,
                    capability_version=spec.version,
                    config={},
                    note=f"local-inference tier={spec.tier.value}",
                )
            )
    return out


def select_remote_inference(
    field: CanonicalField,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> list[FieldPlanStep]:
    """Step 6: remote-inference capabilities for *field*.

    In V1, the only registered remote-inference capability is
    ``inference@1.0`` (with the stub provider). Real providers
    (OpenAI, Anthropic) are V2.
    """
    specs = _specs_by_tier(CapabilityTier.REMOTE_INFERENCE, registry)
    out: list[FieldPlanStep] = []
    for spec in specs:
        if _accepts_field_type(spec, field):
            out.append(
                FieldPlanStep(
                    capability_id=spec.id,
                    capability_version=spec.version,
                    config={},
                    note=f"remote-inference tier={spec.tier.value}",
                )
            )
    return out


def _accepts_field_type(spec: CapabilitySpec, field: CanonicalField) -> bool:
    """Return True if *spec* accepts *field.type* (or no input_types)."""
    if not spec.input_types:
        return True  # No constraint on input; accept all.
    return field.type.name in spec.input_types


def _version_key(version: str) -> tuple[int, ...]:
    """Return a sortable key for a semver string.

    Splits the version on ``.`` and converts each component to
    ``int``. Non-numeric components fall back to ``0`` so the
    function is total (no exception on weird input). Numeric
    comparison is the desired semantic; lexicographic would
    rank ``"1.10"`` before ``"1.9"``.

    Args:
        version: A version string (e.g., ``"1.2.3"``).

    Returns:
        A tuple of non-negative integers (e.g., ``(1, 2, 3)``).
        Mixed-length version tuples compare correctly via
        Python's lexicographic tuple comparison (e.g.,
        ``(1, 10) > (1, 9)`` and ``(2,) > (1, 99)``).
    """
    parts = version.split(".")
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return tuple(out)


def _version_gte(a: str, b: str) -> bool:
    """Return True if version *a* >= version *b* (semver-aware)."""
    return _version_key(a) >= _version_key(b)


def build_capability_chain(
    field: CanonicalField,
    profile: InputProfile,
    policy: Policy | EffectivePolicy,
    budget: Budget | None,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> tuple[FieldPlanStep, ...]:
    """Build the capability chain for *field* under the heuristic chain.

    Implements the 7-step ordering from `ARCHITECTURE.md` §4.2:

    1. Explicit evidence (planner rule on the :class:`InputProfile`).
    2. Local deterministic extraction.
    3. Structured lookup.
    4. Derived computation (skipped in V1).
    5. Local inference (skipped if ``policy.allow_local_inference=False``).
    6. Remote inference (skipped if ``policy.allow_remote_inference=False``
       or if the budget is below the inference cost floor).
    7. ``UNRESOLVED`` (terminal; no chain).

    Args:
        field: The :class:`CanonicalField`.
        profile: The :class:`InputProfile`.
        policy: The call-site :class:`Policy`.
        budget: The :class:`Budget` (optional).
        registry: Optional capability registry (defaults to global).

    Returns:
        A tuple of :class:`FieldPlanStep` records. May be empty
        (``UNRESOLVED`` terminal).
    """
    chain: list[FieldPlanStep] = []

    # Step 1: explicit evidence — short-circuit with text_extraction.
    if has_explicit_evidence(field, profile):
        # The planner emits a text_extraction step (V1's "source")
        # IF text_extraction is registered. If not, the chain is
        # still empty (no text_extraction available).
        # Pick the highest-version ``text_extraction`` from the
        # supplied registry (or the global one when ``registry`` is
        # None). This avoids hard-pinning to ``"1.0"`` so future
        # versions are picked up automatically.
        if registry is None:
            registry = all_capabilities()
        spec: object = None
        chosen_key: tuple[str, str] | None = None
        # Compare versions numerically (semver-aware) so that
        # "1.10" beats "1.9". A naive tuple comparison would do
        # lexicographic ordering, which gets semver wrong.
        for key, _cap in registry.items():
            if key[0] != "text_extraction":
                continue
            if chosen_key is None or _version_gte(key[1], chosen_key[1]):
                chosen_key = key
        if chosen_key is not None:
            spec = getattr(registry[chosen_key], "spec", None)
        if (
            isinstance(spec, CapabilitySpec)
            and _accepts_field_type(spec, field)
            and chosen_key is not None
        ):
            chain.append(
                FieldPlanStep(
                    capability_id="text_extraction",
                    capability_version=chosen_key[1],
                    config={"content_type": profile.input_type},
                    note="explicit-evidence step 1 (planner rule on InputProfile)",
                )
            )

    # Step 2: local deterministic.
    chain.extend(select_local_deterministic(field, registry))

    # Step 3: structured lookup.
    chain.extend(select_structured_lookup(field, registry))

    # Step 4: derived computation — V2 feature, skipped in V1.

    # Step 5: local inference (gated by policy + budget).
    if policy.allow_local_inference and not _budget_excludes_inference(budget):
        chain.extend(select_local_inference(field, registry))

    # Step 6: remote inference (gated by policy + budget).
    if policy.allow_remote_inference and not _budget_excludes_inference(budget):
        chain.extend(select_remote_inference(field, registry))

    return tuple(chain)


def _budget_excludes_inference(budget: Budget | None) -> bool:
    """Return True if the budget excludes the ``inference`` capability.

    Thin alias for :func:`paxman.planner.policies.budget_excludes_inference`.
    Kept as a private function so the heuristic module does not
    import from :mod:`paxman.planner.policies` directly (the policy
    is a public-facing type; the heuristic chain consumes it).
    """
    from paxman.planner.policies import budget_excludes_inference

    return budget_excludes_inference(budget)


def build_field_plan(
    field: CanonicalField,
    profile: InputProfile,
    policy: Policy | EffectivePolicy,
    budget: Budget | None,
    registry: typing.Mapping[tuple[str, str], object] | None = None,
) -> FieldPlan:
    """Build a :class:`FieldPlan` for *field*.

    Thin wrapper over :func:`build_capability_chain`. Returns a
    :class:`FieldPlan` with:

    - ``field_id`` = ``field.id``
    - ``capability_chain`` = the result of :func:`build_capability_chain`
    - ``target_confidence`` = ``field.confidence_threshold``
    - ``fallback_policy`` = ``field.fallback_policy``
    - ``early_stop`` = ``True``

    Args:
        field: The :class:`CanonicalField`.
        profile: The :class:`InputProfile`.
        policy: The effective policy: the call-site :class:`Policy`
            or a pre-computed :class:`EffectivePolicy` (call-site
            combined with the contract-level
            :class:`~paxman.contract._types.ContractPolicy`).
        budget: The :class:`Budget` (optional).
        registry: Optional capability registry (defaults to global).

    Returns:
        The :class:`FieldPlan`. May be empty (``UNRESOLVED``).
    """
    return FieldPlan(
        field_id=field.id,
        capability_chain=build_capability_chain(field, profile, policy, budget, registry),
        target_confidence=field.confidence_threshold,
        fallback_policy=field.fallback_policy,
        early_stop=True,
    )
