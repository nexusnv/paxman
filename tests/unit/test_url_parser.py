import pytest

from paxman._capabilities.url.parser import _SCHEME_TO_DEFAULT_PORT, default_port_for_scheme

# Mandate laws touched (Law 1 determinism, Law 3 never-guess on unknown
# schemes, Law 14 provenance for the IANA-derived default-port values):
# these tests pin the deterministic scheme -> default-port resolution.


@pytest.mark.parametrize(
    ("scheme", "port"),
    [(s, p) for s, p in _SCHEME_TO_DEFAULT_PORT.items()],
)
def test_known_schemes(scheme: str, port: int):
    assert default_port_for_scheme(scheme) == port


def test_case_insensitive():
    assert default_port_for_scheme("HTTP") == 80
    assert default_port_for_scheme("Https") == 443


def test_unknown_scheme_is_none():
    assert default_port_for_scheme("gemini") is None
    assert default_port_for_scheme("not-a-scheme") is None
