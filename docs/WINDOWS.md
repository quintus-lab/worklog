# Windows 11: Daily Work Log

Same Python app as Linux. No Administrator. Data stays in this folder.

- Database: `data\worklog.db`
- Excel export: `data\work_log.xlsx`
- Backups: `data\backups\`

## Cmd or PowerShell: pick one and stay with it

Windows has two different consoles. Commands are not interchangeable.

| You opened | How to tell | Use these files |
|------------|-------------|-----------------|
| File Explorer | You double-click in a folder | `windows\*.cmd` |
| Command Prompt | Title bar says **Command Prompt**, prompt looks like `C:\Users\you>` | `windows\*.cmd` |
| PowerShell | Title bar says **Windows PowerShell** or **PowerShell**, prompt looks like `PS C:\Users\you>` | `windows\*.ps1` |

`.cmd` files are for Explorer and cmd. They only start PowerShell in the background for you.

`.ps1` files are for a PowerShell window. Do not type `.ps1` commands into cmd. Do not type cmd commands (`set`, `type`, `&&`) into PowerShell and expect the same result.

Before any command below, change to the folder that contains `app.py`:

```bat
REM Command Prompt (cmd.exe)
cd /d C:\Users\you\worklog
```

```powershell
# PowerShell
cd C:\Users\you\worklog
```

If PowerShell blocks scripts the first time (one-time, current user only):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

You can skip that if you only double-click `.cmd` files. Those already pass `-ExecutionPolicy Bypass`.

## Commands

| Action | Command Prompt or double-click | PowerShell |
|--------|--------------------------------|------------|
| First-time setup (venv + openpyxl) | `windows\setup.cmd` | `.\windows\setup.ps1` |
| Start | `windows\start.cmd` | `.\windows\start.ps1` |
| Stop | `windows\stop.cmd` | `.\windows\stop.ps1` |
| Status | `windows\status.cmd` | `.\windows\status.ps1` |
| Change user or password | see below | see below |
| Import an old Excel file | `windows\import-excel.cmd` | `.\windows\import-excel.ps1` |
| Start at Windows login | `windows\install-startup.cmd` | `.\windows\install-startup.ps1` |
| Run in this window (debug) | `windows\run-foreground.cmd` | `.\windows\run-foreground.ps1` |

After start, open **http://127.0.0.1:5055/**

| File | Meaning |
|------|---------|
| `data\worklog.db` | Notes (source of truth) |
| `data\work_log.xlsx` | Excel copy |
| `data\credentials.json` | Users (hashed passwords) |
| `data\worklog.log` | App log |
| `data\worklog.err.log` | Startup errors |
| `data\worklog.pid` | Running process id |

## Default login

| Username | Password | Role |
|----------|----------|------|
| `admin` | `changeme` | edit |
| `viewer` | `changeme` | read-only |

Change the default password on first sign-in.

## Change password or username

Use the **Account** page in the browser, or the CLI below. After a CLI change, sign out (or clear cookies) and sign in again.

Command Prompt:

```bat
cd /d C:\Users\you\worklog

windows\set-user.cmd -List

windows\set-user.cmd -Username admin

windows\set-user.cmd -Username admin -NewUsername yourname -NoPassword

windows\set-user.cmd -Username admin -NewUsername yourname -Password "YourNewPassword" -DisplayName "Your Name"
```

PowerShell:

```powershell
cd C:\Users\you\worklog

.\windows\set-user.ps1 -List

.\windows\set-user.ps1 -Username admin

.\windows\set-user.ps1 -Username admin -NewUsername yourname -NoPassword

.\windows\set-user.ps1 -Username admin -NewUsername yourname -Password "YourNewPassword" -DisplayName "Your Name"
```

## Listen on another port or all interfaces

Command Prompt:

```bat
set WORKLOG_HOST=0.0.0.0
set WORKLOG_PORT=5055
windows\start.cmd
```

PowerShell:

```powershell
$env:WORKLOG_HOST = "0.0.0.0"
$env:WORKLOG_PORT = "5055"
.\windows\start.ps1
```

`set` is cmd only. `$env:NAME = "value"` is PowerShell only.

## Troubleshooting

If start exits immediately, read the logs.

Command Prompt:

```bat
type data\worklog.err.log
type data\worklog.log
windows\run-foreground.cmd
```

PowerShell:

```powershell
Get-Content .\data\worklog.err.log
Get-Content .\data\worklog.log
.\windows\run-foreground.ps1
```

Common fixes:

1. Run setup again (`setup.cmd` or `.\windows\setup.ps1`).
2. Check Python: `.venv\Scripts\python.exe --version` (need 3.10+).
3. Port in use: stop first, or set `WORKLOG_PORT` to another port (see above).

## Notes

- No admin is required for port 5055. Windows Firewall may prompt if you bind to all interfaces.
- Copy the whole `worklog` folder to back it up. Keep `data\` when you upgrade.
- Close Excel if it has `work_log.xlsx` open for write; the portal can still save to SQLite.

## Pack for Windows (build the zip on Linux)

`pack-for-windows.sh` is **not** run on the Windows PC. Run it on Linux (or WSL) in this repo when you want a zip to copy to Windows.

What it does:

1. Copies app code, `windows\` scripts, `docs\`, `static\`, `scripts\`, and tests into a staging folder.
2. Adds an empty `data\` folder. It does **not** put your live database, Excel file, passwords, session secret, venv, or logs in the zip.
3. Writes `START-HERE-WINDOWS.txt` inside the zip.
4. Creates `worklog-windows-YYYYMMDD-HHMMSS.zip`.
5. Deletes older `worklog-windows-*.zip` in the same output directory, so only the newest package remains.

```bash
./pack-for-windows.sh ~/packages
```

On the Windows PC: extract the zip, then use **Command Prompt / double-click** (`windows\setup.cmd`, `windows\start.cmd`) or **PowerShell** (`.\windows\setup.ps1`, `.\windows\start.ps1`) as in the tables above.

Upgrade without losing notes: stop the portal, keep the existing `data\` folder, extract the new zip over the app files, then start again.

## Linux or macOS (not this Windows folder layout)

On a Mac or Linux machine, do not use `windows\*.cmd` or `windows\*.ps1`. Use [MACOS.md](MACOS.md) / the repo `./setup.sh` and `./start.sh` in Terminal.

```bash
./setup.sh
./start.sh
./stop.sh
./status.sh
```

Do not run Unix and Windows start scripts against the same port at the same time.
