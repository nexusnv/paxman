"""UUID canonical-form constants.

Verbatim move of the three constants from `paxman._capabilities.builtins.uuid`.
The length/char/hyphen validation logic lives in `canonicalizer.py`; this
module is constants-only so behavior stays identical.

Mandate Law 1 (determinism): `CANONICAL_LENGTH` / `HYPHEN_POSITIONS` /
`CANONICAL_CHARS` fix the canonical 8-4-4-4-12 form so two
implementations agree. Mandate Law 2 (idempotence): re-canonicalizing an
already-canonical value yields the same value.
"""

from __future__ import annotations

# The canonical form has 36 chars total: 32 hex + 4 hyphens at positions
# 8, 13, 18, 23 (counting from 0). The first hex digit of the third
# group is the version-nibble (RFC 4122 §4.1.3).
CANONICAL_LENGTH = 36
HYPHEN_POSITIONS = frozenset({8, 13, 18, 23})
CANONICAL_CHARS = frozenset("0123456789abcdef-")
