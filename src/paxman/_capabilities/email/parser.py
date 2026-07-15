"""Email surface-grammar helpers (RFC 5322 / RFC 5321 / RFC 1035).

Moved VERBATIM from `paxman._capabilities.builtins.email`.

Mandate Law 4 (capability boundaries): these helpers encode the exact
surface grammar the EmailCapability accepts; they never orchestrate.
Mandate Law 8a (pure functions): each helper is a deterministic
predicate over a string with no side effects and no hidden state.
"""

import re

# RFC 5322 §3.2.3 `atext` — the ASCII atom-text character class. Used
# to validate the local part of the mailbox as a `dot-atom`:
#   dot-atom = atext *("." atext)
# Dots are allowed *between* atext runs only (no leading, no trailing,
# no consecutive dots). Quoted-string local parts (RFC 5322 §3.2.4)
# are out of v2.0.0 scope and fail the atext gate.
_ATEXT: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&'*+-/=?^_`{|}~"
)

# RFC 1035 §2.3.1 / RFC 5321 §3.4 `sub-domain` grammar:
#   Let-dig = ALPHA | DIGIT
#   Ldh-str = *( ALPHA | DIGIT | "-" )
#   sub-domain = Let-dig *Ldh-str
# i.e. each label starts and ends with a letter or digit, interior
# characters may be letters, digits, or hyphens, and the label length
# is 1-63. The total domain length is capped at 253 (RFC 1035 §2.3.4).
# Bracketed domain-literals (RFC 5321 §3.4.1 IPv4 / §3.4.2 IPv6) are
# out of v2.0.0 scope and fail the dot-atom-domain gate.
_LABEL_MAX_LEN = 63
_DOMAIN_MAX_LEN = 253

# Pre-compiled dot-atom regexes — dot-atom local part and dot-atom
# domain. Single labels validated by the `_LABEL` pattern; multiple
# labels are joined by dots.
_ATEXT_RUN = r"[!#$%&'*+/=?^_`{|}~A-Za-z0-9-]"
_LABEL_RUN = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_DOT_ATOM_LOCAL = re.compile(rf"^{_ATEXT_RUN}+(?:\.{_ATEXT_RUN}+)*$")
_DOT_ATOM_DOMAIN = re.compile(rf"^{_LABEL_RUN}(?:\.{_LABEL_RUN})*$")


def _validate_dot_atom_local(local: str) -> bool:
    """RFC 5322 §3.2.3 dot-atom local part.

    Rejects:
    - empty string
    - leading or trailing dot
    - consecutive dots
    - any character that is not atext and not `.`
    - quoted-string local parts (RFC 5322 §3.2.4)
    - internal whitespace, parentheses, comments

    Note: the ``/`` (slash) character IS part of the ``atext`` set
    (RFC 5322 §3.2.3), so it is accepted, not rejected.
    """
    if not local:
        return False
    if not _DOT_ATOM_LOCAL.fullmatch(local):
        return False
    # belt-and-braces: atext set membership is the canonical check.
    for ch in local:
        if ch != "." and ch not in _ATEXT:
            return False
    return True


def _validate_dot_atom_domain(domain: str) -> bool:
    """RFC 5321 §3.4 dot-atom domain + RFC 1035 §2.3.1 label rules.

    Rejects:
    - empty string
    - leading or trailing dot
    - consecutive dots
    - label that starts or ends with `-`
    - label longer than 63 characters
    - total domain length longer than 253 characters
    - any label containing characters other than LDH (letters, digits,
      hyphens)
    - bracketed domain-literals (RFC 5321 §3.4.1/§3.4.2 IPv4/IPv6)

    NOTE on intentional acceptances: a single-label domain like
    `localhost` is *valid* under RFC 1035 §2.3.1 (a label is a
    sub-domain). This capability accepts `user@localhost` as
    CANONICALIZED under the v2.0.0 grammar gate. `strict=True` is
    intentionally narrow in v2.0.0 (whitespace + ASCII-only) and
    does NOT reject single-label domains; a contract author wanting
    a tighter multi-label requirement is not served by `strict=True`
    in v2.0.0 and would need a future v2.x capability extension.
    """
    if not domain:
        return False
    if len(domain) > _DOMAIN_MAX_LEN:
        return False
    if not _DOT_ATOM_DOMAIN.fullmatch(domain):
        return False
    labels = domain.split(".")
    for label in labels:
        if len(label) == 0 or len(label) > _LABEL_MAX_LEN:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return True
