@echo off
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\import_excel.py %*
) else (
  python scripts\import_excel.py %*
)
if errorlevel 1 pause
