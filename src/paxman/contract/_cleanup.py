"""Canonical parsing for explicitly declared post-extraction cleanup."""

from __future__ import annotations

import types
import typing

import attrs

__all__ = [
    "CleanupStep",
    "CleanupValidationError",
    "parse_cleanup",
]


_SUPPORTED_CAPABILITIES: typing.Final[frozenset[str]] = frozenset(
    {"case_normalization", "trim_extraction"}
)
_CASE_MODES: typing.Final[frozenset[str]] = frozenset({"lower", "upper", "title", "preserve"})


class CleanupValidationError(ValueError):
    """Raised when a field's cleanup declaration is invalid."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "INVALID_CLEANUP",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context: dict[str, object] = dict(context) if context else {}


def _freeze_config(config: object) -> types.MappingProxyType[str, object]:
    """Validate and make a cleanup config immutable."""
    if not isinstance(config, typing.Mapping):
        raise TypeError(f"cleanup config must be a mapping, got {type(config).__name__}")
    if not all(isinstance(key, str) for key in config):
        raise TypeError("cleanup config keys must be strings")
    return types.MappingProxyType(dict(config))


@attrs.frozen(slots=True)
class CleanupStep:
    """One explicitly declared post-extraction cleanup operation."""

    capability_id: str = attrs.field()
    config: typing.Mapping[str, object] = attrs.field(converter=_freeze_config, factory=dict)

    def __attrs_post_init__(self) -> None:
        """Validate that the step names a supported cleanup capability."""
        if self.capability_id not in _SUPPORTED_CAPABILITIES:
            raise ValueError(f"unsupported cleanup capability {self.capability_id!r}")

    def to_wire(self) -> dict[str, object]:
        """Return the stable schema-extension form of this step."""
        out: dict[str, object] = {"capability": self.capability_id}
        if self.config:
            out["config"] = dict(self.config)
        return out


def parse_cleanup(raw: object, *, field_name: str) -> tuple[CleanupStep, ...]:
    """Parse a field's explicit cleanup declaration.

    The wire form is a list of mappings containing ``capability`` and optional
    ``config`` keys. Only the two existing V1 cleanup capabilities are accepted.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise CleanupValidationError(
            f"field {field_name!r} 'cleanup' must be a list, got {type(raw).__name__}",
            context={"field_name": field_name, "raw_type": type(raw).__name__},
        )

    steps: list[CleanupStep] = []
    for index, item in enumerate(raw):
        context = {"field_name": field_name, "index": index}
        if not isinstance(item, typing.Mapping):
            raise CleanupValidationError(
                f"field {field_name!r} cleanup entry {index} must be a mapping",
                context=context,
            )
        capability = item.get("capability")
        if not isinstance(capability, str) or capability not in _SUPPORTED_CAPABILITIES:
            raise CleanupValidationError(
                f"field {field_name!r} cleanup entry {index} has unsupported capability "
                f"{capability!r}",
                context={**context, "capability": capability},
            )
        config = item.get("config", {})
        if not isinstance(config, typing.Mapping) or not all(
            isinstance(key, str) for key in config
        ):
            raise CleanupValidationError(
                f"field {field_name!r} cleanup entry {index} config must be a string-keyed mapping",
                context={**context, "capability": capability},
            )
        _validate_config(capability, config, field_name=field_name, index=index)
        steps.append(CleanupStep(capability_id=capability, config=config))
    return tuple(steps)


def _validate_config(
    capability: str,
    config: typing.Mapping[str, object],
    *,
    field_name: str,
    index: int,
) -> None:
    """Validate the closed configuration shape for one cleanup capability."""
    allowed = {"mode"} if capability == "case_normalization" else {"chars"}
    unknown = set(config) - allowed
    if unknown:
        raise CleanupValidationError(
            f"field {field_name!r} cleanup entry {index} has unsupported config keys "
            f"{sorted(unknown)!r}",
            context={"field_name": field_name, "index": index, "capability": capability},
        )
    if capability == "case_normalization":
        mode = config.get("mode")
        if not isinstance(mode, str) or mode not in _CASE_MODES:
            raise CleanupValidationError(
                f"field {field_name!r} cleanup entry {index} requires a supported mode",
                context={"field_name": field_name, "index": index, "capability": capability},
            )
    elif "chars" in config and (not isinstance(config["chars"], str) or not config["chars"]):
        raise CleanupValidationError(
            f"field {field_name!r} cleanup entry {index} 'chars' must be a non-empty string",
            context={"field_name": field_name, "index": index, "capability": capability},
        )
