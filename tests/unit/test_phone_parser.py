from paxman._capabilities.phone.parser import _cc_for_country


def test_known_countries():
    assert _cc_for_country("US") == "1"
    assert _cc_for_country("GB") == "44"
    assert _cc_for_country("DE") == "49"


def test_unknown_country_raises():
    import pytest

    from paxman._errors import ContractError

    with pytest.raises(ContractError):
        _cc_for_country("ZZ")
