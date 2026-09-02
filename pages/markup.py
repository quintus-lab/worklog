"""Safe details markup. Escape first; no placeholder engine."""

from __future__ import annotations

import html
import re

DETAILS_PLACEHOLDER = (
    "Tickets, hosts, outcome. **bold**, paste a URL, or [label](https://…)"
)
DETAILS_HINT = "**bold**, - lists, and http(s) links. Bare URLs become clickable."

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_AUTO_RE = re.compile(r"(https?://[^\s<]+)")
_UL_RE = re.compile(r"^[\t ]*- ")
_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")


def _safe_href(url: str) -> str | None:
    url = html.unescape(url).strip()
    low = url.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        return None
    if any(c in url for c in ("\n", "\r", "\t", " ", "<", ">", '"', "'", "\\")):
        return None
    return url


def _anchor(href: str, label_html: str) -> str:
    return (
        f'<a href="{html.escape(href, quote=True)}" rel="noopener noreferrer" '
        f'target="_blank">{label_html}</a>'
    )


def _link_sub(m: re.Match[str]) -> str:
    href = _safe_href(m.group(2))
    if not href:
        return m.group(0)
    return _anchor(href, m.group(1))


def _auto_sub(m: re.Match[str]) -> str:
    url = m.group(1)
    trail = ""
    while url and url[-1] in ".,;:!?":
        trail = url[-1] + trail
        url = url[:-1]
    href = _safe_href(url)
    if not href:
        return m.group(0)
    return _anchor(href, html.escape(href)) + trail


def _autolink_text_nodes(s: str) -> str:
    parts = _TAG_SPLIT_RE.split(s)
    out: list[str] = []
    for part in parts:
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(_AUTO_RE.sub(_auto_sub, part))
    return "".join(out)


def render_inline(text: str, *, ticket: dict | None = None) -> str:
    """Escape, then **bold**, then [text](url), then bare http(s) URLs.

    Ticket IDs are not auto-linked here. Only tags entered in the Tags field
    get ticket-system URLs (see render_tag_chips).
    """
    s = html.escape(text or "", quote=False)
    s = _BOLD_RE.sub(r"<strong>\1</strong>", s)
    s = _LINK_RE.sub(_link_sub, s)
    s = _autolink_text_nodes(s)
    return s


def render_plain_with_tickets(text: str, *, ticket: dict | None = None) -> str:
    """Escape a single line. Ticket URLs belong on tag chips, not titles."""
    return html.escape(text or "", quote=False)


def render_details(text: str, *, ticket: dict | None = None) -> str:
    """Paragraphs, line breaks, and hyphen lists. Input may contain NULs."""
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    if not raw.strip():
        return ""
    blocks: list[str] = []
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        if _UL_RE.match(lines[i]):
            items: list[str] = []
            while i < len(lines) and _UL_RE.match(lines[i]):
                items.append(
                    f"<li>{render_inline(lines[i].lstrip()[2:], ticket=ticket)}</li>"
                )
                i += 1
            blocks.append(f"<ul>{''.join(items)}</ul>")
            continue
        if lines[i].strip() == "":
            i += 1
            continue
        para = [lines[i]]
        i += 1
        while i < len(lines) and lines[i].strip() != "" and not _UL_RE.match(lines[i]):
            para.append(lines[i])
            i += 1
        inner = "<br>".join(render_inline(p, ticket=ticket) for p in para)
        blocks.append(f"<p>{inner}</p>")
    return "".join(blocks)
