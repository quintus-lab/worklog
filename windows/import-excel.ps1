#Requires -Version 5.1
# Import existing work_log.xlsx into SQLite (no re-typing). No admin required.
param(
    [string]$ExcelPath = "",
    [switch]$Replace,
    [switch]$MergeUpdate
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

$script = Join-Path $Root "scripts\import_excel.py"
$argsList = @($script)
if ($ExcelPath) { $argsList += $ExcelPath }
if ($Replace) { $argsList += "--replace" }
if ($MergeUpdate) { $argsList += "--merge-update" }

& $venvPy @argsList
exit $LASTEXITCODE
