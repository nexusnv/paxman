"""Tests for the shared Provenance value object."""

from paxman._capabilities._shared.grammar.provenance import Provenance


def test_provenance_minimal():
    p = Provenance(name="ISO 8601")
    assert p.name == "ISO 8601"
    assert p.version is None
    assert p.citation is None


def test_provenance_full():
    p = Provenance(
        name="NTP epoch", version="RFC 5905", citation="https://tools.ietf.org/html/rfc5905"
    )
    assert p.name == "NTP epoch"
    assert p.version == "RFC 5905"
    assert p.citation == "https://tools.ietf.org/html/rfc5905"


def test_provenance_is_frozen():
    p = Provenance(name="test")
    try:
        p.name = "other"
        assert False, "should be frozen"
    except AttributeError:
        pass


def test_provenance_equality():
    a = Provenance(name="ISO 8601", version="2024")
    b = Provenance(name="ISO 8601", version="2024")
    assert a == b


def test_provenance_inequality():
    a = Provenance(name="ISO 8601")
    b = Provenance(name="RFC 5322")
    assert a != b


def test_provenance_str_representation():
    p = Provenance(name="ISO 8601", version="2024")
    assert "ISO 8601" in repr(p)
