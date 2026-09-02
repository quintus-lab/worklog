# Daily Work Log

A small local web app for short work notes.

I kept forgetting what I did last week in the team meeting. Bigger tools felt like overkill, and I can't install random software on the company laptop. Python is allowed, so this is just a Python app you run locally: jot a few lines after each task, then open the week view before the meeting.

- **Primary store:** SQLite (`data/worklog.db`). No admin rights, no server install.
- **Excel export:** `data/work_log.xlsx` refreshed after each change, plus **Download Excel**.
- **Backups / restore:** `data/backups/` (admin can restore from Account).
- **Windows 11:** `windows\*.cmd` in Command Prompt or Explorer; `windows\*.ps1` in PowerShell. See [docs/WINDOWS.md](docs/WINDOWS.md).
- **macOS / Linux:** same `./setup.sh` and `./start.sh` in Terminal. See [docs/MACOS.md](docs/MACOS.md).

## Get the code (macOS or Linux)

**GitLab is the working copy** (merges land there). **GitHub is the public mirror** of `main`. Other people should clone GitHub. You keep merging on GitLab. Full rationale: [docs/REMOTES.md](docs/REMOTES.md).

| Host | Role | Clone |
|------|------|-------|
| [GitHub](https://github.com/quintus-lab/worklog) | Public mirror | `git clone https://github.com/quintus-lab/worklog.git` |
| [GitLab](https://gitlab.com/qc1048/worklog) | Private working copy | `git clone https://gitlab.com/qc1048/worklog.git` |

GitHub zip (no git): repo page → **Code** → Download ZIP, then `./setup.sh`.

```bash
git clone https://github.com/quintus-lab/worklog.git
cd worklog
./setup.sh
./start.sh
```

Setup creates a local venv and, if there is no database yet, loads **fictional** demo notes (`scripts/seed_demo.py`). Demo login: `admin` / `changeme` (change it if this is not a demo machine).

A first-time GitLab → GitHub push mirror is configured under GitLab **Settings → Repository → Mirroring repositories** (Push, GitHub PAT with Contents read/write). Details in [docs/REMOTES.md](docs/REMOTES.md).

Do not copy `.venv` or `data/worklog.pid` between machines. Real notes live only in your local `data/` folder, which is gitignored. `./pack-for-windows.sh` is only a Windows zip, not a Mac/Linux installer.

## Features

- Sign-in with **admin** (edit) and **viewer** (read-only) roles  
- Forced password change when still on default `changeme`  
- Log / edit / delete entries (space-separated tags, follow-up date, status)  
- Search from the header; date/status filters on **History**  
- Ticket IDs typed in **Tags** (INC/CHG, KEY-123, or 6-12 digit numbers) link out once you set a ticket URL under **Account**. Click a tag to list entries with that tag. Numbers in details are not linked.  
- **Weekly summary** with copy list and print view  
- Paper (default) and dark themes. Paper follows mole.fit parchment and navy ink.  
- Admin: users, backups, restore, ticket URL  

## Windows 11 (no admin)

Cmd and PowerShell are different. Do not mix their syntax.

- **File Explorer or Command Prompt** (`C:\Users\you>`): use `windows\*.cmd`
- **PowerShell** (`PS C:\Users\you>`): use `.\windows\*.ps1`

```bat
REM Command Prompt
cd /d C:\Users\you\worklog
windows\setup.cmd
windows\start.cmd
```

```powershell
# PowerShell
cd C:\Users\you\worklog
.\windows\setup.ps1
.\windows\start.ps1
```

Then open http://127.0.0.1:5055/

| Action | Command Prompt / double-click | PowerShell |
|--------|-------------------------------|------------|
| Setup | `windows\setup.cmd` | `.\windows\setup.ps1` |
| Start | `windows\start.cmd` | `.\windows\start.ps1` |
| Stop | `windows\stop.cmd` | `.\windows\stop.ps1` |
| Status | `windows\status.cmd` | `.\windows\status.ps1` |
| Change password or username | `windows\set-user.cmd -Username admin` | `.\windows\set-user.ps1 -Username admin` |
| Start at login | `windows\install-startup.cmd` | `.\windows\install-startup.ps1` |

Full Windows notes (upgrade, logs, env vars): [docs/WINDOWS.md](docs/WINDOWS.md).

## Default accounts

| User | Password | Role |
|------|----------|------|
| `admin` | `changeme` | full edit |
| `viewer` | `changeme` | view only |

Change immediately in the UI (**Account**) or with `set-user.cmd` / `set-user.ps1` above.

## macOS and Linux

Terminal on a Mac (zsh or bash) uses the same commands as Linux. That is not Command Prompt or PowerShell.

```bash
cd ~/worklog
chmod +x setup.sh start.sh stop.sh status.sh
./setup.sh
./start.sh
./status.sh
./stop.sh
```

Then open http://127.0.0.1:5055/

| Action | Terminal (macOS or Linux) |
|--------|---------------------------|
| Setup | `./setup.sh` |
| Start | `./start.sh` |
| Stop | `./stop.sh` |
| Status | `./status.sh` |
| Change password or username | `./.venv/bin/python scripts/set_password.py admin` |

macOS notes (Homebrew Python, logs): [docs/MACOS.md](docs/MACOS.md).

## Data layout

```
data/
  worklog.db          # source of truth (SQLite)
  work_log.xlsx       # Excel mirror / export
  backups/            # timed DB + Excel snapshots
  credentials.json    # users (hashed passwords)
```

If Excel has the file open for write, the DB still saves; Excel is retried on the next change or **Download Excel**.

## Pack for Windows

`./pack-for-windows.sh` runs on **Linux** (this repo). It does not install or start the app on Windows.

It builds a zip you copy to a Windows PC: app code, `windows\` launchers, docs, and an empty `data\` folder. It does **not** pack Python, `.venv`, live notes, Excel, passwords, or logs. Older `worklog-windows-*.zip` files in the output folder are deleted so only the new zip remains.

```bash
./pack-for-windows.sh ~/packages
```

On Windows, extract the zip, then run `windows\setup.cmd` and `windows\start.cmd` (Command Prompt / double-click) or the `.ps1` pair in PowerShell. Keep your existing `data\` folder when upgrading. Details: [docs/WINDOWS.md](docs/WINDOWS.md#pack-for-windows-build-the-zip-on-linux).
