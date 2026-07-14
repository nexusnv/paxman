"""Built-in capability discovery.

Mandate §5.3: the user's knowledge wins over Paxman's. `load_builtins`
in the registry skips capabilities whose names are already registered,
so a user can override any built-in by registering their own
implementation before the first canonicalize call.
"""

from __future__ import annotations

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.builtins.uuid import UUIDCapability
from paxman._capabilities.protocol import Capability


def builtin_capabilities() -> list[Capability]:
    """Return every built-in capability shipped with this Paxman version.

    The orchestrator calls this on the first `paxman.canonicalize` call
    and feeds the result to `registry.load_builtins(...)`. Adding a
    new built-in here makes it auto-registered before the first
    canonicalize; the user does not need to register it themselves.
    """
    return [EmailCapability(), UUIDCapability()]
