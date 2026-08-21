#Requires -Version 5.1
# Stop Daily Work Log started by windows\start.ps1
$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    if (Test-Path (Join-Path $PWD "app.py")) { $Root = $PWD }
}
Set-Location $Root

if ($env:WORKLOG_PIDFILE) { $pidFile = $env:WORKLOG_PIDFILE } else { $pidFile = Join-Path $Root "data\worklog.pid" }
if ($env:WORKLOG_PORT) { $port = [int]$env:WORKLOG_PORT } else { $port = 5055 }

$stopped = $false

if (Test-Path $pidFile) {
    $old = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($old) { $old = $old.Trim() }
    if ($old -match '^\d+$') {
        $proc = Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping Work Log pid=$old ..."
            Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            $stopped = $true
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$listeners = @()
try {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
} catch {
    $lines = netstat -ano 2>$null | Select-String ":$port\s+.*LISTENING"
    foreach ($ln in $lines) {
        if ("$ln" -match '\s(\d+)\s*$') { $listeners += [int]$Matches[1] }
    }
    $listeners = $listeners | Select-Object -Unique
}

foreach ($opid in $listeners) {
    if (-not $opid -or $opid -eq 0) { continue }
    $proc = Get-Process -Id $opid -ErrorAction SilentlyContinue
    if ($proc -and ($proc.ProcessName -match 'python')) {
        Write-Host "Stopping pid=$opid on port $port ($($proc.ProcessName)) ..."
        Stop-Process -Id $opid -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
}

if ($stopped) {
    Write-Host "Daily Work Log stopped (port $port)."
} else {
    Write-Host "Daily Work Log was not running (port $port)."
}
