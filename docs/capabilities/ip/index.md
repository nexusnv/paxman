# Ip Capability

The ip capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings into ip representations. It is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `ip_canonicalization`

**Contract kind:** `canonical_ip`

**Contract factory:** `IP()`

## What It Does

The ip capability rewrites a string into a single canonical form. The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `IP(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Evidence Rules

| Rule | Citation |
|---|---|
| `not_a_ip_contract` | (dispatch invariant) |\n| `not_a_string_value` | (dispatch invariant) |\n| `trimmed_whitespace` | paxman spec/ip §3.2 (ASCII whitespace trim) |\n| `recognized_ipv4` | RFC 4291 §2.2 (IPv4 address text representation) |\n| `recognized_ipv6` | RFC 4291 §2.2 (IPv6 address text representation) |\n| `canonicalized_ipv4` | RFC 4291 §2.2 (dotted-decimal, no leading zeros) |\n| `canonicalized_ipv6` | RFC 5952 (IPv6 text representation, lowercase compressed) |\n| `canonicalized_ipv6_zone` | RFC 4007 §11 + RFC 5952 §4.3 (zone id preserved, lowercased) |\n| `policy_disabled_family` | paxman spec/ip §3.3 (contract policy disables address family) |\n| `missing_value` | paxman spec/ip §3.4 (Law 8 — required value absent) |\n| `unrecognized_format` | RFC 4291 (input is not a valid IP address) |

## Recognition Layer 1

Before any rewriting, the capability runs `grammar.recognize` over the input. Recognition assigns **no meaning** — it returns only raw captures. The resolver then assigns meaning to the captures and maps the survivors to a `Status`.

## Status Outcomes

- **CANONICALIZED:** The input was successfully matched and canonicalized.
- **INVALID:** The input was rejected due to an unrecognized format or policy restriction.
- **MISSING:** The input was empty or purely whitespace.
- **AMBIGUOUS:** (where applicable) The input could not be definitively resolved.
- **UNSUPPORTED:** (where applicable) The input format is known but explicitly not supported.

## Quickstart

```python
import paxman
from paxman import IP, Status

result = paxman.canonicalize("192.0.2.1", IP())
```

## References

- **Source Module:** [`src/paxman/_capabilities/ip`](../../../src/paxman/_capabilities/ip)
- **Contracts Reference:** [Contracts](../../reference/contracts.md)
