"""HTTP request/response types and cookie helpers. No callback bags."""

from __future__ import annotations

import hmac
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import auth


class Auth(str, Enum):
    NONE = "none"
    USER = "user"
    WRITE = "write"
    ADMIN = "admin"


class Errors(str, Enum):
    AUTO = "auto"
    JSON = "json"
    LOGIN_HTML = "login_html"


def secrets_compare(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
    except Exception:
        return False


def cookie_header(
    name: str,
    value: str,
    *,
    max_age: int,
    httponly: bool = True,
    secure: bool = False,
) -> str:
    if httponly:
        flags = f"Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"
    else:
        flags = f"Path=/; SameSite=Lax; Max-Age={max_age}"
    if secure:
        flags += "; Secure"
    return f"{name}={value}; {flags}"


def session_cookie(token: str, *, secure: bool) -> str:
    return cookie_header(
        auth.COOKIE_NAME, token, max_age=auth.SESSION_TTL_SEC, httponly=True, secure=secure
    )


def csrf_cookie(token: str, *, secure: bool) -> str:
    return cookie_header(
        auth.CSRF_COOKIE, token, max_age=auth.SESSION_TTL_SEC, httponly=False, secure=secure
    )


def clear_session_cookie() -> str:
    return f"{auth.COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def clear_csrf_cookie() -> str:
    return f"{auth.CSRF_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0"


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: Any
    body: dict[str, Any]
    user: str | None
    csrf: str
    client_key: str
    cookies: dict[str, str] = field(default_factory=dict)
    secure: bool = False
    params: dict[str, str] = field(default_factory=dict)

    def q(self, name: str, default: str | None = None) -> str | None:
        vals = self.query.get(name)
        if not vals:
            return default
        return vals[0]

    def wants_json(self) -> bool:
        accept = (self.headers.get("Accept") or "").lower()
        if "application/json" in accept or "application/json" in self.content_type():
            return True
        if "text/html" in accept:
            return False
        return self.path.startswith("/api/")

    def content_type(self) -> str:
        return (self.headers.get("Content-Type") or "").lower()

    def csrf_ok(self) -> bool:
        cookie_tok = self.cookies.get(auth.CSRF_COOKIE) or ""
        if not cookie_tok:
            return False
        candidate = (self.headers.get("X-CSRF-Token") or "") or (
            (self.body or {}).get("csrf_token") or ""
        )
        return bool(candidate) and secrets_compare(cookie_tok, candidate)


@dataclass
class Response:
    status: int = 200
    body: bytes = b""
    content_type: str = "text/plain; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)
    cookies: list[str] = field(default_factory=list)

    def add_cookies(self, *items: str | None) -> Response:
        for item in items:
            if item:
                self.cookies.append(item)
        return self

    @classmethod
    def html(cls, status: int, html: str) -> Response:
        return cls(status=status, body=html.encode("utf-8"), content_type="text/html; charset=utf-8")

    @classmethod
    def json(cls, status: int, obj: dict) -> Response:
        return cls(
            status=status,
            body=json.dumps(obj, ensure_ascii=False).encode("utf-8"),
            content_type="application/json; charset=utf-8",
        )

    @classmethod
    def redirect(cls, location: str, cookies: list[str] | None = None) -> Response:
        return cls(
            status=302,
            body=b"",
            content_type="text/plain",
            headers={"Location": location},
            cookies=list(cookies or []),
        )

    @classmethod
    def file(
        cls,
        path: Path,
        *,
        as_attachment: bool = False,
        download_name: str | None = None,
        cache: str | None = None,
    ) -> Response:
        if not path.is_file():
            return cls.json(404, {"ok": False, "error": "Not found"})
        suffix = path.suffix.lower()
        ctype = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".html": "text/html; charset=utf-8",
        }.get(suffix, "application/octet-stream")
        headers: dict[str, str] = {}
        if as_attachment:
            headers["Content-Disposition"] = (
                f'attachment; filename="{download_name or path.name}"'
            )
        if cache:
            headers["Cache-Control"] = cache
        return cls(status=200, body=path.read_bytes(), content_type=ctype, headers=headers)

    @classmethod
    def empty(cls, status: int = 200) -> Response:
        return cls(status=status, body=b"", content_type="text/plain")


@dataclass(frozen=True)
class Route:
    """Route metadata consumed by a single dispatch middleware."""

    method: str
    match: str | re.Pattern[str]
    handler: Callable[[Request], Response]
    auth: Auth = Auth.USER
    csrf: bool = False
    allow_stale_password: bool = False
    errors: Errors = Errors.AUTO


def parse_query(path_with_query: str) -> tuple[str, dict[str, list[str]]]:
    parsed = urlparse(path_with_query)
    return parsed.path, parse_qs(parsed.query)
