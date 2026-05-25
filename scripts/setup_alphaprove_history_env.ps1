param(
    [Parameter(Mandatory=$true)]
    [string]$SpreadsheetId,

    [string]$ProjectRoot = "C:\Agent_6.8",

    [string]$ServiceAccountFile = "C:\Agent_6.8\secrets\service_account.json",

    [string]$DmaHistoryCsv = "",

    [string]$DmaAlpha = "0.99",

    [ValidateSet("0","1")]
    [string]$Strict = "1",

    [ValidateSet("0","1")]
    [string]$LocalWriteDisabled = "1"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "AlphaProve History / Google Sheets / DMA Environment Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path $ProjectRoot)) {
    throw "ProjectRoot not found: $ProjectRoot"
}

Set-Location $ProjectRoot

try {
    chcp 65001 | Out-Null
} catch {
    Write-Warning "Failed to set code page 65001. Continue anyway."
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$srcPath = Join-Path $ProjectRoot "src"
if (Test-Path $srcPath) {
    $env:PYTHONPATH = (Resolve-Path $srcPath).Path
} else {
    throw "src folder not found under ProjectRoot: $srcPath"
}

$env:ALPHAPROVE_HISTORY_BACKEND = "sheets"
$env:ALPHAPROVE_HISTORY_SPREADSHEET_ID = $SpreadsheetId
$env:ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE = $ServiceAccountFile

# History mode guardrails:
# - Use Google Sheets as history storage.
# - Do not write history-mode outputs into data/<field>/<company>/<agent> folders.
$env:ALPHAPROVE_SHEETS_DB_ONLY = "1"
$env:ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED = $LocalWriteDisabled
$env:ALPHAPROVE_USE_AGENT_HISTORY = "1"
$env:ALPHAPROVE_HISTORY_STRICT = $Strict

# DMA settings:
# If DmaHistoryCsv is empty, the code should use objective equal-prior fallback.
# If DmaHistoryCsv is provided, DMA should calculate posterior weights from the history CSV.
$env:ALPHAPROVE_DMA_ALPHA = $DmaAlpha

if ($DmaHistoryCsv -and $DmaHistoryCsv.Trim().Length -gt 0) {
    $env:ALPHAPROVE_DMA_HISTORY_CSV = $DmaHistoryCsv
} else {
    Remove-Item Env:\ALPHAPROVE_DMA_HISTORY_CSV -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[OK] Environment variables have been set for this PowerShell session." -ForegroundColor Green
Write-Host ""
Write-Host "ProjectRoot                         = $ProjectRoot"
Write-Host "PYTHONPATH                          = $env:PYTHONPATH"
Write-Host "ALPHAPROVE_HISTORY_BACKEND          = $env:ALPHAPROVE_HISTORY_BACKEND"
Write-Host "ALPHAPROVE_HISTORY_SPREADSHEET_ID   = $env:ALPHAPROVE_HISTORY_SPREADSHEET_ID"
Write-Host "ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE = $env:ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE"
Write-Host "ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED = $env:ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"
Write-Host "ALPHAPROVE_DMA_ALPHA                = $env:ALPHAPROVE_DMA_ALPHA"

if ($env:ALPHAPROVE_DMA_HISTORY_CSV) {
    Write-Host "ALPHAPROVE_DMA_HISTORY_CSV          = $env:ALPHAPROVE_DMA_HISTORY_CSV"
} else {
    Write-Host "ALPHAPROVE_DMA_HISTORY_CSV          = <not set; equal-prior fallback>"
}

Write-Host ""

if (-not (Test-Path $ServiceAccountFile)) {
    Write-Warning "Service account file not found: $ServiceAccountFile"
    Write-Warning "Check the path before running Google Sheets scripts."
} else {
    Write-Host "[OK] Service account file exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "Recommended check:" -ForegroundColor Yellow
Write-Host "python .\scripts\check_google_sheets_history_setup.py"
Write-Host ""
Write-Host "Daily example:" -ForegroundColor Yellow
Write-Host "python .\scripts\run_history_sheets_only_pipeline.py --field `"반도체`" --as-of-date `"2025-05-01`" --frequency daily --universe-csv `"data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv`" --continue-on-error"
Write-Host ""
Write-Host "Monthly example:" -ForegroundColor Yellow
Write-Host "python .\scripts\run_history_sheets_only_pipeline.py --field `"반도체`" --as-of-date `"2025-01-31`" --frequency monthly --universe-csv `"data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv`" --continue-on-error"
Write-Host ""
