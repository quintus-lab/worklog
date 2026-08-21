#!/usr/bin/env python3
r"""Create/update worklog users: password, username rename, display name.

Windows 11 PowerShell examples (from the worklog folder, no admin):

  # Change password for admin (prompts securely)
  .\.venv\Scripts\python.exe scripts\set_password.py admin

  # Change password in one line
  .\.venv\Scripts\python.exe scripts\set_password.py admin -p "NewSecret123"

  # Rename admin -> quintus (keep asking for a new password)
  .\.venv\Scripts\python.exe scripts\set_password.py admin --rename quintus

  # Rename + set password + display name together
  .\.venv\Scripts\python.exe scripts\set_password.py admin --rename quintus -p "NewSecret123" -n "Quintus Zhu"

  # Rename only (no password change)
  .\.venv\Scripts\python.exe scripts\set_password.py admin --rename quintus --no-password

  # List users
  .\.venv\Scripts\python.exe scripts\set_password.py --list
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auth  # noqa: E402


def _prompt_password(label: str) -> str:
    password = getpass.getpass(f"{label}: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    if not password:
        raise SystemExit("Password cannot be empty.")
    return password


def main() -> int:
    p = argparse.ArgumentParser(
        description="Set Daily Work Log password and/or rename username"
    )
    p.add_argument(
        "username",
        nargs="?",
        default=None,
        help="Existing username (default: admin). Omit with --list.",
    )
    p.add_argument(
        "--rename",
        "-r",
        metavar="NEW_USERNAME",
        help="Change login username to NEW_USERNAME",
    )
    p.add_argument("--password", "-p", help="New password (prompted if omitted, unless --no-password)")
    p.add_argument(
        "--no-password",
        action="store_true",
        help="Do not change password (use with --rename or --name)",
    )
    p.add_argument("--name", "-n", help="Display name shown in the UI")
    p.add_argument(
        "--role",
        choices=["admin", "viewer"],
        help="Set role: admin (full edit) or viewer (read-only)",
    )
    p.add_argument("--list", "-l", action="store_true", help="List users and exit")
    args = p.parse_args()

    if args.list:
        users = auth.list_users()
        if not users:
            print("(no users)")
            return 0
        print(f"{'USERNAME':<20} {'ROLE':<8} DISPLAY NAME")
        print("-" * 48)
        for u in users:
            print(f"{u['username']:<20} {u.get('role', 'viewer'):<8} {u['display_name']}")
        print(f"\nFile: {auth.AUTH_FILE}")
        return 0

    username = (args.username or "admin").strip()
    if not username:
        print("Username cannot be empty.", file=sys.stderr)
        return 1

    new_username = (args.rename or "").strip() or None
    password: str | None
    if args.no_password:
        password = None
        if not new_username and args.name is None and args.role is None:
            print(
                "Nothing to do. Use --rename, --name, --role, or omit --no-password.",
                file=sys.stderr,
            )
            return 1
    elif args.password is not None:
        password = args.password
        if not password:
            print("Password cannot be empty.", file=sys.stderr)
            return 1
    else:
        # Interactive password when creating/updating password
        who = new_username or username
        password = _prompt_password(f"New password for {who}")

    try:
        if new_username:
            # Rename path (user must exist unless we create — rename requires exist)
            if auth.get_user_record(username) is None:
                # Allow create-as-rename when old doesn't exist but we have password
                if password is None:
                    raise KeyError(f"User not found: {username}")
                auth.set_user_password(
                    new_username,
                    password,
                    display_name=args.name or new_username,
                    create_if_missing=True,
                    role=args.role or "admin",
                )
                print(f"Created user '{new_username}' (source '{username}' not found)")
            else:
                auth.rename_user(
                    username,
                    new_username,
                    password=password,
                    display_name=args.name,
                    role=args.role,
                )
                msg = f"Renamed '{username}' -> '{new_username}'"
                if password is not None:
                    msg += " (password updated)"
                if args.name is not None:
                    msg += f" (display name: {args.name})"
                print(msg)
        else:
            auth.set_user_password(
                username,
                password,
                display_name=args.name,
                create_if_missing=True,
                role=args.role,
            )
            bits = [f"Updated user '{username}'"]
            if password is not None:
                bits.append("password set")
            if args.name is not None:
                bits.append(f"display name: {args.name}")
            print("; ".join(bits))
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved: {auth.AUTH_FILE}")
    print("Sign out / sign in again if the portal is already open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
