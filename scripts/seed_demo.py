#!/usr/bin/env python3
"""Load fictional example notes. Never ships real operator data.

  .venv/bin/python scripts/seed_demo.py          # only if the DB is empty
  .venv/bin/python scripts/seed_demo.py --reset  # wipe entries + demo logins
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

import auth  # noqa: E402
import storage  # noqa: E402

DEMO_TICKET_URL = "https://jira.example.com/browse/{ticket}"
DEMO_PREFIXES = "INC,CHG,NET"

# Fictional lab network. No real customer, ASN, or site names.
DEMO_ENTRIES: list[dict] = [
    {
        "date": "2026-08-19",
        "title": "Closed INC0012345 BGP flap on ns-lab-core01",
        "details": (
            "Peer 192.0.2.10 dropped 4 times between 09:10 and 09:18.\n"
            "- Raised hold-timer on the lab session only\n"
            "- Packet capture: https://example.com/captures/inc0012345\n"
            "**Cause:** lab traffic generator, not a circuit fault."
        ),
        "category": "Incident",
        "status": "done",
        "tags": "INC0012345, BGP",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-19",
        "title": "Weekly peering sync",
        "details": (
            "Agenda: IX capacity, two pending PNIs, NET-42 follow-up.\n"
            "- No production change this week\n"
            "- Next slot: Friday 10:00 lab time"
        ),
        "category": "Meeting",
        "status": "done",
        "tags": "NET-42",
        "follow_up": "2026-08-22",
        "owner": "admin",
    },
    {
        "date": "2026-08-18",
        "title": "CHG004400 firewall window for lab syslog",
        "details": (
            "Opened UDP/514 from 198.51.100.0/28 to the collector.\n"
            "Change recorded as CHG004400. Rolled forward, no rollback."
        ),
        "category": "Change",
        "status": "done",
        "tags": "CHG004400, firewall",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-18",
        "title": "Documented lab prefix list for example.net",
        "details": (
            "Published the **example** prefix list used in training:\n"
            "- 192.0.2.0/24\n"
            "- 198.51.100.0/24\n"
            "- 2001:db8:1::/48\n"
            "Source of truth stays in the lab git repo, not this note."
        ),
        "category": "Documentation",
        "status": "done",
        "tags": "prefixes",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-17",
        "title": "NET-88 PNI cutover rehearsal blocked",
        "details": (
            "Rehearsal stopped: spare optic missing in the lab drawer.\n"
            "Need a 10G LR before Friday. Ticket NET-88 stays **blocked**."
        ),
        "category": "Project",
        "status": "blocked",
        "tags": "NET-88, PNI",
        "follow_up": "2026-08-21",
        "owner": "admin",
    },
    {
        "date": "2026-08-17",
        "title": "INC0012401 high CPU on ns-lab-pe02",
        "details": (
            "CPU 92% for 20 minutes after a route-refresh test.\n"
            "Process: `bgp`. Cleared after stopping the test script.\n"
            "Left a graph: https://example.com/graphs/pe02-cpu"
        ),
        "category": "Incident",
        "status": "done",
        "tags": "INC0012401",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-16",
        "title": "IPv6 peering lab with ExampleIX",
        "details": (
            "Brought up IPv6 only to 2001:db8:ix::21.\n"
            "Max-prefix 500. Session established, 12 prefixes received."
        ),
        "category": "Network",
        "status": "done",
        "tags": "IPv6, IX",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-15",
        "title": "Follow-up: TACACS on lab jumps",
        "details": (
            "ns-lab-jump01 still on local accounts.\n"
            "- Requested firewall to aaa.example.test\n"
            "- Waiting on CHG004512"
        ),
        "category": "Change",
        "status": "follow-up",
        "tags": "CHG004512, TACACS",
        "follow_up": "2026-08-20",
        "owner": "admin",
    },
    {
        "date": "2026-08-14",
        "title": "Wrote lab runbook for BGP dampening",
        "details": (
            "Draft in the docs folder. Covers when **not** to enable dampening "
            "on IX sessions. Review Monday."
        ),
        "category": "Documentation",
        "status": "in-progress",
        "tags": "BGP, runbook",
        "follow_up": "2026-08-24",
        "owner": "admin",
    },
    {
        "date": "2026-08-14",
        "title": "Assigned 192.0.2.128/28 to ns-lab-cmts01",
        "details": "Training CMTS. Not routed outside the lab VRF.",
        "category": "Network",
        "status": "done",
        "tags": "IPAM",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-13",
        "title": "INC0012500 packet loss to lab DNS",
        "details": (
            "Loss 8% toward 192.0.2.53. ACL typo on ns-lab-fw01 denied ICMP "
            "and fragmented UDP. Reverted. Post-mortem notes in INC0012500."
        ),
        "category": "Incident",
        "status": "done",
        "tags": "INC0012500, DNS",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-12",
        "title": "Learning: RPKI ROA refresh in the lab",
        "details": (
            "Enabled `rpki start` on ns-lab-core01. Validator is a local docker "
            "container, not a public service. Cached 3 example ROAs."
        ),
        "category": "Learning",
        "status": "done",
        "tags": "RPKI",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-11",
        "title": "Moved ExampleIX PNI from ns-lab-br02 to ns-lab-br01",
        "details": (
            "Both sides in the lab. Traffic was synthetic.\n"
            "**Steps**\n"
            "- Shutdown old bundle\n"
            "- Relabel LLDP\n"
            "- Confirm LACP 2x10G on br01\n"
            "NET-101 tracks the production copy of this work, which is out of scope here."
        ),
        "category": "Project",
        "status": "done",
        "tags": "NET-101, PNI",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-10",
        "title": "On-call handoff notes",
        "details": (
            "Quiet night. One page for a lab SNMP trap storm, ignored.\n"
            "Open items: NET-88 optic, CHG004512 TACACS."
        ),
        "category": "General",
        "status": "done",
        "tags": "NET-88, CHG004512",
        "follow_up": "",
        "owner": "admin",
    },
    {
        "date": "2026-08-07",
        "title": "Capacity check: lab IX port 40% of 10G",
        "details": "No upgrade. Recheck next month if the traffic generator stays on.",
        "category": "Network",
        "status": "done",
        "tags": "capacity",
        "follow_up": "2026-09-07",
        "owner": "admin",
    },
]


def _reset_auth() -> None:
    if auth.AUTH_FILE.exists():
        auth.AUTH_FILE.unlink()
    if auth.SECRET_FILE.exists():
        auth.SECRET_FILE.unlink()
    auth.load_or_create_auth_config()


def _wipe_entries() -> None:
    storage.init_db()
    with storage._lock:
        conn = storage._connect()
        try:
            conn.execute("DELETE FROM entries")
            conn.commit()
        finally:
            conn.close()
    storage._initialized = False
    storage.init_db()


def seed(*, reset: bool, force: bool) -> int:
    if reset:
        _reset_auth()
        # Avoid re-importing a leftover Excel sheet of real notes
        if storage.EXCEL_PATH.is_file():
            storage.EXCEL_PATH.unlink()
        if storage.DB_PATH.is_file() and storage.count_entries() > 0:
            _wipe_entries()
        else:
            storage.init_db()
    else:
        storage.init_db()
        n = storage.count_entries()
        if n > 0 and not force:
            print(f"Database already has {n} entries. Pass --reset or --force to load demo notes.")
            return 1

    if force and not reset and storage.count_entries() > 0:
        _wipe_entries()

    storage.save_ticket_settings(DEMO_TICKET_URL, DEMO_PREFIXES)
    for row in DEMO_ENTRIES:
        storage.create_entry(dict(row))
    try:
        storage.export_excel(storage.EXCEL_PATH)
    except storage.StorageError as exc:
        print(f"Excel export skipped: {exc}")
    print(f"Loaded {len(DEMO_ENTRIES)} demo entries.")
    print("Logins: admin / changeme  and  viewer / changeme")
    print("Ticket demo URL: https://jira.example.com/browse/{ticket}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Load fictional example work-log notes")
    p.add_argument(
        "--reset",
        action="store_true",
        help="Replace logins with admin/viewer changeme and wipe existing entries",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Wipe entries even if the database is not empty (keep current logins)",
    )
    args = p.parse_args()
    return seed(reset=args.reset, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
