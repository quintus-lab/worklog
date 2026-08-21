#!/usr/bin/env bash
# Status for Daily Work Log portal
set -euo pipefail
cd "$(dirname "$0")"

PIDFILE="${WORKLOG_PIDFILE:-data/worklog.pid}"
PORT="${WORKLOG_PORT:-5055}"
XLSX="data/work_log.xlsx"

echo "Daily Work Log"
echo "  root:  $(pwd)"
echo "  port:  $PORT"
echo "  xlsx:  $XLSX"

running=false
pid=""
if [[ -f "$PIDFILE" ]]; then
  pid=$(tr -d ' \n\r' < "$PIDFILE" || true)
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    running=true
  fi
fi

if $running; then
  echo "  state: RUNNING (pid=$pid)"
  echo "  url:   http://127.0.0.1:${PORT}/"
  if command -v curl >/dev/null 2>&1; then
    health=$(curl -sS --max-time 3 "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)
    if [[ -n "${health:-}" ]]; then
      echo "  health: $health"
    else
      echo "  health: (not responding yet)"
    fi
  fi
else
  echo "  state: STOPPED"
  if [[ -n "${pid:-}" ]]; then
    echo "  stale pid file ignored: $pid"
  fi
fi
