from __future__ import annotations

import paxman
from paxman import (
    IP,
    URL,
    UUID,
    Boolean,
    Country,
    Date,
    Email,
    Geolocation,
    Money,
    Phone,
)


def test_all_ten_domains_canonicalize_unchanged() -> None:
    cases = [
        (Email(provider_aliases="gmail"), "  John.Doe@Gmail.COM  ", "johndoe@gmail.com"),
        (UUID(), "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        (Date(locale="US"), "03/04/2025", "2025-03-04"),
        (Phone(country="US"), "+12025550199", "+12025550199"),
        (URL(), "HTTP://Example.COM/A/", "http://example.com/A/"),
        (Boolean(), "yes", "true"),
        (IP(), "2001:0db8:0000:0000:0000:0000:0000:0001", "2001:db8::1"),
        (Money(currency="MYR"), "RM 12.50", "MYR:12.50"),
        (Geolocation(), "3.139N 101.686E", "3.139000,101.686000"),
        (Country(allow_name=True), "malaysia", "MY"),
    ]
    for contract, raw, expected in cases:
        res = paxman.canonicalize(raw, contract)
        assert res.status.name == "CANONICALIZED", (
            type(contract).__name__,
            raw,
            res.status.name,
            res.evidence,
        )
        assert res.value == expected, (
            type(contract).__name__,
            raw,
            res.value,
            expected,
        )
