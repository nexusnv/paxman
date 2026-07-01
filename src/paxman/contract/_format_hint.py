"""Format-aware hint enum and string resolver.

The :class:`FormatHint` enum is the **single source of truth** for
format-aware capability dispatch. It is consumed by:

- :class:`paxman.contract.canonical.CanonicalField` — the contract
  attribute :attr:`CanonicalField.format_hints` is a
  ``tuple[FormatHint, ...]``.
- :class:`paxman.capabilities.spec.CapabilitySpec` — the per-spec
  attribute :attr:`CapabilitySpec.format_hint` is a
  ``FormatHint | None``.
- The four contract adapters (Dict DSL, Pydantic, JSON Schema,
  OpenAPI) which resolve the wire form (``"csv"`` / ``"json"`` /
  ``"xml"``) into enum members via :func:`resolve_format_hint`.

Design contract
---------------

**Member-agnostic.** This enum is a flat, additive enum. All code
that consumes ``FormatHint`` MUST iterate over the enum's members
or compare against ``cap.format_hint`` directly, and MUST NOT
enumerate the three V1.1.0 members as a hard-coded list. Adding a
new member (e.g. ``PDF`` when ``pdf_extraction`` lands in V1.2 / V2)
is a code-additive change in this file only — the executor,
planner, and adapters require no changes.

**Single-format dispatch.** A capability declares exactly one
``format_hint`` (or ``None``). A field declares a tuple of hints
(usually one). The planner's dispatch is the intersection:
``cap.format_hint in field.format_hints``.

Out of scope
------------

This enum is **only meaningful for tier-1 capabilities that consume
raw input bytes** (the V1.1.0 format-extractor family:
``csv_extraction``, ``json_path_extraction``, ``xpath_extraction``,
and future analogs like ``pdf_extraction``, ``yaml_extraction``,
``email_extraction``).

It is **not** declared on:

- Cleanup transforms (``case_normalization``, ``trim_extraction``,
  and any future post-resolution transforms in the ADR-0014
  family) — they read ``ctx.config["value"]``, not
  ``ctx.raw_input``.
- ``lookup`` (``STRUCTURED_LOOKUP``, tier 2) — keyed on a string,
  not on the input format.
- ``inference`` (``LOCAL_INFERENCE`` / ``REMOTE_INFERENCE``, tiers
  4/5) — the model consumes ``CompletionRequest.prompt: str``;
  the input bytes format is irrelevant.
- ``validation`` (``LOCAL_DETERMINISTIC``, tier 1) — operates on
  candidates produced by upstream steps, not on raw input.

See `GitHub issue #73 <https://github.com/nexusnv/paxman/issues/73>`_
for the design rationale.
"""

from __future__ import annotations

import enum


class FormatHint(enum.Enum):
    """Wire-format hint for input-format-aware tier-1 extractors.

    Members are the V1.1.0 set: CSV, JSON, XML. The enum is **flat
    and additive** — new members (PDF, YAML, EMAIL, HTML, TSV, ...)
    land by adding a member here, with no other code change.

    Attributes:
        CSV: Comma-separated values. Consumed by ``csv_extraction``.
        JSON: JSON document. Consumed by ``json_path_extraction``.
        XML: XML or HTML document. Consumed by ``xpath_extraction``
            (the capability handles both via a documented XPath
            subset; HTML is structural, not the ``text/html`` payload
            that ``text_extraction`` handles).
    """

    CSV = "csv"
    JSON = "json"
    XML = "xml"


def resolve_format_hint(value: object) -> FormatHint:
    """Resolve a wire-form value to a :class:`FormatHint` member.

    Accepts:

    - A :class:`FormatHint` member (returned as-is).
    - A case-insensitive string equal to a member's ``value`` or
      ``name`` (e.g. ``"csv"``, ``"CSV"``, ``"Csv"`` all resolve to
      :attr:`FormatHint.CSV`).

    Raises:
        TypeError: If *value* is not a :class:`FormatHint` and not a
            string.
        ValueError: If *value* is a string but does not match any
            member.

    The function is **member-agnostic**: it looks up by enum value
    (``FormatHint(value)``), not by enumerating the three V1.1.0
    members. A new member added in a follow-up minor release is
    resolved automatically.
    """
    if isinstance(value, FormatHint):
        return value
    if isinstance(value, str):
        # Case-insensitive lookup. Try ``FormatHint(value)`` first
        # (lowercase canonical), then ``FormatHint[value.upper()]``
        # for uppercase strings. Both paths are member-agnostic.
        try:
            return FormatHint(value.lower())
        except ValueError:
            try:
                return FormatHint[value.upper()]
            except KeyError as exc:
                raise ValueError(
                    f"unknown format hint {value!r}; expected one of "
                    f"{[m.value for m in FormatHint]}"
                ) from exc
    raise TypeError(
        f"format hint must be a FormatHint member or string, got {type(value).__name__}"
    )


class FormatHintValidationError(ValueError):
    """Raised by :func:`parse_format_hints` for invalid input.

    Carries ``error_code`` so the four contract adapters can wrap
    it in their own ``InvalidContractError`` with the project
    standard error_code "INVALID_FORMAT_HINT".
    """

    def __init__(self, message: str, *, error_code: str = "INVALID_FORMAT_HINT") -> None:
        super().__init__(message)
        self.error_code = error_code


def parse_format_hints(
    raw: object,
    *,
    field_name: str,
) -> tuple[FormatHint, ...]:
    """Validate, resolve, and deduplicate a wire-form ``format_hints`` value.

    Accepts a list of strings or :class:`FormatHint` members (or
    ``None`` / an empty list to mean "no hints"). Returns a tuple
    of deduplicated :class:`FormatHint` members, preserving
    insertion order.

    The function is **member-agnostic**: it looks up by enum value
    via :func:`resolve_format_hint`, not by enumerating the V1.1.0
    members. A new member added in a follow-up minor release is
    resolved automatically.

    Args:
        raw: The wire-form value. Must be a list, ``None``, or
            absent. Strings or other types are rejected.
        field_name: The field name, used only in the error
            message.

    Returns:
        A tuple of deduplicated :class:`FormatHint` members.

    Raises:
        FormatHintValidationError: With ``error_code="INVALID_FORMAT_HINT"``
            if *raw* is not a list, or if any element is not a
            known format hint.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise FormatHintValidationError(
            f"field {field_name!r} 'format_hints' must be a list, got {type(raw).__name__}"
        )
    out: list[FormatHint] = []
    seen: set[FormatHint] = set()
    for item in raw:
        try:
            hint = resolve_format_hint(item)
        except (TypeError, ValueError) as exc:
            raise FormatHintValidationError(
                f"field {field_name!r} has invalid format_hint {item!r}: {exc}"
            ) from exc
        if hint not in seen:
            seen.add(hint)
            out.append(hint)
    return tuple(out)


__all__ = [
    "FormatHint",
    "FormatHintValidationError",
    "parse_format_hints",
    "resolve_format_hint",
]
