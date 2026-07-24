"""Tests for the string-form DSL parser.

Covers the ``_parse_string_dsl`` function and the string-form path in
``parse_contract``: ``Date(locale="US", output_format="compact")`` syntax.
"""

from __future__ import annotations

import pytest

from paxman._capabilities.country.contract import CanonicalCountryContract
from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._dsl.parser import parse_contract
from paxman._errors import ContractError


class TestStringDslDate:
    def test_date_with_output_format_compact(self) -> None:
        c = parse_contract('Date(locale="US", output_format="compact")')
        assert isinstance(c, CanonicalDateContract)
        assert c.locale == "US"
        assert c.output_format == "compact"

    def test_date_with_output_format_iso(self) -> None:
        c = parse_contract('Date(locale="EU", output_format="iso")')
        assert isinstance(c, CanonicalDateContract)
        assert c.locale == "EU"
        assert c.output_format == "iso"

    def test_date_defaults_output_format(self) -> None:
        c = parse_contract('Date(locale="US")')
        assert isinstance(c, CanonicalDateContract)
        assert c.locale == "US"
        assert c.output_format == "iso"

    def test_date_with_language(self) -> None:
        c = parse_contract('Date(locale="ISO", language="de")')
        assert isinstance(c, CanonicalDateContract)
        assert c.language == "de"


class TestStringDslCountry:
    def test_country_with_output_format_alpha3(self) -> None:
        c = parse_contract('Country(output_format="alpha3")')
        assert isinstance(c, CanonicalCountryContract)
        assert c.output_format == "alpha3"

    def test_country_with_output_format_numeric(self) -> None:
        c = parse_contract('Country(output_format="numeric")')
        assert isinstance(c, CanonicalCountryContract)
        assert c.output_format == "numeric"

    def test_country_defaults_output_format(self) -> None:
        c = parse_contract("Country()")
        assert isinstance(c, CanonicalCountryContract)
        assert c.output_format == "alpha2"


class TestStringDslEmail:
    def test_email_with_provider_aliases(self) -> None:
        c = parse_contract('Email(provider_aliases="gmail")')
        assert isinstance(c, CanonicalEmailContract)
        assert c.provider_aliases == "gmail"

    def test_email_defaults(self) -> None:
        c = parse_contract("Email()")
        assert isinstance(c, CanonicalEmailContract)
        assert c.lowercase is True
        assert c.strict is False


class TestStringDslErrors:
    def test_unknown_name_raises(self) -> None:
        with pytest.raises(ContractError, match="unknown contract name"):
            parse_contract('Foo(bar="baz")')

    def test_not_a_call_raises(self) -> None:
        with pytest.raises(ContractError, match="expected function-call form"):
            parse_contract("Date")

    def test_invalid_syntax_raises(self) -> None:
        with pytest.raises(ContractError, match="invalid string contract DSL"):
            parse_contract("Date(locale=")

    def test_invalid_value_type_raises(self) -> None:
        with pytest.raises(ContractError, match="invalid argument value"):
            parse_contract("Date(locale=variable)")

    def test_no_positional_args(self) -> None:
        with pytest.raises(ContractError, match="positional arguments not supported"):
            parse_contract('Date("US")')

    def test_no_kwargs(self) -> None:
        with pytest.raises(ContractError, match=r"\*\*kwargs not supported"):
            parse_contract('Date(**{"locale": "US"})')

    def test_invalid_output_format_rejected_by_builder(self) -> None:
        with pytest.raises(ContractError):
            parse_contract('Date(output_format="bogus")')

    def test_invalid_country_output_format_rejected(self) -> None:
        with pytest.raises(ContractError):
            parse_contract('Country(output_format="bogus")')
