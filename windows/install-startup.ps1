#Requires -Version 5.1
# Install a per-user Startup shortcut so Work Log starts at login (no admin).
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    if (Test-Path (Join-Path $PWD "app.py")) { $Root = $PWD }
}

$startup = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startup "DailyWorkLog.lnk"
$startCmd = Join-Path $Root "windows\start.cmd"

if ($Remove) {
    if (Test-Path $lnkPath) {
        Remove-Item $lnkPath -Force
        Write-Host "Removed startup shortcut: $lnkPath"
    } else {
        Write-Host "No startup shortcut found."
    }
    exit 0
}

if (-not (Test-Path $startCmd)) {
    Write-Error "Missing $startCmd"
    exit 1
}

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($lnkPath)
$sc.TargetPath = $startCmd
$sc.WorkingDirectory = $Root
$sc.WindowStyle = 7  # minimized
$sc.Description = "Daily Work Log portal (no admin)"
$sc.Save()

Write-Host "Installed startup shortcut:"
Write-Host "  $lnkPath"
Write-Host "Work Log will start when you sign in to Windows."
Write-Host "Remove later: .\windows\install-startup.ps1 -Remove"
