"""Unit tests for :mod:`paxman.planner.input_profile` per Sprint 0 spec."""

from __future__ import annotations

import hashlib

import pytest

from paxman.planner.input_profile import (
    InputProfile,
    classify,
    compute_density,
    make_profile,
)

pytestmark = pytest.mark.unit


# --- InputProfile invariants --------------------------------------------


def test_input_profile_minimal() -> None:
    p = InputProfile(
        input_type="text",
        size=10,
        content_hash="a" * 64,
        density=0.5,
        is_empty=False,
    )
    assert p.input_type == "text"
    assert p.size == 10
    assert p.is_empty is False


def test_input_profile_rejects_invalid_input_type() -> None:
    with pytest.raises(ValueError, match="input_type must be one of"):
        InputProfile(
            input_type="bogus",
            size=0,
            content_hash="a" * 64,
            density=0.0,
            is_empty=True,
        )


def test_input_profile_rejects_negative_size() -> None:
    with pytest.raises(ValueError, match="size must be non-negative"):
        InputProfile(
            input_type="text",
            size=-1,
            content_hash="a" * 64,
            density=0.0,
            is_empty=True,
        )


def test_input_profile_rejects_bool_size() -> None:
    with pytest.raises(TypeError, match="size must be an int"):
        InputProfile(
            input_type="text",
            size=True,  # type: ignore[arg-type]
            content_hash="a" * 64,
            density=0.0,
            is_empty=True,
        )


def test_input_profile_rejects_short_hash() -> None:
    with pytest.raises(ValueError, match="64 lowercase hex chars"):
        InputProfile(
            input_type="text",
            size=0,
            content_hash="abc",
            density=0.0,
            is_empty=True,
        )


def test_input_profile_rejects_uppercase_hash() -> None:
    with pytest.raises(ValueError, match="64 lowercase hex chars"):
        InputProfile(
            input_type="text",
            size=0,
            content_hash="A" * 64,
            density=0.0,
            is_empty=True,
        )


def test_input_profile_rejects_out_of_range_density() -> None:
    with pytest.raises(ValueError, match="density must be in"):
        InputProfile(
            input_type="text",
            size=0,
            content_hash="a" * 64,
            density=1.5,
            is_empty=True,
        )


# --- classify ------------------------------------------------------------


def test_classify_empty() -> None:
    assert classify(b"") == "empty"


def test_classify_text() -> None:
    assert classify(b"Hello, world!") == "text"


def test_classify_html() -> None:
    assert classify(b"<html><body>...</body></html>") == "html"


def test_classify_html_doctype() -> None:
    assert classify(b"<!DOCTYPE html><html>...</html>") == "html"


def test_classify_json() -> None:
    assert classify(b'{"a": 1, "b": [2, 3]}') == "json"


def test_classify_json_array() -> None:
    assert classify(b"[1, 2, 3]") == "json"


def test_classify_invalid_json_falls_through() -> None:
    """A '{' that doesn't parse as JSON falls through to text."""
    assert classify(b"{not valid json") == "text"


def test_classify_csv() -> None:
    assert classify(b"a,b,c,d,e\n") == "csv"


def test_classify_csv_needs_three_commas() -> None:
    """A line with only 1-2 commas is not classified as CSV."""
    assert classify(b"a,b\n") == "text"


def test_classify_pdf_text() -> None:
    assert classify(b"%PDF-1.4\n%hello\n") == "pdf_text"


def test_classify_email() -> None:
    msg = b"From sender@example.com Mon Jan 01 00:00:00 2024\nSubject: Hi\n\nbody\n"
    assert classify(msg) == "email"


def test_classify_email_requires_subject() -> None:
    """A 'From ' line without 'Subject:' is not email."""
    msg = b"From sender@example.com Mon Jan 01 00:00:00 2024\nbody\n"
    assert classify(msg) == "text"


# --- compute_density -----------------------------------------------------


def test_density_empty_input() -> None:
    assert compute_density(b"", "empty") == 0.0


def test_density_unknown_input() -> None:
    assert compute_density(b"abc", "unknown") == 0.0


def test_density_all_whitespace() -> None:
    assert compute_density(b"   \n\t  ", "text") == 0.0


def test_density_dense_text() -> None:
    text = b"hello, world!"
    non_ws = sum(1 for c in text.decode() if not c.isspace())
    assert compute_density(text, "text") == non_ws / len(text)


def test_density_counts_characters_not_bytes() -> None:
    """compute_density must count non-whitespace CHARACTERS, not BYTES.

    Regression test for the Sprint 9 D9.5 optimization: a naive
    byte-level scan (``bytes.count()`` over ASCII whitespace)
    silently returns the wrong density for non-ASCII input because
    UTF-8 multi-byte sequences inflate the byte length.  For
    example, ``"é"`` is 2 bytes but 1 character; without the
    character-based fallback, the density is reported as ``1.0``
    instead of ``0.5``.

    See: CodeRabbit review on PR #16 (2026-06-26).
    """
    # Single character, 2 bytes: density is by-character.
    e_acute = "é".encode("utf-8")  # b"\\xc3\\xa9" — 2 bytes
    assert len(e_acute) == 2
    assert compute_density(e_acute, "text") == 0.5

    # CJK: 2 characters, 6 bytes: density is 2/6.
    hanzi = "汉字".encode("utf-8")
    assert len(hanzi) == 6
    assert abs(compute_density(hanzi, "text") - 2 / 6) < 1e-9

    # Unicode whitespace (NBSP U+00A0, encoded as 2 bytes 0xC2 0xA0)
    # is whitespace by ``str.isspace()`` semantics, so density = 0/2.
    nbsp = b"\xc2\xa0"
    assert compute_density(nbsp, "text") == 0.0

    # Mixed ASCII + CJK + space: character count, byte-denominated.
    mixed = "Hello 汉字 World".encode("utf-8")
    text = mixed.decode("utf-8")
    non_ws = sum(1 for ch in text if not ch.isspace())
    assert compute_density(mixed, "text") == non_ws / len(mixed)


def test_density_ascii_fast_path_matches_char_path() -> None:
    """For ASCII input, the byte-level fast path must equal the
    character-level reference implementation exactly."""
    # 100 KB ASCII text — exercise the fast path on a large input.
    text = (b"the quick brown fox jumps over the lazy dog. " * 2000)[:100_000]
    assert text.isascii()
    expected = sum(1 for ch in text.decode() if not ch.isspace()) / len(text)
    assert compute_density(text, "text") == expected


# --- make_profile --------------------------------------------------------


def test_make_profile_text_example_from_spec() -> None:
    """Worked example from docs/specs/input-profile-spec.md §7."""
    p = make_profile(b"Hello, World!\n")
    assert p.input_type == "text"
    assert p.size == 14
    assert p.is_empty is False
    # Density: non-whitespace chars = 12, total = 14 → 0.857...
    assert abs(p.density - 12 / 14) < 1e-9


def test_make_profile_empty_input() -> None:
    p = make_profile(b"")
    assert p.input_type == "empty"
    assert p.size == 0
    assert p.is_empty is True
    assert p.density == 0.0
    # SHA-256 of empty bytes (per EC1 of the spec).
    assert p.content_hash == hashlib.sha256(b"").hexdigest()


def test_make_profile_whitespace_only() -> None:
    p = make_profile(b"   \n\t  ")
    assert p.is_empty is True
    assert p.density == 0.0


def test_make_profile_invalid_utf8_falls_through_to_text() -> None:
    """Per spec EC3: plain binary that passes all rules without matching
    falls through to ``"text"``, not ``"unknown"``."""
    p = make_profile(b"\xff\xfe\x00\x01")
    assert p.input_type == "text"  # falls through, not "unknown"


def test_input_profile_accepts_unknown_input_type() -> None:
    """``InputProfile`` constructor accepts ``"unknown"`` even though
    :func:`classify` does not currently produce it (the Oracle
    review noted this as a structural coverage gap)."""
    p = InputProfile(
        input_type="unknown",
        size=0,
        content_hash="a" * 64,
        density=0.0,
        is_empty=False,
    )
    assert p.input_type == "unknown"


def test_classify_returns_unknown_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a classification rule raises, ``classify()`` returns
    ``"unknown"`` (per spec §5.1 rule 8)."""
    from paxman.planner import input_profile

    def _raise(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated rule failure")

    # Force json.loads to raise an unexpected exception (not just
    # ValueError / UnicodeDecodeError, which the function already
    # catches).
    monkeypatch.setattr(input_profile._json, "loads", _raise)
    assert input_profile.classify(b'{"a": 1}') == "unknown"


def test_make_profile_str_input() -> None:
    """A str input is encoded as UTF-8 with errors='replace'."""
    p = make_profile("Hello")
    assert p.input_type == "text"
    assert p.size == 5


def test_make_profile_replaces_lone_surrogate() -> None:
    """A lone surrogate is replaced with U+FFFD (3 UTF-8 bytes).

    Per spec EC5, ``"Hello \\ud800 World"`` encodes to 13 bytes. (Verified
    empirically.)  We construct the input via :func:`chr` to avoid a
    pytest collection-time encoding error.
    """
    surrogate = chr(0xD800)
    p = make_profile("Hello " + surrogate + " World")
    assert p.size == 13


def test_make_profile_rejects_dict() -> None:
    """A non-str/bytes input is rejected (the API layer serializes)."""
    with pytest.raises(TypeError, match="input_data must be str or bytes"):
        make_profile({"a": 1})  # type: ignore[arg-type]


# --- determinism ---------------------------------------------------------


@pytest.mark.deterministic
def test_make_profile_is_deterministic() -> None:
    """Same input → same profile, byte-for-byte."""
    raw = b"ACME Corp\nInvoice #1234\nTotal: $1,234.56\n"
    a = make_profile(raw)
    b = make_profile(raw)
    assert a == b


@pytest.mark.deterministic
def test_make_profile_content_hash_matches_sha256() -> None:
    raw = b"hello world"
    p = make_profile(raw)
    assert p.content_hash == hashlib.sha256(raw).hexdigest()
