"""Shared HTML helpers and constants for pages."""
from __future__ import annotations

import html
from datetime import date, timedelta
from urllib.parse import urlencode

import storage
import tickets
from pages.markup import (
    DETAILS_HINT,
    DETAILS_PLACEHOLDER,
    render_details,
    render_plain_with_tickets,
)

CATEGORIES = storage.CATEGORIES
STATUSES = storage.STATUSES
MAX_TITLE_LEN = storage.MAX_TITLE_LEN
MAX_DETAILS_LEN = storage.MAX_DETAILS_LEN

# Default page sizes (keep lists small for speed)
INDEX_PER_PAGE = 20
HISTORY_PER_PAGE = 25
PER_PAGE_CHOICES = (10, 20, 25, 50)


def parse_page(qs: dict, *, default: int = 1) -> int:
    try:
        return max(1, int((qs.get("page") or [str(default)])[0]))
    except (TypeError, ValueError):
        return default


def parse_per_page(qs: dict, *, default: int = INDEX_PER_PAGE) -> int:
    try:
        n = int((qs.get("per") or [str(default)])[0])
    except (TypeError, ValueError):
        return default
    if n in PER_PAGE_CHOICES:
        return n
    return default


def pager_html(
    *,
    page: int,
    total: int,
    per_page: int,
    base_path: str,
    extra_params: dict[str, str] | None = None,
) -> str:
    """Prev / page N of M / Next controls. Newest-first lists stay fast with small per_page."""
    pages = max(1, (total + per_page - 1) // per_page) if total else 1
    page = min(page, pages)

    def link(p: int) -> str:
        params = dict(extra_params or {})
        params["page"] = str(p)
        if per_page != INDEX_PER_PAGE or base_path != "/":
            # always include per when not default for that view
            params["per"] = str(per_page)
        qs = urlencode({k: v for k, v in params.items() if v is not None and v != ""})
        return f"{base_path}?{qs}" if qs else base_path

    prev_p = page - 1 if page > 1 else None
    next_p = page + 1 if page < pages else None
    start_i = 0 if total == 0 else (page - 1) * per_page + 1
    end_i = min(page * per_page, total)

    prev_btn = (
        f'<a class="btn btn-ghost btn-sm" href="{esc(link(prev_p))}">Prev</a>'
        if prev_p
        else '<span class="btn btn-ghost btn-sm" style="visibility:hidden">Prev</span>'
    )
    next_btn = (
        f'<a class="btn btn-ghost btn-sm" href="{esc(link(next_p))}">Next</a>'
        if next_p
        else '<span class="btn btn-ghost btn-sm" style="visibility:hidden">Next</span>'
    )
    return f"""
<nav class="pager" aria-label="Pagination">
  {prev_btn}
  <span class="muted">Page <strong>{page}</strong> / {pages} · showing {start_i}-{end_i} of {total}</span>
  {next_btn}
</nav>
"""

def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def safe_next_url(url: str | None) -> str:
    if not url:
        return "/"
    url = url.strip()
    if not url.startswith("/") or url.startswith("//") or "\\" in url:
        return "/"
    if ":" in url.split("?", 1)[0]:
        return "/"
    return url


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_range(anchor: date | None = None) -> tuple[date, date]:
    if anchor is None:
        anchor = date.today()
    start = monday_of(anchor)
    return start, start + timedelta(days=6)


def previous_week_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    prev_mon = monday_of(today) - timedelta(days=7)
    return prev_mon, prev_mon + timedelta(days=6)


def group_by_day(entries: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group by date with newest days first; keep entry order within each day."""
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["date"], []).append(e)
    # Newest date at the top
    return sorted(groups.items(), key=lambda kv: kv[0], reverse=True)


def category_options(selected: str = "General") -> str:
    return "\n".join(
        f'<option value="{esc(c)}"{" selected" if c == selected else ""}>{esc(c)}</option>'
        for c in CATEGORIES
    )


def status_options(selected: str = "done") -> str:
    labels = {
        "done": "Done",
        "in-progress": "In progress",
        "blocked": "Blocked",
        "follow-up": "Follow-up",
    }
    return "\n".join(
        f'<option value="{esc(s)}"{" selected" if s == selected else ""}>{esc(labels.get(s, s))}</option>'
        for s in STATUSES
    )


def render_tag_chips(raw: str, *, ticket: dict | None = None) -> str:
    """One chip per tag. Chip click filters the log; ticket IDs also link out."""
    tokens = storage.split_tags(raw)
    if not tokens:
        return ""
    prefixes = (ticket or {}).get("prefixes") or ""
    url = (ticket or {}).get("url") or ""
    chips: list[str] = []
    for tok in tokens:
        filter_href = "/?" + urlencode({"tag": tok})
        label = esc(tok)
        ext = ""
        if url and tickets.is_ticket_id(tok, prefixes):
            href = tickets.ticket_href(url, tok)
            if href:
                ext = (
                    f'<a class="tag-ticket-ext" href="{esc(href)}" '
                    f'rel="noopener noreferrer" target="_blank" '
                    f'title="Open {label} in ticket system">↗</a>'
                )
        chips.append(
            f'<span class="tag-chip">'
            f'<a class="tag-chip-filter" href="{esc(filter_href)}">{label}</a>'
            f"{ext}</span>"
        )
    return f'<span class="tag-list">{"".join(chips)}</span>'


def render_entry(e: dict, *, editable: bool = True, ticket: dict | None = None) -> str:
    if ticket is None:
        ticket = storage.get_ticket_settings()
    raw_details = e.get("details") or ""
    details_html = render_details(raw_details, ticket=ticket)
    if not details_html:
        details = ""
    else:
        nlines = len(raw_details.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n"))
        unit = "line" if nlines == 1 else "lines"
        details = (
            f'<details class="entry-details">'
            f"<summary><span class=\"details-kicker\">Details</span>"
            f"<span class=\"details-meta\">{nlines} {unit}</span></summary>"
            f'<div class="entry-details-body">{details_html}</div>'
            f"</details>"
        )
    owner = (
        f'<span class="badge owner">{esc(e["owner"])}</span>' if e.get("owner") else ""
    )
    tags = render_tag_chips(e.get("tags") or "", ticket=ticket)
    fu = (
        f'<span class="badge follow-up">follow-up {esc(e["follow_up"])}</span>'
        if e.get("follow_up")
        else ""
    )
    actions = ""
    if editable:
        actions = f"""
      <div class="entry-actions">
        <button type="button" class="btn btn-ghost btn-sm edit-btn"
          data-id="{esc(e["id"])}"
          data-date="{esc(e["date"])}"
          data-title="{esc(e["title"])}"
          data-details="{esc(e.get("details") or "")}"
          data-category="{esc(e.get("category") or "General")}"
          data-status="{esc(e.get("status") or "done")}"
          data-tags="{esc(e.get("tags") or "")}"
          data-follow-up="{esc(e.get("follow_up") or "")}"
          aria-label="Edit entry">Edit</button>
        <button type="button" class="btn btn-danger-ghost btn-sm delete-btn"
          data-id="{esc(e["id"])}" aria-label="Delete entry">Delete</button>
      </div>"""
    return f"""
    <article class="entry-card" data-id="{esc(e["id"])}">
      <div class="entry-body">
        <div class="entry-meta">
          <time datetime="{esc(e["date"])}">{esc(e["date"])}</time>
          <span class="badge cat">{esc(e.get("category") or "General")}</span>
          <span class="badge status status-{esc(e.get("status") or "done")}">{esc(e.get("status") or "done")}</span>
          {tags}{fu}{owner}
        </div>
        <h3 class="entry-title">{render_plain_with_tickets(e["title"], ticket=ticket)}</h3>
        {details}
      </div>
      {actions}
    </article>"""


def edit_modal_html() -> str:
    return f"""
<div id="edit-modal" class="modal" hidden role="dialog" aria-modal="true" aria-labelledby="edit-title">
  <div class="modal-backdrop" data-close-modal></div>
  <div class="modal-panel card">
    <div class="modal-head">
      <h2 id="edit-title">Edit entry</h2>
      <button type="button" class="btn btn-ghost btn-icon" data-close-modal aria-label="Close">&times;</button>
    </div>
    <form id="edit-form" class="stack">
      <input type="hidden" id="edit-id" />
      <div class="grid-3">
        <label class="field"><span class="field-label">Date</span>
          <input type="date" id="edit-date" required /></label>
        <label class="field"><span class="field-label">Category</span>
          <select id="edit-category">{category_options()}</select></label>
        <label class="field"><span class="field-label">Status</span>
          <select id="edit-entry-status">{status_options()}</select></label>
      </div>
      <div class="grid-2">
        <label class="field"><span class="field-label">Tags</span>
          <input type="text" id="edit-tags" maxlength="200"
            placeholder="HRM BGP 1234567" />
          <span class="field-hint">Space-separated. 6-12 digit IDs and INC/CHG/KEY-123 become tickets.</span></label>
        <label class="field"><span class="field-label">Follow-up date</span>
          <input type="date" id="edit-follow-up" /></label>
      </div>
      <label class="field"><span class="field-label">Title</span>
        <input type="text" id="edit-title-input" required maxlength="{MAX_TITLE_LEN}" /></label>
      <label class="field"><span class="field-label">Details</span>
        <textarea id="edit-details" rows="4" maxlength="{MAX_DETAILS_LEN}"
          placeholder="{esc(DETAILS_PLACEHOLDER)}"></textarea>
        <span class="field-hint">{esc(DETAILS_HINT)}</span></label>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary" id="edit-save-btn">Save changes</button>
        <button type="button" class="btn btn-ghost" data-close-modal>Cancel</button>
        <span id="edit-form-status" class="form-status" aria-live="polite"></span>
      </div>
    </form>
  </div>
</div>
"""



