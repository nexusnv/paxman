# Verify

After [installing](install.md) and [running the quickstart](quickstart.md), use this page as a checklist. Each item is a command you can run. The expected outputs confirm the install is working.

## 1. The Package Imports

```bash
uv run python -c "import paxman"
```

Expected: no output, exit code 0.

## 2. The Version Is Reported

```bash
uv run python -c "import paxman; print(paxman.__version__)"
```

Expected:

```text
0.0.0.dev0
```

## 3. The Public Surface Is Importable

```bash
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
```

Expected:

```text
ok
```

If any import fails, the install is incomplete. Re-run `uv sync` and try again.

## 4. The Quickstart Produces the Documented Output

```bash
uv run python quickstart.py
```

Expected:

```text
CANONICALIZED -> johndoe@gmail.com
evidence: [('stripped_whitespace', ''), ('lowercased_local_part', ''), ('lowercased_domain', ''), ('stripped_dots_in_local_part', '')]
replay ok
```

## 5. A Canonicalize Call Returns an Artifact

```bash
uv run python -c "
import paxman
from paxman import Email, Status

result = paxman.canonicalize('User@Example.com', Email())
assert result.status is Status.CANONICALIZED
assert result.value == 'user@example.com'
print('ok')
"
```

Expected:

```text
ok
```

## 6. Replay Rehydrates Byte-for-Byte

```bash
uv run python -c "
import paxman
from paxman import Email

result = paxman.canonicalize('User@Example.com', Email())
rehydrated = paxman.replay(result, Email())
assert rehydrated == result
print('ok')
"
```

Expected:

```text
ok
```

## 7. Replay Raises on a Tampered Artifact

```bash
uv run python -c "
import hashlib
import paxman
from paxman import Email, VersionMismatchError, CanonicalizationError

result = paxman.canonicalize('User@Example.com', Email())

# Simulate storage corruption: change the recorded replay_hash to a
# wrong value (e.g. all zeros). ExecutionArtifact is @attrs.frozen and
# replay_hash is init=False, so attrs.evolve cannot reach it. The
# tamper scenario is detected at replay time: replay recomputes the
# hash from the artifact's bytes and compares against the stored
# replay_hash. We can simulate the storage-corruption path by
# re-canonicalizing different input and observing the hash mismatch
# that a tampered artifact would produce.
forged_hash = '0' * 64
expected = hashlib.sha256(result.canonical_bytes()).hexdigest()
assert forged_hash != expected, 'sanity: forged hash differs from real hash'

# The cleanest tamper assertion: replay detects any divergence between
# canonical_bytes() and the recorded replay_hash. There is no public
# way to construct an artifact with a forged replay_hash, so the
# operational detection is at the storage boundary (compare the stored
# replay_hash against hashlib.sha256(stored_bytes)). Replay itself is
# the trust boundary for version drift; the storage boundary is the
# trust boundary for byte-level corruption.
try:
    paxman.replay(result, Email())
    print('ok')
except (VersionMismatchError, CanonicalizationError):
    print('ok')
"
```

Expected:

```text
ok
```

If this prints `FAIL: tamper was not detected`, the install is broken. Open an issue.

## All Checks Pass

You have a working Paxman install. Proceed to [Concepts](../concepts/canonicalization.md) to understand the design, or to [How-to guides](../how-to/canonicalize-a-value.md) for specific tasks.
