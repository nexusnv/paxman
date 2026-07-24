"""Grammar class and factory functions for the shared recognition scaffold."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from types import MappingProxyType

import attrs

from paxman._capabilities._shared.grammar.provenance import Provenance


@attrs.frozen
class Grammar:
    """A single recognition rule: an id, provenance, and recognition function.

    Attributes:
        id: Stable identifier for this grammar rule (e.g., ``"addr_spec"``).
        provenance: Structured provenance record (Provenance object).
        recognize_fn: Recognition function. Takes a raw string, returns raw
            captures (if matched) or None (if not).
        shape: Optional shape tag for disambiguation (e.g., ``"date"``).
    """

    id: str
    provenance: Provenance
    recognize_fn: Callable[[str], Mapping[str, str] | None]
    shape: str | None = None


def make_grammar(
    id: str,
    provenance: Provenance,
    pattern: str,
    shape: str | None = None,
) -> Grammar:
    """Create a grammar rule from a regex pattern.

    Compiles the regex and wraps it in a ``recognize_fn`` that performs a
    ``fullmatch`` and returns the named groups as a ``MappingProxyType``.
    """
    compiled = re.compile(pattern)

    def recognize_fn(value: str) -> Mapping[str, str] | None:
        match = compiled.fullmatch(value)
        if match is None:
            return None
        return MappingProxyType(
            {k: v for k, v in match.groupdict().items() if v is not None}
        )

    return Grammar(id=id, provenance=provenance, recognize_fn=recognize_fn, shape=shape)


def parser_grammar(
    id: str,
    provenance: Provenance,
    parser_fn: Callable[[str], Mapping[str, str] | None],
    shape: str | None = None,
) -> Grammar:
    """Create a grammar rule from a parser function."""
    return Grammar(id=id, provenance=provenance, recognize_fn=parser_fn, shape=shape)
