#Requires -Version 5.1
# Show whether Daily Work Log is running.
$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    if (Test-Path (Join-Path $PWD "app.py")) { $Root = $PWD }
}
Set-Location $Root

if ($env:WORKLOG_PIDFILE) { $pidFile = $env:WORKLOG_PIDFILE } else { $pidFile = Join-Path $Root "data\worklog.pid" }
if ($env:WORKLOG_PORT) { $port = [int]$env:WORKLOG_PORT } else { $port = 5055 }

$wbPid = $null
$running = $false
if (Test-Path $pidFile) {
    $raw = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($raw) { $wbPid = $raw.Trim() }
    if ($wbPid -match '^\d+$') {
        $proc = Get-Process -Id ([int]$wbPid) -ErrorAction SilentlyContinue
        if ($proc) { $running = $true }
    }
}

$xlsx = Join-Path $Root "data\work_log.xlsx"

Write-Host "Daily Work Log"
Write-Host "  root:  $Root"
Write-Host "  port:  $port"
Write-Host "  xlsx:  $xlsx"
if ($running) {
    Write-Host "  state: RUNNING (pid=$wbPid)"
    Write-Host "  url:   http://127.0.0.1:${port}/"
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:${port}/health" -UseBasicParsing -TimeoutSec 3
        Write-Host "  health: $($r.Content)"
    } catch {
        Write-Host "  health: (not responding yet)"
    }
} else {
    Write-Host "  state: STOPPED"
    if ($wbPid) { Write-Host "  stale pid file ignored: $wbPid" }
}
