@echo off
REM Windows helper: change password / rename username (no admin)
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\set_password.py %*
) else (
  python scripts\set_password.py %*
)
if errorlevel 1 pause
