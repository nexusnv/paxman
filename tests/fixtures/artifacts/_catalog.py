"""Shared golden-artifact catalog used by the bootstrap script and the
integration tests.

Per Sprint 7 D7.3, the 8 golden ``ExecutionArtifact`` files in
``tests/fixtures/artifacts/`` are bootstrapped from real
``paxman.normalize()`` calls. The catalog below is the *single
source of truth* — both the bootstrap script (``scripts/
bootstrap_golden_artifacts.py``) and the integration test
(``tests/integration/test_golden_artifacts.py``) import from here.
"""

from __future__ import annotations

from typing import NamedTuple


class GoldenFixture(NamedTuple):
    """A single (golden_name, input_text, contract_module, contract_attr) tuple.

    The ``input_text`` may be a literal string or a registered
    sentinel (e.g. :data:`ADVERSARIAL_PROMPT_INJECTION`) that is
    resolved at load time to the contents of
    ``tests/fixtures/inputs/adversarial/...``.
    """

    name: str
    input_text: str
    contract_module: str
    contract_attr: str


#: Sentinel: when ``input_text`` is exactly this value, the loader
#: substitutes the contents of the prompt-injection adversarial file.
#:
#: The value is a non-colliding, human-readable marker so it never
#: coincides with a real fixture payload — including the empty-string
#: fixture (whose ``input_text`` is the empty string).
#: ``resolve_input_text`` dispatches on this sentinel rather than on
#: the golden name so future adversarial fixtures can follow the same
#: pattern by introducing a new sentinel constant.
ADVERSARIAL_PROMPT_INJECTION: str = "<adversarial:prompt_injection>"


#: The 8 golden fixtures, in deterministic order.
#:
#: Format: ``(golden_name, input_text, contract_module, contract_attr)``.
#:
#: The ``input_text`` is either a literal or a sentinel constant
#: (e.g. :data:`ADVERSARIAL_PROMPT_INJECTION`).
GOLDEN_FIXTURES: list[GoldenFixture] = [
    GoldenFixture(
        name="invoice_unresolved_dict_dsl",
        input_text=(
            "ACME Corp\nInvoice #1234\nTotal: $1,234.56\n"
            "Date: 2026-06-22\nCurrency: USD"
        ),
        contract_module="tests.fixtures.contracts.dict_dsl.invoice",
        contract_attr="DICT_DSL_INVOICE",
    ),
    GoldenFixture(
        name="invoice_unresolved_pydantic",
        input_text=(
            "ACME Corp\nInvoice #1234\nTotal: $1,234.56\n"
            "Date: 2026-06-22\nCurrency: USD"
        ),
        contract_module="tests.fixtures.contracts.pydantic.invoice",
        contract_attr="Invoice",
    ),
    GoldenFixture(
        name="invoice_unresolved_json_schema",
        input_text=(
            "ACME Corp\nInvoice #1234\nTotal: $1,234.56\n"
            "Date: 2026-06-22\nCurrency: USD"
        ),
        contract_module="tests.fixtures.contracts.json_schema.invoice",
        contract_attr="JSON_SCHEMA_INVOICE",
    ),
    GoldenFixture(
        name="all_v1_types_unresolved",
        input_text="ACME Corp\n1234\n3.14\ntrue\n2026-06-22\na\n{}\n[1,2,3]\n100.00",
        contract_module="tests.fixtures.contracts.dict_dsl.all_v1_types",
        contract_attr="DICT_DSL_ALL_V1_TYPES",
    ),
    GoldenFixture(
        name="money_unresolved",
        input_text="Money: 1234.56 USD",
        contract_module="tests.fixtures.contracts.dict_dsl.with_money",
        contract_attr="DICT_DSL_WITH_MONEY",
    ),
    GoldenFixture(
        name="empty_input_unresolved",
        input_text="",
        contract_module="tests.fixtures.contracts.dict_dsl.invoice",
        contract_attr="DICT_DSL_INVOICE",
    ),
    GoldenFixture(
        name="unicode_input_unresolved",
        input_text="日本語 中文 €£¥ 日本語",
        contract_module="tests.fixtures.contracts.dict_dsl.invoice",
        contract_attr="DICT_DSL_INVOICE",
    ),
    GoldenFixture(
        name="prompt_injection_unresolved",
        input_text=ADVERSARIAL_PROMPT_INJECTION,
        contract_module="tests.fixtures.contracts.dict_dsl.invoice",
        contract_attr="DICT_DSL_INVOICE",
    ),
]


def resolve_input_text(name: str, default: str) -> str:
    """Resolve a special ``input_text`` to its real contents.

    Dispatches on the ``input_text`` sentinel rather than the golden
    name, so any future golden can opt into adversarial-input
    resolution by setting ``input_text`` to a registered sentinel
    constant (e.g. :data:`ADVERSARIAL_PROMPT_INJECTION`).

    Args:
        name: The golden name (currently unused; kept for backward
            compatibility with callers that pass it).
        default: The default text to return if no rule matches.

    Returns:
        The resolved input text.
    """
    if default == ADVERSARIAL_PROMPT_INJECTION:
        from pathlib import Path

        path = (
            Path(__file__).resolve().parent.parent
            / "inputs"
            / "adversarial"
            / "prompt_injection.txt"
        )
        return path.read_text(encoding="utf-8")
    return default
