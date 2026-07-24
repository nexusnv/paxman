"""RecognizedRep — a single grammar match with raw captures."""

from __future__ import annotations

from collections.abc import Mapping

import attrs

from paxman._capabilities._shared.grammar.provenance import Provenance


@attrs.frozen
class RecognizedRep:
    """A single grammar match: raw string captures, no semantic meaning.

    Attributes:
        grammar_id: The id of the matching grammar.
        provenance: The matching grammar's provenance (Provenance object).
        raw: The full matched substring.
        shape: The matching grammar's shape tag (may be ``None``).
        captures: Raw string captures keyed by regex group name.
            Only groups that participated in the match are present —
            recognition assigns NO meaning.
    """

    grammar_id: str
    provenance: Provenance
    raw: str
    shape: str | None
    captures: Mapping[str, str]
