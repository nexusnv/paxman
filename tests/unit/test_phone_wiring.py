"""Wiring tests for the phone capability.

These tests verify the constitutional guarantees the wiring must preserve:
- Law 1 (Determinism): phone is part of the fixed, known built-in set.
- Mandate §5.3 (user knowledge wins): the public surface re-exports Phone and
  CanonicalPhoneContract, and the Contract union admits the phone contract.
- Replay/registration integrity: a phone contract round-trips through the
  public autoload path (builtin_capabilities -> load_builtins -> canonicalize).
"""

import paxman
from paxman._capabilities.discovery import builtin_capabilities
from paxman._capabilities.phone.contract import CanonicalPhoneContract, Phone


def test_phone_in_builtins():
    names = {c.name for c in builtin_capabilities()}
    assert "phone_canonicalization" in names


def test_public_reexports():
    assert hasattr(paxman, "Phone")
    assert hasattr(paxman, "CanonicalPhoneContract")


def test_contract_union_includes_phone():
    c: paxman.Contract = Phone()
    assert isinstance(c, CanonicalPhoneContract)


def test_end_to_end_autoload():
    art = paxman.canonicalize("(650) 253-0000", Phone(country="US"))
    assert art.status.name == "CANONICALIZED"
    assert art.value == "+16502530000"
