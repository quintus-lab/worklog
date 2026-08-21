#Requires -Version 5.1
# Change Daily Work Log password and/or username (Windows 11, no admin).
#
# Examples:
#   .\windows\set-user.ps1
#   .\windows\set-user.ps1 -Username admin -Password "NewSecret123"
#   .\windows\set-user.ps1 -Username admin -NewUsername quintus -Password "NewSecret123"
#   .\windows\set-user.ps1 -Username admin -NewUsername quintus -NoPassword
#   .\windows\set-user.ps1 -List
#
param(
    [string]$Username = "admin",
    [string]$NewUsername = "",
    [string]$Password = "",
    [string]$DisplayName = "",
    [switch]$NoPassword,
    [switch]$List
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "app.py"))) {
    if (Test-Path (Join-Path $PWD "app.py")) { $Root = $PWD }
}
Set-Location $Root

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "venv missing - run .\windows\setup.ps1 first."
    exit 1
}

$script = Join-Path $Root "scripts\set_password.py"
$pyArgs = @($script)

if ($List) {
    $pyArgs += @("--list")
    & $venvPy @pyArgs
    exit $LASTEXITCODE
}

$pyArgs += @($Username)

if ($NewUsername) {
    $pyArgs += @("--rename", $NewUsername)
}
if ($DisplayName) {
    $pyArgs += @("--name", $DisplayName)
}
if ($NoPassword) {
    $pyArgs += @("--no-password")
} elseif ($Password) {
    $pyArgs += @("--password", $Password)
}
# else: Python script will prompt for password securely

& $venvPy @pyArgs
exit $LASTEXITCODE
