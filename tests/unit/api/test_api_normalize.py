"""Unit tests for the private helpers in ``paxman.api.normalize``.

Tests the four internal functions that the ``normalize`` entry point
delegates to: ``_detect_format``, ``_detect_and_adapt``,
``_resolved_to_field_result``, and ``_compute_overall_status``.

Note: ``normalize()`` itself is NOT called here — that is the domain
of integration / E2E tests.
"""

from __future__ import annotations

import typing
from unittest.mock import patch

import pytest

from paxman.api.normalize import (
    _compute_overall_status,
    _detect_and_adapt,
    _detect_format,
    _resolved_to_field_result,
)
from paxman.budget import Policy
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.errors import InvalidContractError
from paxman.reconciler.truth import ResolvedResult
from paxman.types import ConfidenceBand, FieldType, Status

pytestmark = pytest.mark.deterministic


# ---------------------------------------------------------------------------
# _detect_format
# ---------------------------------------------------------------------------


class FakePydanticModel:
    """Simulates a Pydantic v2 model (has ``model_fields``)."""

    model_fields: typing.ClassVar[dict[str, str]] = {"name": "..."}


class TestDetectFormat:
    """Auto-detection of contract format."""

    def test_pydantic_model_detected(self) -> None:
        """An object with ``model_fields`` is detected as ``"pydantic"``."""
        assert _detect_format(FakePydanticModel()) == "pydantic"

    def test_pydantic_model_class_detected(self) -> None:
        """A class (not instance) with ``model_fields`` is also detected."""
        assert _detect_format(FakePydanticModel) == "pydantic"

    def test_dict_dsl_detected(self) -> None:
        """A ``dict`` with Dict DSL markers (``id`` and ``fields``) is detected as ``"dict_dsl"``."""
        assert (
            _detect_format(
                {
                    "id": "demo",
                    "fields": [{"name": "x", "type": "STRING", "required": True}],
                }
            )
            == "dict_dsl"
        )

    def test_empty_dict_detected(self) -> None:
        """An empty dict is detected as ``"dict_dsl"``."""
        assert _detect_format({}) == "dict_dsl"

    def test_dict_with_json_schema_type_and_properties_is_json_schema(self) -> None:
        """A dict with ``type: "object"`` and ``properties`` is JSON Schema (ADR-0011)."""
        assert (
            _detect_format({"type": "object", "properties": {"x": {"type": "string"}}})
            == "json_schema:draft-2020-12"
        )

    def test_dict_with_dollar_schema_keyword_is_json_schema(self) -> None:
        """A dict with the JSON Schema ``$schema`` keyword is JSON Schema (ADR-0011)."""
        assert (
            _detect_format(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                }
            )
            == "json_schema:draft-2020-12"
        )

    def test_dict_with_openapi_keyword_is_openapi(self) -> None:
        """A dict with the OpenAPI ``openapi`` keyword is OpenAPI (ADR-0011)."""
        assert _detect_format({"openapi": "3.1.0", "info": {}}) == "openapi:3.0"

    def test_dict_with_combinator_keyword_is_json_schema(self) -> None:
        """A dict with any JSON Schema combinator keyword is JSON Schema (ADR-0011)."""
        for keyword in ("allOf", "anyOf", "oneOf", "not", "$ref"):
            assert _detect_format({keyword: []}) == "json_schema:draft-2020-12", keyword

    def test_dict_with_constraint_keyword_is_json_schema(self) -> None:
        """A dict with any JSON Schema constraint keyword is JSON Schema (ADR-0011)."""
        for keyword in ("pattern", "const", "enum", "minLength", "maxLength", "format"):
            assert _detect_format({keyword: "x"}) == "json_schema:draft-2020-12", keyword

    def test_dict_with_dollar_defs_is_json_schema(self) -> None:
        """A dict with ``$defs`` (JSON Schema 2020-12 definitions) is JSON Schema (ADR-0011)."""
        assert _detect_format({"$defs": {}, "type": "object"}) == "json_schema:draft-2020-12"

    def test_str_with_json_schema_adapter(self) -> None:
        """A ``str`` that matches the JSON Schema adapter returns the adapter format_id.

        When JSON Schema adapter is registered, it should be found before
        OpenAPI (insertion-order iteration).
        """
        with patch("paxman.api.normalize.get_adapter") as mock_get:
            mock_get.side_effect = [object(), None]  # first call succeeds
            result = _detect_format('{"type": "object"}')
            assert result == "json_schema:draft-2020-12"
            mock_get.assert_any_call("json_schema:draft-2020-12")

    def test_str_with_openapi_adapter(self) -> None:
        """A ``str`` falls back to OpenAPI when JSON Schema adapter is missing."""
        with patch("paxman.api.normalize.get_adapter") as mock_get:
            mock_get.side_effect = [
                InvalidContractError("no json schema adapter"),
                object(),  # OpenAPI adapter found
            ]
            result = _detect_format('{"openapi": "3.0"}')
            assert result == "openapi:3.0"
            mock_get.assert_any_call("json_schema:draft-2020-12")
            mock_get.assert_any_call("openapi:3.0")

    def test_str_raises_when_no_str_adapter(self) -> None:
        """A ``str`` raises ``InvalidContractError`` when no string adapter is registered."""
        with patch("paxman.api.normalize.get_adapter") as mock_get:
            mock_get.side_effect = InvalidContractError("no adapter")
            with pytest.raises(
                InvalidContractError, match="Cannot determine format for str contract"
            ):
                _detect_format('{"type": "object"}')

    def test_unknown_type_raises(self) -> None:
        """An unsupported type raises ``InvalidContractError``."""
        with pytest.raises(InvalidContractError, match="Cannot determine contract format"):
            _detect_format(42)

    def test_none_raises(self) -> None:
        """``None`` raises ``InvalidContractError``."""
        with pytest.raises(InvalidContractError, match="Cannot determine contract format"):
            _detect_format(None)  # type: ignore[arg-type]

    def test_bytes_raises(self) -> None:
        """``bytes`` raises ``InvalidContractError`` (input != contract)."""
        with pytest.raises(InvalidContractError, match="Cannot determine contract format"):
            _detect_format(b"some bytes")

    def test_float_raises(self) -> None:
        """A ``float`` raises ``InvalidContractError``."""
        with pytest.raises(InvalidContractError, match="Cannot determine contract format"):
            _detect_format(3.14)


# ---------------------------------------------------------------------------
# _detect_and_adapt
# ---------------------------------------------------------------------------


class TestDetectAndAdapt:
    """Integration of format detection and contract adaptation."""

    def test_detect_and_adapt_success(self) -> None:
        """When both detection and adaptation succeed, returns the ``CanonicalContract``."""
        canonical = CanonicalContract(
            id="test",
            fields=(
                CanonicalField(
                    id="f1", path="name", name="Name", type=FieldType.STRING, required=True
                ),
            ),
        )
        with (
            patch("paxman.api.normalize._detect_format", return_value="pydantic"),
            patch("paxman.api.normalize._adapt_contract", return_value=canonical),
        ):
            result = _detect_and_adapt(FakePydanticModel())
            assert result is canonical
            assert result.id == "test"

    def test_detect_and_adapt_detection_failure(self) -> None:
        """When detection fails, ``InvalidContractError`` propagates."""
        with patch("paxman.api.normalize._detect_format", side_effect=InvalidContractError("bad")):
            with pytest.raises(InvalidContractError, match="bad"):
                _detect_and_adapt(42)

    def test_detect_and_adapt_adaptation_failure(self) -> None:
        """When adaptation fails, ``InvalidContractError`` propagates."""
        with (
            patch("paxman.api.normalize._detect_format", return_value="pydantic"),
            patch(
                "paxman.api.normalize._adapt_contract",
                side_effect=InvalidContractError("adapt failed"),
            ),
        ):
            with pytest.raises(InvalidContractError, match="adapt failed"):
                _detect_and_adapt(FakePydanticModel())


# ---------------------------------------------------------------------------
# _resolved_to_field_result
# ---------------------------------------------------------------------------


class TestResolvedToFieldResult:
    """Conversion of ``ResolvedResult`` to ``FieldResult``."""

    def test_resolved_result_converts_success(self) -> None:
        """A RESOLVED ``ResolvedResult`` maps to a ``FieldResult`` with ``SUCCESS`` status."""
        rr = ResolvedResult(
            field_id="f1",
            field_path="supplier_name",
            field_type_name="STRING",
            value="ACME Corp",
            confidence=0.95,
            confidence_band=ConfidenceBand.CERTAIN,
            status="RESOLVED",
        )
        fr = _resolved_to_field_result(rr)
        assert fr.field_path == "supplier_name"
        assert fr.value == "ACME Corp"
        assert fr.confidence is ConfidenceBand.CERTAIN
        assert fr.status is Status.SUCCESS

    def test_unresolved_result_converts_unresolved(self) -> None:
        """An UNRESOLVED ``ResolvedResult`` maps to a ``FieldResult`` with ``UNRESOLVED`` status."""
        rr = ResolvedResult(
            field_id="f1",
            field_path="missing_field",
            field_type_name="STRING",
            confidence=0.0,
            confidence_band=ConfidenceBand.UNTRUSTED,
            status="UNRESOLVED",
        )
        fr = _resolved_to_field_result(rr)
        assert fr.field_path == "missing_field"
        assert fr.value is None
        assert fr.confidence is ConfidenceBand.UNTRUSTED
        assert fr.status is Status.UNRESOLVED

    def test_conversion_preserves_evidence_refs(self) -> None:
        """Evidence refs from ``ResolvedResult`` are passed through to ``FieldResult``."""
        from paxman.capabilities.result import EvidenceRef

        evidence = (
            EvidenceRef(
                capability_id="regex_extraction", capability_version="1.0", field_path="name"
            ),
        )
        rr = ResolvedResult(
            field_id="f1",
            field_path="name",
            field_type_name="STRING",
            value="ACME",
            confidence=0.95,
            confidence_band=ConfidenceBand.CERTAIN,
            status="RESOLVED",
            evidence_refs=evidence,
        )
        fr = _resolved_to_field_result(rr)
        assert len(fr.evidence_refs) == 1
        assert fr.evidence_refs[0].capability_id == "regex_extraction"

    def test_conversion_accepts_empty_evidence(self) -> None:
        """Empty evidence refs are handled correctly."""
        rr = ResolvedResult(
            field_id="f1",
            field_path="name",
            field_type_name="STRING",
            value="ACME",
            confidence=0.95,
            confidence_band=ConfidenceBand.CERTAIN,
            status="RESOLVED",
        )
        fr = _resolved_to_field_result(rr)
        assert fr.evidence_refs == ()


# ---------------------------------------------------------------------------
# _compute_overall_status
# ---------------------------------------------------------------------------


class _CanonicalFactory:
    """Test helper to build minimal contracts and resolved results."""

    @staticmethod
    def contract_with_required(paths: list[str]) -> CanonicalContract:
        fields = tuple(
            CanonicalField(id=f"f{i}", path=p, name=p, type=FieldType.STRING, required=True)
            for i, p in enumerate(paths)
        )
        return CanonicalContract(id="test", fields=fields)

    @staticmethod
    def contract_with_optional(paths: list[str]) -> CanonicalContract:
        fields = tuple(
            CanonicalField(id=f"f{i}", path=p, name=p, type=FieldType.STRING, required=False)
            for i, p in enumerate(paths)
        )
        return CanonicalContract(id="test", fields=fields)

    @staticmethod
    def resolved(path: str) -> ResolvedResult:
        return ResolvedResult(
            field_id=f"f_{path}",
            field_path=path,
            field_type_name="STRING",
            value="val",
            confidence=0.95,
            confidence_band=ConfidenceBand.CERTAIN,
            status="RESOLVED",
        )

    @staticmethod
    def unresolved(path: str) -> ResolvedResult:
        return ResolvedResult(
            field_id=f"f_{path}",
            field_path=path,
            field_type_name="STRING",
            confidence=0.0,
            confidence_band=ConfidenceBand.UNTRUSTED,
            status="UNRESOLVED",
        )


class TestComputeOverallStatus:
    """Status computation logic."""

    def test_all_resolved_required_returns_success(self) -> None:
        """All required fields resolved => SUCCESS."""
        cc = _CanonicalFactory.contract_with_required(["name", "date"])
        results = (_CanonicalFactory.resolved("name"), _CanonicalFactory.resolved("date"))
        assert _compute_overall_status(results, cc, None) is Status.SUCCESS

    def test_all_resolved_optional_returns_success(self) -> None:
        """All fields (all optional) resolved => SUCCESS."""
        cc = _CanonicalFactory.contract_with_optional(["name", "date"])
        results = (_CanonicalFactory.resolved("name"), _CanonicalFactory.resolved("date"))
        assert _compute_overall_status(results, cc, None) is Status.SUCCESS

    def test_some_unresolved_optional_returns_partial_success(self) -> None:
        """Some unresolved fields but none required => PARTIAL_SUCCESS."""
        cc = _CanonicalFactory.contract_with_optional(["name", "date"])
        results = (_CanonicalFactory.resolved("name"), _CanonicalFactory.unresolved("date"))
        assert _compute_overall_status(results, cc, None) is Status.PARTIAL_SUCCESS

    def test_all_required_resolved_returns_success(self) -> None:
        """All required fields resolved (no optional fields) => SUCCESS."""
        cc = _CanonicalFactory.contract_with_required(["name"])
        # "name" is required and resolved; "date" is not in the contract.
        results = (_CanonicalFactory.resolved("name"),)
        assert _compute_overall_status(results, cc, None) is Status.SUCCESS

    def test_unresolved_required_returns_unresolved(self) -> None:
        """At least one unresolved required field => UNRESOLVED."""
        cc = _CanonicalFactory.contract_with_required(["name", "date"])
        results = (_CanonicalFactory.resolved("name"), _CanonicalFactory.unresolved("date"))
        assert _compute_overall_status(results, cc, None) is Status.UNRESOLVED

    def test_all_unresolved_required_returns_unresolved(self) -> None:
        """All required fields unresolved => UNRESOLVED."""
        cc = _CanonicalFactory.contract_with_required(["name", "date"])
        results = (_CanonicalFactory.unresolved("name"), _CanonicalFactory.unresolved("date"))
        assert _compute_overall_status(results, cc, None) is Status.UNRESOLVED

    def test_unresolved_required_with_policy_acceptable_returns_partial_success(self) -> None:
        """Unresolved required fields with ``unresolved_acceptable=True`` policy => PARTIAL_SUCCESS."""
        cc = _CanonicalFactory.contract_with_required(["name", "date"])
        results = (_CanonicalFactory.unresolved("name"), _CanonicalFactory.unresolved("date"))
        policy = Policy(unresolved_acceptable=True)
        assert _compute_overall_status(results, cc, policy) is Status.PARTIAL_SUCCESS

    def test_unresolved_required_with_policy_not_acceptable_returns_unresolved(self) -> None:
        """Unresolved required fields with ``unresolved_acceptable=False`` policy => UNRESOLVED."""
        cc = _CanonicalFactory.contract_with_required(["name"])
        results = (_CanonicalFactory.unresolved("name"),)
        policy = Policy(unresolved_acceptable=False)
        assert _compute_overall_status(results, cc, policy) is Status.UNRESOLVED

    def test_no_fields_returns_success(self) -> None:
        """Single required field resolved => SUCCESS."""
        cc = CanonicalContract(
            id="empty",
            fields=(
                CanonicalField(id="f1", path="x", name="x", type=FieldType.STRING, required=True),
            ),
        )
        results = (_CanonicalFactory.resolved("x"),)
        assert _compute_overall_status(results, cc, None) is Status.SUCCESS

    def test_unresolved_non_required_in_required_contract(self) -> None:
        """Unresolved optional field with also a required field => PARTIAL_SUCCESS.

        If the required field is resolved but an optional field is unresolved,
        the result is PARTIAL_SUCCESS.
        """
        cc = CanonicalContract(
            id="mixed",
            fields=(
                CanonicalField(
                    id="f1",
                    path="required_field",
                    name="Required",
                    type=FieldType.STRING,
                    required=True,
                ),
                CanonicalField(
                    id="f2",
                    path="optional_field",
                    name="Optional",
                    type=FieldType.STRING,
                    required=False,
                ),
            ),
        )
        results = (
            _CanonicalFactory.resolved("required_field"),
            _CanonicalFactory.unresolved("optional_field"),
        )
        assert _compute_overall_status(results, cc, None) is Status.PARTIAL_SUCCESS


# ---------------------------------------------------------------------------
# normalize() orchestration tests (mocked internals, no E2E data)
# ---------------------------------------------------------------------------


class TestNormalizeOrchestration:
    """Key error-handling paths in ``normalize()`` via mocked internals.

    These tests verify the orchestration and early-return paths without
    exercising the full E2E pipeline.
    """

    def test_returns_invalid_contract_on_detect_failure(self) -> None:
        """When contract detection fails, returns artifact with ``INVALID_CONTRACT`` status."""
        from paxman.api.normalize import normalize

        with patch(
            "paxman.api.normalize._detect_and_adapt", side_effect=InvalidContractError("bad")
        ):
            result = normalize(input_data="data", contract={"type": "object"})
        assert result.status is Status.INVALID_CONTRACT
        assert result.normalized_data == {}

    def test_returns_invalid_contract_on_plan_failure(self) -> None:
        """When planning fails, returns artifact with ``INVALID_CONTRACT`` status."""
        from paxman.api.normalize import normalize
        from paxman.budget import Budget

        canonical = CanonicalContract(
            id="test",
            fields=(
                CanonicalField(
                    id="f1", path="name", name="Name", type=FieldType.STRING, required=True
                ),
            ),
        )
        with (
            patch("paxman.api.normalize._detect_and_adapt", return_value=canonical),
            patch("paxman.api.normalize._plan", side_effect=InvalidContractError("plan failed")),
        ):
            result = normalize(
                input_data="data",
                contract={"type": "object"},
                budget=Budget(),
            )
        assert result.status is Status.INVALID_CONTRACT

    def test_handles_budget_exceeded_gracefully(self) -> None:
        """When the executor raises ``BudgetExceededError``, the artifact is still produced."""
        from paxman.api.normalize import normalize
        from paxman.budget import Budget
        from paxman.errors import BudgetExceededError
        from paxman.planner.field_plan import ExecutionPlan
        from paxman.planner.input_profile import InputProfile

        canonical = CanonicalContract(
            id="test",
            fields=(
                CanonicalField(
                    id="f1", path="name", name="Name", type=FieldType.STRING, required=True
                ),
            ),
        )
        profile = InputProfile(
            input_type="text",
            size=4,
            content_hash="d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5",
            density=0.857,
            is_empty=False,
        )
        plan = ExecutionPlan(field_plans=())

        with (
            patch("paxman.api.normalize._detect_and_adapt", return_value=canonical),
            patch("paxman.api.normalize.make_profile", return_value=profile),
            patch("paxman.api.normalize._plan", return_value=plan),
            patch(
                "paxman.api.normalize._run_executor",
                side_effect=BudgetExceededError("budget exceeded"),
            ),
        ):
            # The function should not raise; it should produce an artifact.
            result = normalize(
                input_data="data",
                contract={"type": "object"},
                budget=Budget(max_total_cost_usd=0.01),
            )
        assert result.status is Status.UNRESOLVED
        assert result.normalized_data == {}

    def test_full_mocked_normalize_produces_artifact(self) -> None:
        """With all internals mocked, ``normalize()`` produces a complete artifact."""
        from paxman.api.normalize import normalize
        from paxman.budget import Budget
        from paxman.capabilities.result import Candidate, EvidenceRef
        from paxman.executor.field_runner import CandidateResult
        from paxman.planner.field_plan import ExecutionPlan
        from paxman.planner.input_profile import InputProfile
        from paxman.reconciler.truth import ResolvedResult
        from paxman.types import ConfidenceBand

        canonical = CanonicalContract(
            id="test",
            fields=(
                CanonicalField(
                    id="f1", path="name", name="Name", type=FieldType.STRING, required=True
                ),
            ),
        )
        profile = InputProfile(
            input_type="text",
            size=4,
            content_hash="d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5",
            density=0.857,
            is_empty=False,
        )
        plan = ExecutionPlan(field_plans=())

        rr = ResolvedResult(
            field_id="f1",
            field_path="name",
            field_type_name="STRING",
            value="ACME Corp",
            confidence=0.95,
            confidence_band=ConfidenceBand.CERTAIN,
            status="RESOLVED",
        )

        candidate = Candidate(value="ACME Corp")
        ev = EvidenceRef(
            capability_id="regex_extraction", capability_version="1.0", field_path="name"
        )

        candidate_result = CandidateResult(
            field_id="f1",
            field_path="name",
            field_type_name="STRING",
            candidates=(candidate,),
            evidence=(ev,),
        )

        with (
            patch("paxman.api.normalize._detect_and_adapt", return_value=canonical),
            patch("paxman.api.normalize.make_profile", return_value=profile),
            patch("paxman.api.normalize._plan", return_value=plan),
            patch("paxman.api.normalize._run_executor", return_value=[candidate_result]),
            patch("paxman.api.normalize._reconcile", return_value=(rr,)),
        ):
            result = normalize(
                input_data="ACME Corp",
                contract={"type": "object"},
                budget=Budget(),
            )
        assert result.status is Status.SUCCESS
        assert result.normalized_data == {"name": "ACME Corp"}
        assert result.contract_id == "test"
