#!/usr/bin/env bash
# Stop Daily Work Log portal
set -euo pipefail
cd "$(dirname "$0")"

PIDFILE="${WORKLOG_PIDFILE:-data/worklog.pid}"
PORT="${WORKLOG_PORT:-5055}"

if [[ -f "$PIDFILE" ]]; then
  pid=$(tr -d ' \n\r' < "$PIDFILE" || true)
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping Work Log pid=$pid ..."
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
fi

# Fallback: free the port if something is still listening
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "${pids:-}" ]]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
  fi
fi

echo "Daily Work Log stopped (port $PORT)."
