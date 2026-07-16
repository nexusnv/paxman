# URL Capability Changelog

## v1 (2026-07-16)

- Initial built-in: RFC 3986 normal form via the recognition Layer-1
  four-stage architecture (recognize -> generate_interpretations ->
  resolve_and_validate -> classify).
- Contract levers: `scheme_allow`, `strip_userinfo` (default off),
  `strip_fragment` (default on), `sort_query` (default off),
  `whatwg` (default off).
- `AMBIGUOUS` retained defensively unreachable (disjoint grammars).
