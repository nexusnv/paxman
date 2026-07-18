"""5-Minute Promise quickstart — runnable on first clone.

Verifies: git clone && uv sync && uv run python quickstart.py works
without any private-module imports, without a register_capability call
for the built-in email capability, and prints the canonical value, its
evidence, and a replay byte-equality check.
"""

import paxman
from paxman import Country, Edition, Email, Engine, canonicalize_with

result = paxman.canonicalize(
    "  John.Doe@Gmail.COM  ",
    Email(provider_aliases="gmail"),
)
print(result.status.name, "->", result.value)
print("evidence:", [(e.rule, e.detail) for e in result.evidence])

rehydrated = paxman.replay(result, Email(provider_aliases="gmail"))
assert rehydrated == result
print("replay ok")

# Pin a non-default authority edition via the Engine (Concern 3). The
# zero-config path above uses Engine.default(); canonicalize_with binds an
# explicit edition so the recorded artifact is replay-deterministic against it.
# Paxman bundles only the latest edition of each registry (ISO 3166-1:2024),
# so pinning it (or any edition it ships) records that edition.
eng = Engine.with_authorities({"ISO 3166-1": Edition("2024")})
pinned = canonicalize_with("malaysia", Country(allow_name=True), eng)
assert {a.name: a.edition for a in pinned.authorities}["ISO 3166-1"] == "2024"
print("pinned edition:", {a.name: a.edition for a in pinned.authorities}["ISO 3166-1"])
