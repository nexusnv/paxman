import pytest

from paxman._capabilities.url.parser import default_port_for_scheme

# Mandate laws touched (Law 1 determinism, Law 3 never-guess on unknown
# schemes, Law 14 provenance for the IANA-derived default-port values):
# these tests pin the deterministic scheme -> default-port resolution.


@pytest.mark.parametrize(
    ("scheme", "port"),
    [
        ("http", 80),
        ("https", 443),
        ("ftp", 21),
        ("ftps", 990),
        ("ws", 80),
        ("wss", 443),
        ("ntp", 123),
        ("ldap", 389),
        ("ldaps", 636),
        ("telnet", 23),
        ("smtp", 25),
        ("pop", 110),
        ("imap", 143),
        ("rtsp", 554),
        ("sftp", 22),
    ],
)
def test_known_schemes(scheme: str, port: int):
    assert default_port_for_scheme(scheme) == port


def test_case_insensitive():
    assert default_port_for_scheme("HTTP") == 80
    assert default_port_for_scheme("Https") == 443


def test_unknown_scheme_is_none():
    assert default_port_for_scheme("gemini") is None
    assert default_port_for_scheme("not-a-scheme") is None
