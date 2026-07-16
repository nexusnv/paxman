"""The Dict DSL parser.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The DSL is a closed vocabulary: `kind`
is a fixed set, and an unknown `kind` raises `ContractError` at parse time
(the orchestrator catches that and yields `Status.UNSUPPORTED`).

The parser is registry-driven: each capability domain registers a builder at
import time (see `paxman._capabilities.<domain>.contract`); `parse_contract`
asks the contract registry and never names a concrete contract class. The
public `Contract` union of concrete contracts lives in `paxman.__init__`.
"""

from __future__ import annotations

from typing import Any

from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.phone.contract import CanonicalPhoneContract
from paxman._capabilities.url.contract import CanonicalURLContract
from paxman._capabilities.uuid.contract import CanonicalUUIDContract
from paxman._errors import ContractError
from paxman._registry.contract_registry import get_builder

# Importing the domain contract modules registers their builders with the
# contract registry (register_contract), so get_builder resolves every kind.
# Importing them here also binds the concrete classes referenced by the
# isinstance short-circuit below.


def parse_contract(
    spec: Any,
) -> (
    CanonicalEmailContract
    | CanonicalUUIDContract
    | CanonicalDateContract
    | CanonicalPhoneContract
    | CanonicalURLContract
):
    """Parse a Dict DSL contract into a Contract value object.

    Raises `ContractError` on:
    - non-dict input (unless it's already a contract value object)
    - missing or unknown `kind`
    - invalid field values (wrong type, unknown provider_aliases)
    """
    # Short-circuit: an already-parsed contract value object is the
    # source of truth (Law 5). Exact-type checks (not the parent
    # `Contract` alias) so a future multi-field contract type is NOT
    # silently absorbed here — it must grow its own dispatch branch.
    if isinstance(spec, CanonicalEmailContract):
        return spec
    if isinstance(spec, CanonicalUUIDContract):
        return spec
    if isinstance(spec, CanonicalDateContract):
        return spec
    if isinstance(spec, CanonicalPhoneContract):
        return spec
    if isinstance(spec, CanonicalURLContract):
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
