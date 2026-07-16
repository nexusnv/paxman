# URL Canonicalization

Fifth built-in Paxman v2 capability. Rewrites URI strings into the
RFC 3986 normal form under an explicit, contract-declared policy.

## Contract

```python
from paxman import URL

URL()                                  # RFC 3986, fragment stripped by default
URL(scheme_allow=("http", "https"))        # reject other schemes -> UNSUPPORTED
URL(strip_userinfo=True)              # elide userinfo@
URL(strip_fragment=False)             # preserve #fragment
URL(sort_query=True)                  # sort query params by key
URL(whatwg=True)                     # opt into WHATWG URL Standard authority
```

## Rules (Law 14)

| Rule | Citation |
|------|----------|
| `lowercase_scheme` | RFC 3986 §3.1 |
| `uppercase_pct_hex` | RFC 3986 §2.1 / §6.2.2.1 |
| `lowercase_host` | RFC 3986 §3.2.2 |
| `decode_unreserved_pct` | RFC 3986 §2.3 / §6.2.2.2 |
| `keep_reserved_pct` | RFC 3986 §2.2 |
| `elide_default_port` | RFC 3986 §3.2.3 / §6.2.3 |
| `remove_dot_segments` | RFC 3986 §6.2.2.3 / §5.2.4 |
| `empty_path_to_slash` | RFC 3986 §6.2.3 |
| `strip_userinfo` | Declared Paxman policy (default off) |
| `strip_fragment` | Declared Paxman policy (default ON) |
| `sort_query` | Declared Paxman policy (default off) |
| `whatwg_*` (4 rules) | WHATWG URL Standard (only when `whatwg=True`) |

## Examples

| Input | `URL()` (default) | Note |
|-------|-------------------|------|
| `HTTP://Example.COM:80/./A/../b` | `http://example.com/b` | scheme/host lower, port 80 elided, dot-segments removed, fragment stripped |
| `https://example.com/a#frag` | `https://example.com/a` | fragment stripped by default |
| `https://user:pass@example.com/` | `https://user:pass@example.com/` | userinfo retained by default |
| `http://example.com./` | `http://example.com./` | RFC strict: trailing dot kept |
| `http://example.com./` + `whatwg=True` | `http://example.com/` | WHATWG trailing-dot equivalence |

## Limitations (Drift Excluded by Mandate)

- URL extraction from prose (that is the `extract_*` family).
- WHATWG-liberal parsing under `whatwg=False` (infinite slashes, backslash coercion, `%2e`→`.` path decoding).
- Query/fragment semantic interpretation.
- Scheme/host inference.
