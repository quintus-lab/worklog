#!/usr/bin/env bash
# One-time setup for Daily Work Log on Linux or macOS (no root required).
# Creates .venv and installs requirements.txt.
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f app.py ]]; then
  echo "Run this from the worklog folder (app.py not found)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 not found." >&2
  echo "  macOS:  brew install python    or install from https://www.python.org/downloads/" >&2
  echo "  Linux:  install python3 and python3-venv from your package manager" >&2
  exit 1
fi

ver=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
major=${ver%%.*}
minor=${ver#*.}
if (( major < 3 || (major == 3 && minor < 10) )); then
  echo "Need Python 3.10 or newer (found $ver)." >&2
  exit 1
fi
echo "Using $(python3 --version)"

if [[ ! -x .venv/bin/python ]]; then
  echo "Creating venv at .venv ..."
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p data
if [[ ! -f data/worklog.db ]]; then
  echo "Loading demo notes into a new database ..."
  .venv/bin/python scripts/seed_demo.py
fi

echo
echo "Setup complete."
echo "  Start:  ./start.sh"
echo "  Stop:   ./stop.sh"
echo "  Status: ./status.sh"
echo "  URL:    http://127.0.0.1:5055/"
echo "  Demo login: admin / changeme"
