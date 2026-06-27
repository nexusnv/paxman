"""Unit tests for ``paxman.artifact.artifact`` — FieldResult, ExecutionArtifact, _is_hex64."""

from __future__ import annotations

import pytest

from paxman.artifact.artifact import ExecutionArtifact, FieldResult, _is_hex64
from paxman.artifact.statistics import Statistics
from paxman.capabilities.result import Candidate, EvidenceRef
from paxman.planner.field_plan import ExecutionPlan
from paxman.types import ConfidenceBand, Status

pytestmark = pytest.mark.deterministic

# ============================================================================
# _is_hex64 helper
# ============================================================================

_HEX64_VALID: tuple[str, ...] = (
    "a" * 64,
    "0123456789abcdef" * 4,
    "deadbeef" * 8,
)

_HEX64_INVALID: tuple[object, ...] = (
    "",
    "abc",
    "a" * 63,
    "a" * 65,
    "gggg" + "a" * 60,
    "A" * 64,  # uppercase is not allowed
    "abcdefgh" * 8,
    None,
    123,
)


@pytest.mark.deterministic
def test_is_hex64_accepts_valid() -> None:
    """_is_hex64 returns True for 64-char lowercase hex strings."""
    for s in _HEX64_VALID:
        assert _is_hex64(s) is True, f"expected True for {s!r}"


@pytest.mark.deterministic
def test_is_hex64_rejects_invalid() -> None:
    """_is_hex64 returns False for wrong-length or non-hex strings."""
    for s in _HEX64_INVALID:
        if isinstance(s, str):
            assert _is_hex64(s) is False, f"expected False for {s!r}"


# ============================================================================
# FieldResult
# ============================================================================


@pytest.mark.deterministic
def test_field_result_minimal() -> None:
    """FieldResult with just field_path is valid; defaults apply."""
    fr = FieldResult(field_path="supplier_name")
    assert fr.field_path == "supplier_name"
    assert fr.value is None
    assert fr.confidence is ConfidenceBand.UNTRUSTED
    assert fr.candidates == ()
    assert fr.evidence_refs == ()
    assert fr.status is Status.UNRESOLVED


@pytest.mark.deterministic
def test_field_result_frozen_and_slots() -> None:
    """FieldResult is frozen (immutable) and uses slots."""
    fr = FieldResult(field_path="x")

    # frozen — cannot set attribute
    with pytest.raises(AttributeError):
        fr.field_path = "y"  # type: ignore[misc]

    # slots — no __dict__
    assert not hasattr(fr, "__dict__")


@pytest.mark.deterministic
def test_field_result_with_all_fields() -> None:
    """FieldResult accepts all fields with valid types."""
    ev = EvidenceRef(
        capability_id="regex_extraction",
        capability_version="1.0",
        field_path="name",
    )
    cand = Candidate(value="ACME Corp", evidence_refs=(ev,))
    fr = FieldResult(
        field_path="supplier_name",
        value="ACME Corp",
        confidence=ConfidenceBand.HIGH,
        candidates=(cand,),
        evidence_refs=(ev,),
        status=Status.SUCCESS,
    )
    assert fr.value == "ACME Corp"
    assert fr.confidence is ConfidenceBand.HIGH
    assert fr.candidates == (cand,)
    assert fr.evidence_refs == (ev,)
    assert fr.status is Status.SUCCESS


@pytest.mark.deterministic
def test_field_result_rejects_empty_field_path() -> None:
    """Empty string field_path raises ValueError."""
    with pytest.raises(ValueError, match="field_path must be a non-empty string"):
        FieldResult(field_path="")


@pytest.mark.deterministic
def test_field_result_rejects_non_string_field_path() -> None:
    """Non-string field_path raises ValueError."""
    with pytest.raises(ValueError, match="field_path must be a non-empty string"):
        FieldResult(field_path=123)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_field_result_rejects_non_status() -> None:
    """Non-Status value for status raises TypeError."""
    with pytest.raises(TypeError, match="status must be a Status enum"):
        FieldResult(field_path="a", status="SUCCESS")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_field_result_rejects_invalid_status_value() -> None:
    """Status values not in _FIELD_VALID_STATUSES raise ValueError."""
    # INVALID_CONTRACT is a valid Status enum but not valid per-field.
    with pytest.raises(ValueError, match="status must be one of"):
        FieldResult(field_path="a", status=Status.INVALID_CONTRACT)


@pytest.mark.deterministic
def test_field_result_rejects_non_confidence_band() -> None:
    """Non-ConfidenceBand for confidence raises TypeError."""
    with pytest.raises(TypeError, match="confidence must be a ConfidenceBand"):
        FieldResult(field_path="a", confidence="HIGH")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_field_result_rejects_non_tuple_candidates() -> None:
    """candidates must be a tuple."""
    with pytest.raises(TypeError, match="candidates must be a tuple"):
        FieldResult(field_path="a", candidates=[])  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_field_result_rejects_non_tuple_evidence_refs() -> None:
    """evidence_refs must be a tuple."""
    with pytest.raises(TypeError, match="evidence_refs must be a tuple"):
        FieldResult(field_path="a", evidence_refs=[])  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.parametrize(
    "valid_status",
    ["SUCCESS", "PARTIAL_SUCCESS", "UNRESOLVED", "EXECUTION_FAILED"],
)
def test_field_result_accepts_valid_statuses(valid_status: str) -> None:
    """Each valid per-field status is accepted."""
    fr = FieldResult(field_path="a", status=Status(valid_status))
    assert fr.status.value == valid_status


# ============================================================================
# ExecutionArtifact
# ============================================================================


def _minimal_artifact() -> ExecutionArtifact:
    """Build an ExecutionArtifact with status=SUCCESS and no other required setup."""
    return ExecutionArtifact(status=Status.SUCCESS)


@pytest.mark.deterministic
def test_artifact_minimal() -> None:
    """Minimal ExecutionArtifact with status=SUCCESS is valid; defaults apply."""
    art = _minimal_artifact()
    assert art.status is Status.SUCCESS
    assert art.id.startswith("art_")
    assert art.normalized_data == {}
    assert art.field_results == {}
    assert art.unresolved_fields == []
    assert art.evidence == ()
    assert art.diagnostics == ()
    assert art.execution_plan is None
    assert art.replay_hash == ""
    assert art.statistics is None
    assert art.contract_id == ""
    assert isinstance(art.paxman_version, str)
    assert art.paxman_version == "1.0.0"
    assert isinstance(art.planner_version, str)
    assert art.capability_versions == {}
    assert art.metadata == {}
    assert isinstance(art.created_at, str)
    assert len(art.created_at) > 0


@pytest.mark.deterministic
def test_artifact_frozen_and_slots() -> None:
    """ExecutionArtifact is frozen and uses slots."""
    art = _minimal_artifact()

    with pytest.raises(AttributeError):
        art.status = Status.UNRESOLVED  # type: ignore[misc]

    assert not hasattr(art, "__dict__")


@pytest.mark.deterministic
def test_artifact_rejects_empty_id() -> None:
    """Non-empty string id is required."""
    with pytest.raises(ValueError, match="id must be a non-empty string"):
        ExecutionArtifact(status=Status.SUCCESS, id="")


@pytest.mark.deterministic
def test_artifact_rejects_non_status() -> None:
    """Non-Status raises TypeError."""
    with pytest.raises(TypeError, match="status must be a Status enum"):
        ExecutionArtifact(status="SUCCESS")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_non_dict_normalized_data() -> None:
    """normalized_data must be a dict."""
    with pytest.raises(TypeError, match="normalized_data must be a dict"):
        ExecutionArtifact(status=Status.SUCCESS, normalized_data="not_dict")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_non_dict_field_results() -> None:
    """field_results must be a dict."""
    with pytest.raises(TypeError, match="field_results must be a dict"):
        ExecutionArtifact(status=Status.SUCCESS, field_results="not_dict")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_field_results_with_non_string_key() -> None:
    """field_results keys must be strings."""
    with pytest.raises(TypeError, match="field_results keys must be strings"):
        ExecutionArtifact(
            status=Status.SUCCESS,
            field_results={1: FieldResult(field_path="x")},  # type: ignore[dict-item]
        )


@pytest.mark.deterministic
def test_artifact_rejects_field_results_with_non_field_result_value() -> None:
    """field_results values must be FieldResult instances."""
    with pytest.raises(TypeError, match="field_results values must be FieldResult"):
        ExecutionArtifact(
            status=Status.SUCCESS,
            field_results={"x": "not_a_field_result"},  # type: ignore[dict-item]
        )


@pytest.mark.deterministic
def test_artifact_rejects_non_tuple_evidence() -> None:
    """evidence must be a tuple."""
    with pytest.raises(TypeError, match="evidence must be a tuple"):
        ExecutionArtifact(status=Status.SUCCESS, evidence=[])  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_non_tuple_diagnostics() -> None:
    """diagnostics must be a tuple."""
    with pytest.raises(TypeError, match="diagnostics must be a tuple"):
        ExecutionArtifact(status=Status.SUCCESS, diagnostics=[])  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_non_string_replay_hash() -> None:
    """replay_hash must be a str."""
    with pytest.raises(TypeError, match="replay_hash must be a str"):
        ExecutionArtifact(status=Status.SUCCESS, replay_hash=123)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_invalid_replay_hash_format() -> None:
    """Non-empty replay_hash must be 64 lowercase hex chars."""
    with pytest.raises(ValueError, match="replay_hash must be 64 lowercase hex chars"):
        ExecutionArtifact(status=Status.SUCCESS, replay_hash="abc123")


@pytest.mark.deterministic
def test_artifact_accepts_valid_replay_hash() -> None:
    """A valid 64-char lowercase hex replay_hash is accepted."""
    valid_hash = "a" * 64
    art = ExecutionArtifact(status=Status.SUCCESS, replay_hash=valid_hash)
    assert art.replay_hash == valid_hash


@pytest.mark.deterministic
def test_artifact_accepts_empty_replay_hash() -> None:
    """Empty string replay_hash is accepted (pre-finalisation)."""
    art = ExecutionArtifact(status=Status.SUCCESS, replay_hash="")
    assert art.replay_hash == ""


@pytest.mark.deterministic
def test_artifact_rejects_non_string_paxman_version() -> None:
    """paxman_version must be a str."""
    with pytest.raises(TypeError, match="paxman_version must be a str"):
        ExecutionArtifact(status=Status.SUCCESS, paxman_version=1)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_non_dict_metadata() -> None:
    """metadata must be a dict."""
    with pytest.raises(TypeError, match="metadata must be a dict"):
        ExecutionArtifact(status=Status.SUCCESS, metadata="not_dict")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_empty_created_at() -> None:
    """created_at must be a non-empty string."""
    with pytest.raises(ValueError, match="created_at must be a non-empty ISO-8601 string"):
        ExecutionArtifact(status=Status.SUCCESS, created_at="")


@pytest.mark.deterministic
def test_artifact_rejects_non_string_created_at() -> None:
    """created_at must be a string."""
    with pytest.raises(ValueError, match="created_at must be a non-empty ISO-8601 string"):
        ExecutionArtifact(status=Status.SUCCESS, created_at=123)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_rejects_wrong_type_execution_plan() -> None:
    """execution_plan must be ExecutionPlan or None."""
    with pytest.raises(TypeError, match="execution_plan must be an ExecutionPlan or None"):
        ExecutionArtifact(status=Status.SUCCESS, execution_plan="not_a_plan")  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_artifact_accepts_execution_plan() -> None:
    """A valid ExecutionPlan is accepted."""
    plan = ExecutionPlan(field_plans=())
    art = ExecutionArtifact(status=Status.SUCCESS, execution_plan=plan)
    assert art.execution_plan is plan


@pytest.mark.deterministic
def test_artifact_accepts_field_results() -> None:
    """field_results with valid str→FieldResult mapping is accepted."""
    fr = FieldResult(field_path="x", status=Status.SUCCESS)
    art = ExecutionArtifact(
        status=Status.SUCCESS,
        field_results={"x": fr},
    )
    assert art.field_results["x"] is fr


@pytest.mark.deterministic
def test_artifact_accepts_statistics() -> None:
    """statistics accepts a Statistics instance or None."""
    stats = Statistics(status=Status.SUCCESS)
    art = ExecutionArtifact(status=Status.SUCCESS, statistics=stats)
    assert art.statistics is stats
    art_none = ExecutionArtifact(status=Status.SUCCESS, statistics=None)
    assert art_none.statistics is None


@pytest.mark.deterministic
def test_artifact_accepts_created_at_custom() -> None:
    """A custom created_at string is accepted."""
    art = ExecutionArtifact(status=Status.SUCCESS, created_at="2026-06-25T12:00:00")
    assert art.created_at == "2026-06-25T12:00:00"


@pytest.mark.deterministic
def test_artifact_generates_unique_ids() -> None:
    """Each artifact gets a unique auto-generated ID."""
    art1 = _minimal_artifact()
    art2 = _minimal_artifact()
    assert art1.id != art2.id
