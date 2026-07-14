# Reference: Errors

Paxman distinguishes between **outcomes** (returned on an artifact) and **exceptions** (raised when a call cannot proceed). This page documents the exception hierarchy and when each is raised.

## Outcomes vs. exceptions

| | Outcomes (Status values) | Exceptions |
|---|---|---|
| Returned via | `artifact.status` | `raise` |
| When | The call *can* proceed and reports what happened | The call *cannot* proceed at all |
| Examples | `CANONICALIZED`, `INVALID`, `AMBIGUOUS`, `UNSUPPORTED`, `MISSING` | `ContractError`, `VersionMismatchError`, `FrozenRegistryError`, `ConfigurationError` |
| What you do | Inspect the status and branch | Catch and handle (or let propagate) |

A canonicalize call should never raise an exception for a situation representable as a `Status`. If `paxman.canonicalize()` raises, something unexpected has happened.

## The exception hierarchy

```
PaxmanError
├── CanonicalizationError
│   ├── AmbiguousInputError
│   ├── UnsupportedContractError
│   ├── VersionMismatchError
│   ├── FrozenRegistryError
│   └── ConfigurationError
└── ContractError
```

All Paxman exceptions inherit from `PaxmanError`, which inherits from `Exception`. You can catch all paxman exceptions with `except PaxmanError`.

## `PaxmanError`

The base class. You usually catch this rather than `Exception` to handle all paxman errors at once.

## `CanonicalizationError`

Base class for runtime errors during canonicalization or replay. Subclasses are listed below.

## `ContractError`

The contract is malformed or self-contradictory. Raised **at parse time** (by `parse_contract()`), not by `canonicalize()` itself.

Common causes:

- The spec is not a dict and not a `CanonicalEmailContract`.
- The `kind` field is missing or not a string.
- The `kind` field is not one of the supported kinds.
- A bool field has a non-bool value.
- The `provider_aliases` field has a value other than `"none"` or `"gmail"`.

The orchestrator catches `ContractError` raised inside a capability and maps it to `Status.UNSUPPORTED` on the artifact, so a bad contract is reported as an outcome, not an exception. The exception is raised only when `parse_contract()` is called directly.

**Example:**

```python
import paxman
from paxman import ContractError

try:
    paxman.parse_contract({"kind": "unknown_kind"})
except ContractError as e:
    print(f"bad contract: {e}")
```

## `VersionMismatchError`

Raised by `paxman.replay()` when the artifact's `VersionStamp` does not match the current environment. The four components that must match are:

- `paxman_version`
- `contract_version`
- `capabilities_hash`
- `configuration_version`

Any mismatch raises `VersionMismatchError`. The exception is raised by `replay()` and never returned as a `Status`.

**Example:**

```python
import paxman
from paxman import Email, VersionMismatchError

result = paxman.canonicalize("User@Example.com", Email())
# ... time passes, the Paxman version changes ...

try:
    paxman.replay(result, Email())
except VersionMismatchError:
    print("artifact is from an older Paxman version")
```

## `FrozenRegistryError`

Raised by `paxman.register_capability()` (and by the registry's `register()` method directly) when the registry is already frozen. The default registry freezes implicitly on the first `paxman.canonicalize()` call.

**Example:**

```python
import paxman
from paxman import Email, register_capability, FrozenRegistryError

paxman.canonicalize("User@Example.com", Email())  # freezes the registry

try:
    register_capability(MyCapability())
except FrozenRegistryError:
    print("registry is frozen; cannot register")
```

To avoid this error, register all custom capabilities **before** the first `canonicalize()` call.

## `ConfigurationError`

Raised at register time when a capability is structurally invalid. Causes:

- The object is not a `Capability` (missing `name`, missing `can_handle`, or missing `canonicalize`).
- A capability with the same name is already registered.

**Example:**

```python
import paxman
from paxman import register_capability, ConfigurationError

class BadCapability:
    pass  # no name, no methods

try:
    register_capability(BadCapability())
except ConfigurationError as e:
    print(f"invalid capability: {e}")
```

## `AmbiguousInputError` and `UnsupportedContractError`

These are defensive exceptions raised only in code paths that should never run during normal use.

- `AmbiguousInputError` — the orchestrator detected multiple claimants; this is normally surfaced as `Status.AMBIGUOUS` on the artifact, not raised.
- `UnsupportedContractError` — validation or classification was asked about a contract kind it does not know; the orchestrator catches and yields `Status.UNSUPPORTED`.

If you catch one of these in normal application code, something has gone wrong in the library. Open an issue.

## Decision tree: when is it Status, when is it exception?

```
                    ┌─ Is the contract malformed?
                    │   YES → ContractError (at parse_contract time)
                    │
Did canonicalize()  │   NO
or replay()         │
raise?              ├─ Is the artifact's version stamp current?
                    │   NO → VersionMismatchError (at replay time)
                    │
                    │   YES
                    │
                    └─ Is the registry frozen (or capability invalid)?
                        YES → FrozenRegistryError / ConfigurationError
                            (at register_capability time)

                    None of the above?
                    → The call returned an artifact. Read artifact.status.
                    → Status is one of: CANONICALIZED, INVALID, MISSING,
                      AMBIGUOUS, UNSUPPORTED.
```

## What you should catch

In a typical application:

- Catch `ContractError` around `parse_contract()` calls (or, better, validate the contract shape before parsing).
- Catch `VersionMismatchError` around `replay()` calls (or, better, treat the version stamp as part of the artifact's identity and re-canonicalize the original input if the version has changed).
- Catch `FrozenRegistryError` around `register_capability()` calls (or, better, register everything at startup before the first canonicalize).
- Do not catch `ConfigurationError` in production code; it indicates a bug in your capability class.

You usually do not need to catch `PaxmanError` at the top level, because the outcomes (`Status` values) are returned on the artifact and your code already branches on them. A `PaxmanError` indicates a programmer error or a version mismatch, both of which deserve explicit handling rather than a blanket catch.

## Where to go next

- [API reference](api.md) — the full function signatures and exception lists.
- [Status and evidence](../concepts/status-and-evidence.md) — the outcomes and what each means.
- [How-to: Interpret the five outcomes](../how-to/interpret-the-5-statuses.md) — the recommended if/elif pattern.
