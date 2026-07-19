from paxman._capabilities.uuid.contract import UUID, CanonicalUUIDContract
from paxman._capabilities.uuid.grammar import recognize


def test_uuid_recognize_delegates_to_shared():
    reps = recognize("abcd1234-abcd-1234-abcd-1234567890ab", CanonicalUUIDContract())
    assert len(reps) == 1
    assert reps[0].grammar_id == "canonical_uuid"


def test_uuid_recognize_wrong_contract_empty():
    class _Other:
        pass

    assert recognize("abcd1234-abcd-1234-abcd-1234567890ab", _Other()) == []


def test_uuid_evidence_still_resolves_manifest():
    from paxman._capabilities.uuid.rules import _evidence

    e = _evidence("no_transformation_needed")
    assert e.rule == "no_transformation_needed"
    assert e.authority is not None


def test_uuid_authority_override_field_present():
    c = CanonicalUUIDContract(authority_override={"ISO 4217": "2024"})
    assert c.authority_override == {"ISO 4217": "2024"}


def test_uuid_authority_override_excluded_from_as_dict():
    # The override is an escape hatch for a single call; it must never enter
    # the canonical Dict-DSL form (canonical-form parity / replay determinism).
    c = UUID(authority_override={"ISO 4217": "2024"})
    assert "authority_override" not in c.as_dict()
