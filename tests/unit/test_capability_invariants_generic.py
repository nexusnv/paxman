"""Generic invariant harness proving CapabilityTestBase against all 10 built-ins.

Each subclass sets a small representative ``valid_cases`` / ``invalid_cases`` /
``non_string_inputs`` drawn from that capability's dedicated unit tests (the
exact expected values are copied from those tests so they pass). The module
exists to prove the reusable harness exercises every built-in capability; it is
additive and does not replace the per-capability suites.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

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
from paxman._capabilities.boolean.canonicalizer import BooleanCapability
from paxman._capabilities.country.canonicalizer import CountryCapability
from paxman._capabilities.date.canonicalizer import DateCapability
from paxman._capabilities.email.canonicalizer import EmailCapability
from paxman._capabilities.geolocation.canonicalizer import GeolocationCapability
from paxman._capabilities.ip.canonicalizer import IPCapability
from paxman._capabilities.money.canonicalizer import MoneyCapability
from paxman._capabilities.phone.canonicalizer import PhoneCapability
from paxman._capabilities.url.canonicalizer import URLCapability
from paxman._capabilities.uuid.canonicalizer import UUIDCapability
from paxman._core.status import Status
from tests.unit._capability_test_base import CapabilityTestBase


class TestEmailInvariants(CapabilityTestBase):
    capability_cls = EmailCapability
    contract_factory: ClassVar[Callable[[], object]] = Email
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("John.Doe@Example.COM", "john.doe@example.com"),
        ("user+tag@example.com", "user+tag@example.com"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("not-an-email", Status.INVALID),
        ("a b@c.d", Status.INVALID),
    ]
    non_string_inputs: ClassVar[list[object]] = [123, b"x", 1.5]


class TestUUIDInvariants(CapabilityTestBase):
    capability_cls = UUIDCapability
    contract_factory: ClassVar[Callable[[], object]] = UUID
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440000"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("550E8400-E29B-41D4-A716-446655440000", Status.INVALID),
        ("550e8400e29b41d4a716446655440000", Status.INVALID),
    ]
    non_string_inputs: ClassVar[list[object]] = [12345, b"x", 1.5]


class TestDateInvariants(CapabilityTestBase):
    capability_cls = DateCapability
    contract_factory: ClassVar[Callable[[], object]] = lambda: Date(locale="ISO")
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("2025-01-01", "2025-01-01"),
        ("2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("tomorrow", Status.INVALID),
        ("", Status.MISSING),
    ]
    non_string_inputs: ClassVar[list[object]] = [12345, b"x", 1.5]


class TestPhoneInvariants(CapabilityTestBase):
    capability_cls = PhoneCapability
    contract_factory: ClassVar[Callable[[], object]] = lambda: Phone(country="US")
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("+16502530000", "+16502530000"),
        ("(650) 253-0000", "+16502530000"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("call-me-now", Status.INVALID),
        ("0016502530000", Status.INVALID),
    ]
    non_string_inputs: ClassVar[list[object]] = [6502530000, b"x", 1.5]


class TestURLInvariants(CapabilityTestBase):
    capability_cls = URLCapability
    contract_factory: ClassVar[Callable[[], object]] = URL
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("https://example.com/b", "https://example.com/b"),
        ("HTTP://Example.COM:80/./A/../b?x=1", "http://example.com/b?x=1"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("   ", Status.INVALID),
    ]
    non_string_inputs: ClassVar[list[object]] = [123, b"x", 1.5]


class TestBooleanInvariants(CapabilityTestBase):
    capability_cls = BooleanCapability
    contract_factory: ClassVar[Callable[[], object]] = Boolean
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("true", "true"),
        ("YES", "true"),
        ("No", "false"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("maybe", Status.INVALID),
        ("", Status.MISSING),
    ]
    non_string_inputs: ClassVar[list[object]] = [1, b"x", 1.5]


class TestIPInvariants(CapabilityTestBase):
    capability_cls = IPCapability
    contract_factory: ClassVar[Callable[[], object]] = IP
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("192.168.001.001", "192.168.1.1"),
        ("2001:0DB8:0000:0000:0000:0000:0000:0001", "2001:db8::1"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("example.com", Status.INVALID),
        ("", Status.MISSING),
    ]
    non_string_inputs: ClassVar[list[object]] = [1, b"x", 1.5]


class TestMoneyInvariants(CapabilityTestBase):
    capability_cls = MoneyCapability
    contract_factory: ClassVar[Callable[[], object]] = lambda: Money(currency="MYR")
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("RM 12.50", "MYR:12.50"),
        ("78.90", "MYR:78.90"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("abc", Status.INVALID),
        ("  ", Status.INVALID),
    ]
    non_string_inputs: ClassVar[list[object]] = [1234, b"x", 1.5]


class TestGeolocationInvariants(CapabilityTestBase):
    capability_cls = GeolocationCapability
    contract_factory: ClassVar[Callable[[], object]] = lambda: Geolocation(require_hemisphere=False)
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("40.7128N 74.0060W", "40.712800,-74.006000"),
        ("40.7128, 74.0060", "40.712800,74.006000"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("abc", Status.INVALID),
        ("91.0, 0.0", Status.INVALID),
    ]
    non_string_inputs: ClassVar[list[object]] = [1234, b"x", 1.5]


class TestCountryInvariants(CapabilityTestBase):
    capability_cls = CountryCapability
    contract_factory: ClassVar[Callable[[], object]] = Country
    valid_cases: ClassVar[list[tuple[str, str | Status]]] = [
        ("US", "US"),
        ("usa", "US"),
        ("United States", "US"),
    ]
    invalid_cases: ClassVar[list[tuple[object, Status]]] = [
        ("Atlantis", Status.INVALID),
        ("", Status.MISSING),
    ]
    non_string_inputs: ClassVar[list[object]] = [123, b"x", 1.5]
