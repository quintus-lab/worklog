@echo off
REM Double-click friendly start (no admin). Uses PowerShell.
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
