"""Built-in capability discovery.

Mandate §5.3: the user's knowledge wins over Paxman's. `load_builtins`
in the registry skips capabilities whose names are already registered,
so a user can override any built-in by registering their own
implementation before the first canonicalize call.

This explicit, deterministic discovery upholds Mandate Law 1
(determinism — the built-in set is fixed and known) and Law 6
(pipeline boundaries — discovery is part of the pipeline Paxman
owns, not user-redefinable).

Migrated from `paxman._capabilities.builtins.discovery` as part of the
additive architecture migration into `paxman._capabilities`.
"""

from __future__ import annotations

from paxman._capabilities.boolean.canonicalizer import BooleanCapability
from paxman._capabilities.date.canonicalizer import DateCapability
from paxman._capabilities.email.canonicalizer import EmailCapability
from paxman._capabilities.ip.canonicalizer import IPCapability
from paxman._capabilities.phone.canonicalizer import PhoneCapability
from paxman._capabilities.protocol import Capability
from paxman._capabilities.url.canonicalizer import URLCapability
from paxman._capabilities.uuid.canonicalizer import UUIDCapability


def builtin_capabilities() -> list[Capability]:
    """Return every built-in capability shipped with this Paxman version.

    The orchestrator calls this on the first `paxman.canonicalize` call
    and feeds the result to `registry.load_builtins(...)`. Adding a
    new built-in here makes it auto-registered before the first
    canonicalize; the user does not need to register it themselves.
    """
    # Governing laws for this wiring:
    # - Law 1 (Determinism): the built-in set is fixed and known; the order
    #   here is the deterministic registration order fed to load_builtins.
    # - Law 12 (Replayability) + Law 14 (Evidence provenance): every built-in
    #   contributes only deterministic, provenance-backed canonicalization so
    #   replay(byte-for-byte) holds across the whole built-in set.
    # - Mandate §5.3 (user knowledge wins): load_builtins skips names already
    #   registered, so a user can override any of these before first canonicalize.
    return [
        EmailCapability(),
        UUIDCapability(),
        DateCapability(),
        PhoneCapability(),
        URLCapability(),
        BooleanCapability(),
        IPCapability(),
    ]
