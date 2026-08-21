"""Main work log page with pagination."""
from __future__ import annotations

from datetime import date

import auth
import storage

from pages.common import (
    INDEX_PER_PAGE,
    MAX_DETAILS_LEN,
    MAX_TITLE_LEN,
    PER_PAGE_CHOICES,
    category_options,
    edit_modal_html,
    esc,
    pager_html,
    parse_page,
    parse_per_page,
    render_entry,
    status_options,
)
from pages.markup import DETAILS_HINT, DETAILS_PLACEHOLDER
from pages.layout import layout


def page_index(user: str, qs: dict | None = None, *, csrf_token: str = "") -> str:
    qs = qs or {}
    writable = auth.can_write(user)
    today = date.today().isoformat()
    q = storage.clip_search_q((qs.get("q") or [""])[0]) or ""
    page = parse_page(qs)
    per = parse_per_page(qs, default=INDEX_PER_PAGE)
    total = storage.count_entries(q=q or None)
    offset = (page - 1) * per
    # clamp page if past end
    pages = max(1, (total + per - 1) // per) if total else 1
    if page > pages:
        page = pages
        offset = (page - 1) * per

    ticket = storage.get_ticket_settings()
    entries = storage.load_entries(q=q or None, limit=per, offset=offset)
    if entries:
        entries_html = "\n".join(
            render_entry(e, editable=writable, ticket=ticket) for e in entries
        )
    elif q:
        entries_html = (
            f'<div class="empty-state" id="empty-state"><h3>No matches</h3>'
            f'<p class="muted">Nothing matched “{esc(q)}”. '
            f'<a href="/">Clear search</a></p></div>'
        )
    else:
        entries_html = (
            '<div class="empty-state" id="empty-state"><h3>No entries yet</h3>'
            f'<p class="muted">{"Log your first task above." if writable else "View-only: nothing recorded yet."}</p></div>'
        )
    pager = pager_html(
        page=page,
        total=total,
        per_page=per,
        base_path="/",
        extra_params={"per": str(per), "q": q},
    )

    per_opts = "".join(
        f'<option value="{n}"{" selected" if n == per else ""}>{n} / page</option>'
        for n in PER_PAGE_CHOICES
    )
    clear_btn = (
        f'<a class="btn btn-ghost btn-sm" href="/?per={per}">Clear search</a>' if q else ""
    )

    form = ""
    modal = ""
    if writable:
        form = f"""
<section class="card form-card" aria-labelledby="new-entry-heading">
  <div class="card-head"><h2 id="new-entry-heading">New entry</h2></div>
  <form id="entry-form" class="stack" autocomplete="off">
    <div class="grid-3">
      <label class="field"><span class="field-label">Date</span>
        <input type="date" name="date" id="date" value="{today}" required /></label>
      <label class="field"><span class="field-label">Category</span>
        <select name="category" id="category">{category_options()}</select></label>
      <label class="field"><span class="field-label">Status</span>
        <select name="status" id="status">{status_options()}</select></label>
    </div>
    <div class="grid-2">
      <label class="field"><span class="field-label">Tags / ticket <span class="field-hint">optional</span></span>
        <input type="text" name="tags" id="tags" maxlength="200" placeholder="INC12345, BGP" /></label>
      <label class="field"><span class="field-label">Follow-up date <span class="field-hint">optional</span></span>
        <input type="date" name="follow_up" id="follow_up" /></label>
    </div>
    <label class="field"><span class="field-label">Title</span>
      <input type="text" name="title" id="title" required maxlength="{MAX_TITLE_LEN}"
        placeholder="e.g. Fixed BGP session flapping on ns-ytwr-dr004" /></label>
    <label class="field"><span class="field-label">Details <span class="field-hint">optional · Markdown</span></span>
      <textarea name="details" id="details" rows="4" maxlength="{MAX_DETAILS_LEN}"
        placeholder="{esc(DETAILS_PLACEHOLDER)}"></textarea>
      <span class="field-hint">{esc(DETAILS_HINT)}</span></label>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="submit-btn">Save entry</button>
      <button type="reset" class="btn btn-ghost">Clear</button>
      <span id="form-status" class="form-status" aria-live="polite"></span>
    </div>
  </form>
</section>
"""
        modal = edit_modal_html()
    else:
        form = """
<section class="card view-only-banner" role="status">
  <strong>Viewer mode</strong>
  <span class="muted">Read-only. Admins log and edit work; you can browse and download Excel.</span>
</section>
"""

    body = f"""
<section class="page-header">
  <div>
    <h1>{"What did you do?" if writable else "Work log"}</h1>
    <p class="lede">{"Saved to SQLite; Excel is always available to export." if writable else "View-only access."}</p>
  </div>
  <div class="stat-pills">
    <span class="stat-pill"><strong>{total}</strong> {"match" if q and total == 1 else "matches" if q else "total"}</span>
    <span class="stat-pill muted">page {page} · {per} each</span>
    <a class="stat-pill" href="/history">Advanced search</a>
  </div>
</section>
{form}
<section class="list-section" aria-labelledby="recent-heading">
  <div class="section-head">
    <h2 id="recent-heading">{"Matches" if q else "Entries"}</h2>
    <div class="list-controls">
      <form method="get" action="/" class="per-page-form">
        <input type="hidden" name="page" value="1" />
        <input type="hidden" name="q" value="{esc(q)}" />
        <label class="field-inline">
          <span class="visually-hidden">Per page</span>
          <select name="per" onchange="this.form.submit()" aria-label="Entries per page">
            {per_opts}
          </select>
        </label>
      </form>
      {clear_btn}
    </div>
  </div>
  {pager}
  <div id="entries" class="entry-list">{entries_html}</div>
  {pager}
</section>
{modal}
"""
    return layout(
        "Log work · Daily Work Log" if writable else "Work log · Daily Work Log",
        body,
        active="log",
        user=user,
        csrf_token=csrf_token,
        search_q=q,
    )
