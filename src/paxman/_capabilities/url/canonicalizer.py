from __future__ import annotations

import ipaddress
import re

import attrs

from paxman._capabilities._shared.base import CapabilityBase
from paxman._capabilities.url.contract import CanonicalURLContract
from paxman._capabilities.url.grammar import RecognizedRep, recognize
from paxman._capabilities.url.parser import default_port_for_scheme
from paxman._capabilities.url.rules import _evidence
from paxman._core.engine_env import Engine
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# Constitutional scope of this capability change (MANDATE.md):
#   Law 1  (Determinism)        — canonicalize is a pure function of (value, contract).
#   Law 2  (Idempotence)        — canonicalize(canonicalize(x)) == canonicalize(x).
#   Law 3  (Never guess)        — ambiguous input yields Status.AMBIGUOUS, never a pick.
#   Law 8a (Capability purity)  — no I/O, time, randomness, or network; (value, contract) only.
#   Law 13 (Immutability)       — results are returned as frozen value objects.
#   Law 14 (Provenance)         — every emitted rule cites a source via _RULE_AUTHORITIES.
# The dot-segment and authority normalizations below follow RFC 3986 §5.2.4 / §3.2.

_PCT = re.compile(r"%([0-9a-fA-F]{2})")
_UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*$")


@attrs.frozen
class _Candidate:
    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


@attrs.frozen
class _Survivor:
    value: str
    evidence: tuple[Evidence, ...]


def _uppercase_pct_hex(s: str) -> str:
    return _PCT.sub(lambda m: "%" + m.group(1).upper(), s)


def _decode_unreserved(s: str) -> str:
    def _repl(m: re.Match[str]) -> str:
        ch = chr(int(m.group(1), 16))
        return ch if ch in _UNRESERVED else m.group(0)

    return _PCT.sub(_repl, s)


def _remove_dot_segments(path: str) -> str:
    # RFC 3986 §5.2.4 input/output-buffer algorithm. Preserves empty
    # segments and trailing slashes: //a stays //a, /a/ stays /a/,
    # /a/. normalizes to /a/, /a/../ normalizes to /.
    if not path:
        return ""
    input_buffer = path
    output_buffer = ""
    while input_buffer:
        if input_buffer.startswith("../"):
            input_buffer = input_buffer[3:]
        elif input_buffer.startswith("./"):
            input_buffer = input_buffer[2:]
        elif input_buffer.startswith("/./"):
            input_buffer = "/" + input_buffer[3:]
        elif input_buffer == "/.":
            input_buffer = "/"
        elif input_buffer.startswith("/../"):
            input_buffer = "/" + input_buffer[4:]
            output_buffer = output_buffer[: output_buffer.rfind("/")]
        elif input_buffer == "/..":
            input_buffer = "/"
            output_buffer = output_buffer[: output_buffer.rfind("/")]
        elif input_buffer == ".":
            input_buffer = ""
        elif input_buffer == "..":
            input_buffer = ""
        else:
            if input_buffer.startswith("/"):
                input_buffer = input_buffer[1:]
                prefix, slash, rest = input_buffer.partition("/")
                output_buffer += "/" + prefix
                input_buffer = slash + rest
            else:
                prefix, slash, rest = input_buffer.partition("/")
                output_buffer += prefix
                input_buffer = slash + rest
    return output_buffer


def _sort_query(q: str) -> str:
    return "&".join(sorted(q.split("&")))


def _split_authority(authority: str) -> tuple[str, str, str | None]:
    userinfo = ""
    host = authority
    port: str | None = None
    if "@" in authority:
        userinfo, host = authority.split("@", 1)
    # An IPv6 literal is enclosed in brackets, e.g. [2001:db8::1]; the
    # colons inside it are NOT host/port separators. Only split on a colon
    # that lies OUTSIDE the bracketed zone.
    if host.startswith("[") and "]" in host:
        bracket_end = host.index("]")
        tail = host[bracket_end + 1 :]
        if tail.startswith(":"):
            port = tail[1:]
            host = host[: bracket_end + 1]
    elif ":" in host:
        host, port = host.rsplit(":", 1)
    return userinfo, host, port


def _validate_authority(host: str, port: str | None) -> bool:
    if not host:
        return False
    if host.startswith("[") and host.endswith("]"):
        # Strict IPv6 literal: validate via the stdlib, which fully enforces
        # RFC 4291 (rejects malformed forms such as "[:]" or "2001:db8:::1").
        inner = host[1:-1]
        if not _is_valid_ipv6(inner):
            return False
    elif not _is_valid_reg_name(host) and not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        # Registered name (RFC 3986 §3.2.2, may be digit-leading like 3com.com)
        # or IPv4. A scheme-like host (starts with a letter and matches the
        # scheme production) is not a valid authority host.
        return False
    if port is not None:
        if not port.isdigit():
            return False
        # Ports must be in the 0..65535 range (RFC 3986 §3.2.3).
        if not (0 <= int(port) <= 65535):
            return False
    return True


# RFC 3986 §3.2.2 reg-name: *( unreserved / pct-encoded / sub-delims / "." ).
# Unreserved = ALPHA / DIGIT / "-" / "." / "_" / "~"; sub-delims =
# "!" / "$" / "&" / "'" / "(" / ")" / "*" / "+" / "," / ";" / "=".
_REG_NAME = re.compile(r"^[A-Za-z0-9\-._~!$&'()*+,;=]+$")


def _is_valid_reg_name(host: str) -> bool:
    return bool(_REG_NAME.match(host))


def _is_valid_ipv6(inner: str) -> bool:
    try:
        ipaddress.IPv6Address(inner)
    except ValueError:
        return False
    return True


def generate_interpretations(
    reps: list[RecognizedRep], contract: CanonicalURLContract
) -> list[_Candidate]:
    cands: list[_Candidate] = []
    for rep in reps:
        ev: list[Evidence] = []
        src = rep.captures
        scheme = src.get("scheme")
        authority = src.get("authority", "")
        pathqf = src.get("pathqf", "")

        fragment = ""
        if "#" in pathqf:
            pathqf, fragment = pathqf.split("#", 1)
        query = ""
        if "?" in pathqf:
            pathqf, query = pathqf.split("?", 1)
        path = pathqf

        if scheme is not None:
            scheme = scheme.lower()
            ev.append(_evidence("lowercase_scheme"))
        if authority:
            userinfo, host, port = _split_authority(authority)
            if contract.strip_userinfo and userinfo:
                userinfo = ""
                ev.append(_evidence("strip_userinfo"))
            if host:
                host = host.lower()
                ev.append(_evidence("lowercase_host"))
                if contract.whatwg:
                    if host.endswith("."):
                        host = host.rstrip(".")
                        ev.append(_evidence("whatwg_trailing_dot_host"))
                    if contract.whatwg and "\\" in host:
                        host = host.replace("\\", "")
                        ev.append(_evidence("whatwg_backslash_coerce"))
            if port is not None:
                # Only elide when the port is a well-formed integer equal to the
                # scheme default. A non-numeric or empty port (e.g. "xyz" or the
                # explicitly-empty "http://host:/") is NOT elided; it is passed
                # through to _validate_authority, which rejects it downstream.
                # Guarding with isdigit() prevents int(port) from raising inside
                # the resolver (the same class of crash as the IPv6 bracket bug).
                if port.isdigit():
                    default = default_port_for_scheme(scheme) if scheme else None
                    if default is not None and int(port) == default:
                        port = None
                        ev.append(_evidence("elide_default_port"))
            rebuilt = host
            if userinfo:
                rebuilt = userinfo + "@" + rebuilt
            if port is not None:
                rebuilt = rebuilt + ":" + port
            authority = rebuilt

        if path:
            if contract.whatwg:
                path = path.replace("\\", "/")
                ev.append(_evidence("whatwg_backslash_coerce"))
                path = path.replace("%2e", ".").replace("%2E", ".")
                ev.append(_evidence("whatwg_pct_dot_in_path"))
            upper = _uppercase_pct_hex(path)
            if upper != path:
                path = upper
                ev.append(_evidence("uppercase_pct_hex"))
            decoded = _decode_unreserved(path)
            if decoded != path:
                path = decoded
                ev.append(_evidence("decode_unreserved_pct"))
            dots = _remove_dot_segments(path)
            if dots != path:
                path = dots
                ev.append(_evidence("remove_dot_segments"))

        if authority and path == "":
            path = "/"
            ev.append(_evidence("empty_path_to_slash"))

        if query:
            q_upper = _uppercase_pct_hex(query)
            if q_upper != query:
                query = q_upper
                ev.append(_evidence("uppercase_pct_hex"))
            q_decoded = _decode_unreserved(query)
            if q_decoded != query:
                query = q_decoded
                ev.append(_evidence("decode_unreserved_pct"))
            if contract.sort_query:
                query = _sort_query(query)
                ev.append(_evidence("sort_query"))

        if fragment:
            f_upper = _uppercase_pct_hex(fragment)
            if f_upper != fragment:
                fragment = f_upper
                ev.append(_evidence("uppercase_pct_hex"))
            f_decoded = _decode_unreserved(fragment)
            if f_decoded != fragment:
                fragment = f_decoded
                ev.append(_evidence("decode_unreserved_pct"))
            if contract.strip_fragment:
                fragment = ""
                ev.append(_evidence("strip_fragment"))

        value = ""
        if scheme is not None:
            value += scheme + "://" + authority
        elif authority:
            value += "//" + authority
        value += path
        if query:
            value += "?" + query
        if fragment:
            value += "#" + fragment

        if not ev:
            ev.append(_evidence("no_transformation_needed"))
        cands.append(
            _Candidate(
                value=value,
                rule=ev[-1].rule,
                source="RFC 3986 §6.2.2",
                evidence=tuple(ev),
            )
        )
    return cands


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalURLContract
) -> tuple[list[_Survivor], list[str]]:
    survivors: list[_Survivor] = []
    drops: list[str] = []
    for c in candidates:
        src = c.value
        rest: str | None = None
        if "://" in src:
            head, rest = src.split("://", 1)
            if not _SCHEME_RE.match(head):
                drops.append("grammar_rejected")
                continue
        elif src.startswith("//"):
            rest = src[2:]
        if rest is not None:
            auth = rest.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
            if auth:
                _, host, port = _split_authority(auth)
                if not _validate_authority(host, port):
                    drops.append("grammar_rejected")
                    continue
        survivors.append(_Survivor(value=c.value, evidence=c.evidence))
    return survivors, drops


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalURLContract,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    ev: list[Evidence] = []
    if not candidates:
        ev.append(_evidence("unrecognized_format"))
        return Status.INVALID, None, tuple(ev), None
    if not survivors:
        ev.append(_evidence("grammar_rejected"))
        return Status.INVALID, None, tuple(ev), None
    if len(survivors) > 1:
        return (
            Status.AMBIGUOUS,
            None,
            tuple(ev),
            tuple(sorted(s.value for s in survivors)),
        )
    return Status.CANONICALIZED, survivors[0].value, survivors[0].evidence, None


class URLCapability(CapabilityBase):
    name: str = "url_canonicalization"

    def can_handle(self, contract: object, value: object) -> bool:
        return isinstance(contract, CanonicalURLContract) and isinstance(value, str)

    def canonicalize(
        self, value: object, contract: object, engine: Engine | None = None
    ) -> CapabilityResult:
        if not isinstance(contract, CanonicalURLContract):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_url_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )
        reps = recognize(value, contract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("unrecognized_format"),),
            )
        if value.strip() == "" and all(
            rep.captures.get("scheme") is None and rep.captures.get("authority") is None
            for rep in reps
        ):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("unrecognized_format"),),
            )
        if contract.scheme_allow is not None:
            for rep in reps:
                sch = rep.captures.get("scheme")
                if sch is not None and sch.lower() not in contract.scheme_allow:
                    return CapabilityResult(
                        status=Status.UNSUPPORTED,
                        evidence=(_evidence("scheme_not_allowed"),),
                    )
        cands = generate_interpretations(reps, contract)
        survivors, drops = resolve_and_validate(cands, contract)
        status, val, ev, cands_out = classify(cands, survivors, drops, contract)
        return CapabilityResult(status=status, value=val, evidence=ev, candidates=cands_out)
