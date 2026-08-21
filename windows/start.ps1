#Requires -Version 5.1
# Start Daily Work Log portal in the background.
# No admin required.
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

$dataDir = Join-Path $Root "data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
if ($env:WORKLOG_PIDFILE) { $pidFile = $env:WORKLOG_PIDFILE } else { $pidFile = Join-Path $dataDir "worklog.pid" }
if ($env:WORKLOG_LOGFILE) { $logFile = $env:WORKLOG_LOGFILE } else { $logFile = Join-Path $dataDir "worklog.log" }
$errLog = Join-Path $dataDir "worklog.err.log"

function Show-LogTail {
    param([string]$Path, [string]$Label)
    if (Test-Path $Path) {
        Write-Host ""
        Write-Host "----- $Label ($Path) -----"
        Get-Content $Path -ErrorAction SilentlyContinue | Select-Object -Last 40
        Write-Host "----- end $Label -----"
    } else {
        Write-Host "(no $Label file yet: $Path)"
    }
}

if (Test-Path $pidFile) {
    $old = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($old) { $old = $old.Trim() }
    if ($old -match '^\d+$') {
        $proc = Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Work Log already running (pid=$old). Use .\windows\stop.ps1 first."
            exit 0
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

if ($env:WORKLOG_HOST) { $hostBind = $env:WORKLOG_HOST } else { $hostBind = "127.0.0.1" }
if ($env:WORKLOG_PORT) { $port = [int]$env:WORKLOG_PORT } else { $port = 5055 }

$inUse = $null
try {
    $inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
} catch {
    $inUse = $null
}
if (-not $inUse) {
    try {
        $inUse = netstat -ano | Select-String ":$port\s+.*LISTENING"
    } catch {
        $inUse = $null
    }
}
if ($inUse) {
    Write-Host "Port $port is already in use. Run .\windows\stop.ps1 or change WORKLOG_PORT."
    exit 1
}

# Preflight: catch missing deps before backgrounding
Write-Host "Checking Python deps..."
$pre = & $venvPy -c "import openpyxl; import auth; import app; print('ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight failed. Output:"
    Write-Host $pre
    Write-Host ""
    Write-Host "Try: .\windows\setup.ps1"
    exit 1
}

$env:WORKLOG_HOST = $hostBind
$env:WORKLOG_PORT = "$port"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Clear old logs so a failed start is easy to read
Remove-Item $logFile -Force -ErrorAction SilentlyContinue
Remove-Item $errLog -Force -ErrorAction SilentlyContinue

Write-Host "Starting Daily Work Log..."
Write-Host "  host: $hostBind  port: $port"
Write-Host "  log:  $logFile"

$p = Start-Process -FilePath $venvPy `
    -ArgumentList @("-u", "app.py") `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errLog `
    -PassThru

if (-not $p) {
    Write-Error "Failed to start process"
    exit 1
}
Set-Content -Path $pidFile -Value $p.Id -Encoding ascii

Start-Sleep -Seconds 2
$alive = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($alive) {
    Write-Host "Daily Work Log started."
    Write-Host "  pid:  $($p.Id)"
    Write-Host "  url:  http://127.0.0.1:${port}/"
    if ($hostBind -ne "127.0.0.1" -and $hostBind -ne "localhost") {
        Write-Host "  bind: http://${hostBind}:${port}/"
    }
    Write-Host "  xlsx: $(Join-Path $dataDir 'work_log.xlsx')"
    Write-Host "  log:  $logFile"
} else {
    Write-Host "Process exited immediately."
    Show-LogTail -Path $errLog -Label "STDERR"
    Show-LogTail -Path $logFile -Label "STDOUT"
    Write-Host ""
    Write-Host "Tip: run foreground for full error:"
    Write-Host "  .\windows\run-foreground.ps1"
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    exit 1
}
