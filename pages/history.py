"""History & search with pagination."""
from __future__ import annotations

import auth
import storage

from pages.common import (
    HISTORY_PER_PAGE,
    PER_PAGE_CHOICES,
    STATUSES,
    edit_modal_html,
    esc,
    pager_html,
    parse_page,
    parse_per_page,
    render_entry,
)
from pages.layout import layout


def page_history(user: str, qs: dict, *, csrf_token: str = "") -> str:
    q = storage.clip_search_q((qs.get("q") or [""])[0]) or ""
    tag = storage.clip_tag_filter((qs.get("tag") or [""])[0])
    status = ((qs.get("status") or [""])[0] or "").strip()
    start = ((qs.get("start") or [""])[0] or "").strip() or None
    end = ((qs.get("end") or [""])[0] or "").strip() or None
    page = parse_page(qs)
    per = parse_per_page(qs, default=HISTORY_PER_PAGE)
    total = storage.count_entries(
        start=start, end=end, q=q or None, tag=tag, status=status or None
    )
    pages = max(1, (total + per - 1) // per) if total else 1
    if page > pages:
        page = pages
    offset = (page - 1) * per
    ticket = storage.get_ticket_settings()
    entries = storage.load_entries(
        start=start,
        end=end,
        q=q or None,
        tag=tag,
        status=status or None,
        limit=per,
        offset=offset,
    )
    writable = auth.can_write(user)
    entries_html = (
        "\n".join(
            render_entry(e, editable=writable, ticket=ticket) for e in entries
        )
        if entries
        else '<div class="empty-state"><h3>No matches</h3></div>'
    )
    extra = {
        "q": q,
        "tag": tag or "",
        "status": status,
        "start": start or "",
        "end": end or "",
        "per": str(per),
    }
    pager = pager_html(
        page=page,
        total=total,
        per_page=per,
        base_path="/history",
        extra_params=extra,
    )
    per_opts = "".join(
        f'<option value="{n}"{" selected" if n == per else ""}>{n} / page</option>'
        for n in PER_PAGE_CHOICES
    )
    status_opts = "".join(
        f'<option value="{esc(s)}"{" selected" if s == status else ""}>{esc(s)}</option>'
        for s in STATUSES
    )

    body = f"""
<section class="page-header">
  <div>
    <h1>History &amp; search</h1>
    <p class="lede">Search the full log. Results are paged so large histories stay fast.</p>
  </div>
</section>
<section class="card">
  <form class="stack" method="get" action="/history">
    <div class="grid-3">
      <label class="field"><span class="field-label">Search</span>
        <input type="search" name="q" value="{esc(q)}" placeholder="title, tags, details…" maxlength="200" /></label>
      <label class="field"><span class="field-label">From</span>
        <input type="date" name="start" value="{esc(start or "")}" /></label>
      <label class="field"><span class="field-label">To</span>
        <input type="date" name="end" value="{esc(end or "")}" /></label>
    </div>
    <div class="grid-3">
      <label class="field"><span class="field-label">Status</span>
        <select name="status">
          <option value=""{" selected" if not status else ""}>Any</option>
          {status_opts}
        </select>
      </label>
      <label class="field"><span class="field-label">Per page</span>
        <select name="per">{per_opts}</select>
      </label>
      <div class="form-actions" style="align-self:end">
        <button type="submit" class="btn btn-primary">Search</button>
        <a class="btn btn-ghost" href="/history">Reset</a>
      </div>
    </div>
  </form>
</section>
{pager}
<div class="entry-list">{entries_html}</div>
{pager}
{edit_modal_html() if writable else ""}
"""
    return layout(
        "History · Daily Work Log",
        body,
        active="history",
        user=user,
        csrf_token=csrf_token,
        search_q=q,
    )
