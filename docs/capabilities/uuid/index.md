# UUID capability

The UUID capability is the second built-in capability shipped with Paxman v2. It canonicalizes strings into RFC 4122 36-char canonical form.

**Capability name:** `uuid_canonicalization`

**Contract kind:** `canonical_uuid`

**Contract factory:** `UUID()`

## What it does

The UUID capability accepts a string that is *already* in RFC 4122 §3 canonical form (32 lowercase hex characters, 8-4-4-4-12 grouping, total 36 characters) and emits the same string. A string that is not in that form is `Status.INVALID`.

The capability does not interpret non-canonical inputs as the canonical form of "the same" UUID. A v1 UUID and a v4 UUID are different values; the capability does not unify them.

## The contract fields

| Field | Type | Default | What it does |
|---|---|---|---|
| `version` | `"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"` | `"any"` | Which UUID version to accept. `"any"` accepts all five. A specific value rejects other versions with `Status.INVALID`. |

The `kind` and `version_field` fields are fixed (`"canonical_uuid"` and `1` respectively). They are not part of the `UUID()` factory signature.

## The rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Rejecting rules

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_uuid_contract` | The contract is not a `CanonicalUUIDContract`. (Dispatch invariant.) | (Law 14 §3.6 allow-list) |
| `not_a_string_value` | The value is not a `str`. (Dispatch invariant.) | (Law 14 §3.6 allow-list) |
| `not_canonical_form` | The string is not 36 characters, contains non-canonical characters, or has hyphens in the wrong positions. | RFC 4122 §3 |
| `version_mismatch` | The contract specifies a specific version and the input's version-nibble disagrees. | RFC 4122 §4.1.3 |

### Transforming rule

| Rule | When it fires | Citation |
|---|---|---|
| `no_transformation_needed` | The input is already in canonical form and matches the version policy. The canonical value is the input verbatim. | RFC 4122 §3 |

## Limitations of v1

The v1 UUID capability is intentionally narrow. It does not accept:

- The 32-hex-no-hyphens form.
- The braced `{...}` form.
- The URN `urn:uuid:...` form.
- Uppercase hex characters.
- Inputs with extra whitespace.

These are different surface forms of the same UUID value; the v1 capability rejects them rather than silently rewriting. A future capability may canonicalize to those forms.

## Worked examples

### Example 1: A canonical v4 UUID

```python
import paxman
from paxman import UUID, Status

result = paxman.canonicalize(
    "550e8400-e29b-41d4-a716-446655440000", UUID()
)
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"550e8400-e29b-41d4-a716-446655440000"`
- `result.evidence[0].rule` is `"no_transformation_needed"`

### Example 2: Version filter

```python
result = paxman.canonicalize(
    "e034b584-7d89-11ed-a1eb-0242ac120002",  # a v1 UUID
    UUID(version="4"),
)
```

- `result.status` is `Status.INVALID`
- `result.value` is `None`
- `result.evidence[0].rule` is `"version_mismatch"`

### Example 3: Replay

```python
original = paxman.canonicalize(
    "550e8400-e29b-41d4-a716-446655440000", UUID()
)
rehydrated = paxman.replay(original, UUID())
assert rehydrated == original
```

The artifact's `replay_hash` is computed from the canonical form, the contract, the version stamp, and the evidence. Replay verifies all four.
