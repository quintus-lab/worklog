"""HTTP server: parse request, dispatch, serialize Response."""

from __future__ import annotations

import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

import auth
import handlers
import storage
from web import Request, Response, csrf_cookie, parse_query

MAX_BODY_BYTES = 256 * 1024


class PayloadTooLarge(ValueError):
    pass


class Handler(BaseHTTPRequestHandler):
    server_version = "WorkLog/3.2"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def _parse_cookies(self) -> dict[str, str]:
        raw = self.headers.get("Cookie") or ""
        c = SimpleCookie()
        try:
            c.load(raw)
        except Exception:
            return {}
        return {k: m.value for k, m in c.items()}

    def _secure_cookie(self) -> bool:
        if os.environ.get("WORKLOG_SECURE_COOKIES", "").lower() in ("1", "true", "yes"):
            return True
        proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        return proto == "https"

    def client_key(self) -> str:
        xff = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return xff or (self.client_address[0] if self.client_address else "unknown")

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return b""
        if length > MAX_BODY_BYTES:
            raise PayloadTooLarge("payload_too_large")
        return self.rfile.read(length)

    def read_json_or_form(self) -> dict[str, Any]:
        ctype = (self.headers.get("Content-Type") or "").lower()
        raw = self.read_body()
        if not raw:
            return {}
        if "application/json" in ctype:
            try:
                data = json.loads(raw.decode("utf-8"))
                return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}
        qs = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
        return {k: (v[0] if v else "") for k, v in qs.items()}

    def security_headers(self) -> dict[str, str]:
        csp = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Content-Security-Policy": csp,
            "Cache-Control": "no-store",
        }

    def write_response(self, resp: Response) -> None:
        self.send_response(resp.status)
        self.send_header("Content-Type", resp.content_type)
        self.send_header("Content-Length", str(len(resp.body)))
        extra = dict(resp.headers)
        for k, v in self.security_headers().items():
            if k in extra:
                continue
            self.send_header(k, v)
        for k, v in extra.items():
            if k.lower() == "set-cookie":
                continue
            self.send_header(k, v)
        for item in resp.cookies:
            self.send_header("Set-Cookie", item)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(resp.body)

    def build_request(self, method: str) -> tuple[Request, str | None]:
        path, query = parse_query(self.path)
        cookies = self._parse_cookies()
        csrf = cookies.get(auth.CSRF_COOKIE) or ""
        new_csrf: str | None = None
        if not csrf or len(csrf) < 16:
            csrf = auth.new_csrf_token()
            new_csrf = csrf_cookie(csrf, secure=self._secure_cookie())
        body: dict[str, Any] = {}
        if method in ("POST", "PUT", "PATCH") or (
            method == "DELETE" and int(self.headers.get("Content-Length") or 0) > 0
        ):
            body = self.read_json_or_form()
        req = Request(
            method=method,
            path=path,
            query=query,
            headers=self.headers,
            body=body,
            user=auth.verify_session_token(cookies.get(auth.COOKIE_NAME)),
            csrf=csrf,
            client_key=self.client_key(),
            cookies=cookies,
            secure=self._secure_cookie(),
        )
        return req, new_csrf

    def _handle(self, method: str) -> None:
        try:
            req, new_csrf = self.build_request(method)
        except PayloadTooLarge:
            self.write_response(Response.json(413, {"ok": False, "error": "Payload too large"}))
            return
        resp = handlers.dispatch(req)
        if new_csrf and not any(c.startswith(f"{auth.CSRF_COOKIE}=") for c in resp.cookies):
            resp.cookies.append(new_csrf)
        self.write_response(resp)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_HEAD(self) -> None:
        self._handle("HEAD")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")


def run_server(host: str = "127.0.0.1", port: int = 5055) -> None:
    auth.load_or_create_auth_config()
    storage.init_db()
    try:
        storage.export_excel(storage.EXCEL_PATH)
    except storage.StorageError as exc:
        print(f"Excel export warning: {exc}", flush=True)

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Work Log portal -> http://{host}:{port}", flush=True)
    print(f"SQLite DB       -> {storage.DB_PATH}", flush=True)
    print(f"Excel export    -> {storage.EXCEL_PATH}", flush=True)
    print(f"Backups         -> {storage.BACKUP_DIR}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down.", flush=True)
        httpd.server_close()
