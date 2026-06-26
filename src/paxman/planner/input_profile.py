"""Lightweight input classifier — derives :class:`InputProfile` from raw input.

Per ``docs/specs/input-profile-spec.md``, the :class:`InputProfile`
is a 5-field metadata structure that the planner reads to make
heuristic decisions **without invoking capabilities**. It is
derived once per :func:`paxman.normalize()` call and passed into
the planner.

The function :func:`make_profile` is a **pure function**: same input
bytes → same :class:`InputProfile` byte-for-byte. No I/O, no clock,
no random state, no capability invocation.

5-field V1 surface (per the Sprint 0 spec):

- ``input_type`` (8-value :class:`InputType`) — coarse format
  classification.
- ``size`` (int) — byte count.
- ``content_hash`` (str) — 64-char lowercase hex SHA-256.
- ``density`` (float) — non-whitespace ratio in ``[0.0, 1.0]``.
- ``is_empty`` (bool) — ``True`` if size == 0 or whitespace-only.
"""

from __future__ import annotations

import hashlib
import json as _json
import re
import typing

import attrs

__all__ = [
    "InputProfile",
    "InputType",
    "classify",
    "compute_density",
    "make_profile",
]


#: The 8 V1 input types (per ``docs/specs/input-profile-spec.md`` §3.1).
InputType = typing.Literal[
    "text",
    "html",
    "csv",
    "json",
    "pdf_text",
    "email",
    "empty",
    "unknown",
]


#: Set of all 8 valid input type values (used for runtime validation).
_VALID_INPUT_TYPES: typing.Final[frozenset[str]] = frozenset(
    {"text", "html", "csv", "json", "pdf_text", "email", "empty", "unknown"}
)


#: Marker used by ``classify()`` to fall through to "unknown" when
# every rule fails to match.
_UNKNOWN_FALLTHROUGH: typing.Final[str] = "unknown"


@attrs.frozen(slots=True)
class InputProfile:
    """Lightweight metadata derived from raw input bytes.

    Per ``docs/specs/input-profile-spec.md`` §3.1:

    Attributes:
        input_type: Coarse classification of the raw input format
            (one of 8 :data:`InputType` values).
        size: Byte count of the normalized input (``>= 0``).
        content_hash: 64-char lowercase hex SHA-256 of the
            normalized bytes.
        density: Ratio of non-whitespace characters to total bytes
            (``0.0 <= density <= 1.0``).
        is_empty: ``True`` if the input is empty (size == 0) or
            whitespace-only.

    Examples:
        >>> InputProfile(
        ...     input_type="text",
        ...     size=14,
        ...     content_hash="d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5",
        ...     density=0.857,
        ...     is_empty=False,
        ... )
        InputProfile(input_type='text', size=14, ...)
    """

    input_type: str = attrs.field()
    size: int = attrs.field()
    content_hash: str = attrs.field()
    density: float = attrs.field()
    is_empty: bool = attrs.field()

    def __attrs_post_init__(self) -> None:
        """Validate invariants per ``docs/specs/input-profile-spec.md`` §3.2."""
        if not isinstance(self.input_type, str):
            raise TypeError(f"input_type must be a str, got {type(self.input_type).__name__}")
        if self.input_type not in _VALID_INPUT_TYPES:
            raise ValueError(
                f"input_type must be one of {sorted(_VALID_INPUT_TYPES)}, got {self.input_type!r}"
            )
        if type(self.size) is not int or isinstance(self.size, bool):
            raise TypeError(f"size must be an int, got {type(self.size).__name__}: {self.size!r}")
        if self.size < 0:
            raise ValueError(f"size must be non-negative, got {self.size}")
        if not isinstance(self.content_hash, str):
            raise TypeError(f"content_hash must be a str, got {type(self.content_hash).__name__}")
        if not _HEX64_PATTERN.fullmatch(self.content_hash):
            raise ValueError(
                f"content_hash must be 64 lowercase hex chars, got {self.content_hash!r}"
            )
        if not isinstance(self.density, (int, float)) or isinstance(self.density, bool):
            raise TypeError(f"density must be a number, got {type(self.density).__name__}")
        if not 0.0 <= float(self.density) <= 1.0:
            raise ValueError(f"density must be in [0.0, 1.0], got {self.density}")
        if not isinstance(self.is_empty, bool):
            raise TypeError(f"is_empty must be a bool, got {type(self.is_empty).__name__}")


#: 64 lowercase hex chars (SHA-256). Compiled once.
_HEX64_PATTERN: typing.Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


#: ``text/html`` / ``<!DOCTYPE html`` pattern, case-insensitive,
#: scanned in the first 4096 bytes.
_HTML_PATTERN: typing.Final[re.Pattern[bytes]] = re.compile(
    rb"<\s*html|<!doctype\s+html",
    re.IGNORECASE,
)


#: Email RFC 822 markers scanned in the first 4096 bytes.
_FROM_HEADER_PATTERN: typing.Final[re.Pattern[bytes]] = re.compile(rb"^From ", re.MULTILINE)
_SUBJECT_HEADER_PATTERN: typing.Final[re.Pattern[bytes]] = re.compile(rb"^Subject:", re.MULTILINE)


def _to_bytes(input_data: str | bytes) -> bytes:
    """Normalize input to ``bytes`` (UTF-8 with ``errors="replace"``)."""
    if isinstance(input_data, bytes):
        return input_data
    if isinstance(input_data, str):
        return input_data.encode("utf-8", errors="replace")
    raise TypeError(f"input_data must be str or bytes, got {type(input_data).__name__}")


def classify(normalized_bytes: bytes) -> str:
    """Classify the raw input into one of 8 :data:`InputType` values.

    Per ``docs/specs/input-profile-spec.md`` §5.1, rules are evaluated
    in order; the first match wins. The last rule (``"unknown"``)
    is the catch-all for inputs that fail to match any rule.

    The 8 rules are wrapped in a :keyword:`try` block so that an
    unexpected exception (e.g., a future regex on an exotic
    encoding) is reported as ``"unknown"`` rather than crashing
    the planner. Per the spec, ``"unknown"`` is the documented
    fallback for "binary garbage that causes errors in the
    classification rules."

    Args:
        normalized_bytes: The input as ``bytes``.

    Returns:
        One of the 8 ``InputType`` values. ``"unknown"`` is only
        returned when an exception is raised during rule evaluation.
    """
    try:
        if len(normalized_bytes) == 0:
            return "empty"

        head = normalized_bytes[:16]
        if head.startswith(b"%PDF-"):
            return "pdf_text"

        # JSON: first non-whitespace byte is { or [, and json.loads succeeds
        # on the first 8192 bytes (or full input if smaller).
        stripped = normalized_bytes.lstrip()
        if stripped[:1] in (b"{", b"["):
            sample = normalized_bytes[:8192]
            try:
                _json.loads(sample)
                return "json"
            except (ValueError, UnicodeDecodeError):
                pass

        # Email: From header at the start of a line + Subject in first 4096 bytes.
        head_email = normalized_bytes[:4096]
        if _FROM_HEADER_PATTERN.search(head_email) and _SUBJECT_HEADER_PATTERN.search(head_email):
            return "email"

        # HTML: <html or <!DOCTYPE html in first 4096 bytes.
        if _HTML_PATTERN.search(head_email):
            return "html"

        # CSV: first non-whitespace line has 3+ commas.
        first_line_end = normalized_bytes.find(b"\n")
        first_line = (
            normalized_bytes[:first_line_end] if first_line_end != -1 else normalized_bytes
        ).lstrip()
        if first_line.count(b",") >= 3:
            return "csv"

        return "text"
    except Exception:
        # Per spec EC §5.1 rule 8: classification failures fall through
        # to "unknown". This is a safety belt; the regexes used in
        # the rules above are unlikely to raise on bytes, but future
        # additions (e.g., chardet in V2) could.
        return "unknown"


#: ASCII whitespace bytes used by :func:`compute_density`. Operating
#: on bytes directly is ~10-20x faster than decoding to text and
#: calling ``str.isspace()`` per character, and produces the same
#: result for ASCII whitespace (which dominates real input).
_WHITESPACE_BYTES: frozenset[int] = frozenset({0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20})


def compute_density(normalized_bytes: bytes, input_type: str) -> float:
    """Compute the non-whitespace density of *normalized_bytes*.

    Per ``docs/specs/input-profile-spec.md`` §6:

    - For ``"empty"`` and ``"unknown"`` types, returns ``0.0``.
    - For all other types, counts the non-whitespace bytes via a
      set-based C-level scan (``set`` membership is O(1) and avoids
      the per-character Python method dispatch of ``str.isspace()``).

    Args:
        normalized_bytes: The input as ``bytes``.
        input_type: The classified :data:`InputType`.

    Returns:
        The density as a float in ``[0.0, 1.0]``. ``0.0`` for
        ``"empty"`` and ``"unknown"``; otherwise the
        non-whitespace ratio.

    Note:
        Whitespace is defined as the ASCII whitespace bytes
        ``0x09`` (TAB), ``0x0A`` (LF), ``0x0B`` (VT), ``0x0C`` (FF),
        ``0x0D`` (CR), and ``0x20`` (SPACE). This is a strict
        subset of :py:meth:`str.isspace()` — Unicode whitespace
        characters (``U+00A0`` NO-BREAK SPACE, ``U+3000``
        IDEOGRAPHIC SPACE, ``U+0085`` NEL, ``U+1680`` OGHAM
        SPACE, etc.) are counted as **non-whitespace** by this
        implementation. For the input domains PAXMAN targets
        (invoices, procurement docs, emails), ASCII whitespace
        dominates and the difference is negligible. Density is a
        planner heuristic, not a correctness-critical value.
    """
    if input_type in ("empty", "unknown"):
        return 0.0
    if len(normalized_bytes) == 0:
        return 0.0
    non_ws = sum(1 for b in normalized_bytes if b not in _WHITESPACE_BYTES)
    return non_ws / len(normalized_bytes)


def make_profile(input_data: str | bytes) -> InputProfile:
    """Derive an :class:`InputProfile` from raw input.

    Per ``docs/specs/input-profile-spec.md`` §4, this is a pure
    function. Same input bytes → same :class:`InputProfile`,
    byte-for-byte. No I/O, no clock, no random state, no capability
    invocation.

    Args:
        input_data: Raw input as ``str`` or ``bytes``. ``str`` is
            encoded as UTF-8 with ``errors="replace"``.

    Returns:
        A frozen :class:`InputProfile` with 5 fields.

    Examples:
        >>> p = make_profile(b"Hello, World!\\n")
        >>> p.input_type
        'text'
        >>> p.size
        14
        >>> p.is_empty
        False
    """
    normalized = _to_bytes(input_data)
    size = len(normalized)
    content_hash = hashlib.sha256(normalized).hexdigest()
    is_empty = (size == 0) or (normalized.strip() == b"")
    input_type = classify(normalized)
    density = compute_density(normalized, input_type)
    return InputProfile(
        input_type=input_type,
        size=size,
        content_hash=content_hash,
        density=density,
        is_empty=is_empty,
    )
