# Paxman v2.0.0-rc1

This is the first release candidate of Paxman v2.0.0. It is published to
[TestPyPI](https://test.pypi.org/project/paxman/) first for verification
before being promoted to the production [PyPI](https://pypi.org/project/paxman/).

## What ships in v2.0.0-rc1

Paxman is a deterministic canonicalization engine. It transforms equivalent
representations of known information into a single canonical form. When the
input does not contain enough information to determine a unique result,
Paxman reports that fact rather than guessing.

### The three public verbs

- `paxman.canonicalize(input, contract)` — produce a canonical artifact.
- `paxman.replay(artifact, contract)` — byte-equal rehydration without
  re-executing the capability.
- `paxman.register_capability(capability)` — register a custom capability
  with the default registry before the first `canonicalize()` call.

### The Built-In Capabilities

v2.0.0-rc1 ships with two built-in capabilities:

- `email_canonicalization` — canonicalizes email addresses under the
  `canonical_email` contract kind. The contract is built with the
  `Email()` factory. See
  [Email capability spec](../capabilities/email/index.md) for the full
  rule table.
- `uuid_canonicalization` — canonicalizes UUIDs under the
  `canonical_uuid` contract kind. The contract is built with the
  `UUID()` factory. See
  [UUID capability spec](../capabilities/uuid/index.md) for the full
  rule table.

### The five outcomes

Every `canonicalize()` call returns an `ExecutionArtifact` with one of
five `Status` values:

- `CANONICALIZED` — the input was canonicalized.
- `INVALID` — the input cannot satisfy the contract.
- `MISSING` — the contract requires information the input does not provide.
- `AMBIGUOUS` — more than one capability claimed the pair; Paxman will not
  pick one.
- `UNSUPPORTED` — no capability declared it canonicalizes this pair, or
  the contract's `kind` is not recognized.

These are outcomes, not exceptions. See
[Status and evidence](../concepts/status-and-evidence.md).

### The three invariants

Every artifact satisfies three invariants. See
[The three invariants](../concepts/the-three-invariants.md).

- **Identity** — Paxman only canonicalizes; it never interprets, infers,
  or orchestrates.
- **Determinism** — same input, contract, registered capabilities,
  configuration, and Paxman version produce the same artifact.
- **Replay** — `replay(artifact, contract) == artifact` byte-for-byte,
  without re-executing the capability.

## Verify the install

After installing paxman from this release candidate, run the verification
checklist from [Verify the install](../getting-started/verify.md). Each
item is a command; the expected outputs confirm the install is working.

```bash
# 1. The package imports
uv run python -c "import paxman"

# 2. The version is reported
uv run python -c "import paxman; print(paxman.__version__)"

# 3. The public surface is importable
uv run python -c "
from paxman import (
    canonicalize, replay, register_capability, parse_contract,
    Email, CanonicalEmailContract, Contract, Capability, CapabilityRegistry,
    ExecutionArtifact, Status, Evidence, VersionStamp, CapabilityResult,
    ValidationResult,
    PaxmanError, CanonicalizationError, ContractError,
    UnsupportedContractError, VersionMismatchError,
    FrozenRegistryError, ConfigurationError,
)
print('ok')
"

# 4. The quickstart produces the documented output
uv run python quickstart.py

# 5. A canonicalize call returns an artifact
uv run python -c "
import paxman
from paxman import Email, Status
result = paxman.canonicalize('User@Example.com', Email())
assert result.status is Status.CANONICALIZED
assert result.value == 'user@example.com'
print('ok')
"

# 6. Replay rehydrates byte-for-byte
uv run python -c "
import paxman
from paxman import Email
result = paxman.canonicalize('User@Example.com', Email())
rehydrated = paxman.replay(result, Email())
assert rehydrated == result
print('ok')
"
```

If every step prints `ok` (or the expected output), the install is working.

## Known limitations

v2.0.0-rc1 ships with two built-in capabilities: email_canonicalization
and uuid_canonicalization. Other canonical
types (date, money, URL, etc.) are not in this release candidate.

The email capability is intentionally narrow in v2.0.0-rc1. It does not
accept:

- Quoted-string local parts (`"foo"@example.com`).
- Bracketed IPv4 or IPv6 domain-literals (`user@[127.0.0.1]`,
  `user@[IPv6:::1]`).
- Internationalized email addresses (IDN).

Future v2.x versions may extend the grammar gate. The contract `version`
is part of the artifact's `VersionStamp`; any grammar extension will be
visible on every new artifact.

## How to install

```bash
# TestPyPI verification:
uv pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  paxman==2.0.0rc1

# Production PyPI (after rc1 is promoted):
uv pip install paxman==2.0.0
```

## Where to report issues

Open an issue on the project's issue tracker. For security
vulnerabilities, follow the disclosure process in `SECURITY.md`; do not
open a public issue.
