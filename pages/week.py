"""page_week page."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import auth
import storage

from pages.common import (
    edit_modal_html,
    esc,
    render_plain_with_tickets,
    render_tag_chips,
    group_by_day,
    previous_week_range,
    render_entry,
    week_range,
)
from pages.layout import layout


def page_week(user: str, qs: dict, *, csrf_token: str = "") -> str:
    writable = auth.can_write(user)
    today = date.today()
    which = (qs.get("which") or ["auto"])[0]
    week_param = (qs.get("week") or [None])[0]
    print_mode = (qs.get("print") or [""])[0] in ("1", "true", "yes")

    if week_param:
        try:
            anchor = datetime.strptime(week_param, "%Y-%m-%d").date()
        except ValueError:
            anchor = today
        start, end = week_range(anchor)
    elif which == "last":
        start, end = previous_week_range(today)
    elif which == "this":
        start, end = week_range(today)
    else:
        start, end = (
            previous_week_range(today) if today.weekday() == 0 else week_range(today)
        )

    # Newest first (load_entries already DESC; keep explicit for the week slice)
    week_entries = storage.load_entries(start=start.isoformat(), end=end.isoformat())
    week_entries.sort(key=lambda e: (e["date"], e["created_at"]), reverse=True)
    by_day = group_by_day(week_entries)
    prev_start = (start - timedelta(days=7)).isoformat()
    next_start = (start + timedelta(days=7)).isoformat()
    mon_note = (
        "Start of the week: showing <strong>last week</strong> by default."
        if today.weekday() == 0
        else "Browse a full week of work. Use the highlights list for a quick recap."
    )

    if by_day:
        ticket = storage.get_ticket_settings()
        tp_items = []
        plain_lines = []
        for day, items in by_day:
            for e in items:
                cat = (
                    f'<span class="badge cat">{esc(e["category"])}</span>'
                    if e.get("category") and e["category"] != "General"
                    else ""
                )
                tags = render_tag_chips(e.get("tags") or "", ticket=ticket)
                tp_items.append(
                    f'<li><span class="tp-date">{esc(day)}</span>'
                    f'<span class="tp-title">{render_plain_with_tickets(e["title"], ticket=ticket)}</span>{cat}{tags}</li>'
                )
                plain_lines.append(f"- {day}: {e['title']}" + (f" [{e['tags']}]" if e.get("tags") else ""))
        talking = f"""
  <section class="card no-print-actions">
    <div class="card-head">
      <h2>Highlights</h2>
      <div class="week-actions">
        <button type="button" class="btn btn-primary btn-sm" id="copy-talking-points"
          data-text="{esc(chr(10).join(plain_lines))}">Copy list</button>
        <a class="btn btn-ghost btn-sm" href="/week?week={start.isoformat()}&print=1" target="_blank">Print view</a>
      </div>
    </div>
    <ol class="talking-points" id="talking-points-list">{"".join(tp_items)}</ol>
    <textarea id="talking-points-raw" class="visually-hidden" readonly>{esc(storage.talking_points_text(start.isoformat(), end.isoformat()))}</textarea>
  </section>"""
        day_blocks = []
        for day, items in by_day:
            n = len(items)
            entries_html = "\n".join(
                render_entry(e, editable=writable and not print_mode, ticket=ticket)
                for e in items
            )
            day_blocks.append(f"""
  <section class="day-block">
    <h2 class="day-heading"><time datetime="{esc(day)}">{esc(day)}</time>
      <span class="muted">{n} item{"s" if n != 1 else ""}</span></h2>
    <div class="entry-list">{entries_html}</div>
  </section>""")
        content = talking + "\n".join(day_blocks)
    else:
        content = '<section class="card empty-state"><h3>No work this week</h3></section>'

    body_class = "print-page" if print_mode else ""
    body = f"""
<section class="page-header no-print-actions">
  <div>
    <h1>Weekly summary</h1>
    <p class="lede">{mon_note}</p>
  </div>
</section>
<section class="card week-toolbar no-print-actions">
  <a class="btn btn-ghost btn-sm" href="/week?week={prev_start}">Previous</a>
  <div class="week-range">
    <strong>{start.isoformat()}</strong> <span class="muted">to</span> <strong>{end.isoformat()}</strong>
    <span class="badge">{len(week_entries)}</span>
  </div>
  <div class="week-actions">
    <a class="btn btn-ghost btn-sm" href="/week?which=this">This week</a>
    <a class="btn btn-ghost btn-sm" href="/week?which=last">Last week</a>
    <a class="btn btn-ghost btn-sm" href="/week?week={next_start}">Next</a>
  </div>
</section>
{content}
{edit_modal_html() if writable and not print_mode else ""}
"""
    if print_mode:
        body += """
<script>window.addEventListener('load', function(){ setTimeout(function(){ window.print(); }, 300); });</script>
"""
    return layout(
        "Weekly summary · Daily Work Log",
        body,
        active="week",
        user=user,
        csrf_token=csrf_token,
        body_class=body_class,
    )



