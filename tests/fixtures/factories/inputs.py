"""Input text factories — realistic-looking invoice, receipt, and quotation text.

Per Sprint 7 D7.4 and ``docs/TEST_DATA.md`` §7.1, these factories
generate realistic input *texts* (the raw strings passed to
``paxman.normalize()``). They are *synthetic* — no real PII — but
have the same shape as real invoice / receipt / quotation data.

Factories:

- :class:`InvoiceInputFactory` — a multi-line invoice with supplier, total, date.
- :class:`ReceiptInputFactory` — a short receipt with one or two line items.
- :class:`QuotationInputFactory` — a quotation with a quote number and total.
- :class:`MultiPageInputFactory` — a multi-section text mimicking a scanned PDF.
"""

from __future__ import annotations

import factory


class InvoiceInputFactory(factory.Factory):
    """A multi-line invoice text."""

    class Meta:
        model = str

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        f = factory.Faker._get_faker()
        supplier = f.company().replace(",", " ")
        invoice_num = f"INV-{f.random_number(digits=6, fix_len=True)}"
        total = f.pydecimal(min_value=10, max_value=10_000, right_digits=2)
        currency = f.currency_code()
        date = f.date_object().isoformat()
        return (
            f"Supplier: {supplier}\n"
            f"Invoice #: {invoice_num}\n"
            f"Date: {date}\n"
            f"Total: ${total} {currency}\n"
            f"Currency: {currency}\n"
        )


class ReceiptInputFactory(factory.Factory):
    """A short receipt text."""

    class Meta:
        model = str

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        f = factory.Faker._get_faker()
        merchant = f.company().replace(",", " ")
        amount = f.pydecimal(min_value=1, max_value=500, right_digits=2)
        currency = f.currency_code()
        return (
            f"Merchant: {merchant}\n"
            f"Amount: ${amount} {currency}\n"
            f"Date: {f.date_object().isoformat()}\n"
        )


class QuotationInputFactory(factory.Factory):
    """A quotation text with a quote number, line items, and total."""

    class Meta:
        model = str

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        f = factory.Faker._get_faker()
        supplier = f.company().replace(",", " ")
        quote_num = f"Q-{f.random_number(digits=6, fix_len=True)}"
        total = f.pydecimal(min_value=100, max_value=50_000, right_digits=2)
        currency = f.currency_code()
        return (
            f"Quotation\n"
            f"Supplier: {supplier}\n"
            f"Quote #: {quote_num}\n"
            f"Valid until: {f.future_date().isoformat()}\n"
            f"Total: ${total} {currency}\n"
        )


class MultiPageInputFactory(factory.Factory):
    """A multi-section text mimicking a scanned PDF (3 sections)."""

    class Meta:
        model = str

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        f = factory.Faker._get_faker()
        sections: list[str] = []
        for page in range(3):
            sections.append(
                f"=== Page {page + 1} ===\n"
                f"Supplier: {f.company().replace(',', ' ')}\n"
                f"Page {page + 1} content {f.sentence()}\n"
                f"Subtotal: ${f.pydecimal(min_value=10, max_value=1000, right_digits=2)}\n"
            )
        return "\n".join(sections)
