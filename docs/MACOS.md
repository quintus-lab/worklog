# macOS: Daily Work Log

Same Python app as Linux. No admin. Data stays in this folder.

- Database: `data/worklog.db`
- Excel export: `data/work_log.xlsx`
- Backups: `data/backups/`

## Terminal: one command style

macOS is not like Windows. **Terminal**, **iTerm**, **zsh**, and **bash** all use the same commands below.

| You opened | Prompt looks like | Use |
|------------|-------------------|-----|
| Terminal.app or iTerm | `%` (zsh) or `$` (bash) | `./start.sh` |
| Windows Command Prompt | `C:\Users\you>` | Do not use these scripts. See [WINDOWS.md](WINDOWS.md). |
| Windows PowerShell | `PS C:\Users\you>` | Do not use these scripts. See [WINDOWS.md](WINDOWS.md). |

Do not run `windows\*.cmd` or `windows\*.ps1` on a Mac.

## Get the code

Prefer the **public GitHub** clone. GitLab is the private working copy; see [REMOTES.md](REMOTES.md).

```bash
git clone https://github.com/quintus-lab/worklog.git
cd worklog
```

Or GitLab (invite required if that repo stays private):

```bash
git clone https://gitlab.com/qc1048/worklog.git
cd worklog
```

```bash
cd ~/worklog
chmod +x setup.sh start.sh stop.sh status.sh
./setup.sh
./start.sh
```

Then open http://127.0.0.1:5055/

## One-time setup

1. Install Python 3.10 or newer (user install is enough):
   - Homebrew: `brew install python`
   - Or the installer at https://www.python.org/downloads/macos/
2. If `python3` opens a dialog about Command Line Tools, install them, then run `python3 --version` again.
3. In the worklog folder:

```bash
./setup.sh
```

That creates `.venv` and installs `openpyxl`. You do not need sudo.

## Daily use

| Action | Terminal (zsh or bash) |
|--------|------------------------|
| Setup | `./setup.sh` |
| Start | `./start.sh` |
| Stop | `./stop.sh` |
| Status | `./status.sh` |
| Change password or username | `./.venv/bin/python scripts/set_password.py --list` |

Default login: `admin` / `changeme` (edit) and `viewer` / `changeme` (read-only). Change the default password on first sign-in.

Change password from Terminal:

```bash
cd ~/worklog
./.venv/bin/python scripts/set_password.py admin
./.venv/bin/python scripts/set_password.py admin -p "YourNewPassword"
./.venv/bin/python scripts/set_password.py admin --rename yourname --no-password
```

After a CLI user change, sign out in the browser and sign in again.

## Listen on another port

```bash
export WORKLOG_HOST=127.0.0.1
export WORKLOG_PORT=5056
./start.sh
```

## Troubleshooting

```bash
cat data/worklog.err.log
cat data/worklog.log
./.venv/bin/python app.py
```

The last command runs in the current window so errors print live.

Common fixes:

1. Run `./setup.sh` again.
2. Confirm `./.venv/bin/python --version` is 3.10 or newer.
3. Port in use: `./stop.sh`, or set `WORKLOG_PORT` to another port.

If Excel for Mac has `data/work_log.xlsx` open for write, SQLite still saves. Close Excel if the spreadsheet copy looks stale.

## Pack for Windows is not for Mac

`./pack-for-windows.sh` only builds a zip for a **Windows** PC. On a Mac, copy or clone this folder and run `./setup.sh`. Keep your existing `data/` folder when you replace app files.

## Optional: start at login

System Settings > General > Login Items is for apps, not this script. Easiest path: open Terminal and run `./start.sh` after you log in. A LaunchAgent can run `app.py` in the foreground if you want it unattended; that is optional and not required.
