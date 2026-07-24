"""The DSL parser (Dict and String forms).

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The DSL is a closed vocabulary: `kind`
is a fixed set, and an unknown `kind` raises `ContractError` at parse time
(the orchestrator catches that and yields `Status.UNSUPPORTED`).

Supports two concrete forms:
- **Dict DSL**: ``{"kind": "canonical_date", "locale": "US"}``
- **String DSL**: ``Date(locale="US", output_format="compact")``

Both forms are resolved via the contract registry (``get_builder``): each
capability domain registers a builder at import time
(see ``paxman._capabilities.<domain>.contract``), and ``parse_contract``
asks the registry by ``kind`` — it never names a concrete contract class.
An already-parsed contract value object is returned by identity through a
structural ``Contract`` Protocol check (the module no longer enumerates
concrete contract classes). The public ``Contract`` union of concrete
contracts lives in ``paxman.__init__``.
"""

from __future__ import annotations

import ast
from typing import Any

from paxman._core.contracts import Contract
from paxman._errors import ContractError
from paxman._registry.contract_registry import get_builder

# Importing the domain contract modules registers their builders with the
# contract registry (register_contract), so get_builder resolves every kind.

# Mapping from user-facing contract factory names (e.g. ``"Date"``) to the
# registered builder kind strings (e.g. ``"canonical_date"``).  This map is
# the single source of truth for the string-form DSL name resolution
# (Law 7 — Explicit Over Clever).
_STRING_DSL_NAME_MAP: dict[str, str] = {
    "Boolean": "canonical_boolean",
    "Country": "canonical_country",
    "Date": "canonical_date",
    "Email": "canonical_email",
    "Geolocation": "canonical_geolocation",
    "IP": "canonical_ip",
    "Money": "canonical_money",
    "Phone": "canonical_phone",
    "URL": "canonical_url",
    "UUID": "canonical_uuid",
}


def _parse_string_dsl(spec: str) -> dict[str, Any]:
    """Parse a string-form DSL expression into a dict for builder dispatch.

    Accepts the call-like syntax:
    ``Date(locale="US", output_format="compact")``.

    The function name is mapped to a registered kind via
    ``_STRING_DSL_NAME_MAP``.  Keyword argument values are evaluated with
    ``ast.literal_eval`` (strings, ints, bools, None, tuples, lists, dicts).

    Raises ``ContractError`` on non-call syntax, unknown function names,
    ``**kwargs`` usage, or unparseable argument values.
    """
    spec_stripped = spec.strip()
    if not spec_stripped.endswith(")"):
        raise ContractError(
            f"invalid string contract DSL: expected function-call form, got {spec!r}"
        )

    try:
        tree = ast.parse(spec_stripped, mode="eval")
    except SyntaxError as exc:
        raise ContractError(f"invalid string contract DSL: {spec!r}") from exc

    if not isinstance(tree.body, ast.Call):
        raise ContractError(
            f"invalid string contract DSL: expected function-call form, got {spec!r}"
        )

    if isinstance(tree.body.func, ast.Name):
        name = tree.body.func.id
    else:
        raise ContractError(f"invalid string contract DSL: expected simple name, got {spec!r}")

    kind = _STRING_DSL_NAME_MAP.get(name)
    if kind is None:
        supported = sorted(_STRING_DSL_NAME_MAP)
        raise ContractError(
            f"unknown contract name in string DSL: {name!r}; supported names: {supported}"
        )

    # Reject positional args and **kwargs (Law 7 — explicit keyword arguments only).
    if tree.body.args:
        raise ContractError(f"positional arguments not supported in string contract DSL: {spec!r}")
    if any(kw.arg is None for kw in tree.body.keywords):
        raise ContractError(f"**kwargs not supported in string contract DSL: {spec!r}")

    kwargs: dict[str, Any] = {}
    for kw in tree.body.keywords:
        assert kw.arg is not None  # guarded above
        try:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, TypeError) as exc:
            raise ContractError(
                f"invalid argument value in string DSL for {kw.arg!r}: {spec!r}"
            ) from exc

    kwargs["kind"] = kind
    return kwargs


def parse_contract(
    spec: Any,
) -> Contract:
    """Parse a Dict DSL or string DSL contract into a Contract value object.

    Supports two forms:
    - **Dict DSL**: ``{"kind": "canonical_date", "locale": "US"}``
    - **String DSL**: ``Date(locale="US", output_format="compact")``

    Raises `ContractError` on:
    - unsupported input type (not dict, string, or contract value object)
    - missing or unknown `kind`
    - invalid field values (wrong type, unknown provider_aliases)

    An already-parsed contract value object satisfies the structural
    `Contract` Protocol and is returned by identity (Law 5) — no
    reconstruction.  Dict specs are dispatched through the contract registry
    via `get_builder(kind)`.  String specs are parsed into a dict and
    dispatched through the same path.
    """
    # Identity: an already-parsed contract value object is the source of
    # truth (Law 5). A single structural Protocol check replaces the former
    # per-domain isinstance branches — any value object satisfying `Contract`
    # is returned unchanged, and a future contract type needs no new branch.
    if isinstance(spec, Contract):
        return spec

    # String DSL form: 'Date(locale="US", output_format="compact")'
    if isinstance(spec, str):
        spec = _parse_string_dsl(spec)

    if not isinstance(spec, dict):
        raise ContractError(f"contract must be a dict or string, got {type(spec).__name__}")

    kind = spec.get("kind")
    if not isinstance(kind, str):
        raise ContractError("contract must have a string 'kind' field")

    # Registry-driven dispatch. The builder performs the per-kind field
    # validation and raises ContractError on invalid input — byte-identical
    # to the former inline branches.
    builder = get_builder(kind)
    return builder(spec)
