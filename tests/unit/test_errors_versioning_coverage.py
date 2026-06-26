"""Coverage tests for ``errors.py`` and ``versioning.py`` (D7.15).

These tests target specific lines that were previously uncovered
to push the per-subsystem coverage to 100% (per Sprint 7 D7.15).
"""

from __future__ import annotations

import pytest

from paxman.errors import PaxmanError
from paxman.versioning import PAXMAN_VERSION, PLANNER_VERSION, format_version

pytestmark = [pytest.mark.deterministic, pytest.mark.unit]


class TestErrorsCoverage:
    """Targeted coverage for ``src/paxman/errors.py``."""

    def test_empty_error_code_raises(self) -> None:
        """An empty ``error_code`` raises ``ValueError``."""
        with pytest.raises(ValueError, match="error_code must be a non-empty string"):
            PaxmanError("test", error_code="")

    def test_context_must_be_dict(self) -> None:
        """A non-dict ``context`` raises ``TypeError``."""
        with pytest.raises(TypeError, match="context must be dict"):
            PaxmanError("test", error_code="ERR", context="not a dict")  # type: ignore[arg-type]

    def test_context_default_to_empty_dict(self) -> None:
        """A ``None`` context defaults to ``{}``."""
        exc = PaxmanError("test", error_code="ERR", context=None)
        assert exc.context == {}


class TestVersioningCoverage:
    """Targeted coverage for ``src/paxman/versioning.py``."""

    def test_format_version_validates_types(self) -> None:
        """``format_version`` raises ``ValueError`` for non-int inputs."""
        with pytest.raises(ValueError, match="major must be an int"):
            format_version("1", 0, 0)  # type: ignore[arg-type]

    def test_format_version_rejects_bool(self) -> None:
        """``format_version`` rejects ``bool`` for major (Python treats bool as int)."""
        with pytest.raises(ValueError, match="major must be an int"):
            format_version(True, 0, 0)  # type: ignore[arg-type]

    def test_format_version_rejects_negative(self) -> None:
        """``format_version`` raises ``ValueError`` for negative inputs."""
        with pytest.raises(ValueError, match="major must be a non-negative integer"):
            format_version(-1, 0, 0)
        with pytest.raises(ValueError, match="minor must be a non-negative integer"):
            format_version(0, -1, 0)
        with pytest.raises(ValueError, match="patch must be a non-negative integer"):
            format_version(0, 0, -1)

    def test_paxman_version_is_non_empty(self) -> None:
        """``PAXMAN_VERSION`` is a non-empty string."""
        assert isinstance(PAXMAN_VERSION, str)
        assert PAXMAN_VERSION

    def test_planner_version_is_non_empty(self) -> None:
        """``PLANNER_VERSION`` is a non-empty string."""
        assert isinstance(PLANNER_VERSION, str)
        assert PLANNER_VERSION
