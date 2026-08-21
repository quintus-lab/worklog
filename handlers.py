"""HTTP action handlers. Return Response; guards live in dispatch middleware."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

import auth
import storage
from pages import (
    layout,
    page_history,
    page_index,
    page_login,
    page_settings,
    page_week,
    safe_next_url,
)
from web import (
    Auth,
    Errors,
    Request,
    Response,
    Route,
    clear_csrf_cookie,
    clear_session_cookie,
    csrf_cookie,
    session_cookie,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
ENTRY_ID_RE = re.compile(r"^/api/entries/(?P<id>[0-9a-fA-F-]{36})$")


def _unauth(req: Request) -> Response:
    if req.wants_json():
        return Response.json(401, {"ok": False, "error": "Sign in required"})
    nxt = quote(safe_next_url(req.path))
    return Response.redirect(f"/login?next={nxt}")


def _forbidden_admin(req: Request) -> Response:
    if req.wants_json():
        return Response.json(403, {"ok": False, "error": "Admin access required"})
    return Response.html(
        403,
        layout(
            "Forbidden",
            '<div class="card empty-state"><h1>403</h1>'
            "<p>Admin access required.</p>"
            '<a class="btn btn-primary" href="/">Back</a></div>',
            user=req.user,
            csrf_token=req.csrf,
        ),
    )


def _stale_password(req: Request) -> Response:
    if req.wants_json():
        return Response.json(
            403,
            {
                "ok": False,
                "error": "Password change required",
                "must_change_password": True,
            },
        )
    return Response.redirect("/settings")


def _csrf_fail(req: Request, route: Route) -> Response:
    if route.errors is Errors.LOGIN_HTML and "application/json" not in req.content_type():
        return Response.html(
            403,
            page_login(error="Session expired. Please try again.", csrf_token=req.csrf),
        )
    return Response.json(403, {"ok": False, "error": "CSRF validation failed"})


def apply_guards(req: Request, route: Route) -> Response | None:
    if route.auth is not Auth.NONE:
        if not req.user:
            return _unauth(req)
        if route.auth is Auth.ADMIN and not auth.is_admin(req.user):
            return _forbidden_admin(req)
        if route.auth is Auth.WRITE and not auth.can_write(req.user):
            return Response.json(403, {"ok": False, "error": "Viewer accounts are read-only"})
        if not route.allow_stale_password and auth.user_must_change_password(req.user):
            return _stale_password(req)
    if route.csrf and not req.csrf_ok():
        return _csrf_fail(req, route)
    return None


def health(_req: Request) -> Response:
    return Response.json(200, {"ok": True, **storage.stats()})


def head_root(_req: Request) -> Response:
    return Response.empty(200)


def static_file(req: Request) -> Response:
    rel = req.path[len("/static/") :]
    if ".." in rel or rel.startswith("/") or "\\" in rel:
        return Response.json(404, {"ok": False, "error": "Not found"})
    target = (STATIC_DIR / rel).resolve()
    try:
        target.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return Response.json(404, {"ok": False, "error": "Not found"})
    return Response.file(target, cache="public, max-age=3600")


def login_page(req: Request) -> Response:
    if req.user:
        dest = "/settings" if auth.user_must_change_password(req.user) else "/"
        return Response.redirect(dest)
    next_url = safe_next_url(req.q("next", "/"))
    return Response.html(200, page_login(next_url=next_url or "/", csrf_token=req.csrf))


def logout(_req: Request) -> Response:
    return Response.redirect("/login", cookies=[clear_session_cookie(), clear_csrf_cookie()])


def home(req: Request) -> Response:
    return Response.html(200, page_index(req.user or "", req.query, csrf_token=req.csrf))


def week(req: Request) -> Response:
    return Response.html(200, page_week(req.user or "", req.query, csrf_token=req.csrf))


def history(req: Request) -> Response:
    return Response.html(200, page_history(req.user or "", req.query, csrf_token=req.csrf))


def settings(req: Request) -> Response:
    user = req.user or ""
    return Response.html(
        200,
        page_settings(
            user,
            csrf_token=req.csrf,
            force_password=auth.user_must_change_password(user),
        ),
    )


def download_excel(_req: Request) -> Response:
    try:
        storage.export_excel(storage.EXCEL_PATH)
    except storage.StorageError as exc:
        return Response.json(503, {"ok": False, "error": str(exc)})
    return Response.file(
        storage.EXCEL_PATH, as_attachment=True, download_name="work_log.xlsx"
    )


def not_found(req: Request) -> Response:
    if req.user:
        return Response.html(
            404,
            layout(
                "Not found",
                '<div class="card empty-state"><h1>404</h1>'
                '<a class="btn btn-primary" href="/">Home</a></div>',
                user=req.user,
                csrf_token=req.csrf,
            ),
        )
    return Response.json(404, {"ok": False, "error": "Not found"})


def api_me(req: Request) -> Response:
    user = req.user or ""
    return Response.json(
        200,
        {
            "ok": True,
            "username": user,
            "display_name": auth.display_name_for(user),
            "role": auth.get_role(user),
            "can_write": auth.can_write(user),
            "must_change_password": auth.user_must_change_password(user),
        },
    )


def api_entries_list(req: Request) -> Response:
    q = req.q("q")
    start = req.q("start")
    end = req.q("end")
    status = req.q("status")
    try:
        limit = int(req.q("limit", "200") or "200")
    except ValueError:
        limit = 200
    limit = min(max(limit, 1), 500)
    try:
        offset = int(req.q("offset", "0") or "0")
    except ValueError:
        offset = 0
    offset = max(offset, 0)
    entries = storage.load_entries(
        start=start, end=end, q=q, status=status, limit=limit, offset=offset
    )
    return Response.json(
        200,
        {
            "entries": entries,
            "count": len(entries),
            "total": storage.count_entries(start=start, end=end, q=q, status=status),
        },
    )


def api_talking_points(req: Request) -> Response:
    start = req.q("start") or ""
    end = req.q("end") or ""
    if not start or not end:
        return Response.json(400, {"ok": False, "error": "start and end required"})
    return Response.json(200, {"ok": True, "text": storage.talking_points_text(start, end)})


def api_backups_list(_req: Request) -> Response:
    return Response.json(200, {"ok": True, "backups": storage.list_backups()})


def api_login(req: Request) -> Response:
    data = req.body
    json_req = "application/json" in req.content_type()
    allowed, wait = auth.login_allowed(req.client_key)
    if not allowed:
        msg = f"Too many failed attempts. Try again in {wait}s."
        if json_req:
            return Response.json(429, {"ok": False, "error": msg})
        return Response.html(429, page_login(error=msg, csrf_token=req.csrf))

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    next_url = safe_next_url(data.get("next") or "/")
    rec = auth.authenticate(username, password)
    if not rec:
        auth.record_login_failure(req.client_key)
        msg = "Invalid username or password"
        if json_req:
            return Response.json(401, {"ok": False, "error": msg})
        return Response.html(
            401,
            page_login(error=msg, next_url=next_url or "/", csrf_token=req.csrf),
        )

    auth.clear_login_failures(req.client_key)
    token = auth.create_session_token(username)
    new_csrf = auth.new_csrf_token()
    cookies = [
        session_cookie(token, secure=req.secure),
        csrf_cookie(new_csrf, secure=req.secure),
    ]
    if auth.user_must_change_password(username):
        next_url = "/settings"
    if json_req:
        return Response.json(
            200,
            {
                "ok": True,
                "username": username,
                "role": auth.get_role(username),
                "must_change_password": auth.user_must_change_password(username),
            },
        ).add_cookies(*cookies)
    return Response.redirect(next_url or "/", cookies=cookies)


def api_change_password(req: Request) -> Response:
    data = req.body
    try:
        if (data.get("new_password") or "") != (
            data.get("confirm_password") or data.get("new_password") or ""
        ):
            raise ValueError("New passwords do not match")
        auth.change_password(
            req.user or "",
            data.get("current_password") or "",
            data.get("new_password") or "",
        )
    except ValueError as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(200, {"ok": True, "relogin": True}).add_cookies(
        clear_session_cookie(),
        csrf_cookie(auth.new_csrf_token(), secure=req.secure),
    )


def api_rename_user(req: Request) -> Response:
    data = req.body
    new_username = (data.get("new_username") or "").strip()
    display_name = (data.get("display_name") or "").strip() or None
    try:
        auth.rename_user(req.user or "", new_username, display_name=display_name)
    except (KeyError, ValueError) as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(
        200, {"ok": True, "username": new_username, "relogin": True}
    ).add_cookies(
        clear_session_cookie(),
        csrf_cookie(auth.new_csrf_token(), secure=req.secure),
    )


def api_users(req: Request) -> Response:
    data = req.body
    action = (data.get("action") or "create").strip()
    try:
        if action == "create":
            uname = (data.get("username") or "").strip()
            err = auth.validate_username(uname)
            if err:
                raise ValueError(err)
            if auth.get_user_record(uname):
                raise ValueError("Username already exists")
            auth.set_user_password(
                uname,
                data.get("password") or "",
                display_name=(data.get("display_name") or uname).strip(),
                create_if_missing=True,
                enforce_strength=True,
                role=data.get("role") or "viewer",
            )
        elif action == "update":
            uname = (data.get("username") or "").strip()
            if not auth.get_user_record(uname):
                raise KeyError("User not found")
            pw = data.get("password")
            if pw == "":
                pw = None
            role = data.get("role") or None
            if role == "":
                role = None
            auth.set_user_password(
                uname,
                pw,
                display_name=(data.get("display_name") or None),
                create_if_missing=False,
                enforce_strength=bool(pw),
                role=role,
            )
        else:
            raise ValueError("Unknown action")
    except (KeyError, ValueError) as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(200, {"ok": True, "users": auth.list_users()})


def api_backup(_req: Request) -> Response:
    paths = storage.create_backup(reason="manual")
    return Response.json(200, {"ok": True, "backup": paths, "backups": storage.list_backups()})


def api_restore(req: Request) -> Response:
    name = (req.body.get("name") or "").strip()
    try:
        storage.restore_backup(name)
    except (ValueError, FileNotFoundError) as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(200, {"ok": True})



def api_ticket_settings_get(_req: Request) -> Response:
    return Response.json(200, {"ok": True, **storage.get_ticket_settings()})


def api_ticket_settings_save(req: Request) -> Response:
    data = req.body or {}
    try:
        cfg = storage.save_ticket_settings(
            data.get("url") or "",
            data.get("prefixes") or data.get("pattern") or "",
        )
    except ValueError as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(200, {"ok": True, **cfg})


def api_entries_create(req: Request) -> Response:
    data = req.body
    try:
        entry = storage.create_entry(
            {
                "date": data.get("date"),
                "title": data.get("title"),
                "details": data.get("details"),
                "category": data.get("category"),
                "status": data.get("status"),
                "tags": data.get("tags"),
                "follow_up": data.get("follow_up"),
                "owner": req.user,
            }
        )
    except ValueError as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(200, {"ok": True, "entry": entry})


def api_entries_update(req: Request) -> Response:
    try:
        entry = storage.update_entry(req.params.get("id") or "", req.body)
    except KeyError:
        return Response.json(404, {"ok": False, "error": "Not found"})
    except ValueError as exc:
        return Response.json(400, {"ok": False, "error": str(exc)})
    return Response.json(200, {"ok": True, "entry": entry})


def api_entries_delete(req: Request) -> Response:
    try:
        storage.delete_entry(req.params.get("id") or "")
    except KeyError:
        return Response.json(404, {"ok": False, "error": "Not found"})
    return Response.json(200, {"ok": True})


ROUTES: list[Route] = [
    Route("GET", "/health", health, auth=Auth.NONE),
    Route("HEAD", "/health", health, auth=Auth.NONE),
    Route("HEAD", "/", head_root, auth=Auth.NONE),
    Route("GET", "/login", login_page, auth=Auth.NONE),
    Route("GET", "/logout", logout, auth=Auth.NONE, allow_stale_password=True),
    Route("GET", "/", home),
    Route("GET", "/week", week),
    Route("GET", "/history", history),
    Route("GET", "/settings", settings, allow_stale_password=True),
    Route("GET", "/download", download_excel),
    Route("GET", "/api/me", api_me, allow_stale_password=True),
    Route("GET", "/api/entries", api_entries_list),
    Route("GET", "/api/talking-points", api_talking_points),
    Route("GET", "/api/backups", api_backups_list, auth=Auth.ADMIN),
    Route("POST", "/api/login", api_login, auth=Auth.NONE, csrf=True, errors=Errors.LOGIN_HTML),
    Route("POST", "/api/change-password", api_change_password, csrf=True, allow_stale_password=True),
    Route("POST", "/api/rename-user", api_rename_user, auth=Auth.ADMIN, csrf=True),
    Route("POST", "/api/users", api_users, auth=Auth.ADMIN, csrf=True),
    Route("GET", "/api/ticket-settings", api_ticket_settings_get),
    Route("POST", "/api/ticket-settings", api_ticket_settings_save, auth=Auth.ADMIN, csrf=True),
    Route("POST", "/api/backup", api_backup, auth=Auth.ADMIN, csrf=True),
    Route("POST", "/api/restore", api_restore, auth=Auth.ADMIN, csrf=True),
    Route("POST", "/api/entries", api_entries_create, auth=Auth.WRITE, csrf=True),
    Route("PUT", ENTRY_ID_RE, api_entries_update, auth=Auth.WRITE, csrf=True),
    Route("PATCH", ENTRY_ID_RE, api_entries_update, auth=Auth.WRITE, csrf=True),
    Route("DELETE", ENTRY_ID_RE, api_entries_delete, auth=Auth.WRITE, csrf=True),
]


def match_route(method: str, path: str) -> tuple[Route, dict[str, str]] | None:
    for route in ROUTES:
        if route.method != method:
            continue
        if isinstance(route.match, str):
            if route.match == path:
                return route, {}
            continue
        m = route.match.match(path)
        if m:
            return route, m.groupdict()
    return None


def dispatch(req: Request) -> Response:
    if req.path.startswith("/static/") and req.method in ("GET", "HEAD"):
        return static_file(req)
    found = match_route(req.method, req.path)
    if found is None:
        return not_found(req)
    route, params = found
    req.params = params
    blocked = apply_guards(req, route)
    if blocked is not None:
        return blocked
    return route.handler(req)
