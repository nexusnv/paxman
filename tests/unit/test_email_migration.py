from paxman._capabilities.email.contract import CanonicalEmailContract, Email
from paxman._capabilities.email.grammar import recognize


def test_email_recognize_delegates_to_shared():
    reps = recognize("John.Doe@Gmail.COM", CanonicalEmailContract())
    assert any(r.grammar_id == "addr_spec" for r in reps)


def test_email_recognize_wrong_contract_empty():
    class _Other:
        pass

    assert recognize("John.Doe@Gmail.COM", _Other()) == []


def test_email_evidence_still_resolves_manifest():
    from paxman._capabilities.email.rules import _evidence

    e = _evidence("lowercased_domain")
    assert e.rule == "lowercased_domain"
    assert e.authority is not None


def test_email_authority_override_field_present():
    c = Email(authority_override={"ISO 4217": "2024"})
    assert c.authority_override == {"ISO 4217": "2024"}


def test_email_authority_override_excluded_from_as_dict():
    c = Email(authority_override={"ISO 4217": "2024"})
    assert "authority_override" not in c.as_dict()
