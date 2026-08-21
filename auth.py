"""Username/password auth with signed session cookies (stdlib only)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
AUTH_FILE = DATA_DIR / "credentials.json"
SECRET_FILE = DATA_DIR / ".session_secret"

COOKIE_NAME = "worklog_session"
CSRF_COOKIE = "worklog_csrf"
SESSION_TTL_SEC = 60 * 60 * 24 * 14  # 14 days
PBKDF2_ITER = 120_000
MIN_PASSWORD_LEN = 8
ROLES = ("admin", "viewer")

# Dummy hash so missing-user checks take similar time (timing side-channel)
_DUMMY_HASH = None

# Login rate limit (per client key)
_login_lock = threading.Lock()
_login_attempts: dict[str, list[float]] = {}
LOGIN_MAX_ATTEMPTS = 8
LOGIN_WINDOW_SEC = 15 * 60  # 15 minutes
LOGIN_LOCKOUT_SEC = 15 * 60


def _ensure_secret() -> bytes:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_FILE.is_file():
        return SECRET_FILE.read_bytes().strip()
    secret = secrets.token_hex(32).encode("utf-8")
    SECRET_FILE.write_bytes(secret + b"\n")
    try:
        SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return secret


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITER
    )
    return f"pbkdf2_sha256${PBKDF2_ITER}${salt.hex()}${dk.hex()}"


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("timing-dummy-not-a-real-password")
    return _DUMMY_HASH


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iters
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def validate_password_strength(password: str) -> str | None:
    """Return error message or None if OK."""
    if not password:
        return "Password cannot be empty"
    if len(password) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters"
    if password.lower() in ("changeme", "password", "admin", "12345678", "worklog"):
        return "Password is too common; choose something stronger"
    return None


def normalize_role(role: str | None) -> str:
    r = (role or "viewer").strip().lower()
    return "admin" if r == "admin" else "viewer"


def load_or_create_auth_config() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if AUTH_FILE.is_file():
        try:
            cfg = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            return _migrate_auth_config(cfg)
        except (json.JSONDecodeError, OSError):
            pass

    user = os.environ.get("WORKLOG_USER", "admin").strip() or "admin"
    password = os.environ.get("WORKLOG_PASSWORD", "changeme").strip() or "changeme"
    viewer_user = os.environ.get("WORKLOG_VIEWER_USER", "viewer").strip() or "viewer"
    viewer_password = (
        os.environ.get("WORKLOG_VIEWER_PASSWORD", "changeme").strip() or "changeme"
    )
    users = [
        {
            "username": user,
            "password_hash": hash_password(password),
            "display_name": user,
            "role": "admin",
        }
    ]
    # Bootstrap a read-only viewer (skip if same as admin username)
    if viewer_user != user:
        users.append(
            {
                "username": viewer_user,
                "password_hash": hash_password(viewer_password),
                "display_name": "Viewer",
                "role": "viewer",
            }
        )
    cfg = {
        "users": users,
        "must_change_password": password == "changeme" or viewer_password == "changeme",
    }
    save_auth_config(cfg)
    return cfg


def _migrate_auth_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Ensure every user has a role; existing single-user installs become admin."""
    changed = False
    users = cfg.setdefault("users", [])
    if not users:
        return cfg
    # First user without role -> admin; others without role -> viewer
    saw_admin = any(normalize_role(u.get("role")) == "admin" for u in users if u.get("role"))
    for i, u in enumerate(users):
        if not u.get("role"):
            u["role"] = "admin" if (i == 0 and not saw_admin) else "viewer"
            if u["role"] == "admin":
                saw_admin = True
            changed = True
        else:
            nr = normalize_role(u.get("role"))
            if u.get("role") != nr:
                u["role"] = nr
                changed = True
    if not saw_admin and users:
        users[0]["role"] = "admin"
        changed = True
    # Ensure a viewer account exists for convenience
    names = {u.get("username") for u in users}
    if "viewer" not in names:
        users.append(
            {
                "username": "viewer",
                "password_hash": hash_password("changeme"),
                "display_name": "Viewer",
                "role": "viewer",
            }
        )
        cfg["must_change_password"] = True
        changed = True
    if changed:
        save_auth_config(cfg)
    return cfg


def save_auth_config(cfg: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    try:
        AUTH_FILE.chmod(0o600)
    except OSError:
        pass


def get_user_record(username: str) -> dict[str, Any] | None:
    cfg = load_or_create_auth_config()
    for u in cfg.get("users", []):
        if u.get("username") == username:
            return u
    return None


def get_role(username: str | None) -> str:
    if not username:
        return "viewer"
    rec = get_user_record(username)
    if not rec:
        return "viewer"
    return normalize_role(rec.get("role"))


def is_admin(username: str | None) -> bool:
    return get_role(username) == "admin"


def can_write(username: str | None) -> bool:
    """Admins can create/edit/delete entries; viewers are read-only."""
    return is_admin(username)


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    username = (username or "").strip()
    rec = get_user_record(username) if username else None
    stored = rec.get("password_hash", "") if rec else _dummy_hash()
    ok = verify_password(password or "", stored)
    if not rec or not ok:
        return None
    return rec


def login_allowed(client_key: str) -> tuple[bool, int]:
    """Return (allowed, seconds_until_retry)."""
    now = time.time()
    with _login_lock:
        attempts = _login_attempts.get(client_key, [])
        attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SEC]
        _login_attempts[client_key] = attempts
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            oldest = min(attempts)
            wait = int(LOGIN_LOCKOUT_SEC - (now - oldest)) + 1
            return False, max(wait, 1)
        return True, 0


def record_login_failure(client_key: str) -> None:
    now = time.time()
    with _login_lock:
        attempts = _login_attempts.get(client_key, [])
        attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SEC]
        attempts.append(now)
        _login_attempts[client_key] = attempts


def clear_login_failures(client_key: str) -> None:
    with _login_lock:
        _login_attempts.pop(client_key, None)


def list_users() -> list[dict[str, Any]]:
    cfg = load_or_create_auth_config()
    out = []
    for u in cfg.get("users", []):
        out.append(
            {
                "username": u.get("username", ""),
                "display_name": u.get("display_name") or u.get("username", ""),
                "role": normalize_role(u.get("role")),
            }
        )
    return out


def user_must_change_password(username: str | None) -> bool:
    """True if this user's password is still the bootstrap default."""
    if not username:
        return False
    rec = get_user_record(username)
    if not rec:
        return False
    return verify_password("changeme", rec.get("password_hash", ""))


def uses_default_password() -> bool:
    """True if any user still accepts the bootstrap password 'changeme'."""
    cfg = load_or_create_auth_config()
    if cfg.get("must_change_password"):
        # Verify rather than trust flag alone
        pass
    for u in cfg.get("users", []):
        if verify_password("changeme", u.get("password_hash", "")):
            return True
    return False


def set_user_password(
    username: str,
    password: str | None = None,
    display_name: str | None = None,
    *,
    create_if_missing: bool = True,
    enforce_strength: bool = False,
    role: str | None = None,
) -> None:
    if password is not None and enforce_strength:
        err = validate_password_strength(password)
        if err:
            raise ValueError(err)

    cfg = load_or_create_auth_config()
    users = cfg.setdefault("users", [])
    found = None
    for u in users:
        if u.get("username") == username:
            found = u
            break

    if found is None:
        if not create_if_missing:
            raise KeyError(f"User not found: {username}")
        if not password:
            raise ValueError("Password is required when creating a new user")
        if enforce_strength:
            err = validate_password_strength(password)
            if err:
                raise ValueError(err)
        users.append(
            {
                "username": username,
                "password_hash": hash_password(password),
                "display_name": display_name or username,
                "role": normalize_role(role or "viewer"),
            }
        )
    else:
        if password is not None:
            if not password:
                raise ValueError("Password cannot be empty")
            found["password_hash"] = hash_password(password)
        if display_name is not None:
            found["display_name"] = display_name
        if role is not None:
            found["role"] = normalize_role(role)

    if password is not None and password != "changeme":
        # Only clear flag when no user still has changeme
        if not any(
            verify_password("changeme", u.get("password_hash", "")) for u in users
        ):
            cfg["must_change_password"] = False
    save_auth_config(cfg)


def change_password(username: str, current: str, new_password: str) -> None:
    rec = get_user_record(username)
    if not rec:
        raise KeyError("User not found")
    if not verify_password(current, rec.get("password_hash", "")):
        raise ValueError("Current password is incorrect")
    err = validate_password_strength(new_password)
    if err:
        raise ValueError(err)
    if current == new_password:
        raise ValueError("New password must be different from the current password")
    set_user_password(username, new_password, enforce_strength=True)


def rename_user(
    old_username: str,
    new_username: str,
    *,
    password: str | None = None,
    display_name: str | None = None,
    role: str | None = None,
) -> None:
    old_username = (old_username or "").strip()
    new_username = (new_username or "").strip()
    err = validate_username(new_username)
    if err:
        raise ValueError(err)
    if not old_username:
        raise ValueError("Old username is required")
    if (
        old_username == new_username
        and password is None
        and display_name is None
        and role is None
    ):
        return

    cfg = load_or_create_auth_config()
    users = cfg.setdefault("users", [])
    target = None
    for u in users:
        if u.get("username") == old_username:
            target = u
            break
    if target is None:
        raise KeyError(f"User not found: {old_username}")

    if new_username != old_username:
        for u in users:
            if u.get("username") == new_username:
                raise ValueError(f"Username already exists: {new_username}")
        target["username"] = new_username
        if display_name is None and (target.get("display_name") in (None, "", old_username)):
            target["display_name"] = new_username

    if password is not None:
        err = validate_password_strength(password)
        if err:
            raise ValueError(err)
        target["password_hash"] = hash_password(password)
    if display_name is not None:
        target["display_name"] = display_name
    if role is not None:
        target["role"] = normalize_role(role)

    if not any(normalize_role(u.get("role")) == "admin" for u in users):
        target["role"] = "admin"

    if password is not None and not any(
        verify_password("changeme", u.get("password_hash", "")) for u in users
    ):
        cfg["must_change_password"] = False

    save_auth_config(cfg)


def validate_username(username: str) -> str | None:
    username = (username or "").strip()
    if not username:
        return "Username cannot be empty"
    if len(username) > 64:
        return "Username is too long"
    if any(c.isspace() for c in username):
        return "Username cannot contain spaces"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", username):
        return "Username may only use letters, numbers, . _ -"
    return None


def create_session_token(username: str) -> str:
    secret = _ensure_secret()
    exp = int(time.time()) + SESSION_TTL_SEC
    nonce = secrets.token_hex(8)
    payload = f"{username}|{exp}|{nonce}"
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_session_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        parts = token.split("|")
        if len(parts) != 4:
            return None
        username, exp_s, _nonce, sig = parts
        exp = int(exp_s)
        if exp < int(time.time()):
            return None
        secret = _ensure_secret()
        payload = f"{username}|{exp_s}|{_nonce}"
        expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if not get_user_record(username):
            return None
        return username
    except Exception:
        return None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def display_name_for(username: str | None) -> str:
    if not username:
        return ""
    rec = get_user_record(username)
    if rec and rec.get("display_name"):
        return str(rec["display_name"])
    return username or ""
