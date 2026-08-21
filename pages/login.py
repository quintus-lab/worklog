"""page_login page."""
from __future__ import annotations

import auth

from pages.common import esc, safe_next_url
from pages.layout import layout


def page_login(error: str = "", next_url: str = "/", *, csrf_token: str = "") -> str:
    err = f'<div class="alert alert-error" role="alert">{esc(error)}</div>' if error else ""
    if auth.uses_default_password():
        hint = (
            '<p class="auth-hint muted">First-run defaults still active for some accounts '
            "(e.g. <code>admin</code>/<code>viewer</code> with <code>changeme</code>). "
            "You will be asked to change it after sign-in.</p>"
        )
    else:
        hint = '<p class="auth-hint muted">Protected work log.</p>'
    body = f"""
<section class="auth-shell">
  <div class="card auth-card">
    <div class="auth-header">
      <h1>Sign in</h1>
      <p class="muted">Your work log is private. Sign in to continue.</p>
    </div>
    {err}
    <form method="post" action="/api/login" class="stack" autocomplete="on">
      <input type="hidden" name="next" value="{esc(safe_next_url(next_url))}" />
      <input type="hidden" name="csrf_token" value="{esc(csrf_token)}" />
      <label class="field"><span class="field-label">Username</span>
        <input type="text" name="username" required autofocus autocomplete="username" maxlength="64" spellcheck="false" /></label>
      <label class="field"><span class="field-label">Password</span>
        <input type="password" name="password" required autocomplete="current-password" maxlength="128" /></label>
      <button type="submit" class="btn btn-primary btn-block">Sign in</button>
    </form>
    {hint}
  </div>
</section>
"""
    return layout("Sign in · Daily Work Log", body, body_class="auth-page", csrf_token=csrf_token)



