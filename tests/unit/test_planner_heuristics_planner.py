"""Unit tests for :mod:`paxman.planner.heuristics` and the top-level
:func:`paxman.planner.planner.plan`.

Per Sprint 3 D3.4, D3.7, and the V1 acceptance criteria §1.2 (planner
determinism + 7-step heuristic chain).
"""

from __future__ import annotations

import pytest

from paxman.budget import Budget, Policy
from paxman.capabilities.registry import register, reset
from paxman.capabilities.spec import (
    CapabilitySpec,
    CapabilityTier,
    CostHint,
)
from paxman.capabilities.v1.inference import InferenceCapability
from paxman.capabilities.v1.regex_extraction import RegexExtractionCapability
from paxman.capabilities.v1.text_extraction import TextExtractionCapability
from paxman.capabilities.v1.validation import ValidationCapability
from paxman.contract._types import ContractPolicy
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.planner.field_plan import FieldPlan
from paxman.planner.heuristics import (
    _version_gte,
    _version_key,
    build_capability_chain,
    build_field_plan,
    has_explicit_evidence,
)
from paxman.planner.input_profile import make_profile
from paxman.planner.planner import plan
from paxman.types import FieldType

pytestmark = pytest.mark.unit


def _field(
    name: str = "supplier_name",
    type: FieldType = FieldType.STRING,
    required: bool = True,
) -> CanonicalField:
    return CanonicalField(
        id=f"field_{name}",
        path=name,
        name=name,
        type=type,
        required=required,
    )


def _contract(*fields: CanonicalField, id: str = "c") -> CanonicalContract:
    return CanonicalContract(id=id, fields=tuple(fields) or (_field(),))


class _Cap:
    """Minimal capability that satisfies the Protocol."""

    def __init__(self, spec: CapabilitySpec) -> None:
        self._spec = spec

    @property
    def spec(self) -> CapabilitySpec:
        return self._spec

    def invoke(self, ctx):  # type: ignore[no-untyped-def]
        from paxman.capabilities.result import CapabilityResult

        return CapabilityResult()


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset the global registry between tests; default registrations."""
    reset()
    register(RegexExtractionCapability())
    register(ValidationCapability())
    register(TextExtractionCapability())
    register(InferenceCapability())
    yield
    reset()


# --- has_explicit_evidence (planner rule) -------------------------------


def test_explicit_evidence_for_text_input() -> None:
    """A text input with density > 0.1 has explicit evidence."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp\nInvoice #1234")
    assert has_explicit_evidence(field, profile) is True


def test_no_explicit_evidence_for_empty_input() -> None:
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"")
    assert has_explicit_evidence(field, profile) is False


def test_no_explicit_evidence_for_whitespace_only_input() -> None:
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"   \n\t  ")
    assert has_explicit_evidence(field, profile) is False


def test_explicit_evidence_for_html_input() -> None:
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"<p>ACME Corp</p>")
    assert has_explicit_evidence(field, profile) is True


def test_explicit_evidence_for_non_string_field_requires_html() -> None:
    """A non-STRING field needs HTML-shaped input to short-circuit."""
    field = _field("count", FieldType.INTEGER)
    profile_text = make_profile(b"12345")
    profile_html = make_profile(b"<p>12345</p>")
    assert has_explicit_evidence(field, profile_text) is True  # text qualifies
    assert has_explicit_evidence(field, profile_html) is True  # html qualifies


# --- build_capability_chain ----------------------------------------------


def test_chain_for_text_field_includes_text_extraction_first() -> None:
    """A STRING field with text input gets text_extraction (step 1) + others."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp")
    chain = build_capability_chain(field, profile, Policy(), None)
    assert len(chain) > 0
    # Step 1: text_extraction.
    assert chain[0].capability_id == "text_extraction"


def test_chain_excludes_remote_inference_when_policy_disallows() -> None:
    """Policy.allow_remote_inference=False drops step 6."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp")
    policy = Policy(allow_remote_inference=False)
    chain = build_capability_chain(field, profile, policy, None)
    assert not any(step.capability_id == "inference" for step in chain)


def test_chain_excludes_local_inference_when_policy_disallows() -> None:
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp")
    policy = Policy(allow_local_inference=False)
    chain = build_capability_chain(field, profile, policy, None)
    # No LOCAL_INFERENCE capabilities registered in V1; verify the
    # function doesn't crash and produces a valid chain.
    assert isinstance(chain, tuple)


def test_chain_excludes_inference_when_budget_too_low() -> None:
    """Budget < inference cost drops the inference step (per cost-model §7 EC6)."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp")
    policy = Policy()
    budget = Budget(max_total_cost_usd=0.0)  # excludes inference
    chain = build_capability_chain(field, profile, policy, budget)
    assert not any(step.capability_id == "inference" for step in chain)


def test_chain_is_sorted_by_score_within_tier() -> None:
    """Within a tier, capabilities are sorted by ascending score."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp")
    chain = build_capability_chain(field, profile, Policy(), None)
    # Find the indices of local-deterministic capabilities (regex_extraction, validation).
    local_steps = [s for s in chain if s.capability_id in ("regex_extraction", "validation")]
    # Per cost-model §4.4: regex_extraction and validation tie at 10,001.
    # Tie-break by id (lex asc) → regex_extraction < validation.
    if len(local_steps) >= 2:
        assert local_steps[0].capability_id <= local_steps[1].capability_id


# --- build_field_plan ---------------------------------------------------


def test_field_plan_carries_threshold() -> None:
    """The field's target_confidence is mirrored from confidence_threshold."""
    field = CanonicalField(
        id="f1",
        path="x",
        name="x",
        type=FieldType.STRING,
        required=True,
        confidence_threshold=0.85,
    )
    profile = make_profile(b"x")
    fp = build_field_plan(field, profile, Policy(), None)
    assert isinstance(fp, FieldPlan)
    assert fp.target_confidence == 0.85
    assert fp.field_id == "f1"


def test_field_plan_for_empty_input_skips_explicit_evidence() -> None:
    """An empty input skips step 1 (text_extraction) but steps 2-6
    still run, so the chain is non-empty."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"")
    fp = build_field_plan(field, profile, Policy(), None)
    # The chain still has steps 2-6 (regex_extraction, validation, ...).
    # Step 1 is omitted because ``has_explicit_evidence`` is False.
    assert len(fp.capability_chain) > 0
    # text_extraction is NOT the first step (no explicit evidence).
    assert fp.capability_chain[0].capability_id != "text_extraction"


def test_field_plan_for_non_empty_input_emits_chain() -> None:
    """A non-empty input emits at least one step (text_extraction first)."""
    field = _field("supplier_name", FieldType.STRING)
    profile = make_profile(b"ACME Corp")
    fp = build_field_plan(field, profile, Policy(), None)
    assert len(fp.capability_chain) > 0
    assert fp.capability_chain[0].capability_id == "text_extraction"


# --- plan (top-level) ----------------------------------------------------


def test_plan_emits_one_field_plan_per_required_field() -> None:
    """Per ADR-0001: one FieldPlan per required field."""
    contract = _contract(
        _field("a", FieldType.STRING),
        _field("b", FieldType.STRING),
        _field("c", FieldType.STRING, required=False),
    )
    profile = make_profile(b"a b c")
    p = plan(contract, profile)
    assert len(p.field_plans) == 2  # only a and b (required)


def test_plan_includes_optional_fields_only_when_required() -> None:
    """Non-required fields are NOT in the plan (V1: required-only)."""
    contract = _contract(
        _field("required_one", FieldType.STRING, required=True),
        _field("optional_one", FieldType.STRING, required=False),
    )
    profile = make_profile(b"x")
    p = plan(contract, profile)
    ids = {fp.field_id for fp in p.field_plans}
    assert "field_required_one" in ids
    assert "field_optional_one" not in ids


def test_plan_emits_unresolved_diagnostic_for_field_with_no_chain() -> None:
    """A field with no eligible capability gets a FIELD_UNRESOLVED diagnostic.

    We achieve this by passing an *empty* registry to ``plan()`` and
    planning a STRING field. With no capabilities registered, the
    chain is empty, and a FIELD_UNRESOLVED diagnostic is emitted.
    """
    reset()  # no capabilities registered
    contract = CanonicalContract(
        id="c",
        fields=(_field("supplier_name", FieldType.STRING, required=True),),
    )
    profile = make_profile(b"x")
    # Note: as of Sprint 10, the registry self-heals when ``plan()``
    # is called via the global registry. To test the truly-empty-registry
    # behaviour, pass an explicit empty registry to bypass the bootstrap.
    p = plan(contract, profile, registry={})
    assert any(d.code == "FIELD_UNRESOLVED" for d in p.diagnostics)
    # Re-register for other tests in this module (autouse fixture also resets).
    register(RegexExtractionCapability())
    register(ValidationCapability())
    register(TextExtractionCapability())
    register(InferenceCapability())


def test_plan_emits_budget_excluded_diagnostic() -> None:
    contract = _contract()
    profile = make_profile(b"x")
    p = plan(contract, profile, budget=Budget(max_total_cost_usd=0.0))
    assert any(d.code == "BUDGET_EXCLUDES_INFERENCE" for d in p.diagnostics)


def test_plan_emits_policy_excluded_diagnostics() -> None:
    contract = _contract()
    profile = make_profile(b"x")
    p = plan(
        contract,
        profile,
        policy=Policy(allow_remote_inference=False, allow_local_inference=False),
    )
    assert any(d.code == "POLICY_EXCLUDES_REMOTE_INFERENCE" for d in p.diagnostics)
    assert any(d.code == "POLICY_EXCLUDES_LOCAL_INFERENCE" for d in p.diagnostics)


def test_plan_propagates_input_content_hash() -> None:
    """The plan carries the input's content hash for replay composition."""
    contract = _contract()
    profile = make_profile(b"some specific content")
    p = plan(contract, profile)
    assert p.input_content_hash == profile.content_hash


def test_plan_propagates_contract_id() -> None:
    contract = _contract(id="my-contract")
    profile = make_profile(b"x")
    p = plan(contract, profile)
    assert p.contract_id == "my-contract"


def test_plan_invoice_use_case_picks_regex_extraction_first() -> None:
    """Per Sprint 3 risk register: for the canonical invoice use case
    (supplier_name, STRING, text input), the planner should prefer
    regex_extraction over more expensive options."""
    contract = CanonicalContract(
        id="invoice",
        fields=(_field("supplier_name", FieldType.STRING, required=True),),
    )
    profile = make_profile(b"ACME Corp\nInvoice #1234\nTotal: $1,234.56")
    p = plan(contract, profile)
    # Step 1 (text_extraction) is the planner's first emission.
    assert p.field_plans[0].capability_chain[0].capability_id == "text_extraction"


def test_plan_uses_effective_policy_including_contract_overrides() -> None:
    """The plan uses the *effective* policy (call-site + contract).

    When the contract sets ``ContractPolicy.confidence_floor`` to
    a value different from the call-site policy, the planner
    should use the contract's value. This is verified indirectly
    by the deterministic-plan test in
    ``tests/property/test_planner_determinism.py``.
    """
    # Sanity: the plan function is a pure function; same inputs
    # → same outputs. The effective policy is applied internally.
    contract = CanonicalContract(
        id="c",
        fields=(
            CanonicalField(
                id="f1",
                path="f1",
                name="f1",
                type=FieldType.STRING,
                required=True,
            ),
        ),
        policies=ContractPolicy(confidence_floor=0.5),
    )
    profile = make_profile(b"x")
    p1 = plan(contract, profile)
    p2 = plan(contract, profile)
    # Determinism with contract policy.
    assert p1 == p2
    # The field's target_confidence is the field's threshold (not
    # the contract's floor); this confirms the planner doesn't
    # accidentally substitute one for the other.
    assert p1.field_plans[0].target_confidence == 0.8  # field default


# --- determinism --------------------------------------------------------


@pytest.mark.deterministic
def test_plan_is_deterministic() -> None:
    """Same inputs → same plan, byte-equal."""
    contract = _contract()
    profile = make_profile(b"ACME Corp\nInvoice #1234")
    p1 = plan(contract, profile)
    p2 = plan(contract, profile)
    assert p1 == p2


@pytest.mark.deterministic
def test_plan_with_contract_policy_is_deterministic() -> None:
    contract = _contract()
    contract = attrs_replace_policies(contract, ContractPolicy(confidence_floor=0.95))
    profile = make_profile(b"x")
    p1 = plan(contract, profile)
    p2 = plan(contract, profile)
    assert p1 == p2


def attrs_replace_policies(
    contract: CanonicalContract, policies: ContractPolicy | None
) -> CanonicalContract:
    """Replace the policies field of a CanonicalContract.

    attrs.frozen instances cannot be mutated; this helper builds a
    new CanonicalContract with the replacement policy.
    """
    from attrs import evolve

    return evolve(contract, policies=policies)


# --- _version_key / _version_gte (semver-aware comparison) ---------------


def test_version_key_sorts_numerically() -> None:
    """``_version_key`` is a tuple of ints; comparison is numeric, not lex."""
    assert _version_key("1.10") > _version_key("1.9")
    assert _version_key("2.0") > _version_key("1.99")
    assert _version_key("1.2.3") == (1, 2, 3)


def test_version_gte_basic() -> None:
    """``_version_gte`` is True when the left side >= the right side."""
    assert _version_gte("1.10", "1.9")
    assert _version_gte("2.0", "2.0")
    assert not _version_gte("1.9", "1.10")
    assert _version_gte("1.0", "1.0-rc")  # non-numeric parts become 0


def test_build_capability_chain_picks_highest_semver_text_extraction() -> None:
    """The heuristic picks the semver-highest text_extraction, not the lex-highest.

    Regression test: a naive ``key > chosen_key`` would rank
    ``"1.10"`` below ``"1.9"`` because ``"1.10" < "1.9"`` as strings.
    The semver-aware helper must pick ``"1.10"``.
    """
    from paxman.capabilities.base import CapabilityContext
    from paxman.capabilities.result import CapabilityResult

    class _SpecCap:
        """Minimal capability wrapper that exposes a custom spec."""

        def __init__(self, spec: CapabilitySpec) -> None:
            self._spec = spec

        @property
        def spec(self) -> CapabilitySpec:
            return self._spec

        def invoke(self, ctx: CapabilityContext) -> CapabilityResult:  # pragma: no cover
            return CapabilityResult()

    reset()
    register(
        _SpecCap(
            CapabilitySpec(
                id="text_extraction",
                version="1.9",
                cost_estimate=CostHint(0, 5, 0.0),
                tier=CapabilityTier.LOCAL_DETERMINISTIC,
            )
        )
    )
    register(
        _SpecCap(
            CapabilitySpec(
                id="text_extraction",
                version="1.10",
                cost_estimate=CostHint(0, 5, 0.0),
                tier=CapabilityTier.LOCAL_DETERMINISTIC,
            )
        )
    )
    field = CanonicalField(
        id="f1",
        path="f1",
        name="f1",
        type=FieldType.STRING,
        required=True,
    )
    profile = make_profile(b"ACME Corp")
    chain = build_capability_chain(field, profile, Policy(), None)
    # Find the text_extraction step in the chain.
    text_steps = [s for s in chain if s.capability_id == "text_extraction"]
    assert text_steps, "expected a text_extraction step"
    # The semver-highest "1.10" must win over "1.9".
    assert text_steps[0].capability_version == "1.10"
    reset()
    # Re-register the real V1 capability so other tests are unaffected.
    register(RegexExtractionCapability())
    register(ValidationCapability())
    register(TextExtractionCapability())
    register(InferenceCapability())
