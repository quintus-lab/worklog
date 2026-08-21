"""Page shell / layout."""
from __future__ import annotations

import auth

from pages.common import esc

def layout(
    title: str,
    body: str,
    *,
    active: str = "",
    user: str | None = None,
    body_class: str = "",
    csrf_token: str = "",
    force_password: bool = False,
    search_q: str = "",
) -> str:
    def nav_cls(name: str) -> str:
        return ' class="nav-link active"' if active == name else ' class="nav-link"'

    user_block = ""
    nav = ""
    banners = ""
    if user:
        dn = esc(auth.display_name_for(user))
        role = auth.get_role(user)
        writable = auth.can_write(user)
        user_block = f"""
          <span class="user-chip" title="{esc(user)} ({esc(role)})">
            <span class="user-avatar" aria-hidden="true">{esc((dn or user)[:1].upper())}</span>
            <span class="user-name">{dn}</span>
            <span class="badge role role-{esc(role)}">{esc(role)}</span>
          </span>
          <a href="/settings"{nav_cls("settings")}>Account</a>
          <a class="nav-link" href="/logout">Sign out</a>"""
        if not force_password:
            log_label = "Log work" if writable else "Work log"
            nav = f"""
        <nav class="nav" aria-label="Main">
          <a href="/"{nav_cls("log")}>{log_label}</a>
          <a href="/week"{nav_cls("week")}>Weekly summary</a>
          <a href="/history"{nav_cls("history")}>History</a>
          <a href="/download" class="nav-link nav-secondary">Download Excel</a>
          <form class="nav-search" method="get" action="/" role="search">
            <label class="visually-hidden" for="nav-q">Search log</label>
            <input type="search" id="nav-q" name="q" value="{esc(search_q)}"
              placeholder="Search log…" maxlength="200" />
            <button type="submit" class="btn btn-ghost btn-sm">Search</button>
          </form>
        </nav>"""
        if force_password:
            banners += """
  <div class="security-banner security-banner-strong" role="alert">
    <strong>Action required:</strong> Change the default password before continuing.
  </div>"""
        elif auth.user_must_change_password(user):
            banners += """
  <div class="security-banner" role="status">
    <strong>Security:</strong> You are still using a default password.
    <a href="/settings">Change it now</a>.
  </div>"""
        elif auth.uses_default_password() and auth.is_admin(user):
            banners += """
  <div class="security-banner" role="status">
    <strong>Security:</strong> Some accounts still use the default password.
    Update them under Account > Users.
  </div>"""

    prefs_boot = """
  <script src="/static/prefs.js"></script>
  <script>WorklogPrefs.boot();</script>"""
    csrf_meta = (
        f'<meta name="csrf-token" content="{esc(csrf_token)}" />' if csrf_token else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="paper">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  <meta name="theme-color" content="#f5f4ed" />
  <meta name="description" content="Private daily work log with weekly summary." />
  <meta name="referrer" content="same-origin" />
  {csrf_meta}
  <title>{esc(title)}</title>
  {prefs_boot}
  <link rel="stylesheet" href="/static/style.css" />
  <link rel="stylesheet" href="/static/entries.css" />
  <link rel="stylesheet" href="/static/print.css" />
</head>
<body class="{esc(body_class)}">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="topbar">
    <div class="brand">
      <span class="logo" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect x="3" y="4" width="18" height="17" rx="3" stroke="currentColor" stroke-width="1.6"/><path d="M3 9h18M8 2.5v3M16 2.5v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M8 13h3M8 16h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      </span>
      <div class="brand-text">
        <strong>Daily Work Log</strong>
        <span class="tagline">Local log and Excel export</span>
      </div>
    </div>
    {nav}
    <div class="topbar-actions">
      <button type="button" id="theme-toggle" class="btn btn-ghost btn-sm theme-toggle"
        aria-label="Paper (click to change)" title="Paper">
        <span class="theme-icon theme-icon-moon" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z"/></svg></span>
        <span class="theme-icon theme-icon-paper" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 3.5h7.5L20 9v11.5H7z"/><path d="M14.5 3.5V9H20"/></svg></span>
        <span class="theme-label" id="theme-toggle-label">Paper</span>
      </button>
      <button type="button" id="font-toggle" class="btn btn-ghost btn-sm font-toggle"
        aria-label="Change text size" title="Text size">
        <span class="font-mark" aria-hidden="true">A</span>
        <span class="theme-label" id="font-toggle-label">Md</span>
      </button>
      {user_block}
    </div>
  </header>
  {banners}
  <main id="main" class="container">
{body}
  </main>
  <footer class="footer">
    <span>Data: <code>data/worklog.db</code> | Excel: <code>data/work_log.xlsx</code> | Backups: <code>data/backups/</code></span>
  </footer>
  <div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
  <script src="/static/app.js"></script>
</body>
</html>
"""



