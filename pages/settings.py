"""page_settings page."""
from __future__ import annotations

import auth
import storage

from pages.common import esc
from pages.layout import layout


def page_settings(
    user: str,
    *,
    csrf_token: str = "",
    error: str = "",
    success: str = "",
    force_password: bool = False,
) -> str:
    err = f'<div class="alert alert-error" role="alert">{esc(error)}</div>' if error else ""
    ok = f'<div class="alert alert-ok" role="status">{esc(success)}</div>' if success else ""
    dn = esc(auth.display_name_for(user))
    role = auth.get_role(user)
    is_admin = auth.is_admin(user)
    backups = storage.list_backups() if is_admin else []
    st = storage.stats()

    rename_card = ""
    users_card = ""
    backup_card = ""
    ticket_cfg = storage.get_ticket_settings()
    ticket_url = esc(ticket_cfg.get("url") or "")
    ticket_prefixes = esc(ticket_cfg.get("prefixes") or "")
    ticket_defaults = esc(ticket_cfg.get("default_prefixes") or "INC,CHG,PRB")
    ticket_ro = " readonly disabled" if (not is_admin or force_password) else ""
    ticket_actions = ""
    if is_admin and not force_password:
        ticket_actions = """
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="ticket-submit">Save ticket system</button>
      <span id="ticket-status" class="form-status" aria-live="polite"></span>
    </div>"""
    ticket_card = f"""
<section class="card" aria-labelledby="ticket-heading">
  <div class="card-head"><h2 id="ticket-heading">Ticket system</h2></div>
  <p class="muted small">When a URL is set, ticket IDs typed in the <strong>Tags</strong> field become
  links (opens in a new tab). Numbers in title or details are not linked. Matches INC/CHG-style
  prefixes, Jira <code>KEY-123</code>, and 6-12 digit IDs such as <code>1234567</code>.
  Put <code>{{ticket}}</code> where the ID goes, for example
  <code>https://jira.example.com/browse/{{ticket}}</code>.</p>
  <form id="ticket-form" class="stack">
    <label class="field"><span class="field-label">Ticket URL</span>
      <input type="text" id="ticket-url" value="{ticket_url}" maxlength="500"
        placeholder="https://jira.example.com/browse/{{ticket}}"{ticket_ro} /></label>
    <label class="field"><span class="field-label">Extra prefixes <span class="field-hint">optional</span></span>
      <input type="text" id="ticket-prefixes" value="{ticket_prefixes}" maxlength="200"
        placeholder="{ticket_defaults}" spellcheck="false"{ticket_ro} />
      <span class="field-hint">Comma-separated, e.g. <code>INC,CHG,NET</code>. Blank uses
      <code>{ticket_defaults}</code>. Jira-style <code>KEY-123</code> and 6-12 digit numbers are always recognized. Matching is case-insensitive.</span></label>
    {ticket_actions}
  </form>
</section>
"""
    if is_admin and not force_password:
        rename_card = f"""
<section class="card" aria-labelledby="rename-heading">
  <div class="card-head"><h2 id="rename-heading">Change my username</h2></div>
  <form id="rename-form" class="stack" autocomplete="off">
    <label class="field"><span class="field-label">Current</span>
      <input type="text" value="{esc(user)}" disabled /></label>
    <label class="field"><span class="field-label">New username</span>
      <input type="text" id="new-username" required maxlength="64" pattern="[A-Za-z0-9._\\-]+" spellcheck="false" /></label>
    <label class="field"><span class="field-label">Display name</span>
      <input type="text" id="new-display-name" maxlength="80" placeholder="{dn}" /></label>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="rename-submit">Rename login</button>
      <span id="rename-status" class="form-status" aria-live="polite"></span>
    </div>
  </form>
</section>
"""
        user_rows = "".join(
            f'<tr data-username="{esc(u["username"])}">'
            f'<td><code>{esc(u["username"])}</code></td>'
            f'<td>{esc(u["display_name"])}</td>'
            f'<td><span class="badge role role-{esc(u["role"])}">{esc(u["role"])}</span></td>'
            f"</tr>"
            for u in auth.list_users()
        )
        users_card = f"""
<section class="card" aria-labelledby="users-heading">
  <div class="card-head"><h2 id="users-heading">Users</h2></div>
  <table class="data-table">
    <thead><tr><th>Username</th><th>Display</th><th>Role</th></tr></thead>
    <tbody>{user_rows}</tbody>
  </table>
  <h3 class="subhead">Create user</h3>
  <form id="create-user-form" class="stack">
    <div class="grid-3">
      <label class="field"><span class="field-label">Username</span>
        <input type="text" id="cu-username" required maxlength="64" pattern="[A-Za-z0-9._\\-]+" /></label>
      <label class="field"><span class="field-label">Role</span>
        <select id="cu-role"><option value="viewer">viewer</option><option value="admin">admin</option></select></label>
      <label class="field"><span class="field-label">Password</span>
        <input type="password" id="cu-password" required minlength="{auth.MIN_PASSWORD_LEN}" /></label>
    </div>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="cu-submit">Create user</button>
      <span id="cu-status" class="form-status" aria-live="polite"></span>
    </div>
  </form>
  <h3 class="subhead">Reset user password / role</h3>
  <form id="admin-user-form" class="stack">
    <div class="grid-3">
      <label class="field"><span class="field-label">Username</span>
        <input type="text" id="au-username" required maxlength="64" /></label>
      <label class="field"><span class="field-label">New role</span>
        <select id="au-role">
          <option value="">(keep)</option>
          <option value="admin">admin</option>
          <option value="viewer">viewer</option>
        </select></label>
      <label class="field"><span class="field-label">New password</span>
        <input type="password" id="au-password" minlength="{auth.MIN_PASSWORD_LEN}" placeholder="leave blank to keep" /></label>
    </div>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="au-submit">Update user</button>
      <span id="au-status" class="form-status" aria-live="polite"></span>
    </div>
  </form>
</section>
"""
        b_rows = "".join(
            f'<tr><td><code>{esc(b["name"])}</code></td><td>{esc(b["mtime"])}</td>'
            f'<td>{b["size"] // 1024} KB</td>'
            f'<td><button type="button" class="btn btn-ghost btn-sm restore-btn" data-name="{esc(b["name"])}">Restore</button></td></tr>'
            for b in backups
        ) or '<tr><td colspan="4" class="muted">No backups yet</td></tr>'
        backup_card = f"""
<section class="card" aria-labelledby="backup-heading">
  <div class="card-head">
    <h2 id="backup-heading">Backups &amp; Excel</h2>
    <button type="button" class="btn btn-primary btn-sm" id="backup-now-btn">Backup now</button>
  </div>
  <p class="muted small">SQLite is the source of truth. Excel is refreshed on each change and included in backups.
  Restore reloads the database (a pre-restore backup is taken first).</p>
  <dl class="detail-list">
    <div><dt>Entries</dt><dd>{st["total_entries"]}</dd></div>
    <div><dt>Database</dt><dd><code>data/worklog.db</code></dd></div>
    <div><dt>Excel mirror</dt><dd><code>data/work_log.xlsx</code> {"yes" if st["excel_exists"] else "(not written yet)"}</dd></div>
  </dl>
  <table class="data-table">
    <thead><tr><th>Backup</th><th>When</th><th>Size</th><th></th></tr></thead>
    <tbody id="backup-tbody">{b_rows}</tbody>
  </table>
  <span id="backup-status" class="form-status" aria-live="polite"></span>
</section>
"""

    body = f"""
<section class="page-header">
  <div>
    <h1>Account</h1>
    <p class="lede">{"Change your default password to unlock the app." if force_password else "Security, users, ticket links, and restore points."}</p>
  </div>
</section>
<section class="card">
  <div class="card-head"><h2>Profile</h2></div>
  <dl class="detail-list">
    <div><dt>Username</dt><dd><code>{esc(user)}</code></dd></div>
    <div><dt>Display name</dt><dd>{dn}</dd></div>
    <div><dt>Role</dt><dd><span class="badge role role-{esc(role)}">{esc(role)}</span></dd></div>
  </dl>
</section>
<section class="card" aria-labelledby="pw-heading">
  <div class="card-head"><h2 id="pw-heading">Change password</h2></div>
  {err}{ok}
  <form id="password-form" class="stack" autocomplete="off">
    <label class="field"><span class="field-label">Current password</span>
      <input type="password" id="current_password" required autocomplete="current-password" /></label>
    <label class="field"><span class="field-label">New password</span>
      <input type="password" id="new_password" required minlength="{auth.MIN_PASSWORD_LEN}" autocomplete="new-password" />
      <span class="field-hint">At least {auth.MIN_PASSWORD_LEN} characters; not a common password.</span></label>
    <label class="field"><span class="field-label">Confirm new password</span>
      <input type="password" id="confirm_password" required minlength="{auth.MIN_PASSWORD_LEN}" autocomplete="new-password" /></label>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="pw-submit">Update password</button>
      <span id="pw-status" class="form-status" aria-live="polite"></span>
    </div>
  </form>
</section>
{ticket_card}
{rename_card}
{users_card}
{backup_card}
"""
    return layout(
        "Account · Daily Work Log",
        body,
        active="settings",
        user=user,
        csrf_token=csrf_token,
        force_password=force_password,
    )


