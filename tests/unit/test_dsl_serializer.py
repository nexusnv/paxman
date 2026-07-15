from paxman._capabilities.date.contract import Date
from paxman._capabilities.email.contract import Email
from paxman._capabilities.uuid.contract import UUID
from paxman._dsl.serializer import serialize_contract


def test_serialize_email() -> None:
    c = Email(provider_aliases="gmail")
    d = serialize_contract(c)
    assert d == {
        "kind": "canonical_email",
        "lowercase": True,
        "strip_whitespace": True,
        "provider_aliases": "gmail",
        "strict": False,
        "version": 1,
    }


def test_serialize_uuid() -> None:
    assert serialize_contract(UUID(version="4"))["version"] == "4"


def test_serialize_date() -> None:
    assert serialize_contract(Date(locale="ISO"))["locale"] == "ISO"
