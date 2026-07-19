# src/paxman/_capabilities/ip/contract.py
"""IP contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced.
"""

from __future__ import annotations

from typing import Any

import attrs

from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract


@attrs.frozen
class CanonicalIPContract:
    """The IP contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    There is no `auto_detect`. The caller declares the policy; the
    capability applies it.
    """

    allow_ipv4: bool = True
    allow_ipv6: bool = True
    preserve_zone_id: bool = True
    kind: str = "canonical_ip"
    version: int = 1
    version_field: int = 1

    authority_override: Any = attrs.field(
        default=None,
        repr=False,
        eq=False,
        hash=False,
    )

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return {
            "kind": self.kind,
            "allow_ipv4": self.allow_ipv4,
            "allow_ipv6": self.allow_ipv6,
            "preserve_zone_id": self.preserve_zone_id,
            "version": self.version,
            "version_field": self.version_field,
        }


def IP(
    *,
    allow_ipv4: bool = True,
    allow_ipv6: bool = True,
    preserve_zone_id: bool = True,
    authority_override: Any | None = None,
) -> CanonicalIPContract:
    """Domain-type sugar: declare an IP contract in user vocabulary.

    Args:
        allow_ipv4: accept IPv4 inputs. Default True.
        allow_ipv6: accept IPv6 inputs. Default True.
        preserve_zone_id: keep the `%zone` scope identifier on link-local
            addresses (RFC 4007), lowercased. Default True.

    Returns:
        A frozen CanonicalIPContract instance.
    """
    return CanonicalIPContract(
        allow_ipv4=allow_ipv4,
        allow_ipv6=allow_ipv6,
        preserve_zone_id=preserve_zone_id,
        authority_override=authority_override,
    )


def _require_bool(field: str, value: object) -> bool:
    """Validate that a contract field is a real bool (Law 7 — explicit)."""
    if not isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be a bool, got {type(value).__name__}")
    return value


def _require_v1(field: str, value: object) -> int:
    """Validate that a contract version field is the supported v1 (Law 7)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be int 1, got {type(value).__name__}")
    if value != 1:
        raise ContractError(
            f"contract field {field!r} must be 1 (only v1 is supported), got {value}"
        )
    return value


def _build_ip(spec: dict[str, Any]) -> CanonicalIPContract:
    _require_v1("version", spec.get("version", 1))
    _require_v1("version_field", spec.get("version_field", 1))
    return CanonicalIPContract(
        allow_ipv4=_require_bool("allow_ipv4", spec.get("allow_ipv4", True)),
        allow_ipv6=_require_bool("allow_ipv6", spec.get("allow_ipv6", True)),
        preserve_zone_id=_require_bool("preserve_zone_id", spec.get("preserve_zone_id", True)),
        authority_override=spec.get("authority_override", None),
    )


register_contract("canonical_ip", _build_ip)
