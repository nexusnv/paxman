# UUID Capability

The UUID capability is a built-in capability shipped with Paxman v2. It canonicalizes strings into the RFC 4122 §3 36-char canonical form (the supported legacy profile; RFC 9562 is the current authority). Like the email and date capabilities, it is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `uuid_canonicalization`

**Contract kind:** `canonical_uuid`

**Contract factory:** `UUID()`

## What It Does

The UUID capability accepts a string that is *already* in RFC 4122 §3 canonical form (32 lowercase hex characters, 8-4-4-4-12 grouping, total 36 characters) and emits the same string. A string that is not in that form is `Status.INVALID`.

The capability does not interpret non-canonical inputs as the canonical form of "the same" UUID. A v1 UUID and a v4 UUID are different values; the capability does not unify them.

### Recognition Layer 1

`grammar.recognize` full-matches the input against a single `canonical_uuid` grammar (RFC 4122 §3, anchored regex). It returns only raw captures — no semantic meaning. Inputs that fail to full-match (32-hex, braced, URN, uppercase, extra whitespace, non-hex, wrong hyphen positions) produce no recognition and are rejected with `unrecognized_format`. The resolver (`generate_interpretations`) then re-checks the canonical form and applies the version-nibble policy (`resolve_and_validate`), and `classify` maps the result to a `Status`.

## The Contract Fields

| Field | Type | Default | What it does |
|---|---|---|---|
| `version` | `"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"` | `"any"` | Which UUID version to accept. Under `version="any"` the capability validates only RFC 4122 §3 form — any version nibble (and any variant nibble) in canonical form is accepted verbatim. A specific value (e.g. `"4"`) adds an RFC 4122 §4.1.3 check that rejects other versions with `Status.INVALID`. |

The `kind` and `version_field` fields are fixed (`"canonical_uuid"` and `1` respectively). They are not part of the `UUID()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Rejecting Rules

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_uuid_contract` | The contract is not a `CanonicalUUIDContract`. (Dispatch invariant.) | (Law 14 allow-list) |
| `not_a_string_value` | The value is not a `str`. (Dispatch invariant.) | (Law 14 allow-list) |
| `unrecognized_format` | The string does not full-match the RFC 4122 §3 canonical-form grammar (not 36 chars, non-hex characters, wrong hyphen positions, uppercase, braced/URN/extra whitespace). | RFC 4122 §3 |
| `version_mismatch` | The contract specifies a specific version and the input's version-nibble disagrees. | RFC 4122 §4.1.3 |

### Transforming Rule

| Rule | When it fires | Citation |
|---|---|---|
| `no_transformation_needed` | The input is already in canonical form and matches the version policy (under `version="any"`, any version nibble in canonical form matches). The canonical value is the input verbatim. | RFC 4122 §3 |

## Limitations

The UUID capability is intentionally narrow. It does not accept:

- The 32-hex-no-hyphens form.
- The braced `{...}` form.
- The URN `urn:uuid:...` form.
- Uppercase hex characters.
- Inputs with extra whitespace.

These are different surface forms of the same UUID value; the capability rejects them rather than silently rewriting. A future capability may canonicalize to those forms.

## Worked Examples

### Example 1: A Canonical v4 UUID

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

### Example 2: Version Filter

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
