from paxman._capabilities.phone.rules import _RULE_PROVENANCE, _evidence


def test_manifest_exhaustive_for_emitted_rules():
    # Every rule the capability can emit must have a manifest entry.
    emitted = {
        "not_a_phone_contract",
        "not_a_string_value",
        "unrecognized_format",
        "grammar_rejected",
        "no_transformation_needed",
    }
    for rule in emitted:
        assert rule in _RULE_PROVENANCE


def test_evidence_pulls_provenance():
    ev = _evidence("no_transformation_needed")
    assert ev.rule == "no_transformation_needed"
    assert ev.provenance  # non-empty citation


def test_unknown_rule_raises():
    import pytest

    with pytest.raises(KeyError):
        _evidence("not_a_real_rule")
