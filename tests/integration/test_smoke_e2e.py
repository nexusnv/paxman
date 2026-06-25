"""E2E smoke test — paxman.normalize() with a real Dict DSL contract and Pydantic contract.

Exercises the full normalize pipeline: contract adaptation → planning →
execution → reconciliation → artifact assembly. Since no V1 capabilities
are registered in the test environment, all required fields are expected
to be UNRESOLVED — but the artifact should still be well-formed.
"""

from __future__ import annotations

import pytest

import paxman

# Trigger auto-registration for Dict DSL adapter on import.
# Without this, the contract registry has no adapter for ``format_id="dict_dsl"``.
import paxman.contract.adapters.dict_dsl
from paxman.artifact.artifact import ExecutionArtifact
from paxman.types import Status
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

pytestmark = pytest.mark.integration


class TestSmokeE2E:
    """End-to-end smoke tests for ``paxman.normalize()``."""

    # ------------------------------------------------------------------
    # W3a: Dict DSL contract smoke test
    # ------------------------------------------------------------------

    def test_normalize_dict_dsl_returns_artifact(self) -> None:
        """Calling ``normalize()`` with a Dict DSL contract returns an ``ExecutionArtifact``."""
        artifact = paxman.normalize(
            input_data="ACME Corp\nInvoice #1234\nTotal: $1,234.56",
            contract=DICT_DSL_INVOICE,
        )

        # 1. Type check
        assert isinstance(artifact, ExecutionArtifact)

        # 2. replay_hash is a non-empty 64-char lowercase hex string
        assert isinstance(artifact.replay_hash, str)
        assert len(artifact.replay_hash) == 64
        assert all(c in "0123456789abcdef" for c in artifact.replay_hash)

        # 3. id is a non-empty string
        assert isinstance(artifact.id, str)
        assert artifact.id

        # 4. contract_id matches the Dict DSL contract
        assert artifact.contract_id == "invoice-v1"

        # 5. status is a valid Status enum value
        assert isinstance(artifact.status, Status)

        # 6. paxman_version matches the library version
        assert artifact.paxman_version == paxman.__version__

    # ------------------------------------------------------------------
    # W3a: Pydantic contract smoke test
    # ------------------------------------------------------------------

    def test_normalize_pydantic_contract_works(self) -> None:
        """Calling ``normalize()`` with a Pydantic contract returns a valid artifact.

        The Pydantic adapter must be auto-registered for this to work.
        """
        # Trigger Pydantic adapter auto-registration.
        import paxman.contract.adapters.pydantic
        from tests.fixtures.contracts.pydantic.invoice import Invoice

        artifact = paxman.normalize(
            input_data="some text",
            contract=Invoice,
        )

        assert isinstance(artifact, ExecutionArtifact)
        assert isinstance(artifact.status, Status)
        # The Pydantic adapter registers and adapts successfully, so
        # the artifact should NOT have INVALID_CONTRACT status.
        assert artifact.status is not Status.INVALID_CONTRACT
        # The contract id is derived from the model's class name.
        assert artifact.contract_id == "Invoice"
