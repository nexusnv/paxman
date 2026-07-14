"""Contract adapters.

v2.0.0 supports two equivalent contract forms:

1. **Dict DSL** — `{"kind": "canonical_email", "lowercase": True, ...}`.
   The closed `kind` discriminator is the wire form; an unknown `kind`
   raises `ContractError` at parse time.
2. **Value-object / factory form** — `CanonicalEmailContract(...)` or
   the `Email(...)` domain-type factory. `parse_contract` short-circuits
   on an already-parsed `CanonicalEmailContract` (Law 5 — the contract
   is the truth), so calling `parse_contract(Email(...))` is a no-op
   identity.

Both forms resolve to the same `CanonicalEmailContract` value object
that the orchestrator and capabilities consume.
"""

from paxman._contracts.contract import (
    UUID,
    CanonicalDateContract,
    CanonicalEmailContract,
    CanonicalUUIDContract,
    Contract,
    Date,
    parse_contract,
)

__all__ = [
    "UUID",
    "CanonicalDateContract",
    "CanonicalEmailContract",
    "CanonicalUUIDContract",
    "Contract",
    "Date",
    "parse_contract",
]
