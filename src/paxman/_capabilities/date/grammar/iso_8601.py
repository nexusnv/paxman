"""ISO 8601 date/datetime grammars."""

from paxman._capabilities._shared.grammar import Grammar, Provenance, make_grammar

ISO_8601 = Provenance(name="ISO 8601")

ISO_DATE = make_grammar(
    "iso_date",
    ISO_8601,
    r"\s*(?P<year>\d{2,4})\s*-\s*(?P<month>\d{1,2})\s*-\s*(?P<day>\d{1,2})\s*",
)

ISO_GRAMMARS: tuple[Grammar, ...] = (ISO_DATE,)
