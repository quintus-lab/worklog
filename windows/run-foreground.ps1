#Requires -Version 5.1
# Run Daily Work Log in this console window (debug / see errors).
# No admin required. Ctrl+C to stop.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    if (Test-Path (Join-Path $PWD "app.py")) { $Root = $PWD }
}
Set-Location $Root

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "venv missing - running setup first..."
    & (Join-Path $PSScriptRoot "setup.ps1")
    if (-not (Test-Path $venvPy)) { exit 1 }
}

if ($env:WORKLOG_HOST) { $hostBind = $env:WORKLOG_HOST } else { $hostBind = "127.0.0.1" }
if ($env:WORKLOG_PORT) { $port = [int]$env:WORKLOG_PORT } else { $port = 5055 }

$env:WORKLOG_HOST = $hostBind
$env:WORKLOG_PORT = "$port"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "Running in foreground (Ctrl+C to stop)"
Write-Host "  python: $venvPy"
Write-Host "  url:    http://127.0.0.1:${port}/"
Write-Host ""

& $venvPy -u app.py
exit $LASTEXITCODE
