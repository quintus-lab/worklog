#Requires -Version 5.1
# One-time setup for Daily Work Log on Windows 11 (no admin required).
# Creates .venv and installs requirements.txt.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    if (Test-Path (Join-Path $PWD "app.py")) {
        $Root = $PWD
    }
}
Set-Location $Root
Write-Host "Install root: $Root"

function Find-Python {
    $cmds = @(
        @{ Exe = "py"; Args = @("-3") },
        @{ Exe = "python"; Args = @() },
        @{ Exe = "python3"; Args = @() }
    )
    foreach ($c in $cmds) {
        $cmd = Get-Command $c.Exe -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $ver = & $c.Exe @($c.Args + @("--version")) 2>&1 | Out-String
            if ($ver -match "Python 3\.") {
                return @{ Exe = $c.Exe; Args = $c.Args; Version = $ver.Trim() }
            }
        } catch { }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Error "Python 3 not found on PATH. Install Python 3 from python.org (user install is fine; tick 'Add python.exe to PATH') and re-open PowerShell."
    exit 1
}
Write-Host "Using $($py.Version) via $($py.Exe) $($py.Args -join ' ')"

$venvDir = Join-Path $Root ".venv"
$venvPy = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Creating venv at $venvDir ..."
    & $py.Exe @($py.Args + @("-m", "venv", $venvDir))
    if (-not (Test-Path $venvPy)) {
        Write-Error "Failed to create venv. Ensure 'python -m venv' works without admin."
        exit 1
    }
} else {
    Write-Host "venv already exists: $venvDir"
}

Write-Host "Upgrading pip ..."
& $venvPy -m pip install --upgrade pip

$req = Join-Path $Root "requirements.txt"
if (-not (Test-Path $req)) {
    Write-Error "Missing requirements.txt at $req"
    exit 1
}
Write-Host "Installing dependencies from requirements.txt ..."
& $venvPy -m pip install -r $req

New-Item -ItemType Directory -Force -Path (Join-Path $Root "data") | Out-Null

$db = Join-Path $Root "data\worklog.db"
if (-not (Test-Path $db)) {
    Write-Host "Loading demo notes into a new database ..."
    & $venvPy (Join-Path $Root "scripts\seed_demo.py")
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "  Start:  .\windows\start.ps1   or double-click windows\start.cmd"
Write-Host "  Stop:   .\windows\stop.ps1"
Write-Host "  Status: .\windows\status.ps1"
Write-Host "  URL:    http://127.0.0.1:5055/"
Write-Host "  Demo login: admin / changeme"
