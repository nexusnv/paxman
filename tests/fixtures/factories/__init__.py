"""``factory_boy`` + ``faker`` programmatic fixtures for paxman tests.

Per Sprint 7 D7.4 and ``docs/TEST_DATA.md`` §7.1, this package contains
programmatic fixtures that generate realistic-looking test data
without using real (potentially PII-containing) production data.

All factories use ``factory.Faker`` with a shared ``seed`` (set in
``tests.fixtures.factories/__init__.py``) so that the same call sequence
produces byte-equal output across test runs.

Usage::

    from tests.fixtures.factories import contracts, inputs

    contract = contracts.DictDSLInvoiceFactory()
    text = inputs.InvoiceInputFactory()
"""

from __future__ import annotations

import factory.random

#: Default deterministic seed for all ``factory_boy`` factories in this
#: package. The seed is the hex encoding of ``"pax!"`` (the project
#: exclamation). It is recorded here so a failing test can be reproduced.
SEED: int = 0x70617821  # "pax!" in hex

#: Initialize ``factory_boy``'s global random state with the deterministic
#: seed. Tests that need a different seed should call :func:`reseed` with
#: the desired value before invoking any factory.
factory.random.reseed_random(SEED)


def reseed(seed: int) -> None:
    """Reseed ``factory_boy``'s global random state.

    Args:
        seed: The new seed value. Tests that need a non-default
            sequence of generated values should call this with a unique
            seed (e.g., ``reseed(int(time.time()))``).
    """
    factory.random.reseed_random(seed)
