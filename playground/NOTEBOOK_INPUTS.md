# Paxman Capability Notebook Inputs — Factual Backbone

> **Source of truth:** `src/paxman/_capabilities/<domain>/` (contract.py, canonicalizer.py, grammar.py, rules.py, parser.py) and `src/paxman/_core/` (artifact.py, result.py, status.py). All snippets below were executed against the working tree on 2026-07-19 and produced the shown outputs.

## Universal API contract (applies to ALL 10 capabilities)

```python
import paxman
from paxman import canonicalize, replay, ContractError, CanonicalizationError

# Public entry points (src/paxman/__init__.py):
#   paxman.canonicalize(input_data, contract) -> ExecutionArtifact
#   paxman.replay(artifact, contract) -> ExecutionArtifact
#
# Contract value objects are constructed with keyword-only factories:
#   Email(...), Country(...), Date(...), ...  (each returns a frozen Canonical*Contract)
#
# The canonical value lives on the artifact:
#   artifact.status   -> enum Status: CANONICALIZED | INVALID | MISSING | AMBIGUOUS | UNSUPPORTED
#   artifact.value    -> str | None  (the canonical string when CANONICALIZED; None otherwise)
#   artifact.candidates -> tuple[str, ...] | None  (the enumerated readings when AMBIGUOUS)
#   artifact.evidence -> tuple[Evidence, ...]  (rule + detail + authority provenance)
#
# IMPORTANT for notebook authors:
#   * canonicalize() takes the RAW value (a str) as the FIRST arg and the
#     contract value object as the SECOND arg. There is no wrapper/adapter.
#   * The contract is the ONLY place policy is declared. There is NO
#     auto_detect / infer / guess anywhere (Mandate Law 3 / Law 7).
#   * A broken contract (bad enum, unknown currency, etc.) raises ContractError
#     AT CONSTRUCTION TIME — before canonicalize is ever called.
#   * A value that cannot be resolved is NOT an exception: it is a Status.INVALID
#     (or MISSING / AMBIGUOUS / UNSUPPORTED) recorded on the artifact.
#   * replay(artifact, contract) returns a byte-equal artifact (Mandate Law 12).
```

---

## 1. Boolean

**Contract factory:** `Boolean(*, accept_numeric=True, accept_words=True, case_sensitive=False, authority_override=None) -> CanonicalBooleanContract`

**Accepted input:** a `str` (or `None` → `Status.MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** the lowercase string `"true"` or `"false"` (in `artifact.value`).

```python
from paxman import Boolean, canonicalize

canonicalize("Yes", Boolean())                 # CANONICALIZED -> "true"
canonicalize("1", Boolean())                   # CANONICALIZED -> "true"
canonicalize("TRUE", Boolean())                # CANONICALIZED -> "true"
canonicalize("1", Boolean(accept_numeric=False))  # INVALID (policy_disabled_token)
canonicalize("maybe", Boolean())               # INVALID (unrecognized_token)
canonicalize("  yes  ", Boolean())             # CANONICALIZED -> "true" (whitespace trimmed)
```

**Edge / "refuses to guess":**
- `accept_numeric=False` + input `"1"` → `INVALID` (the numeric token is disabled by policy, not silently accepted).
- `"true"`/`"false"` are always accepted even when both `accept_numeric` and `accept_words` are `False` (they are the *result*, not a gated user token — preserves idempotence).
- Non-boolean words (`"maybe"`) → `INVALID`, never guessed.
- `None` or `""` → `Status.MISSING`.

---

## 2. Country

**Contract factory:** `Country(*, allow_alpha3=True, allow_name=True, allow_synonym=True, allow_numeric=True, localized_names=False, historical_names=False, extra_synonyms=None, authority_override=None) -> CanonicalCountryContract`

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** the ISO 3166-1 **alpha-2** code (uppercase, 2 letters) in `artifact.value`.

```python
from paxman import Country, canonicalize

canonicalize("USA", Country())                 # CANONICALIZED -> "US"   (synonym)
canonicalize("us", Country())                  # CANONICALIZED -> "US"   (alpha-2, case-folded)
canonicalize("United States", Country())        # CANONICALIZED -> "US"   (name)
canonicalize("840", Country())                 # CANONICALIZED -> "US"   (numeric M49, zero-padded)
canonicalize("DEU", Country())                 # CANONICALIZED -> "DE"   (alpha-3)
canonicalize("malaysia", Country(allow_name=True))   # CANONICALIZED -> "MY"
canonicalize("Burma", Country(historical_names=True)) # CANONICALIZED -> "MM"
canonicalize("Atlantis", Country())            # INVALID (unrecognized_format)
```

**Edge / "refuses to guess":**
- `allow_alpha3=False` + an alpha-3 token → `INVALID` with `policy_disabled_kind` (not silently downgraded).
- `localized_names=False` (default) → non-Latin names like `"日本"` are `INVALID` unless `localized_names=True`.
- `historical_names=False` (default) → `"Burma"` is `INVALID` unless opted in.
- Unknown token → `INVALID`, never guessed.
- `extra_synonyms={"america": "US"}` lets callers add replayable aliases.

---

## 3. Date

**Contract factory:** `Date(*, locale="ISO", language="en", two_digit_year=None, authority_override=None) -> CanonicalDateContract`
- `locale`: `"ISO"` (default; enumerates both MM/DD and DD/MM → AMBIGUOUS), `"US"` (MM/DD), `"EU"` (DD/MM).
- `two_digit_year`: `None` (default → AMBIGUOUS across centuries), `"reject"`/`"require_four_digit_year"`, or `"pivot:YYYY"`.

**Accepted input:** a `str` (or `None` → `MISSING`). Empty → `MISSING`.

**Canonical output:** `"YYYY-MM-DD"` for dates, `"YYYY-MM-DDTHH:MM:SS[.ffffff]Z"` for datetimes (RFC 3339, normalized to UTC), in `artifact.value`.

```python
from paxman import Date, canonicalize

canonicalize("2025-03-04", Date(locale="US"))            # CANONICALIZED -> "2025-03-04"
canonicalize("03/04/2025", Date(locale="US"))            # CANONICALIZED -> "2025-03-04"  (MM/DD)
canonicalize("03/04/2025", Date(locale="EU"))            # CANONICALIZED -> "2025-04-03"  (DD/MM)
canonicalize("03/04/2025", Date(locale="ISO"))           # AMBIGUOUS -> ('2025-03-04', '2025-04-03')
canonicalize("16 July 2026", Date(language="en"))        # CANONICALIZED -> "2026-07-16"
canonicalize("2025-01-01T07:00:00-05:00", Date(locale="ISO"))  # CANONICALIZED -> "2025-01-01T12:00:00Z"
canonicalize("2025-01-01T07:00:00", Date(locale="ISO"))  # AMBIGUOUS (naive datetime, no zone)
canonicalize("03/04/26", Date(locale="US"))              # AMBIGUOUS -> ('1926-03-04','2026-03-04','2126-03-04')
canonicalize("not a date", Date(locale="US"))            # INVALID (unrecognized_format)
```

**Edge / "refuses to guess":**
- `locale="ISO"` + ambiguous slash form → `AMBIGUOUS` (both readings surfaced in `candidates`), never guessed.
- 2-digit year with no `two_digit_year` policy → `AMBIGUOUS` across 1900/2000/2100 centuries.
- Naive datetime (no timezone) → `AMBIGUOUS` per RFC 3339 §5.6.
- `two_digit_year="reject"` + `"03/04/26"` → `INVALID` (`rejected_two_digit_year`).
- Invalid calendar date (e.g. `2025-13-40`) → `INVALID` (`invalid_calendar_date`).
- Recognized-but-unparseable → `INVALID`, never guessed.

---

## 4. Email

**Contract factory:** `Email(*, strict=False, provider_aliases="none", lowercase=True, strip_whitespace=True, authority_override=None) -> CanonicalEmailContract`
- `provider_aliases`: `"none"` (default, preserves input domain) or `"gmail"` (applies Gmail dot-stripping + `+tag` removal + `googlemail.com`→`gmail.com`).

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** the lowercased `local@domain` mailbox string in `artifact.value`.

```python
from paxman import Email, canonicalize

canonicalize("  John.Doe@Gmail.COM  ", Email(provider_aliases="gmail"))  # CANONICALIZED -> "johndoe@gmail.com"
canonicalize("A@B.COM", Email())                  # CANONICALIZED -> "a@b.com"
canonicalize("  a@b.com  ", Email())              # CANONICALIZED -> "a@b.com"  (whitespace stripped)
canonicalize("John Doe <a@b.com>", Email())       # INVALID (unrecognized_format — display-name form not supported)
canonicalize("a@b", Email())                       # CANONICALIZED -> "a@b"  (no dot in domain is allowed)
canonicalize("foo@@bar.com", Email())             # INVALID (unrecognized_format)
```

**Edge / "refuses to guess":**
- `provider_aliases="gmail"` collapses `John.Doe` → `johndoe` and strips `+tag`; `provider_aliases="none"` keeps the literal domain.
- `strict=True` rejects inputs with embedded whitespace or non-ASCII (`strict_rejected_whitespace` / `strict_rejected_non_ascii`).
- Display-name forms (`Name <a@b.com>`) and double-`@` are `INVALID`, never partially parsed.
- A dot-invalid local part (leading/trailing/consecutive dots) is NOT repaired into a Gmail address — it is rejected (Identity: canonicalize only, never guess).
- `lowercase=False` preserves the original casing.

---

## 5. Geolocation

**Contract factory:** `Geolocation(*, datum="WGS84", coordinate_order="lat_lon", require_hemisphere=True, output_format="decimal", precision=6, authority_override=None) -> CanonicalGeolocationContract`
- `datum`: only `"WGS84"` supported in v1.
- `coordinate_order`: `"lat_lon"` (default) or `"lon_lat"` — declares how to READ the input; output is ALWAYS `"latitude,longitude"`.
- `require_hemisphere`: `True` (default) requires an explicit sign or N/S/E/W on each axis.
- `precision`: int 0..12 (decimal places; trailing zeros kept).

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** `"<lat>,<lon>"` decimal-degrees string (exactly `precision` places) in `artifact.value`.

```python
from paxman import Geolocation, canonicalize

canonicalize("40.7128, -74.0060", Geolocation(require_hemisphere=False))  # CANONICALIZED -> "40.712800,-74.006000"
canonicalize("40.7128N 74.0060W", Geolocation())                         # CANONICALIZED -> "40.712800,-74.006000"
canonicalize("40.7128, -74.0060", Geolocation())                         # AMBIGUOUS -> ('40.712800,74.006000', '-40.712800,74.006000')
canonicalize("40.7128, 74.0060", Geolocation())                          # AMBIGUOUS (4 sign combos)
canonicalize("91, 0", Geolocation())                                     # INVALID (out_of_range)
canonicalize("40.7128 -74.0060", Geolocation())                          # INVALID (unrecognized_format — needs comma)
```

**Edge / "refuses to guess":**
- `require_hemisphere=True` (default) + an unsigned axis → `AMBIGUOUS` enumerating both sign readings (never guesses the missing sign).
- `require_hemisphere=False` → unsigned axes default to positive and canonicalize.
- Out-of-range (lat outside [-90,90], lon outside [-180,180]) → `INVALID`.
- DMS (`40°42'46"N ...`) and signed-DMS forms are supported; hemisphere letters must be attached to the number (`40.7128N 74.0060W` works; `N40.7128 W74.0060` does NOT — verify before using letter-prefix forms in a notebook).
- No auto-detection of datum or axis order — both are declared policy.

---

## 6. IP

**Contract factory:** `IP(*, allow_ipv4=True, allow_ipv6=True, preserve_zone_id=True, authority_override=None) -> CanonicalIPContract`

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** RFC 4291 (IPv4 dotted-decimal, no leading zeros) / RFC 5952 (IPv6 lowercase compressed) string in `artifact.value`. IPv6 zone id kept as `%zone` (lowercased) when `preserve_zone_id=True`.

```python
from paxman import IP, canonicalize

canonicalize("192.168.001.001", IP())            # CANONICALIZED -> "192.168.1.1"
canonicalize("2001:DB8::1", IP())                # CANONICALIZED -> "2001:db8::1"
canonicalize("2001:db8::1%eth0", IP())           # CANONICALIZED -> "2001:db8::1%eth0"
canonicalize("999.1.1.1", IP())                  # INVALID (unrecognized_format)
canonicalize("192.168.1.1", IP(allow_ipv4=False))  # INVALID (policy_disabled_family)
```

**Edge / "refuses to guess":**
- Leading zeros in IPv4 octets are stripped (`001` → `1`).
- IPv6 is lowercased and compressed per RFC 5952.
- `allow_ipv4=False` + an IPv4 input → `INVALID` (`policy_disabled_family`), not silently accepted.
- Malformed addresses (`999.1.1.1`) → `INVALID`, never coerced.

---

## 7. Money

**Contract factory:** `Money(*, currency: str, allow_symbol=True, allow_code=True, strip_spaces=True, authority_override=None) -> CanonicalMoneyContract`
- **`currency` is REQUIRED with no default** (Mandate Law 3 — Paxman never guesses currency).

**Accepted input:** a `str` (or `None` → `INVALID` — empty money is rejected, not MISSING).

**Canonical output:** `"<ISO4217>:<amount>"` string in `artifact.value` (e.g. `"MYR:12.50"`).

```python
from paxman import Money, canonicalize, ContractError

canonicalize("RM 12.50", Money(currency="MYR"))     # CANONICALIZED -> "MYR:12.50"
canonicalize("$12.50", Money(currency="USD"))       # CANONICALIZED -> "USD:12.50"
canonicalize("12.50", Money(currency="USD"))        # CANONICALIZED -> "USD:12.50"  (no symbol/code needed)
canonicalize("€12.50", Money(currency="EUR"))       # INVALID (symbol does not match contract currency)
canonicalize("USD 12.50", Money(currency="USD", allow_code=False))  # INVALID (code present but allow_code=False)
canonicalize("12.50", Money(currency="GBP", allow_symbol=False))   # CANONICALIZED -> "GBP:12.50"
Money(currency="XYZ")                               # ContractError at CONSTRUCTION (unknown ISO 4217 code)
```

**Edge / "refuses to guess":**
- `currency` is mandatory — omitting it is a `TypeError` (no default); an unknown code (`"XYZ"`) raises `ContractError` at contract construction.
- A symbol/code in the input that does NOT match `contract.currency` → `INVALID` (symbol_validated / code_validated must agree with the contract).
- `None` or `""` → `INVALID` (missing_value), NOT `MISSING` (money has no "absent" semantics).
- The amount is parsed as an exact decimal; literal decimal places are preserved.

---

## 8. Phone

**Contract factory:** `Phone(*, country="US", authority_override=None) -> CanonicalPhoneContract`
- `country`: ISO 3166-1 alpha-2 used to expand national numbers into E.164. Declared policy; never inferred.

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** the E.164 string `"+<cc><national>"` in `artifact.value`.

```python
from paxman import Phone, canonicalize

canonicalize("+1 (212) 555-0199", Phone(country="US"))  # INVALID (formatted + number rejected, not partially parsed)
canonicalize("(212) 555-0199", Phone(country="US"))     # CANONICALIZED -> "+12125550199"
canonicalize("2125550199", Phone(country="US"))         # CANONICALIZED -> "+12125550199"
canonicalize("0199", Phone(country="US"))               # INVALID (grammar_rejected — too short / no valid E.164)
canonicalize("2125550199", Phone(country="GB"))         # CANONICALIZED -> "+442125550199" (GB cc applied)
```

**Edge / "refuses to guess":**
- A leading `+` input is treated as already-global (idempotent reassembly).
- National / digits-only inputs get the contract's declared country code prepended — the country is NEVER inferred from the digits.
- A number that fails the E.164 global shape (1–15 digits, leading digit 1–9, non-empty national part) → `INVALID` (`grammar_rejected`).
- An unknown `country` raises `ContractError` at contract construction (validated against the v1 lookup table).

---

## 9. URL

**Contract factory:** `URL(*, scheme_allow=None, strip_userinfo=False, strip_fragment=True, sort_query=False, whatwg=False, authority_override=None) -> CanonicalURLContract`
- `scheme_allow`: `None` (accept any scheme) or a tuple of allowed schemes.
- `strip_fragment`: `True` by default (drops `#frag`).
- `strip_userinfo`: `False` by default (keeps `user:pass@`).
- `sort_query`: `False` by default (keeps query order).
- `whatwg`: `False` by default (RFC 3986 §6.2.2 normalization).

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** the normalized URL string in `artifact.value` (scheme lowercased, host lowercased, default port elided, dot-segments removed, percent-hex uppercased, unreserved percent-encoding decoded).

```python
from paxman import URL, canonicalize

canonicalize("HTTP://Example.COM:80/foo/bar", URL())              # CANONICALIZED -> "http://example.com/foo/bar"
canonicalize("http://example.com/foo/../bar", URL())             # CANONICALIZED -> "http://example.com/bar"
canonicalize("http://user:pass@example.com/path#frag", URL())    # CANONICALIZED -> "http://user:pass@example.com/path"
canonicalize("https://example.com/a?b=2&c=1", URL(sort_query=True))  # CANONICALIZED -> "https://example.com/a?b=2&c=1" (sorted)
canonicalize("ftp://example.com/file", URL())                    # CANONICALIZED -> "ftp://example.com/file"
canonicalize("ftp://example.com/file", URL(scheme_allow=("https",)))  # UNSUPPORTED (scheme_not_allowed)
canonicalize("not a url", URL())                                  # CANONICALIZED -> "not a url" (URL is lenient; unparseable input passes through)
canonicalize("example.com/path", URL())                           # CANONICALIZED -> "example.com/path" (scheme-less, authority kept)
```

**Edge / "refuses to guess":**
- `scheme_allow` set and the input scheme not in it → `Status.UNSUPPORTED` (not INVALID — the capability declines, it does not reject as malformed).
- `strip_fragment=True` (default) drops `#frag`; set `strip_fragment=False` to keep it.
- `strip_userinfo=True` removes `user:pass@`.
- Malformed authority (bad host, port out of 0..65535) → `INVALID` (`grammar_rejected`).
- `whatwg=True` applies additional WHATWG-style coercions (trailing-dot host stripping, backslash coercion).

---

## 10. UUID

**Contract factory:** `UUID(*, version="any", authority_override=None) -> CanonicalUUIDContract`
- `version`: `"any"` (default, form-only validation) or one of `"1","3","4","5","7"` (also rejects mismatched version nibbles).

**Accepted input:** a `str` (or `None` → `MISSING`). Whitespace-only → `MISSING`.

**Canonical output:** the RFC 4122 §3 form — 32 lowercase hex chars in 8-4-4-4-12 grouping (36 chars) — in `artifact.value`.

```python
from paxman import UUID, canonicalize

canonicalize("123e4567-e89b-12d3-a456-426614174000", UUID())     # CANONICALIZED -> "123e4567-e89b-12d3-a456-426614174000"
canonicalize("123E4567-E89B-12D3-A456-426614174000", UUID())     # INVALID (uppercase rejected — strict-only, no lowercasing)
canonicalize("123e4567-e89b-42d3-a456-426614174000", UUID(version="4"))  # CANONICALIZED (version nibble 4)
canonicalize("123e4567-e89b-12d3-a456-426614174000", UUID(version="4"))  # INVALID (version_mismatch — nibble is 1)
canonicalize("not-a-uuid", UUID())                                # INVALID (unrecognized_format)
canonicalize("123e4567e89b12d3a456426614174000", UUID())         # INVALID (unrecognized_format — 32 hex without hyphens NOT accepted)
UUID(version="99")                                                # ContractError at CONSTRUCTION (invalid version)
```

**Edge / "refuses to guess":**
- **Only the exact lowercase hyphenated RFC 4122 form is accepted.** Uppercase (NOT lowercased), braced (`{...}`), URN (`urn:uuid:...`), 32-hex-without-hyphens, and whitespace-padded inputs are ALL `INVALID` (`unrecognized_format`). UUID does NOT strip whitespace or normalize alternate shapes.
- `version="any"` validates form only; a specific `version` also checks the version nibble (3rd group, 1st hex digit) and rejects mismatches with `version_mismatch`.
- An invalid `version` string (`"99"`) raises `ContractError` at contract construction.

---

## Cross-cutting notes for notebook authors

1. **`artifact.value` is the canonical string** for all 10 capabilities. It is `None` for `INVALID`/`MISSING`/`AMBIGUOUS`/`UNSUPPORTED`.
2. **`artifact.candidates`** is non-`None` only for `AMBIGUOUS` outcomes (date century/ordering, geolocation hemisphere, url multi-reading). It is the tuple of every surviving canonical form — Paxman surfaces ambiguity instead of guessing.
3. **`ContractError` vs `CanonicalizationError`:** `ContractError` fires at *contract construction* (bad enum value, unknown currency, unknown country, invalid version). A *value* that cannot be canonicalized is NOT an exception — it is a `Status.INVALID`/`MISSING`/`AMBIGUOUS`/`UNSUPPORTED` on the artifact. `CanonicalizationError` is reserved for internal invariant violations (e.g. a replay_hash mismatch during `replay`).
4. **`None` / empty input:** boolean, country, date, email, geolocation, ip, phone, uuid → `Status.MISSING`. **Money is the exception** — `None`/`""` → `INVALID` (money has no "absent" semantics).
5. **No `normalize` attribute** exists on `paxman` (it raises `AttributeError` by design — Paxman canonicalizes, it does not normalize).
6. **Replay is byte-equal:** `replay(artifact, same_contract) == artifact` (verified empirically). The contract passed to `replay` must be the same (or version-compatible) contract used for `canonicalize`.
