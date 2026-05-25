param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("monthly","daily")]
    [string]$Frequency,

    [Parameter(Mandatory=$true)]
    [string]$Start,

    [Parameter(Mandatory=$true)]
    [string]$End,

    [string]$Field = "반도체",

    [string]$UniverseCsv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",

    [switch]$BusinessDaysOnly,

    [switch]$WithDataIntake,

    [ValidateSet("fast","full")]
    [string]$DataIntakeMode = "fast",

    [string]$DataIntakeAgents = "macro,finance,tech,valuation,market,issue",

    [switch]$DataIntakeForceFetch,

    [switch]$DataIntakeSkipNetwork,

    [switch]$DataIntakeSkipAgent,

    [switch]$ContinueOnError,

    [string]$SpreadsheetId = "",

    [string]$ServiceAccountFile = "",

    [string]$InitialHistoryCsv = "",

    [string]$DmaAlpha = "0.99",

    [string]$RunIdPrefix = "",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Set-Location "C:\Agent_6.8"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path .\src).Path

$argsList = @(
    ".\scripts\run_history_range.py",
    "--field", $Field,
    "--frequency", $Frequency,
    "--start", $Start,
    "--end", $End,
    "--universe-csv", $UniverseCsv,
    "--dma-alpha", $DmaAlpha
)

if ($BusinessDaysOnly) { $argsList += "--business-days-only" }
if ($WithDataIntake) {
    $argsList += "--with-data-intake"
    $argsList += @("--data-intake-mode", $DataIntakeMode)
    $argsList += @("--data-intake-agents", $DataIntakeAgents)
}
if ($DataIntakeForceFetch) { $argsList += "--data-intake-force-fetch" }
if ($DataIntakeSkipNetwork) { $argsList += "--data-intake-skip-network" }
if ($DataIntakeSkipAgent) { $argsList += "--data-intake-skip-agent" }
if ($ContinueOnError) { $argsList += "--continue-on-error" }
if ($SpreadsheetId -and $SpreadsheetId.Trim().Length -gt 0) { $argsList += @("--spreadsheet-id", $SpreadsheetId) }
if ($ServiceAccountFile -and $ServiceAccountFile.Trim().Length -gt 0) { $argsList += @("--service-account-file", $ServiceAccountFile) }
if ($InitialHistoryCsv -and $InitialHistoryCsv.Trim().Length -gt 0) { $argsList += @("--initial-history-csv", $InitialHistoryCsv) }
if ($RunIdPrefix -and $RunIdPrefix.Trim().Length -gt 0) { $argsList += @("--run-id-prefix", $RunIdPrefix) }
if ($DryRun) { $argsList += "--dry-run" }

Write-Host "[RUN] python $($argsList -join ' ')" -ForegroundColor Cyan
python @argsList
