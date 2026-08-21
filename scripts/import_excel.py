#!/usr/bin/env python3
"""Import entries from Excel .xlsx into SQLite (no re-typing).

Windows PowerShell (from worklog folder):

  .\\.venv\\Scripts\\python.exe scripts\\import_excel.py
  .\\.venv\\Scripts\\python.exe scripts\\import_excel.py "C:\\path\\work_log.xlsx"
  .\\.venv\\Scripts\\python.exe scripts\\import_excel.py --replace
  .\\.venv\\Scripts\\python.exe scripts\\import_excel.py --merge-update
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import storage  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Import work_log.xlsx into SQLite")
    p.add_argument(
        "excel",
        nargs="?",
        default=str(storage.EXCEL_PATH),
        help="Path to .xlsx (default: data/work_log.xlsx)",
    )
    p.add_argument(
        "--replace",
        action="store_true",
        help="Wipe entries first (safety backup), then import Excel",
    )
    p.add_argument(
        "--merge-update",
        action="store_true",
        help="Update rows when ID already exists (default: skip existing IDs)",
    )
    p.add_argument(
        "--legacy-9col",
        action="store_true",
        help="Treat sheet as old 9-column layout when no header row",
    )
    args = p.parse_args()

    if args.replace:
        mode = "replace"
    elif args.merge_update:
        mode = "upsert"
    else:
        mode = "insert"

    try:
        result = storage.import_excel(
            args.excel,
            mode=mode,
            legacy_9col=args.legacy_9col,
        )
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        print(
            "Copy your old work_log.xlsx into data\\ first, or pass the full path.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1

    print(f"Mode:     {result['mode']}")
    print(f"Parsed:   {result['parsed']}")
    print(f"Inserted: {result['inserted']}")
    print(f"Updated:  {result['updated']}")
    print(f"Skipped:  {result['skipped']}")
    print(f"Entries before: {result['before']}")
    print(f"Entries after:  {result['after']}")
    print("Done. Restart the portal if running, then refresh the browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
