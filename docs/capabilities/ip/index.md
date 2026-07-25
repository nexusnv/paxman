# IP Capability

The IP capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings that represent IPv4 or IPv6 addresses into a single normalized form per RFC 4291, RFC 5952, and RFC 4007. The actual parse and canonical formatting is delegated to Python's stdlib `ipaddress` module, which is the deterministic authority for IP address representation. The capability is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `ip_canonicalization`

**Contract kind:** `canonical_ip`

**Contract factory:** `IP()`

## What It Does

The IP capability rewrites a string into a single canonical IP address form. IPv4 addresses are rendered in dotted-decimal notation with no leading zeros. IPv6 addresses are rendered in lowercase compressed form per RFC 5952. IPv6 zone identifiers (RFC 4007) are preserved or stripped based on contract policy.

The capability does not interpret IP networks, CIDR ranges, or subnet masks. It canonicalizes individual host addresses only.

The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `IP(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Contract Fields

Every field is a policy declaration. There is no auto-detection; the contract declares what canonical means, and the capability applies it.

| Field | Type | Default | What it does |
|---|---|---|---|
| `allow_ipv4` | `bool` | `True` | Accept IPv4 addresses. When `False`, IPv4 inputs are rejected with `policy_disabled_family`. |
| `allow_ipv6` | `bool` | `True` | Accept IPv6 addresses (with or without zone IDs). When `False`, IPv6 inputs are rejected with `policy_disabled_family`. |
| `preserve_zone_id` | `bool` | `True` | Keep the `%zone` scope identifier on IPv6 link-local addresses (RFC 4007), lowercased. When `False`, the zone ID is stripped. |
| `output_format` | `"normalized"` | `"normalized"` | The canonical output form. Only `"normalized"` is supported in v2.0.0. |

The `kind`, `version`, and `version_field` fields are fixed (`"canonical_ip"`, `1`, and `1` respectively). They are not part of the `IP()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Transforming Rules (Fire on Success)

These rules rewrite the input into the canonical form. They are recorded on the artifact in execution order.

| Rule | When it fires | Citation |
|---|---|---|
| `trimmed_whitespace` | Leading or trailing ASCII whitespace was removed from the input. | Paxman spec/IP section 3.2 (ASCII whitespace trim) |
| `canonicalized_ipv4` | The input was an IPv4 address. Leading zeros in octets are stripped and the address is rendered in dotted-decimal form. | RFC 4291 section 2.2 (dotted-decimal, no leading zeros) |
| `canonicalized_ipv6` | The input was an IPv6 address. The address is rendered in lowercase compressed form per RFC 5952 section 4. | RFC 5952 section 4 (IPv6 text representation, lowercase compressed) |
| `canonicalized_ipv6_zone` | The input was an IPv6 address with a zone ID, and `preserve_zone_id=True`. The zone ID is lowercased and appended. | RFC 4007 section 11 + RFC 5952 section 4.3 (zone id preserved, lowercased) |

### Rejecting Rules (Fire on Rejection)

These rules cause the capability to return `Status.INVALID` with a single evidence entry. The string is *not* canonicalized; the artifact holds no `value`.

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_ip_contract` | The contract is not a `CanonicalIPContract`. (Defensive; the orchestrator normally routes IP contracts to this capability.) | (dispatch invariant) |
| `not_a_string_value` | The value is not a `str`. | (dispatch invariant) |
| `missing_value` | The value is `None` or whitespace-only. | Paxman spec/IP section 3.4 (Law 8: required value absent) |
| `unrecognized_format` | The input did not match any IP grammar (not a valid textual IP address), or the stdlib `ipaddress` module rejected it as malformed (e.g. `999.1.1.1`). | RFC 4291 section 2.1 (input is not a valid textual IP address) |
| `policy_disabled_family` | The input is an IPv4 address with `allow_ipv4=False`, or an IPv6 address with `allow_ipv6=False`. | Paxman spec/IP section 3.3 (contract policy disables address family) |

## Worked Examples

### Example 1: A Normal IPv4 Address

```python
import paxman
from paxman import IP, Status

result = paxman.canonicalize("192.168.001.001", IP())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"192.168.1.1"`
- `result.evidence` includes `Evidence(rule="canonicalized_ipv4", ...)`

### Example 2: An IPv6 Address with Zone ID

```python
result = paxman.canonicalize("FE80::1%ETH0", IP())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"fe80::1%eth0"`
- `result.evidence` includes `Evidence(rule="canonicalized_ipv6_zone", ...)`

### Example 3: Policy Rejection

```python
result = paxman.canonicalize("192.168.1.1", IP(allow_ipv4=False))
```

- `result.status` is `Status.INVALID`
- `result.value` is `None`
- `result.evidence` is `(Evidence(rule="policy_disabled_family", ...),)`

## Limitations of v2.0.0

The v2.0.0 IP capability is intentionally narrow. It does not accept:

- IP networks or CIDR ranges (`192.168.1.0/24`, `fe80::/10`).
- Bracketed IPv6 forms (`[::1]`) used in URIs.
- Mixed IPv4-in-IPv6 notation (`::ffff:192.168.1.1`) beyond what the stdlib `ipaddress` module handles.
- IP addresses with port numbers (`127.0.0.1:8080`).

Future v2.x versions may add network/CIDR support as a separate capability.
