"""Unit tests for ``paxman.contract.semantics`` — semantic-tag handling.

Covers KNOWN_SEMANTIC_TAGS (frozenset, 11 tags), is_known_tag,
suggest_field_type_from_tags (type-hint tag mapping, first-wins, planner-hint
tags return None), and validate_semantic_tags (sorted dedup, non-string
rejection, empty rejection, uppercase rejection).
"""

from __future__ import annotations

import pytest

from paxman.contract.semantics import (
    KNOWN_SEMANTIC_TAGS,
    is_known_tag,
    suggest_field_type_from_tags,
    validate_semantic_tags,
)
from paxman.errors import InvalidSemanticTagError
from paxman.types import FieldType

# --- KNOWN_SEMANTIC_TAGS ----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_known_semantic_tags_is_frozenset() -> None:
    """KNOWN_SEMANTIC_TAGS is a frozenset (immutable)."""
    assert isinstance(KNOWN_SEMANTIC_TAGS, frozenset)


@pytest.mark.deterministic
@pytest.mark.unit
def test_known_semantic_tags_has_eleven_members() -> None:
    """KNOWN_SEMANTIC_TAGS has the 11 documented V1 tags."""
    expected = {
        "iso4217",
        "email",
        "url",
        "phone",
        "date",
        "datetime",
        "pii",
        "currency-sensitive",
        "high-stakes",
        "regex-able",
        "lookup-able",
    }
    assert set(KNOWN_SEMANTIC_TAGS) == expected
    assert len(KNOWN_SEMANTIC_TAGS) == 11


@pytest.mark.deterministic
@pytest.mark.unit
def test_known_semantic_tags_is_immutable() -> None:
    """KNOWN_SEMANTIC_TAGS cannot be mutated (frozenset)."""
    with pytest.raises(AttributeError):
        KNOWN_SEMANTIC_TAGS.add("new-tag")  # type: ignore[attr-defined]


# --- is_known_tag -----------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
@pytest.mark.parametrize("tag", sorted(KNOWN_SEMANTIC_TAGS))
def test_is_known_tag_returns_true_for_known(tag: str) -> None:
    """is_known_tag returns True for every known tag."""
    assert is_known_tag(tag) is True


@pytest.mark.deterministic
@pytest.mark.unit
def test_is_known_tag_returns_false_for_unknown() -> None:
    """is_known_tag returns False for an unknown tag."""
    assert is_known_tag("non-existent-tag") is False


@pytest.mark.deterministic
@pytest.mark.unit
def test_is_known_tag_returns_false_for_empty() -> None:
    """is_known_tag returns False for the empty string."""
    assert is_known_tag("") is False


@pytest.mark.deterministic
@pytest.mark.unit
def test_is_known_tag_returns_false_for_uppercase() -> None:
    """is_known_tag returns False for uppercase variant (case-sensitive)."""
    assert is_known_tag("PII") is False


# --- suggest_field_type_from_tags -------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_field_type_empty_returns_none() -> None:
    """Empty iterable returns None."""
    assert suggest_field_type_from_tags([]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_email_returns_string() -> None:
    """'email' tag suggests STRING."""
    assert suggest_field_type_from_tags(["email"]) is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_date_returns_date() -> None:
    """'date' tag suggests DATE."""
    assert suggest_field_type_from_tags(["date"]) is FieldType.DATE


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_datetime_returns_date() -> None:
    """'datetime' tag suggests DATE."""
    assert suggest_field_type_from_tags(["datetime"]) is FieldType.DATE


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_iso4217_returns_string() -> None:
    """'iso4217' tag suggests STRING (the currency code, not MONEY)."""
    assert suggest_field_type_from_tags(["iso4217"]) is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_url_returns_string() -> None:
    """'url' tag suggests STRING."""
    assert suggest_field_type_from_tags(["url"]) is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_phone_returns_string() -> None:
    """'phone' tag suggests STRING."""
    assert suggest_field_type_from_tags(["phone"]) is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_pii_returns_none() -> None:
    """'pii' is a planner-hint tag, returns None."""
    assert suggest_field_type_from_tags(["pii"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_currency_sensitive_returns_none() -> None:
    """'currency-sensitive' is a planner-hint tag, returns None."""
    assert suggest_field_type_from_tags(["currency-sensitive"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_high_stakes_returns_none() -> None:
    """'high-stakes' is a planner-hint tag, returns None."""
    assert suggest_field_type_from_tags(["high-stakes"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_regex_able_returns_none() -> None:
    """'regex-able' is a planner-hint tag, returns None."""
    assert suggest_field_type_from_tags(["regex-able"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_lookup_able_returns_none() -> None:
    """'lookup-able' is a planner-hint tag, returns None."""
    assert suggest_field_type_from_tags(["lookup-able"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_first_type_hint_wins() -> None:
    """First type-hint tag in iteration order wins."""
    assert suggest_field_type_from_tags(["email", "date"]) is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_skips_planner_hints() -> None:
    """Planner-hint tags are skipped; type-hint tag after them wins."""
    assert suggest_field_type_from_tags(["pii", "currency-sensitive", "email"]) is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_only_planner_hints_returns_none() -> None:
    """All planner-hint tags returns None."""
    assert suggest_field_type_from_tags(["pii", "high-stakes"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_unknown_tag_returns_none() -> None:
    """Unknown tags return None (not in the type-hint mapping)."""
    assert suggest_field_type_from_tags(["unknown-tag"]) is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_suggest_accepts_tuple() -> None:
    """suggest_field_type_from_tags accepts a tuple."""
    assert suggest_field_type_from_tags(("email",)) is FieldType.STRING


# --- validate_semantic_tags -------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_empty_returns_empty_tuple() -> None:
    """Empty iterable returns ()."""
    assert validate_semantic_tags([]) == ()


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_single_valid_tag() -> None:
    """Single valid tag returns a 1-tuple."""
    assert validate_semantic_tags(["pii"]) == ("pii",)


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_multiple_valid_tags_sorted() -> None:
    """Multiple valid tags are returned sorted."""
    result = validate_semantic_tags(["pii", "email"])
    assert result == ("email", "pii")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_deduplicates_tags() -> None:
    """Duplicate tags are deduplicated."""
    result = validate_semantic_tags(["pii", "pii", "email"])
    assert result == ("email", "pii")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_preserves_only_unique() -> None:
    """Result contains only unique tags."""
    result = validate_semantic_tags(["a", "b", "a", "c", "b"])
    assert result == ("a", "b", "c")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_rejects_uppercase_tag() -> None:
    """Uppercase tag raises InvalidSemanticTagError."""
    with pytest.raises(InvalidSemanticTagError, match="lowercase ASCII"):
        validate_semantic_tags(["PII"])


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_rejects_mixed_case_tag() -> None:
    """Mixed-case tag raises InvalidSemanticTagError."""
    with pytest.raises(InvalidSemanticTagError, match="lowercase ASCII"):
        validate_semantic_tags(["Pii"])


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_rejects_non_string_tag() -> None:
    """Non-string tag raises InvalidSemanticTagError."""
    with pytest.raises(InvalidSemanticTagError, match="must be a string"):
        validate_semantic_tags([42])  # type: ignore[list-item]


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_rejects_none_tag() -> None:
    """None tag raises InvalidSemanticTagError."""
    with pytest.raises(InvalidSemanticTagError, match="must be a string"):
        validate_semantic_tags([None])  # type: ignore[list-item]


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_rejects_empty_string_tag() -> None:
    """Empty string tag raises InvalidSemanticTagError."""
    with pytest.raises(InvalidSemanticTagError, match="must be non-empty"):
        validate_semantic_tags([""])


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_rejects_non_ascii_tag() -> None:
    """Non-ASCII tag raises InvalidSemanticTagError."""
    with pytest.raises(InvalidSemanticTagError, match="lowercase ASCII"):
        validate_semantic_tags(["café"])


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_returns_tuple_type() -> None:
    """Result is a tuple (not a list)."""
    result = validate_semantic_tags(["pii"])
    assert isinstance(result, tuple)


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_result_is_sorted() -> None:
    """Result is always sorted alphabetically."""
    result = validate_semantic_tags(["z", "a", "m"])
    assert result == ("a", "m", "z")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_accepts_set_input() -> None:
    """validate_semantic_tags accepts a set (any iterable)."""
    result = validate_semantic_tags({"pii", "email"})
    assert result == ("email", "pii")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_context_has_reason_for_non_string() -> None:
    """Error context carries 'reason' key for non-string tags."""
    try:
        validate_semantic_tags([42])
    except InvalidSemanticTagError as e:
        assert e.context.get("reason") == "not-a-string"
    else:
        pytest.fail("should have raised")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_context_has_reason_for_empty() -> None:
    """Error context carries 'reason' key for empty tags."""
    try:
        validate_semantic_tags([""])
    except InvalidSemanticTagError as e:
        assert e.context.get("reason") == "empty"
    else:
        pytest.fail("should have raised")


@pytest.mark.deterministic
@pytest.mark.unit
def test_validate_context_has_reason_for_uppercase() -> None:
    """Error context carries 'reason' key for non-lowercase tags."""
    try:
        validate_semantic_tags(["PII"])
    except InvalidSemanticTagError as e:
        assert e.context.get("reason") == "not-lowercase-ascii"
    else:
        pytest.fail("should have raised")
