from __future__ import annotations

import attrs

from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract


@attrs.frozen
class CanonicalURLContract:
    """Declares the *policy* for URL canonicalization (Law 5).

    The capability implements *how*; the contract declares *what* normal form
    is required. No `auto_detect` — every lever is an explicit, declared value.
    """

    scheme_allow: tuple[str, ...] | None = None
    strip_userinfo: bool = False
    strip_fragment: bool = True
    sort_query: bool = False
    whatwg: bool = False
    kind: str = "canonical_url"
    version: int = 1
    version_field: int = 1  # required by the Contract Protocol (mirrors CanonicalPhoneContract)

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "scheme_allow": list(self.scheme_allow) if self.scheme_allow is not None else None,
            "strip_userinfo": self.strip_userinfo,
            "strip_fragment": self.strip_fragment,
            "sort_query": self.sort_query,
            "whatwg": self.whatwg,
            "version": self.version,
            "version_field": self.version_field,
        }


def URL(
    *,
    scheme_allow: tuple[str, ...] | None = None,
    strip_userinfo: bool = False,
    strip_fragment: bool = True,
    sort_query: bool = False,
    whatwg: bool = False,
) -> CanonicalURLContract:
    """Domain-type sugar for declaring a URL contract (mirrors Phone()/Date())."""
    return CanonicalURLContract(
        scheme_allow=tuple(scheme_allow) if scheme_allow is not None else None,
        strip_userinfo=strip_userinfo,
        strip_fragment=strip_fragment,
        sort_query=sort_query,
        whatwg=whatwg,
    )


def _build_url(spec: dict[str, object]) -> CanonicalURLContract:
    raw_allow = spec.get("scheme_allow", None)
    if raw_allow is not None:
        if not isinstance(raw_allow, (list, tuple)):
            raise ContractError("canonical_url: 'scheme_allow' must be a list/tuple of strings")
        for entry in raw_allow:
            if not isinstance(entry, str):
                raise ContractError("canonical_url: every 'scheme_allow' entry must be a string")
    allow = tuple(raw_allow) if raw_allow is not None else None

    def _int(key: str, default: int) -> int:
        v = spec.get(key, default)
        if not isinstance(v, int):
            raise ContractError(f"canonical_url: '{key}' must be an int")
        return int(v)

    # Only version 1 is supported in this release. Reject any other value
    # explicitly rather than silently falling back to version 1, which would
    # break byte-for-byte replay of versioned inputs (Mandate Law 12).
    version = _int("version", 1)
    if version != 1:
        raise ContractError(f"canonical_url: unsupported version: {version!r} (only 1 supported)")
    version_field = _int("version_field", 1)
    if version_field != 1:
        raise ContractError(
            f"canonical_url: unsupported version_field: {version_field!r} (only 1 supported)"
        )

    def _bool(key: str, default: bool) -> bool:
        v = spec.get(key, default)
        if not isinstance(v, bool):
            raise ContractError(f"canonical_url: '{key}' must be a bool")
        return bool(v)

    return CanonicalURLContract(
        scheme_allow=allow,
        strip_userinfo=_bool("strip_userinfo", False),
        strip_fragment=_bool("strip_fragment", True),
        sort_query=_bool("sort_query", False),
        whatwg=_bool("whatwg", False),
        version=version,
        version_field=version_field,
    )


register_contract("canonical_url", _build_url)
