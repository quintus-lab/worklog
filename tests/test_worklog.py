#!/usr/bin/env python3
"""Regression tests for worklog (storage + live HTTP)."""

from __future__ import annotations

import http.client
import json
import re
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class IsolatedAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="worklog-test-"))
        import auth
        import storage

        self.auth = auth
        self.storage = storage
        self._orig = {
            "auth_data": auth.DATA_DIR,
            "auth_file": auth.AUTH_FILE,
            "secret": auth.SECRET_FILE,
            "s_data": storage.DATA_DIR,
            "db": storage.DB_PATH,
            "xlsx": storage.EXCEL_PATH,
            "bak": storage.BACKUP_DIR,
            "legacy": storage.LEGACY_XLSX,
        }
        data = self.tmp / "data"
        data.mkdir()
        auth.DATA_DIR = data
        auth.AUTH_FILE = data / "credentials.json"
        auth.SECRET_FILE = data / ".session_secret"
        storage.DATA_DIR = data
        storage.DB_PATH = data / "worklog.db"
        storage.EXCEL_PATH = data / "work_log.xlsx"
        storage.BACKUP_DIR = data / "backups"
        storage.LEGACY_XLSX = data / "work_log.xlsx"
        storage._initialized = False
        auth._login_attempts.clear()
        if auth.AUTH_FILE.exists():
            auth.AUTH_FILE.unlink()
        auth.load_or_create_auth_config()
        storage.init_db()

    def tearDown(self) -> None:
        import auth
        import storage

        auth.DATA_DIR = self._orig["auth_data"]
        auth.AUTH_FILE = self._orig["auth_file"]
        auth.SECRET_FILE = self._orig["secret"]
        storage.DATA_DIR = self._orig["s_data"]
        storage.DB_PATH = self._orig["db"]
        storage.EXCEL_PATH = self._orig["xlsx"]
        storage.BACKUP_DIR = self._orig["bak"]
        storage.LEGACY_XLSX = self._orig["legacy"]
        storage._initialized = False
        auth._login_attempts.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)


class WorklogTests(IsolatedAppTest):
    def test_crud_and_newest_first(self) -> None:
        a = self.storage.create_entry(
            {"title": "Older", "date": "2026-01-01", "owner": "admin"}
        )
        b = self.storage.create_entry(
            {"title": "Newer", "date": "2026-07-01", "owner": "admin", "tags": "T1"}
        )
        entries = self.storage.load_entries()
        self.assertEqual(entries[0]["id"], b["id"])
        self.assertEqual(entries[1]["id"], a["id"])
        self.storage.update_entry(a["id"], {"title": "Older updated"})
        self.assertEqual(self.storage.get_entry(a["id"])["title"], "Older updated")
        self.storage.delete_entry(a["id"])
        self.assertIsNone(self.storage.get_entry(a["id"]))

    def test_entry_validation(self) -> None:
        with self.assertRaises(ValueError):
            self.storage.create_entry({"title": "", "date": "2026-01-01"})
        with self.assertRaises(ValueError):
            self.storage.create_entry({"title": "x", "date": "not-a-date"})
        with self.assertRaises(ValueError):
            self.storage.create_entry(
                {"title": "x", "date": "2026-01-01", "follow_up": "13-40"}
            )
        e = self.storage.create_entry(
            {"title": "ok", "date": "2026-01-01", "category": "Nope", "status": "weird"}
        )
        self.assertEqual(e["category"], "Other")
        self.assertEqual(e["status"], "done")
        with self.assertRaises(ValueError):
            self.storage.update_entry(e["id"], {"title": "   "})

    def test_pagination_offset(self) -> None:
        for i in range(5):
            self.storage.create_entry(
                {"title": f"E{i}", "date": f"2026-07-{i + 1:02d}"}
            )
        page = self.storage.load_entries(limit=2, offset=0)
        self.assertEqual(len(page), 2)
        self.assertEqual(self.storage.count_entries(), 5)
        rest = self.storage.load_entries(limit=2, offset=2)
        self.assertEqual(len(rest), 2)
        self.assertNotEqual(page[0]["id"], rest[0]["id"])

    def test_viewer_cannot_write_role(self) -> None:
        self.assertTrue(self.auth.can_write("admin"))
        self.assertFalse(self.auth.can_write("viewer"))
        self.assertTrue(self.auth.is_admin("admin"))
        self.assertFalse(self.auth.is_admin("viewer"))

    def test_import_excel_roundtrip(self) -> None:
        self.storage.create_entry(
            {
                "title": "From DB",
                "date": "2026-06-01",
                "owner": "admin",
                "tags": "X",
            }
        )
        self.storage.export_excel(self.storage.EXCEL_PATH)
        result = self.storage.import_excel(self.storage.EXCEL_PATH, mode="replace")
        self.assertGreaterEqual(result["inserted"], 1)
        self.assertGreaterEqual(result["after"], 1)
        titles = [e["title"] for e in self.storage.load_entries()]
        self.assertIn("From DB", titles)

    def test_backup_restore(self) -> None:
        e = self.storage.create_entry({"title": "Keep me", "date": "2026-05-01"})
        paths = self.storage.create_backup("test")
        self.assertTrue(Path(paths["db"]).is_file())
        self.storage.delete_entry(e["id"])
        self.assertEqual(self.storage.count_entries(), 0)
        name = Path(paths["db"]).name
        self.storage.restore_backup(name)
        self.assertIsNotNone(self.storage.get_entry(e["id"]))

    def test_details_markdown_and_xss(self) -> None:
        from pages.markup import render_details

        html = render_details("See **bold** and https://example.com/path")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn('href="https://example.com/path"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        html = render_details("<script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        html = render_details("[x](javascript:alert(1))")
        self.assertNotIn("href=", html)
        self.assertNotIn("<a ", html)
        html = render_details("[ok](https://wiki.example/a?q=1&b=2)")
        self.assertIn("https://wiki.example/a?q=1&amp;b=2", html)
        html = render_details("- one\n- two")
        self.assertIn("<ul>", html)
        self.assertIn("<li>one</li>", html)
        html = render_details("**see https://example.com**")
        self.assertIn("<strong>", html)
        self.assertIn('href="https://example.com"', html)
        html = render_details("keep\x00going **ok**")
        self.assertIn("<strong>ok</strong>", html)

    def test_search_and_ticket_links(self) -> None:
        self.storage.create_entry(
            {
                "title": "Fixed BGP on INC0012345",
                "date": "2026-08-10",
                "details": "See NET-99 in the runbook",
                "tags": "INC0012345, BGP",
            }
        )
        self.storage.create_entry(
            {
                "title": "Unrelated meeting notes",
                "date": "2026-08-11",
                "details": "no ticket here",
            }
        )
        hits = self.storage.load_entries(q="INC0012345")
        self.assertEqual(len(hits), 1)
        self.assertIn("BGP", hits[0]["title"])
        self.assertEqual(self.storage.count_entries(q="INC0012345"), 1)
        # LIKE wildcards in the query are literal, not "match everything"
        self.assertEqual(self.storage.count_entries(q="%"), 0)
        self.assertEqual(self.storage.count_entries(q="_"), 0)

        cfg = self.storage.save_ticket_settings(
            "https://jira.example.com/browse/{ticket}", "INC,NET"
        )
        self.assertIn("{ticket}", cfg["url"])
        self.assertEqual(cfg["prefixes"], "INC,NET")
        from pages.common import render_entry

        card = render_entry(hits[0], editable=False)
        self.assertIn("https://jira.example.com/browse/INC0012345", card)
        self.assertIn("https://jira.example.com/browse/NET-99", card)
        self.assertIn('class="ticket-link"', card)
        # case-insensitive match; URL uses uppercase id
        lower = self.storage.create_entry(
            {
                "title": "closed inc0011111",
                "date": "2026-08-12",
                "details": "net-42 done",
            }
        )
        low_card = render_entry(lower, editable=False)
        self.assertIn("https://jira.example.com/browse/INC0011111", low_card)
        self.assertIn("https://jira.example.com/browse/NET-42", low_card)
        with self.assertRaises(ValueError):
            self.storage.save_ticket_settings("javascript:alert(1)", "")
        with self.assertRaises(ValueError):
            self.storage.save_ticket_settings(
                "https://x.example/{ticket}", "(a+)+"
            )
        with self.assertRaises(ValueError):
            self.storage.save_ticket_settings(
                "https://x.example/{ticket}", "bad prefix!"
            )

    def test_seed_demo_loads_examples(self) -> None:
        import importlib.util

        path = ROOT / "scripts" / "seed_demo.py"
        spec = importlib.util.spec_from_file_location("seed_demo", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        self.assertGreaterEqual(len(mod.DEMO_ENTRIES), 12)
        self.assertEqual(mod.seed(reset=True, force=False), 0)
        self.assertGreaterEqual(self.storage.count_entries(), 12)
        self.assertTrue(self.auth.authenticate("admin", "changeme"))

    def test_entry_details_disclosure(self) -> None:
        from pages.common import render_entry

        e = self.storage.create_entry(
            {
                "title": "Short",
                "date": "2026-08-01",
                "details": "one line",
            }
        )
        card = render_entry(e, editable=False)
        self.assertIn("<details class=\"entry-details\">", card)
        self.assertNotIn("<details open", card)
        self.assertIn("Details", card)
        self.assertIn("1 line", card)
        self.assertNotIn("details-preview", card)
        long = self.storage.create_entry(
            {
                "title": "Long",
                "date": "2026-08-02",
                "details": "line1\nline2\nline3\nline4 extra",
            }
        )
        folded = render_entry(long, editable=False)
        self.assertIn("4 lines", folded)
        self.assertIn("line4 extra", folded)

    def test_password_strength_and_change(self) -> None:
        self.assertIsNotNone(self.auth.validate_password_strength("short"))
        self.assertIsNone(self.auth.validate_password_strength("GoodPass99"))
        self.auth.change_password("admin", "changeme", "GoodPass99")
        self.assertIsNotNone(self.auth.authenticate("admin", "GoodPass99"))
        self.assertFalse(self.auth.user_must_change_password("admin"))


class HttpTests(IsolatedAppTest):
    def setUp(self) -> None:
        super().setUp()
        from server import Handler

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.cookies: dict[str, str] = {}

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = dict(headers or {})
        if self.cookies:
            hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if content_type:
            hdrs["Content-Type"] = content_type
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        collected: dict[str, str] = {}
        for k, v in resp.getheaders():
            collected.setdefault(k.lower(), v)
            if k.lower() == "set-cookie":
                name, _, rest = v.partition("=")
                val = rest.split(";", 1)[0]
                if "Max-Age=0" in v or val == "":
                    self.cookies.pop(name, None)
                else:
                    self.cookies[name] = val
        location = resp.getheader("Location") or ""
        collected["location"] = location
        status = resp.status
        conn.close()
        return status, collected, raw

    def _csrf_from_login(self) -> str:
        status, _, raw = self._request("GET", "/login")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8")
        m = re.search(r'name="csrf_token" value="([^"]+)"', html)
        self.assertIsNotNone(m)
        return m.group(1)

    def _login_form(self, username: str, password: str, *, next_url: str = "/") -> int:
        csrf = self._csrf_from_login()
        body = urlencode(
            {
                "username": username,
                "password": password,
                "csrf_token": csrf,
                "next": next_url,
            }
        ).encode("utf-8")
        status, _, _ = self._request(
            "POST",
            "/api/login",
            body=body,
            content_type="application/x-www-form-urlencoded",
        )
        return status

    def _login_json(self, username: str, password: str, *, csrf: str | None = None) -> tuple[int, dict]:
        if csrf is None:
            csrf = self._csrf_from_login()
        payload = json.dumps(
            {"username": username, "password": password, "csrf_token": csrf}
        ).encode("utf-8")
        status, _, raw = self._request(
            "POST",
            "/api/login",
            body=payload,
            content_type="application/json",
            headers={"X-CSRF-Token": csrf, "Accept": "application/json"},
        )
        try:
            obj = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            obj = {}
        return status, obj

    def test_head_root_empty(self) -> None:
        status, headers, raw = self._request("HEAD", "/")
        self.assertEqual(status, 200)
        self.assertEqual(raw, b"")
        self.assertNotIn("application/json", headers.get("content-type", ""))

    def test_health_public(self) -> None:
        status, _, raw = self._request("GET", "/health")
        self.assertEqual(status, 200)
        data = json.loads(raw.decode("utf-8"))
        self.assertTrue(data.get("ok"))

    def test_login_requires_csrf(self) -> None:
        self._request("GET", "/login")
        body = urlencode(
            {"username": "admin", "password": "changeme", "next": "/"}
        ).encode("utf-8")
        status, _, raw = self._request(
            "POST",
            "/api/login",
            body=body,
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(status, 403)
        self.assertIn(b"Session expired", raw)

    def test_login_json_csrf_header(self) -> None:
        status, data = self._login_json("admin", "changeme")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertTrue(data.get("must_change_password"))

    def test_unknown_path_is_404_not_force_password(self) -> None:
        status = self._login_form("admin", "changeme")
        self.assertEqual(status, 302)
        status, headers, _ = self._request("GET", "/does-not-exist")
        self.assertEqual(status, 404)
        self.assertNotEqual(headers.get("location"), "/settings")

    def test_force_password_redirects_to_settings(self) -> None:
        status = self._login_form("admin", "changeme", next_url="/")
        self.assertEqual(status, 302)
        status, headers, _ = self._request("GET", "/")
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/settings")
        status, _, raw = self._request("GET", "/settings")
        self.assertEqual(status, 200)
        self.assertIn(b"Change your default password", raw)
        status, _, raw = self._request(
            "GET", "/api/entries", headers={"Accept": "application/json"}
        )
        self.assertEqual(status, 403)
        data = json.loads(raw.decode("utf-8"))
        self.assertTrue(data.get("must_change_password"))

    def test_viewer_cannot_create_entry(self) -> None:
        self.auth.set_user_password(
            "viewer", "ViewerPass99", enforce_strength=True
        )
        status, data = self._login_json("viewer", "ViewerPass99")
        self.assertEqual(status, 200)
        self.assertFalse(data.get("must_change_password"))
        csrf = self.cookies.get("worklog_csrf") or ""
        payload = json.dumps({"title": "nope", "csrf_token": csrf}).encode("utf-8")
        status, _, raw = self._request(
            "POST",
            "/api/entries",
            body=payload,
            content_type="application/json",
            headers={"X-CSRF-Token": csrf, "Accept": "application/json"},
        )
        self.assertEqual(status, 403)
        data = json.loads(raw.decode("utf-8"))
        self.assertIn("read-only", data.get("error", "").lower())

    def test_pagination_http(self) -> None:
        self.auth.change_password("admin", "changeme", "GoodPass99")
        for i in range(15):
            self.storage.create_entry(
                {"title": f"Item {i:02d}", "date": f"2026-08-{(i % 28) + 1:02d}"}
            )
        status, data = self._login_json("admin", "GoodPass99")
        self.assertEqual(status, 200)
        status, _, raw = self._request("GET", "/?per=10")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8")
        self.assertIn("Page <strong>1</strong>", html)
        self.assertIn("of 15", html)
        status, _, raw = self._request(
            "GET",
            "/api/entries?limit=10&offset=0",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(status, 200)
        data = json.loads(raw.decode("utf-8"))
        self.assertEqual(data["count"], 10)
        self.assertEqual(data["total"], 15)

    def test_search_http_and_ticket_settings(self) -> None:
        self.auth.change_password("admin", "changeme", "GoodPass99")
        self.storage.create_entry(
            {
                "title": "Closed INC0099999 flap",
                "date": "2026-08-12",
                "details": "NET-42 follow-up",
                "tags": "INC0099999",
            }
        )
        self.storage.create_entry(
            {"title": "Coffee chat", "date": "2026-08-12", "details": "no tickets"}
        )
        status, _ = self._login_json("admin", "GoodPass99")
        self.assertEqual(status, 200)
        status, _, raw = self._request("GET", "/?q=INC0099999")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8")
        self.assertIn("Closed INC0099999 flap", html)
        self.assertNotIn("Coffee chat", html)
        status, _, raw = self._request("GET", "/history?q=INC0099999")
        self.assertEqual(status, 200)
        self.assertIn("Closed INC0099999 flap", raw.decode("utf-8"))
        csrf = self.cookies.get("worklog_csrf") or ""
        payload = json.dumps(
            {
                "url": "https://jira.example.com/browse/{ticket}",
                "prefixes": "INC,NET",
                "csrf_token": csrf,
            }
        ).encode("utf-8")
        status, _, raw = self._request(
            "POST",
            "/api/ticket-settings",
            body=payload,
            content_type="application/json",
            headers={"X-CSRF-Token": csrf, "Accept": "application/json"},
        )
        self.assertEqual(status, 200)
        data = json.loads(raw.decode("utf-8"))
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("prefixes"), "INC,NET")
        status, _, raw = self._request("GET", "/?q=INC0099999")
        html = raw.decode("utf-8")
        self.assertIn("https://jira.example.com/browse/INC0099999", html)
        self.assertIn("https://jira.example.com/browse/NET-42", html)
        status, _, raw = self._request("GET", "/settings")
        self.assertEqual(status, 200)
        self.assertIn("Ticket system", raw.decode("utf-8"))
        status, _, raw = self._request("GET", "/")
        self.assertIn('name="q"', raw.decode("utf-8"))
        self.assertIn("Search log", raw.decode("utf-8"))
        self.assertNotIn("data-search=", raw.decode("utf-8"))
        self.assertNotIn('id="entry-filter"', raw.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
