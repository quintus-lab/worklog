"""Ticket ID → URL linking from admin-configured URL + safe prefixes.

Arbitrary regex is not accepted (ReDoS). Matching uses a fixed shape:
prefix+digits and Jira-style KEY-123, built only from validated prefixes.
"""

from __future__ import annotations

import html
import re
import threading
from urllib.parse import quote

# Built-in when the admin leaves prefixes blank.
DEFAULT_PREFIXES: tuple[str, ...] = (
    "INC",
    "CHG",
    "PRB",
    "REQ",
    "RITM",
    "TASK",
    "SCTASK",
)

MAX_TICKET_URL_LEN = 500
MAX_PREFIXES_LEN = 200
MAX_PREFIX_COUNT = 24
_PREFIX_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,15}$")
_TICKET_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
_TICKET_PLACEHOLDER = "{ticket}"

_lock = threading.Lock()
_pattern_cache: dict[str, re.Pattern[str]] = {}


def normalize_ticket_url(url: str) -> str:
    return (url or "").strip()[:MAX_TICKET_URL_LEN]


def normalize_prefixes(raw: str) -> str:
    """Return a canonical comma-separated prefix list (uppercase), or ''."""
    seen: list[str] = []
    for part in (raw or "").replace(";", ",").split(","):
        tok = part.strip().upper()
        if not tok:
            continue
        if tok in seen:
            continue
        seen.append(tok)
        if len(seen) >= MAX_PREFIX_COUNT:
            break
    return ",".join(seen)


def parse_prefixes(raw: str) -> list[str]:
    """Validated prefix tokens. Empty input → default ServiceNow-style list."""
    normalized = normalize_prefixes(raw)
    if not normalized:
        return list(DEFAULT_PREFIXES)
    out: list[str] = []
    for tok in normalized.split(","):
        if not _PREFIX_TOKEN_RE.fullmatch(tok):
            raise ValueError(
                f"Invalid ticket prefix {tok!r} "
                "(use letters/digits, start with a letter, max 16 chars)"
            )
        out.append(tok)
    if not out:
        return list(DEFAULT_PREFIXES)
    return out


def validate_ticket_settings(url: str, prefixes: str) -> tuple[str, str]:
    """Return cleaned (url, prefixes). Raises ValueError on bad input."""
    url = normalize_ticket_url(url)
    # Validate tokens even when empty (empty → defaults at match time).
    if (prefixes or "").strip():
        parse_prefixes(prefixes)
    prefixes = normalize_prefixes(prefixes)
    if len(prefixes) > MAX_PREFIXES_LEN:
        raise ValueError("Too many ticket prefixes")
    if url:
        low = url.lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            raise ValueError("Ticket URL must start with http:// or https://")
        if any(tok in low for tok in ("javascript:", "data:", "vbscript:")):
            raise ValueError("Invalid ticket URL")
        if _TICKET_PLACEHOLDER not in url:
            raise ValueError("Ticket URL must include {ticket} where the ID goes")
        if url.count(_TICKET_PLACEHOLDER) != 1:
            raise ValueError("Ticket URL must include {ticket} exactly once")
        if any(c in url for c in ("\n", "\r", "\t", " ", "<", ">", '"', "'")):
            raise ValueError("Ticket URL contains invalid characters")
    return url, prefixes


def _build_pattern(prefixes: list[str]) -> re.Pattern[str]:
    """Prefix+digits or Jira KEY-123. Always case-insensitive."""
    alts = [re.escape(p) + r"\d{4,12}" for p in prefixes]
    # Jira / Linear style project keys
    alts.append(r"[A-Z][A-Z0-9]{1,15}-\d{1,8}")
    body = "|".join(alts)
    return re.compile(rf"\b(?:{body})\b", re.IGNORECASE)


def compile_ticket_pattern(prefixes: str) -> re.Pattern[str]:
    key = normalize_prefixes(prefixes)
    with _lock:
        cached = _pattern_cache.get(key)
        if cached is not None:
            return cached
        tokens = parse_prefixes(key)
        compiled = _build_pattern(tokens)
        _pattern_cache[key] = compiled
        return compiled


def ticket_href(url_template: str, ticket_id: str) -> str | None:
    """Build a safe http(s) ticket URL, or None if linking is disabled/invalid."""
    url = normalize_ticket_url(url_template)
    tid = (ticket_id or "").strip()
    if not url or not tid or _TICKET_PLACEHOLDER not in url:
        return None
    if not _TICKET_ID_RE.fullmatch(tid):
        return None
    # Keep alphanumeric case from the note, but normalize for systems that expect uppercase.
    encoded = quote(tid.upper(), safe="")
    built = url.replace(_TICKET_PLACEHOLDER, encoded)
    low = built.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        return None
    if any(tok in low for tok in ("javascript:", "data:", "vbscript:")):
        return None
    return built


def _ticket_anchor(href: str, label: str) -> str:
    return (
        f'<a class="ticket-link" href="{html.escape(href, quote=True)}" '
        f'rel="noopener noreferrer" target="_blank">{html.escape(label)}</a>'
    )


def linkify_tickets(escaped_or_html: str, *, url: str, prefixes: str = "") -> str:
    """Turn ticket IDs into links. Input is already HTML-escaped (may contain tags)."""
    href_template = normalize_ticket_url(url)
    if not href_template:
        return escaped_or_html
    try:
        compiled = compile_ticket_pattern(prefixes)
    except ValueError:
        compiled = compile_ticket_pattern("")

    def repl_text(text: str) -> str:
        def one(m: re.Match[str]) -> str:
            ticket = m.group(0)
            href = ticket_href(href_template, ticket)
            if not href:
                return ticket
            return _ticket_anchor(href, ticket)

        return compiled.sub(one, text)

    parts = _TAG_SPLIT_RE.split(escaped_or_html or "")
    out: list[str] = []
    in_anchor = 0
    for part in parts:
        if part.startswith("<"):
            low = part.lower()
            if low.startswith("<a ") or low.startswith("<a>"):
                in_anchor += 1
            elif low.startswith("</a"):
                in_anchor = max(0, in_anchor - 1)
            out.append(part)
        elif in_anchor:
            out.append(part)
        else:
            out.append(repl_text(part))
    return "".join(out)
