# Verify

After [installing](install.md) and [running the quickstart](quickstart.md), use this page as a checklist. Each item is a command you can run. The expected outputs confirm the install is working.

## 1. The package imports

```bash
uv run python -c "import paxman"
```

Expected: no output, exit code 0.

## 2. The version is reported

```bash
uv run python -c "import paxman; print(paxman.__version__)"
```

Expected:

```text
0.0.0.dev0
```

## 3. The public surface is importable

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

## 4. The quickstart produces the documented output

```bash
uv run python quickstart.py
```

Expected:

```text
CANONICALIZED -> johndoe@gmail.com
evidence: [('stripped_whitespace', ''), ('lowercased_local_part', ''), ('lowercased_domain', ''), ('stripped_dots_in_local_part', '')]
replay ok
```

## 5. A canonicalize call returns an artifact

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

## 6. Replay rehydrates byte-for-byte

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

## 7. Replay raises on a tampered artifact

```bash
uv run python -c "
import attrs
import paxman
from paxman import Email, VersionMismatchError

result = paxman.canonicalize('User@Example.com', Email())

# Replace the artifact with one whose replay_hash has been zeroed.
# This simulates storage corruption.
tampered = attrs.evolve(result, replay_hash='0' * 64)
try:
    paxman.replay(tampered, Email())
    print('FAIL: tamper was not detected')
except (VersionMismatchError, paxman.CanonicalizationError):
    print('ok')
"
```

Expected:

```text
ok
```

If this prints `FAIL: tamper was not detected`, the install is broken. Open an issue.

## All checks pass

You have a working Paxman install. Proceed to [Concepts](../concepts/canonicalization.md) to understand the design, or to [How-to guides](../how-to/canonicalize-a-value.md) for specific tasks.
