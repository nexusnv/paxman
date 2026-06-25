"""Unit tests for ``paxman.api.version`` — version string re-export.

Verifies that ``__version__`` is importable from ``paxman.api.version``
and conforms to the ``MAJOR.MINOR.PATCH`` semver format.
"""

from __future__ import annotations

import re

import pytest

from paxman.api.version import __version__

pytestmark = pytest.mark.deterministic


class TestVersionString:
    """``__version__`` is a non-empty string in ``MAJOR.MINOR.PATCH`` format."""

    def test_version_is_string(self) -> None:
        assert isinstance(__version__, str)

    def test_version_is_non_empty(self) -> None:
        assert __version__

    def test_version_is_major_minor_patch(self) -> None:
        """Version matches ``MAJOR.MINOR.PATCH`` semver pattern (e.g. ``"0.0.0"``)."""
        assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)

    def test_version_has_three_parts(self) -> None:
        parts = __version__.split(".")
        assert len(parts) == 3

    def test_version_parts_are_integers(self) -> None:
        for part in __version__.split("."):
            part_int = int(part)
            assert part_int >= 0

    def test_version_matches_paxman_versioning(self) -> None:
        """The re-exported version matches the canonical source in ``paxman.versioning``."""
        from paxman.versioning import PAXMAN_VERSION

        assert __version__ == PAXMAN_VERSION

    def test_version_accessible_via_paxman_api(self) -> None:
        """``paxman.api.version.__version__`` is the same as ``paxman.__version__``."""
        import paxman

        assert __version__ == paxman.__version__
