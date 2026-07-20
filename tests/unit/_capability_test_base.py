"""Reusable pytest base class for capability invariant tests (Finding B).

A capability's dedicated unit tests stay the source of truth for its exact
behaviour. This base class extracts the *shared* invariant surface every
built-in capability must honour (mandate Laws 1, 2, 4, 8a, 12):

- ``can_handle`` claims only its own contract and only string (or None) values.
- valid inputs canonicalize to the expected value (or carry the expected Status).
- canonicalization is idempotent (Law 2): ``canon(canon(x)) == canon(x)``.
- ``replay`` is byte-equal to the original artifact (Law 12).
- invalid / non-string inputs report the deterministic Status (Law 8).

Subclass it, set the class-level configuration hooks, and pytest collects the
``test_*`` methods. The base class itself is never collected (it has no
``test_*`` methods of its own at module scope — only instance methods on the
subclass are).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

import paxman
from paxman._core.status import Status


class CapabilityTestBase:
    """Base for capability invariant tests. Subclass and set the hooks.

    Class-level configuration hooks (set on the subclass):

    - ``capability_cls``: the capability class, e.g. ``EmailCapability``.
    - ``contract_factory``: zero-arg callable returning a default contract.
    - ``valid_cases``: ``list[tuple[str, str | Status]]``. If the expected
      value is a ``Status`` (not ``CANONICALIZED``), that status is asserted;
      if a string, ``Status.CANONICALIZED`` and ``artifact.value == expected``
      are asserted.
    - ``invalid_cases``: ``list[tuple[object, Status]]`` — (input, expected
      Status), e.g. ``("", Status.MISSING)`` or ``("!!!", Status.INVALID)``.
    - ``non_string_inputs``: ``list[object]`` — each must yield
      ``Status.INVALID`` (``not_a_string_value``).
    """

    capability_cls: type
    contract_factory: ClassVar[Callable[[], object]]
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = []
    invalid_cases: ClassVar[list[tuple[object, Status]]] = []
    non_string_inputs: ClassVar[list[object]] = []

    def _make_contract(self) -> object:
        """Build a fresh default contract via the subclass factory."""
        factory = type(self).contract_factory
        return factory()

    def test_can_handle_claims_own_contract(self) -> None:
        cap = self.capability_cls()
        assert cap.can_handle(self._make_contract(), "x") is True
        assert cap.can_handle(object(), "x") is False

    def test_can_handle_rejects_non_string(self) -> None:
        cap = self.capability_cls()
        for value in self.non_string_inputs:
            assert cap.can_handle(self._make_contract(), value) is False

    def test_valid_cases_canonicalize(self) -> None:
        for raw_input, expected in self.valid_cases:
            artifact = paxman.canonicalize(raw_input, self._make_contract())
            if isinstance(expected, Status):
                assert artifact.status is expected, (raw_input, expected, artifact.status)
            else:
                assert artifact.status is Status.CANONICALIZED, (
                    raw_input,
                    artifact.status,
                )
                assert artifact.value == expected, (raw_input, expected, artifact.value)

    def test_valid_cases_idempotent(self) -> None:
        for raw_input, expected in self.valid_cases:
            if isinstance(expected, Status) and expected is not Status.CANONICALIZED:
                continue
            contract = self._make_contract()
            first = paxman.canonicalize(raw_input, contract)
            if first.status is not Status.CANONICALIZED:
                continue
            second = paxman.canonicalize(first.value, contract)
            assert second.value == first.value, (raw_input, first.value, second.value)
            assert second.status is first.status, (raw_input, first.status, second.status)

    def test_valid_cases_replay_byte_equal(self) -> None:
        for raw_input, expected in self.valid_cases:
            if isinstance(expected, Status) and expected is not Status.CANONICALIZED:
                continue
            contract = self._make_contract()
            first = paxman.canonicalize(raw_input, contract)
            if first.status is not Status.CANONICALIZED:
                continue
            replayed = paxman.replay(first, contract)
            assert replayed == first, (raw_input, first, replayed)

    def test_invalid_cases_status(self) -> None:
        for raw_input, expected_status in self.invalid_cases:
            artifact = paxman.canonicalize(raw_input, self._make_contract())
            assert artifact.status is expected_status, (
                raw_input,
                expected_status,
                artifact.status,
            )

    def test_non_string_inputs_invalid(self) -> None:
        cap = self.capability_cls()
        for value in self.non_string_inputs:
            artifact = cap.canonicalize(value, self._make_contract())
            assert artifact.status is Status.INVALID, (value, artifact.status)
