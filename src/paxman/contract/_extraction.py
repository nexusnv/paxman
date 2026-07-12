"""Canonical parsing for explicitly declared field extraction."""

from __future__ import annotations

import types
import typing

import attrs

__all__ = [
    "ExtractionStep",
    "ExtractionValidationError",
    "parse_extraction",
]


class ExtractionValidationError(ValueError):
    """Raised when a field's extraction declaration is invalid."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "INVALID_EXTRACTION",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context: dict[str, object] = dict(context) if context else {}


def _freeze_config(config: object) -> types.MappingProxyType[str, object]:
    """Validate and make extractor configuration immutable."""
    if not isinstance(config, typing.Mapping):
        raise TypeError(f"extraction config must be a mapping, got {type(config).__name__}")
    if not all(isinstance(key, str) for key in config):
        raise TypeError("extraction config keys must be strings")
    return types.MappingProxyType(dict(config))


@attrs.frozen(slots=True)
class ExtractionStep:
    """One field-specific extraction operation declared by a contract."""

    capability_id: str = attrs.field()
    config: typing.Mapping[str, object] = attrs.field(converter=_freeze_config)

    def __attrs_post_init__(self) -> None:
        """Validate the closed Sprint 4 extractor set."""
        if self.capability_id != "regex_extraction":
            raise ValueError(f"unsupported extraction capability {self.capability_id!r}")

    def to_wire(self) -> dict[str, object]:
        """Return the stable contract wire form."""
        return {"capability": self.capability_id, "config": dict(self.config)}


def parse_extraction(raw: object, *, field_name: str) -> ExtractionStep | None:
    """Parse a field-specific regex extraction declaration."""
    if raw is None:
        return None
    context: dict[str, object] = {"field_name": field_name}
    if not isinstance(raw, typing.Mapping):
        raise ExtractionValidationError(
            f"field {field_name!r} 'extract' must be a mapping",
            context={**context, "raw_type": type(raw).__name__},
        )
    capability = raw.get("capability")
    if capability != "regex_extraction":
        raise ExtractionValidationError(
            f"field {field_name!r} extraction must use 'regex_extraction', got {capability!r}",
            context={**context, "capability": capability},
        )
    config = raw.get("config")
    if not isinstance(config, typing.Mapping) or not all(isinstance(key, str) for key in config):
        raise ExtractionValidationError(
            f"field {field_name!r} extraction config must be a string-keyed mapping",
            context=context,
        )
    if (
        set(config) != {"pattern"}
        or not isinstance(config["pattern"], str)
        or not config["pattern"]
    ):
        raise ExtractionValidationError(
            f"field {field_name!r} extraction requires a non-empty string pattern",
            context=context,
        )
    return ExtractionStep(capability_id="regex_extraction", config=config)
