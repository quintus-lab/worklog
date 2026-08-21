#!/usr/bin/env bash
# Start the Daily Work Log portal (Linux / macOS / WSL)
set -euo pipefail
cd "$(dirname "$0")"

export WORKLOG_HOST="${WORKLOG_HOST:-127.0.0.1}"
export WORKLOG_PORT="${WORKLOG_PORT:-5055}"
PIDFILE="${WORKLOG_PIDFILE:-data/worklog.pid}"
LOGFILE="${WORKLOG_LOGFILE:-data/worklog.log}"

mkdir -p data

if [[ -f "$PIDFILE" ]]; then
  old=$(tr -d ' \n\r' < "$PIDFILE" || true)
  if [[ -n "${old:-}" ]] && kill -0 "$old" 2>/dev/null; then
    echo "Work Log already running (pid=$old). Use ./stop.sh first."
    exit 0
  fi
  rm -f "$PIDFILE"
fi

# Prefer venv if present (same layout Windows creates); else system python3
if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "Python 3 not found." >&2
  exit 1
fi

if ! "$PY" -c "import openpyxl" 2>/dev/null; then
  echo "Missing openpyxl. Install with one of:"
  echo "  $PY -m pip install --user openpyxl"
  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Starting Work Log portal on http://${WORKLOG_HOST}:${WORKLOG_PORT}"
nohup "$PY" app.py >>"$LOGFILE" 2>&1 &
echo $! >"$PIDFILE"
sleep 0.5
if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "  pid:  $(cat "$PIDFILE")"
  echo "  url:  http://127.0.0.1:${WORKLOG_PORT}/"
  echo "  xlsx: data/work_log.xlsx"
  echo "  log:  $LOGFILE"
else
  echo "Process exited immediately - see $LOGFILE" >&2
  rm -f "$PIDFILE"
  exit 1
fi
