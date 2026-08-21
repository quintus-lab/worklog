#!/usr/bin/env bash
# Build a portable zip for Windows 11 (no admin). Copy zip to the PC and extract.
set -euo pipefail
cd "$(dirname "$0")"

NAME="worklog"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="${1:-.}"
mkdir -p "$OUT_DIR"
OUT_DIR_ABS="$(cd "$OUT_DIR" && pwd)"
OUT="${OUT_DIR_ABS}/${NAME}-windows-${STAMP}.zip"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

STAGE="$TMP/$NAME"
mkdir -p "$STAGE"

# Core app (code only — never ship live credentials / DB)
cp -a app.py auth.py storage.py server.py handlers.py web.py tickets.py requirements.txt README.md setup.sh start.sh stop.sh status.sh "$STAGE/"
cp -a pages "$STAGE/"
cp -a static "$STAGE/"
cp -a windows "$STAGE/"
cp -a scripts "$STAGE/"
cp -a docs "$STAGE/" 2>/dev/null || mkdir -p "$STAGE/docs"
cp -a tests "$STAGE/" 2>/dev/null || true

# Empty data dir for first install (user keeps their own data\ when upgrading)
mkdir -p "$STAGE/data"
: > "$STAGE/data/.gitkeep"

# Strip junk
find "$STAGE" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -type d -name '.venv' -exec rm -rf {} + 2>/dev/null || true
rm -f "$STAGE/data/"*.pid "$STAGE/data/"*.log "$STAGE/data/"*.db "$STAGE/data/"*.xlsx \
  "$STAGE/data/credentials.json" "$STAGE/data/.session_secret" 2>/dev/null || true

# README for Windows drop-in
cat > "$STAGE/START-HERE-WINDOWS.txt" <<'EOF'
Daily Work Log - Windows 11 (no Administrator)

Cmd and PowerShell are different. Pick one style and stay with it.

  File Explorer (double-click) or Command Prompt (C:\Users\you>):
    use  windows\something.cmd

  PowerShell (PS C:\Users\you>):
    use  .\windows\something.ps1

  Do not type .ps1 commands into Command Prompt.
  Do not type cmd commands (set, type) into PowerShell.

*** Fresh install ***
1. Install Python 3.10+ from https://www.python.org/downloads/
   - Tick "Add python.exe to PATH" (user install is fine)

2. Extract this zip anywhere under your user profile, e.g.
   C:\Users\you\worklog

3. Setup, then start:
   - Double-click / Command Prompt:  windows\setup.cmd   then  windows\start.cmd
   - PowerShell:  .\windows\setup.ps1   then  .\windows\start.ps1
   First setup loads fictional demo notes if data\worklog.db is missing.

4. Open:  http://127.0.0.1:5055/
   Login: admin / changeme   (viewer / changeme = read-only)
   Change the default password on first use if this is not a demo PC.

*** Upgrade (keep your notes) ***
- Stop:  windows\stop.cmd   or   .\windows\stop.ps1
- Back up the whole data folder
- Extract this zip over the app, but KEEP your existing data\ folder
  (worklog.db, work_log.xlsx, backups\, credentials.json)
- Run setup if needed, then start again

*** Optional ***
- Auto-start at login:  windows\install-startup.cmd   or   .\windows\install-startup.ps1
- Import old Excel:     windows\import-excel.cmd      or   .\windows\import-excel.ps1
- Change password:      windows\set-user.cmd -Username admin
                        .\windows\set-user.ps1 -Username admin

This zip was built by pack-for-windows.sh on Linux. It is app code only.
It does not include Python, .venv, or your live data\ files.

Data:     data\worklog.db
Excel:    data\work_log.xlsx
Backups:  data\backups\
Docs:     docs\WINDOWS.md
EOF

# Build zip
if command -v zip >/dev/null 2>&1; then
  (cd "$TMP" && zip -r -q "$OUT" "$NAME")
elif command -v python3 >/dev/null 2>&1; then
  python3 - <<PY
import zipfile
from pathlib import Path
root = Path(r"$STAGE").parent
out = Path(r"$OUT")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in (root / "$NAME").rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(root).as_posix())
print("wrote", out)
PY
else
  echo "Need 'zip' or python3 to create archive" >&2
  exit 1
fi

# Remove older worklog-windows packages in the same output dir (keep only the new one)
shopt -s nullglob
for old in "${OUT_DIR_ABS}"/worklog-windows-*.zip; do
  if [[ "$(basename "$old")" != "$(basename "$OUT")" ]]; then
    rm -f -- "$old"
    echo "Deleted outdated: $old"
  fi
done

echo "Created: $OUT"
ls -lh "$OUT"
# quick content check
python3 - <<PY
import zipfile
from pathlib import Path
z = zipfile.ZipFile(r"$OUT")
names = z.namelist()
need = [
    "worklog/app.py",
    "worklog/server.py",
    "worklog/handlers.py",
    "worklog/storage.py",
    "worklog/web.py",
    "worklog/tickets.py",
    "worklog/pages/index.py",
    "worklog/static/prefs.js",
    "worklog/windows/start.ps1",
    "worklog/START-HERE-WINDOWS.txt",
]
for n in need:
    assert n in names, f"missing {n}"
# must not ship secrets
bad = [n for n in names if "credentials.json" in n or n.endswith(".db") or ".session_secret" in n]
assert not bad, f"package must not include secrets/data: {bad}"
print("package check: OK (%d files)" % len(names))
PY
