from paxman._capabilities.date.contract import Date
from paxman._capabilities.email.contract import Email
from paxman._capabilities.uuid.contract import UUID
from paxman._dsl.parser import parse_contract
from paxman._dsl.serializer import serialize_contract


def test_serialize_email() -> None:
    c = Email(provider_aliases="gmail")
    d = serialize_contract(c)
    # Assert the complete serialized mapping, not just one field.
    assert d == {
        "kind": "canonical_email",
        "lowercase": True,
        "strip_whitespace": True,
        "provider_aliases": "gmail",
        "strict": False,
        "output_format": "email",
        "include_grammar": (),
        "exclude_grammar": (),
        "version": 1,
    }
    # Round-trips back to an equivalent contract via parse_contract.
    assert parse_contract(d) == c


def test_serialize_uuid() -> None:
    c = UUID(version="4")
    d = serialize_contract(c)
    # Assert the complete serialized mapping, not just the version field.
    assert d == {
        "kind": "canonical_uuid",
        "version": "4",
        "output_format": "hex",
        "include_grammar": (),
        "exclude_grammar": (),
        "version_field": 1,
    }
    # Round-trips back to an equivalent contract via parse_contract.
    assert parse_contract(d) == c


def test_serialize_date() -> None:
    c = Date(locale="ISO")
    d = serialize_contract(c)
    # Assert the complete serialized mapping, not just one field.
    # language and two_digit_year are exposed per spec §3.
    assert d == {
        "kind": "canonical_date",
        "locale": "ISO",
        "language": "en",
        "two_digit_year": None,
        "output_format": "iso",
        "include_grammar": (),
        "exclude_grammar": (),
        "version_field": 1,
    }
    # Round-trips back to an equivalent contract via parse_contract.
    assert parse_contract(d) == c
