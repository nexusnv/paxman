"""Semantic-tag handling for canonical contracts.

Semantic tags are **free-form string labels** attached to a
:class:`~paxman.contract.canonical.CanonicalField` via its
``semantic_tags`` attribute. They describe the *meaning* of a field (e.g.,
``"iso4217"``, ``"email"``, ``"pii"``, ``"currency-sensitive"``) as opposed
to its *structure* (its :class:`~paxman.types.FieldType` and constraints).

This module provides:

- :data:`KNOWN_SEMANTIC_TAGS` — the V1 registry of well-known tags. The
  set is closed in V1; adding a tag requires an ADR.
- :func:`is_known_tag` — membership check.
- :func:`suggest_field_type_from_tags` — when a contract author uses a
  well-known tag (e.g., ``"iso4217"``) without an explicit type, an
  adapter may consult this function to suggest a default. Adapters are
  free to override; this is a hint, not a rule.
- :func:`validate_semantic_tags` — raise
  :class:`~paxman.errors.InvalidSemanticTagError` for malformed tags
  (empty strings, duplicates).

Design notes
------------

- Tags are **advisory** for adapters. An adapter may produce a field with
  an unknown tag without raising; the contract layer does not enforce a
  closed vocabulary at the canonical-form level. Enforcement is at the
  adapter level (e.g., Dict DSL parser rejects unknown tag forms).
- This module is the single source of truth for the V1 known-tag set.
"""

from __future__ import annotations

import typing

from paxman.errors import InvalidSemanticTagError
from paxman.types import FieldType

__all__ = [
    "KNOWN_SEMANTIC_TAGS",
    "is_known_tag",
    "suggest_field_type_from_tags",
    "validate_semantic_tags",
]


# ---------------------------------------------------------------------------
# Known-tag registry
# ---------------------------------------------------------------------------

#: The V1 registry of well-known semantic tags. The set is closed in V1;
#: adding a tag requires an ADR per ``PACKAGE_STRUCTURE.md`` §3.4.
#:
#: Tags are grouped by their primary planner effect (per
#: ``docs/specs/dict-dsl-spec.md`` §3.3 + ``docs/reference/extending.md`` §1.4):
#:
#: Type hints (suggest a V1 field type when none is given):
#: - ``"iso4217"`` — ISO-4217 currency code. Hints ``STRING`` or ``MONEY``.
#: - ``"email"`` — RFC 5322 email address. Hints ``STRING``.
#: - ``"url"`` — RFC 3986 URL. Hints ``STRING``.
#: - ``"phone"`` — E.164 phone number. Hints ``STRING``.
#: - ``"date"`` — ISO-8601 date. Hints ``DATE``.
#: - ``"datetime"`` — ISO-8601 datetime. Hints ``DATE``.
#:
#: Planner hints (steer heuristic selection):
#: - ``"pii"`` — personally identifying information.
#: - ``"currency-sensitive"`` — monetary field, prefer MONEY-aware paths.
#: - ``"high-stakes"`` — flag for human review on low confidence.
#: - ``"regex-able"`` — field is likely to match a regex.
#: - ``"lookup-able"`` — field is likely to be found in a lookup table.
KNOWN_SEMANTIC_TAGS: typing.Final[frozenset[str]] = frozenset(
    {
        # Type hints
        "iso4217",
        "email",
        "url",
        "phone",
        "date",
        "datetime",
        # Planner hints
        "pii",
        "currency-sensitive",
        "high-stakes",
        "regex-able",
        "lookup-able",
    }
)


#: Mapping from type-hint tags to the suggested V1 field type. Used by
#: :func:`suggest_field_type_from_tags` when an adapter is given a tag
#: but no explicit type.
_TYPE_HINT_TO_FIELD_TYPE: typing.Final[dict[str, FieldType]] = {
    "iso4217": FieldType.STRING,  # the currency code itself, not the MONEY value
    "email": FieldType.STRING,
    "url": FieldType.STRING,
    "phone": FieldType.STRING,
    "date": FieldType.DATE,
    "datetime": FieldType.DATE,
}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def is_known_tag(tag: str) -> bool:
    """Return ``True`` if *tag* is in the V1 known-tag registry.

    Args:
        tag: The tag string to check.

    Returns:
        Whether *tag* is a known V1 semantic tag.

    Examples:
        >>> is_known_tag("pii")
        True
        >>> is_known_tag("non-existent-tag")
        False
    """
    return tag in KNOWN_SEMANTIC_TAGS


def suggest_field_type_from_tags(tags: typing.Iterable[str]) -> FieldType | None:
    """Suggest a V1 field type from a set of semantic tags.

    When a contract author attaches a type-hint tag (e.g., ``"email"``)
    but does not specify a type, an adapter may call this function to
    pick a sensible default. The first type-hint tag encountered wins;
    planner-hint tags (``"pii"``, ``"currency-sensitive"``, ...) do not
    influence the suggestion.

    Args:
        tags: An iterable of semantic tag strings.

    Returns:
        A suggested :class:`~paxman.types.FieldType`, or ``None`` if no
        type-hint tag is present in the iterable.

    Examples:
        >>> suggest_field_type_from_tags(["email"])
        <FieldType.STRING: 'STRING'>
        >>> suggest_field_type_from_tags(["pii", "currency-sensitive"])
        >>> suggest_field_type_from_tags(["date", "pii"])
        <FieldType.DATE: 'DATE'>
    """
    for tag in tags:
        suggested = _TYPE_HINT_TO_FIELD_TYPE.get(tag)
        if suggested is not None:
            return suggested
    return None


def validate_semantic_tags(tags: typing.Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize a collection of semantic tags.

    Performs three checks:

    1. All tags are non-empty strings.
    2. All tags are lowercase ASCII (the V1 convention; mixed-case tags
       are rejected for forward-compatibility).
    3. No duplicates.

    The result is a deterministic-order tuple (sorted).

    Args:
        tags: An iterable of tag strings.

    Returns:
        A tuple of validated, sorted, deduplicated tags.

    Raises:
        InvalidSemanticTagError: If any tag is empty, not a string, or
            not lowercase ASCII.

    Examples:
        >>> validate_semantic_tags(["pii", "currency-sensitive"])
        ('currency-sensitive', 'pii')
        >>> validate_semantic_tags([])
        ()
    """
    seen: set[str] = set()
    validated: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            raise InvalidSemanticTagError(
                f"semantic tag must be a string, got {type(tag).__name__}: {tag!r}",
                context={"tag": repr(tag), "reason": "not-a-string"},
            )
        if not tag:
            raise InvalidSemanticTagError(
                "semantic tag must be non-empty",
                context={"tag": repr(tag), "reason": "empty"},
            )
        if not tag.isascii() or not tag.islower():
            raise InvalidSemanticTagError(
                f"semantic tag must be lowercase ASCII, got {tag!r}",
                context={"tag": tag, "reason": "not-lowercase-ascii"},
            )
        if tag not in seen:
            seen.add(tag)
            validated.append(tag)
    return tuple(sorted(validated))
