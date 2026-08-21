#!/usr/bin/env python3
"""Daily Work Log entrypoint — stdlib HTTP server, no admin required."""

from __future__ import annotations

import os
import sys

from server import run_server


def main() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    host = os.environ.get("WORKLOG_HOST", "127.0.0.1")
    port = int(os.environ.get("WORKLOG_PORT", "5055"))
    try:
        run_server(host, port)
    except OSError as exc:
        print(f"ERROR: cannot bind {host}:{port} - {exc}", flush=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        raise SystemExit(1)
