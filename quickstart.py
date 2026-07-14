"""5-Minute Promise quickstart — runnable on first clone.

Verifies: git clone && uv sync && uv run python quickstart.py works
without any private-module imports, without a register_capability call
for the built-in email capability, and prints the canonical value, its
evidence, and a replay byte-equality check.
"""

import paxman
from paxman import Email

result = paxman.canonicalize(
    "  John.Doe@Gmail.COM  ",
    Email(provider_aliases="gmail"),
)
print(result.status.name, "->", result.value)
print("evidence:", [(e.rule, e.detail) for e in result.evidence])

rehydrated = paxman.replay(result, Email(provider_aliases="gmail"))
assert rehydrated == result
print("replay ok")
