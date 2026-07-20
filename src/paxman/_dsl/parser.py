"""The Dict DSL parser.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The DSL is a closed vocabulary: `kind`
is a fixed set, and an unknown `kind` raises `ContractError` at parse time
(the orchestrator catches that and yields `Status.UNSUPPORTED`).

Dict specs are resolved via the contract registry (`get_builder`): each
capability domain registers a builder at import time
(see `paxman._capabilities.<domain>.contract`), and `parse_contract` asks the
registry by `kind` — it never names a concrete contract class. An
already-parsed contract value object is returned by identity through a
structural `Contract` Protocol check (the module no longer enumerates
concrete contract classes). The public `Contract` union of concrete contracts
lives in `paxman.__init__`.
"""

from __future__ import annotations

from typing import Any

from paxman._core.contracts import Contract
from paxman._errors import ContractError
from paxman._registry.contract_registry import get_builder

# Importing the domain contract modules registers their builders with the
# contract registry (register_contract), so get_builder resolves every kind.


def parse_contract(
    spec: Any,
) -> Contract:
    """Parse a Dict DSL contract into a Contract value object.

    Raises `ContractError` on:
    - non-dict input (unless it's already a contract value object)
    - missing or unknown `kind`
    - invalid field values (wrong type, unknown provider_aliases)

    An already-parsed contract value object satisfies the structural
    `Contract` Protocol and is returned by identity (Law 5) — no
    reconstruction. Dict specs are dispatched through the contract registry
    via `get_builder(kind)`.
    """
    # Identity: an already-parsed contract value object is the source of
    # truth (Law 5). A single structural Protocol check replaces the former
    # per-domain isinstance branches — any value object satisfying `Contract`
    # is returned unchanged, and a future contract type needs no new branch.
    if isinstance(spec, Contract):
        return spec

    if not isinstance(spec, dict):
        raise ContractError(f"contract must be a dict, got {type(spec).__name__}")

    kind = spec.get("kind")
    if not isinstance(kind, str):
        raise ContractError("contract must have a string 'kind' field")

    # Registry-driven dispatch. The builder performs the per-kind field
    # validation and raises ContractError on invalid input — byte-identical
    # to the former inline branches.
    builder = get_builder(kind)
    return builder(spec)
