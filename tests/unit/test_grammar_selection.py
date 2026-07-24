"""Tests for the _select_grammars helper and include/exclude grammar selection.

TDD RED phase: these tests must fail before implementation.
"""

from __future__ import annotations

from paxman._capabilities._shared.grammar import Grammar, Provenance, _select_grammars, make_grammar

# ---------------------------------------------------------------------------
# Fixtures: a small grammar set for testing _select_grammars in isolation
# ---------------------------------------------------------------------------
_SOURCE = Provenance(name="test", version="1")


def _g(id: str) -> Grammar:
    return make_grammar(id, _SOURCE, r"^(?P<v>.+)$")


_ALL_GRAMMARS: tuple[Grammar, ...] = (
    _g("alpha"),
    _g("beta"),
    _g("gamma"),
    _g("delta"),
)


# ---------------------------------------------------------------------------
# _select_grammars unit tests
# ---------------------------------------------------------------------------


class TestSelectGrammars:
    def test_no_include_no_exclude_returns_all(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS)
        assert result == _ALL_GRAMMARS

    def test_empty_include_returns_all(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, include=())
        assert result == _ALL_GRAMMARS

    def test_empty_exclude_returns_all(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, exclude=())
        assert result == _ALL_GRAMMARS

    def test_include_filters_to_subset(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, include=("alpha", "gamma"))
        assert len(result) == 2
        assert result[0].id == "alpha"
        assert result[1].id == "gamma"

    def test_include_single_grammar(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, include=("delta",))
        assert len(result) == 1
        assert result[0].id == "delta"

    def test_include_nonexistent_grammar_returns_empty(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, include=("nonexistent",))
        assert result == ()

    def test_exclude_removes_from_set(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, exclude=("beta", "delta"))
        assert len(result) == 2
        assert result[0].id == "alpha"
        assert result[1].id == "gamma"

    def test_exclude_all_returns_empty(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, exclude=("alpha", "beta", "gamma", "delta"))
        assert result == ()

    def test_exclude_nonexistent_grammar_returns_all(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, exclude=("nonexistent",))
        assert result == _ALL_GRAMMARS

    def test_include_then_exclude(self) -> None:
        """Include first, then exclude from the included set."""
        result = _select_grammars(
            _ALL_GRAMMARS, include=("alpha", "beta", "gamma"), exclude=("beta",)
        )
        assert len(result) == 2
        assert result[0].id == "alpha"
        assert result[1].id == "gamma"

    def test_include_and_exclude_same_ids_returns_empty(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, include=("alpha",), exclude=("alpha",))
        assert result == ()

    def test_returns_tuple_not_list(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS)
        assert isinstance(result, tuple)

    def test_preserves_grammar_objects(self) -> None:
        result = _select_grammars(_ALL_GRAMMARS, include=("alpha",))
        assert result[0] is _ALL_GRAMMARS[0]


# ---------------------------------------------------------------------------
# Contract field defaults tests
# ---------------------------------------------------------------------------


class TestContractGrammarFields:
    """Every contract must have include_grammar and exclude_grammar defaults."""

    def test_email_defaults(self) -> None:
        from paxman._capabilities.email.contract import CanonicalEmailContract

        c = CanonicalEmailContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_boolean_defaults(self) -> None:
        from paxman._capabilities.boolean.contract import CanonicalBooleanContract

        c = CanonicalBooleanContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_uuid_defaults(self) -> None:
        from paxman._capabilities.uuid.contract import CanonicalUUIDContract

        c = CanonicalUUIDContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_phone_defaults(self) -> None:
        from paxman._capabilities.phone.contract import CanonicalPhoneContract

        c = CanonicalPhoneContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_ip_defaults(self) -> None:
        from paxman._capabilities.ip.contract import CanonicalIPContract

        c = CanonicalIPContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_url_defaults(self) -> None:
        from paxman._capabilities.url.contract import CanonicalURLContract

        c = CanonicalURLContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_country_defaults(self) -> None:
        from paxman._capabilities.country.contract import CanonicalCountryContract

        c = CanonicalCountryContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_geolocation_defaults(self) -> None:
        from paxman._capabilities.geolocation.contract import CanonicalGeolocationContract

        c = CanonicalGeolocationContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_money_defaults(self) -> None:
        from paxman._capabilities.money.contract import CanonicalMoneyContract

        c = CanonicalMoneyContract(currency="USD")
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()

    def test_date_defaults(self) -> None:
        from paxman._capabilities.date.contract import CanonicalDateContract

        c = CanonicalDateContract()
        assert c.include_grammar == ()
        assert c.exclude_grammar == ()


# ---------------------------------------------------------------------------
# Factory function tests — include_grammar / exclude_grammar pass-through
# ---------------------------------------------------------------------------


class TestFactoryGrammarSelection:
    def test_email_factory_include_grammar(self) -> None:
        from paxman import Email

        c = Email(include_grammar=("addr_spec",))
        assert c.include_grammar == ("addr_spec",)
        assert c.exclude_grammar == ()

    def test_boolean_factory_exclude_grammar(self) -> None:
        from paxman import Boolean

        c = Boolean(exclude_grammar=("bool_numeric_true", "bool_numeric_false"))
        assert c.exclude_grammar == ("bool_numeric_true", "bool_numeric_false")

    def test_uuid_factory_include_and_exclude(self) -> None:
        from paxman import UUID

        c = UUID(include_grammar=("canonical_uuid",))
        assert c.include_grammar == ("canonical_uuid",)
        assert c.exclude_grammar == ()


# ---------------------------------------------------------------------------
# Integration-style tests: grammar selection actually filters recognize()
# ---------------------------------------------------------------------------


class TestGrammarSelectionIntegration:
    def test_email_include_addr_spec_only(self) -> None:
        """Only addr_spec grammar should match when included."""
        from paxman._capabilities.email.contract import CanonicalEmailContract
        from paxman._capabilities.email.grammar import recognize

        contract = CanonicalEmailContract(include_grammar=("addr_spec",))
        # addr_spec matches clean emails
        reps = recognize("user@example.com", contract)
        ids = [r.grammar_id for r in reps]
        assert "addr_spec" in ids
        # ws_padded should NOT match (excluded by include filter)
        assert "ws_padded_addr_spec" not in ids

    def test_email_exclude_verbal_at_dot(self) -> None:
        """verbal_at_dot grammar should not match when excluded."""
        from paxman._capabilities.email.contract import CanonicalEmailContract
        from paxman._capabilities.email.grammar import recognize

        contract = CanonicalEmailContract(exclude_grammar=("verbal_at_dot_addr_spec",))
        reps = recognize("user at example dot com", contract)
        ids = [r.grammar_id for r in reps]
        assert "verbal_at_dot_addr_spec" not in ids

    def test_boolean_exclude_numeric(self) -> None:
        """Numeric boolean grammars should not match when excluded."""
        from paxman._capabilities.boolean.contract import CanonicalBooleanContract
        from paxman._capabilities.boolean.grammar import recognize

        contract = CanonicalBooleanContract(
            exclude_grammar=("bool_numeric_true", "bool_numeric_false")
        )
        reps = recognize("1", contract)
        ids = [r.grammar_id for r in reps]
        assert "bool_numeric_true" not in ids
        # true/false words should still work
        reps_true = recognize("true", contract)
        ids_true = [r.grammar_id for r in reps_true]
        assert "bool_true_words" in ids_true

    def test_ip_include_ipv4_only(self) -> None:
        """Only ipv4 grammar should match when included."""
        from paxman._capabilities.ip.contract import CanonicalIPContract
        from paxman._capabilities.ip.grammar import recognize

        contract = CanonicalIPContract(include_grammar=("ip_ipv4",))
        reps = recognize("192.168.1.1", contract)
        ids = [r.grammar_id for r in reps]
        assert "ip_ipv4" in ids
        # ipv6 should not be in results
        assert "ip_ipv6" not in ids
        assert "ip_ipv6_zone" not in ids

    def test_url_include_absolute_only(self) -> None:
        """Only absolute URL grammar should match when included."""
        from paxman._capabilities.url.contract import CanonicalURLContract
        from paxman._capabilities.url.grammar import recognize

        contract = CanonicalURLContract(include_grammar=("absolute",))
        reps = recognize("https://example.com/path", contract)
        ids = [r.grammar_id for r in reps]
        assert "absolute" in ids
        assert "path_relative" not in ids

    def test_country_include_alpha2_only(self) -> None:
        """Only alpha2 grammar should match when included."""
        from paxman._capabilities.country.contract import CanonicalCountryContract
        from paxman._capabilities.country.grammar import recognize

        contract = CanonicalCountryContract(include_grammar=("country_alpha2",))
        reps = recognize("US", contract)
        ids = [r.grammar_id for r in reps]
        assert "country_alpha2" in ids
        assert "country_alpha3" not in ids

    def test_geolocation_exclude_dms(self) -> None:
        """DMS grammars should not match when excluded."""
        from paxman._capabilities.geolocation.contract import (
            CanonicalGeolocationContract,
        )
        from paxman._capabilities.geolocation.grammar import recognize

        contract = CanonicalGeolocationContract(
            exclude_grammar=("geo_dms", "geo_dms_lonlat", "geo_dms_signed"),
            require_hemisphere=False,
        )
        reps = recognize("51.5074,-0.1278", contract)
        ids = [r.grammar_id for r in reps]
        assert "geo_dms" not in ids
        assert "geo_dms_lonlat" not in ids
        assert "geo_dms_signed" not in ids

    def test_date_exclude_iso_date(self) -> None:
        """ISO date grammar should not match when excluded."""
        from paxman._capabilities.date.contract import CanonicalDateContract
        from paxman._capabilities.date.grammar import recognize

        contract = CanonicalDateContract(exclude_grammar=("iso_date",))
        reps = recognize("2025-03-04", contract)
        ids = [r.grammar_id for r in reps]
        assert "iso_date" not in ids

    def test_phone_include_e164_only(self) -> None:
        """Only e164 grammar should match when included."""
        from paxman._capabilities.phone.contract import CanonicalPhoneContract
        from paxman._capabilities.phone.grammar import recognize

        contract = CanonicalPhoneContract(include_grammar=("e164",))
        reps = recognize("+12025551234", contract)
        ids = [r.grammar_id for r in reps]
        assert "e164" in ids
        assert "national" not in ids
        assert "digits_only" not in ids

    def test_uuid_include_nonexistent_returns_empty(self) -> None:
        """Including a nonexistent grammar ID should produce no matches."""
        from paxman._capabilities.uuid.contract import CanonicalUUIDContract
        from paxman._capabilities.uuid.grammar import recognize

        contract = CanonicalUUIDContract(include_grammar=("nonexistent",))
        reps = recognize("550e8400-e29b-41d4-a716-446655440000", contract)
        assert reps == []


# ---------------------------------------------------------------------------
# as_dict round-trip tests
# ---------------------------------------------------------------------------


class TestAsDictGrammarFields:
    def test_email_as_dict_includes_grammar_fields(self) -> None:
        from paxman import Email

        c = Email(include_grammar=("addr_spec",), exclude_grammar=("ws_padded",))
        d = c.as_dict()
        assert d["include_grammar"] == ("addr_spec",)
        assert d["exclude_grammar"] == ("ws_padded",)

    def test_boolean_as_dict_includes_grammar_fields(self) -> None:
        from paxman import Boolean

        c = Boolean(exclude_grammar=("bool_numeric_true",))
        d = c.as_dict()
        assert d["include_grammar"] == ()
        assert d["exclude_grammar"] == ("bool_numeric_true",)

    def test_date_as_dict_includes_grammar_fields(self) -> None:
        from paxman import Date

        c = Date(include_grammar=("iso_date",))
        d = c.as_dict()
        assert d["include_grammar"] == ("iso_date",)
        assert d["exclude_grammar"] == ()
