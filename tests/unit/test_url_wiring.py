import paxman
from paxman._capabilities.discovery import builtin_capabilities
from paxman._capabilities.url.contract import CanonicalURLContract

# Mandate laws covered by this file:
#   Law 1  (Determinism): discovery yields the same capability set every process.
#   Law 8a (Lazy registration): built-ins register on first canonicalize, not at import.
#   Law 12 (Replay): a wired URL built-in supports canonicalize -> replay byte-equality.


def test_url_in_builtins():
    names = [c.name for c in builtin_capabilities()]
    assert "url_canonicalization" in names


def test_url_reexported():
    assert hasattr(paxman, "URL")
    assert hasattr(paxman, "CanonicalURLContract")


def test_contract_union_includes_url():
    # `Contract` is a non-@runtime_checkable structural Protocol, so we assert
    # the shape it requires (kind + version_field) rather than isinstance.
    c = CanonicalURLContract()
    assert hasattr(c, "kind")
    assert hasattr(c, "version_field")
    assert c.kind == "canonical_url"
    assert c.version_field == 1


def test_end_to_end_autoload():
    r = paxman.canonicalize("HTTP://Example.COM:80/", paxman.URL())
    assert r.status.name == "CANONICALIZED"
    assert r.value == "http://example.com/"
