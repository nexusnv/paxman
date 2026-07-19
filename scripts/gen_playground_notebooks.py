"""Generate the 9 remaining capability notebooks for the Paxman playground.

Each notebook follows the locked reference template
(playground/notebooks/00_email.ipynb):
  - markdown title + scope header
  - one imports cell + shared show() helper
  - concept -> runnable example cells (variants copied verbatim from
    NOTEBOOK_INPUTS.md, which were executed against the working tree)
  - error/edge-case cell
  - cross-link cell to 10_engine / 11_dsl

Emits valid nbformat 4.5 (every code cell has id + outputs +
execution_count).
"""

from __future__ import annotations

import nbformat

# Display names for titles (ip/url/uuid must stay upper-case).
DISPLAY = {
    "boolean": "Boolean",
    "country": "Country",
    "date": "Date",
    "geolocation": "Geolocation",
    "ip": "IP",
    "money": "Money",
    "phone": "Phone",
    "url": "URL",
    "uuid": "UUID",
}

# ---------------------------------------------------------------------------
# Per-capability spec: (number, domain, contract_factory, intro, sections)
#   sections: list of (markdown_explainer, [code_lines...])
# All example snippets are source-verified (NOTEBOOK_INPUTS.md, 2026-07-19).
# ---------------------------------------------------------------------------

CAPS = [
    {
        "num": "01",
        "domain": "boolean",
        "contract": "Boolean",
        "intro": (
            "**Domain:** boolean  \n"
            "**Capability contract:** `Boolean` (frozen `CanonicalBooleanContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. Boolean canonicalizes many spellings of "
            'yes/no into the lowercase strings `"true"` / `"false"`.'
        ),
        "sections": [
            (
                "`Boolean()` accepts words, digits, and mixed case, trimming "
                'whitespace. The canonical form is always `"true"` or `"false"`.',
                [
                    'show("Yes", Boolean())',
                    'show("1", Boolean())',
                    'show("TRUE", Boolean())',
                    'show("  yes  ", Boolean())   # whitespace trimmed',
                ],
            ),
            (
                "Policy can *disable* a token family. With `accept_numeric=False`, "
                'the digit `"1"` is no longer a valid boolean token — it is '
                '`INVALID`, not silently accepted. `"true"`/`"false"` themselves '
                "always parse (they are the result, not a gated token).",
                [
                    'show("1", Boolean(accept_numeric=False))   # INVALID (policy)',
                    'show("true", Boolean(accept_numeric=False)) # CANONICALIZED',
                ],
            ),
            (
                "Unrecognized words are `INVALID` — Paxman does not guess. Empty / "
                "`None` input is `MISSING` (no value to judge).",
                [
                    'show("maybe", Boolean())        # INVALID (unrecognized)',
                    "show(None, Boolean())           # MISSING (no guess)",
                    'show("", Boolean())             # MISSING',
                ],
            ),
        ],
    },
    {
        "num": "02",
        "domain": "country",
        "contract": "Country",
        "intro": (
            "**Domain:** country  \n"
            "**Capability contract:** `Country` (frozen `CanonicalCountryContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. Country canonicalizes names, alpha-2, "
            "alpha-3, numeric M49, and synonyms into the ISO 3166-1 **alpha-2** code."
        ),
        "sections": [
            (
                "Many spellings collapse to the same alpha-2 code: synonym (`USA`), "
                "case-folded alpha-2 (`us`), name (`United States`), numeric (`840`), "
                "and alpha-3 (`DEU`).",
                [
                    'show("USA", Country())                  # synonym',
                    'show("us", Country())                   # alpha-2',
                    'show("United States", Country())        # name',
                    'show("840", Country())                  # numeric M49',
                    'show("DEU", Country())                  # alpha-3',
                    'show("malaysia", Country(allow_name=True))',
                ],
            ),
            (
                "Policy gates which input *kinds* are accepted. Historical names "
                "(`Burma`) need `historical_names=True`; an unknown token is `INVALID`.",
                [
                    'show("Burma", Country(historical_names=True))  # MM',
                    'show("Atlantis", Country())                    # INVALID',
                    'show("DEU", Country(allow_alpha3=False))       # INVALID',
                ],
            ),
            (
                "You can add your own replayable aliases via `extra_synonyms`.",
                [
                    'show("america", Country(extra_synonyms={"america": "US"}))',
                ],
            ),
        ],
    },
    {
        "num": "03",
        "domain": "date",
        "contract": "Date",
        "intro": (
            "**Domain:** date  \n"
            "**Capability contract:** `Date` (frozen `CanonicalDateContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. Date canonicalizes many date/datetime "
            "spellings into `YYYY-MM-DD` (or `...T...Z`). When a format is "
            "ambiguous, Paxman surfaces the readings instead of guessing."
        ),
        "sections": [
            (
                "With an explicit `locale`, slash forms resolve deterministically: "
                "`US` = MM/DD, `EU` = DD/MM.",
                [
                    'show("2025-03-04", Date(locale="US"))',
                    'show("03/04/2025", Date(locale="US"))   # MM/DD',
                    'show("03/04/2025", Date(locale="EU"))   # DD/MM',
                    'show("16 July 2026", Date(language="en"))',
                ],
            ),
            (
                "Datetimes normalize to RFC 3339 UTC (`Z`). A *naive* datetime (no "
                "zone) is `AMBIGUOUS` per RFC 3339 §5.6 — Paxman will not assume a zone.",
                [
                    'show("2025-01-01T07:00:00-05:00", Date(locale="ISO"))',
                    'show("2025-01-01T07:00:00", Date(locale="ISO"))   # AMBIGUOUS',
                ],
            ),
            (
                'Ambiguity is surfaced, never guessed: `locale="ISO"` leaves MM/DD '
                "vs DD/MM open; a 2-digit year with no policy spans centuries.",
                [
                    'show("03/04/2025", Date(locale="ISO"))   # AMBIGUOUS',
                    'show("03/04/26", Date(locale="US"))      # AMBIGUOUS',
                    'show("not a date", Date(locale="US"))    # INVALID',
                ],
            ),
        ],
    },
    {
        "num": "04",
        "domain": "geolocation",
        "contract": "Geolocation",
        "intro": (
            "**Domain:** geolocation  \n"
            "**Capability contract:** `Geolocation` (frozen `CanonicalGeolocation"
            "Contract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. Geolocation canonicalizes coordinates into "
            '`"<lat>,<lon>"` at a fixed decimal precision. The default requires '
            "an explicit hemisphere sign."
        ),
        "sections": [
            (
                "With `require_hemisphere=False`, unsigned axes default to positive. "
                "Hemisphere letters (`N`/`S`/`E`/`W`) are accepted when attached to "
                "the number.",
                [
                    'show("40.7128, -74.0060", Geolocation(require_hemisphere=False))',
                    'show("40.7128N 74.0060W", Geolocation())',
                ],
            ),
            (
                "With the default `require_hemisphere=True`, an unsigned axis is "
                "`AMBIGUOUS` — Paxman enumerates the sign readings rather than "
                "guessing which hemisphere you meant.",
                [
                    'show("40.7128, -74.0060", Geolocation())   # AMBIGUOUS',
                    'show("40.7128, 74.0060", Geolocation())    # AMBIGUOUS',
                ],
            ),
            (
                "Out-of-range and malformed inputs are `INVALID`. Hemisphere letters "
                "must be attached to the number (`40.7128N 74.0060W` works; `N40.7128` "
                "does not).",
                [
                    'show("91, 0", Geolocation())                 # INVALID',
                    'show("40.7128 -74.0060", Geolocation())      # INVALID',
                    'show("N40.7128 W74.0060", Geolocation())     # INVALID',
                ],
            ),
        ],
    },
    {
        "num": "05",
        "domain": "ip",
        "contract": "IP",
        "intro": (
            "**Domain:** ip  \n"
            "**Capability contract:** `IP` (frozen `CanonicalIPContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. IP canonicalizes addresses to RFC 4291 "
            "(IPv4) / RFC 5952 (IPv6, lowercased + compressed)."
        ),
        "sections": [
            (
                "IPv4 leading zeros are stripped; IPv6 is lowercased and compressed; "
                "a zone id is preserved (lowercased).",
                [
                    'show("192.168.001.001", IP())',
                    'show("2001:DB8::1", IP())',
                    'show("2001:db8::1%eth0", IP())',
                ],
            ),
            (
                "Policy gates address families. `allow_ipv4=False` + an IPv4 input is "
                "`INVALID` (the capability declines that family); malformed addresses "
                "are `INVALID`, never coerced.",
                [
                    'show("999.1.1.1", IP())                   # INVALID',
                    'show("192.168.1.1", IP(allow_ipv4=False)) # INVALID',
                ],
            ),
        ],
    },
    {
        "num": "06",
        "domain": "money",
        "contract": "Money",
        "intro": (
            "**Domain:** money  \n"
            "**Capability contract:** `Money` (frozen `CanonicalMoneyContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. Money canonicalizes amount strings into "
            '`"<ISO4217>:<amount>"`. **`currency` is required** — Paxman never '
            "guesses it."
        ),
        "sections": [
            (
                "A currency is declared on the contract. The amount parses whether or "
                "not a symbol/code is present; the symbol/code must *match* the "
                "contract currency.",
                [
                    'show("RM 12.50", Money(currency="MYR"))',
                    'show("$12.50", Money(currency="USD"))',
                    'show("12.50", Money(currency="USD"))',
                    'show("12.50", Money(currency="GBP", allow_symbol=False))',
                ],
            ),
            (
                "A symbol/code that does NOT match the contract currency is "
                '`INVALID`. `None`/`""` money is `INVALID` too — money has no '
                '"absent" semantics (unlike other capabilities, which return '
                "`MISSING`).",
                [
                    'show("€12.50", Money(currency="EUR"))',
                    'show("USD 12.50", Money(currency="USD", allow_code=False))',
                    'show(None, Money(currency="USD"))',
                    'show("", Money(currency="USD"))',
                ],
            ),
            (
                "A broken *contract* (unknown currency) raises `ContractError` at "
                "construction — before canonicalize runs.",
                [
                    'try:\n    Money(currency="XYZ")\n'
                    'except ContractError as exc:\n    print("ContractError:", exc)',
                ],
            ),
        ],
    },
    {
        "num": "07",
        "domain": "phone",
        "contract": "Phone",
        "intro": (
            "**Domain:** phone  \n"
            "**Capability contract:** `Phone` (frozen `CanonicalPhoneContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. Phone canonicalizes national and "
            'international formats into E.164 (`"+<cc><national>"`). The country '
            "is declared, never inferred."
        ),
        "sections": [
            (
                "National / digits-only inputs get the contract's declared country "
                "code prepended. A `+`-prefixed input is treated as already-global — "
                "but it must already be valid E.164: formatting *inside* a `+` number "
                "(like `(212)`) is rejected, not partially parsed.",
                [
                    'show("+1 (212) 555-0199", Phone(country="US"))  # INVALID',
                    'show("(212) 555-0199", Phone(country="US"))',
                    'show("2125550199", Phone(country="US"))',
                ],
            ),
            (
                "The country is NEVER inferred from the digits — changing the "
                "contract country changes the result. A number that cannot form valid "
                "E.164 is `INVALID`.",
                [
                    'show("2125550199", Phone(country="GB"))   # GB code applied',
                    'show("0199", Phone(country="US"))          # INVALID',
                ],
            ),
            (
                "An unknown `country` raises `ContractError` at contract construction.",
                [
                    'try:\n    Phone(country="XX")\n'
                    'except ContractError as exc:\n    print("ContractError:", exc)',
                ],
            ),
        ],
    },
    {
        "num": "08",
        "domain": "url",
        "contract": "URL",
        "intro": (
            "**Domain:** url  \n"
            "**Capability contract:** `URL` (frozen `CanonicalURLContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. URL normalizes to RFC 3986 §6.2.2 form "
            "(scheme/host lowercased, default port elided, dot-segments removed)."
        ),
        "sections": [
            (
                "Scheme and host are lowercased; the default port (`:80`) is elided; "
                "`..` dot-segments are resolved; fragments are dropped by default.",
                [
                    'show("HTTP://Example.COM:80/foo/bar", URL())',
                    'show("http://example.com/foo/../bar", URL())',
                    'show("http://user:pass@example.com/path#frag", URL())',
                    'show("https://example.com/a?b=2&c=1", URL(sort_query=True))',
                ],
            ),
            (
                "`scheme_allow` declares accepted schemes. An input whose scheme is "
                "NOT allowed is `UNSUPPORTED` — the capability declines, distinct from "
                "`INVALID`. Note: the URL capability is lenient — an unparseable "
                "string is passed through as `CANONICALIZED`, so do not rely on it to "
                "validate free text.",
                [
                    'show("ftp://example.com/file", URL())',
                    'show("ftp://example.com/file", URL(scheme_allow=("https",)))',
                    'show("not a url", URL())',
                ],
            ),
        ],
    },
    {
        "num": "09",
        "domain": "uuid",
        "contract": "UUID",
        "intro": (
            "**Domain:** uuid  \n"
            "**Capability contract:** `UUID` (frozen `CanonicalUUIDContract`)  \n"
            "**Public API:** `paxman.canonicalize(input_data, contract)`\n\n"
            "Follows the **reference template** (`00_email.ipynb`). Run every cell "
            "in order; no hidden state. UUID is **strict-only**: it accepts *only* "
            "the hyphenated RFC 4122 form and lowercases it. It does NOT normalize "
            "alternate shapes."
        ),
        "sections": [
            (
                "The canonical RFC 4122 form — lowercase, hyphenated 8-4-4-4-12 — is "
                "accepted. A specific `version` also validates the version nibble.",
                [
                    'show("123e4567-e89b-12d3-a456-426614174000", UUID())',
                    'show("123e4567-e89b-42d3-a456-426614174000", UUID(version="4"))',
                ],
            ),
            (
                "UUID is STRICT-ONLY: it accepts exactly the lowercase hyphenated "
                "RFC 4122 form. Uppercase, braced, URN, 32-hex-without-hyphens, and "
                "whitespace-padded inputs are ALL `INVALID` — no lowercasing, no "
                "normalization. A version mismatch is `INVALID`.",
                [
                    'show("123E4567-E89B-12D3-A456-426614174000", UUID())  # INVALID',
                    'show("123e4567-e89b-12d3-a456-426614174000", UUID(version="4"))',
                    'show("123e4567e89b12d3a456426614174000", UUID())     # INVALID',
                    'show("not-a-uuid", UUID())                           # INVALID',
                ],
            ),
            (
                "An invalid `version` string raises `ContractError` at contract construction.",
                [
                    'try:\n    UUID(version="99")\n'
                    'except ContractError as exc:\n    print("ContractError:", exc)',
                ],
            ),
        ],
    },
]


def build_notebook(spec: dict) -> nbformat.NotebookNode:
    c = spec["contract"]
    domain = spec["domain"]
    title = DISPLAY.get(domain, domain.capitalize())
    cells = []
    # Deterministic cell ids so regeneration is diff-stable (no random churn).
    idx = 0

    def cid() -> str:
        nonlocal idx
        idx += 1
        return f"{domain}-{idx:02d}"

    cells.append(
        nbformat.v4.new_markdown_cell(
            f"# {title} — Canonicalizing {domain} "
            f"values with Paxman\n\n"
            + spec["intro"]
            + "\n\n> Run every cell in order. `artifact.value` holds the canonical "
            'string when `artifact.status == "CANONICALIZED"`; otherwise it is '
            "`None`.",
            id=cid(),
        )
    )

    cells.append(
        nbformat.v4.new_code_cell(
            f"from paxman import canonicalize, {c}, ContractError, "
            "CanonicalizationError\n"
            "\n"
            "def show(raw, contract):\n"
            '    """Canonicalize `raw`; print status + value."""\n'
            "    artifact = canonicalize(raw, contract)\n"
            '    if artifact.status.name == "CANONICALIZED":\n'
            '        print(f"{raw!r:38} -> {artifact.status.name:14} '
            '{artifact.value!r}")\n'
            "    else:\n"
            '        print(f"{raw!r:38} -> {artifact.status.name:14} '
            '(no canonical value)")\n'
            "    return artifact",
            id=cid(),
        )
    )

    for md, code_lines in spec["sections"]:
        cells.append(nbformat.v4.new_markdown_cell(md, id=cid()))
        cells.append(nbformat.v4.new_code_cell("\n".join(code_lines), id=cid()))

    cells.append(
        nbformat.v4.new_markdown_cell(
            "## Where to go next\n\n"
            "- **`10_engine.ipynb`** — `Engine.default()`, "
            "`Engine.with_authorities(...)`, `canonicalize_with(...)`, and the "
            "`authority_override` escape hatch.\n"
            "- **`11_dsl.ipynb`** — build contracts from a DSL string with "
            "`parse_contract`.\n"
            "- All inputs above are sourced from `NOTEBOOK_INPUTS.md` (verified "
            "against the working tree).\n\n"
            "> Every other capability notebook ("
            + ", ".join(DISPLAY[d] for d in [s["domain"] for s in CAPS] if d != spec["domain"])
            + ") follows this exact structure.",
            id=cid(),
        )
    )

    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11"},
    }
    return nb


def main() -> None:
    import argparse
    import filecmp
    import shutil
    import tempfile

    parser = argparse.ArgumentParser(description="Generate Paxman playground notebooks.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write to a temp dir and diff against the committed notebooks; "
        "exit non-zero if they differ (CI drift guard). Does not modify the tree.",
    )
    args = parser.parse_args()

    out_dir = "playground/notebooks"
    if args.check:
        # Regenerate into a throwaway dir so we never touch the working tree.
        tmp = tempfile.mkdtemp(prefix="paxman-nb-")
        target_dir = tmp
    else:
        target_dir = out_dir

    for spec in CAPS:
        nb = build_notebook(spec)
        nbformat.validate(nb)
        path = f"{target_dir}/{spec['num']}_{spec['domain']}.ipynb"
        nbformat.write(nb, path)
        if not args.check:
            print("wrote", path)

    if args.check:
        mismatches = 0
        for spec in CAPS:
            name = f"{spec['num']}_{spec['domain']}.ipynb"
            committed = f"{out_dir}/{name}"
            generated = f"{tmp}/{name}"
            if not filecmp.cmp(committed, generated, shallow=False):
                mismatches += 1
                print(f"DRIFT: {name} differs from generated output")
        shutil.rmtree(tmp, ignore_errors=True)
        if mismatches:
            print(
                f"::error:: {mismatches} notebook(s) out of sync with "
                "scripts/gen_playground_notebooks.py — run the generator and commit."
            )
            raise SystemExit(1)
        print("notebooks in sync with generator")


if __name__ == "__main__":
    main()
