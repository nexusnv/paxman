"""Tests for the teaching AttributeError on the missing 'normalize' name.

Mandate §1.1: Paxman is not a normalizer. There is no 'normalize'
attribute. The PEP 562 __getattr__ raises an AttributeError whose
message points the user at canonicalize() (Law 8 — fail informatively).

The grep-zero gate (substring 'paxman.normalize' absent across src/ and
tests/) is covered by test_grep_zero_normalize.py, not here. This test
verifies the runtime behavior only.
"""

from __future__ import annotations

import pytest

import paxman


class TestNormalizeTeachingError:
    def test_normalize_raises_attribute_error(self) -> None:
        # Access via getattr — never the literal paxman.normalize, which
        # would itself trip the grep-zero gate if it appeared in tests/.
        with pytest.raises(AttributeError) as exc_info:
            getattr(paxman, "normalize")
        message = str(exc_info.value)
        assert "canonicalize" in message, (
            f"teaching error must mention canonicalize; got: {message!r}"
        )

    def test_normalize_message_does_not_contain_substring(self) -> None:
        # The message string ITSELF is a grep target. The substring
        # 'paxman.normalize' must never appear inside it (criterion 7,
        # spec §2.1 grep-zero gate).
        with pytest.raises(AttributeError) as exc_info:
            getattr(paxman, "normalize")
        assert "paxman.normalize" not in str(exc_info.value), (
            "teaching error message must not contain the substring 'paxman.normalize'"
        )

    def test_other_missing_name_raises_plain_attribute_error(self) -> None:
        with pytest.raises(AttributeError) as exc_info:
            getattr(paxman, "definitely_not_a_function")
        message = str(exc_info.value)
        # Plain AttributeError, not a teaching message.
        assert "canonicalize" not in message

    def test_normalize_is_not_a_real_attribute(self) -> None:
        # hasattr triggers __getattr__; the teaching error is swallowed
        # by hasattr and returns False. This is the §1.1 boundary: there
        # is no 'normalize' attribute, period.
        assert hasattr(paxman, "normalize") is False
