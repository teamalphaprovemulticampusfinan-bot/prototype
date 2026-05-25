param(
    [string]$Field = "반도체",
    [ValidateSet("monthly", "daily")]
    [string]$Frequency = "monthly",
    [string]$Start = "2025-01",
    [string]$End = "2026-01",
    [string]$UniverseCsv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",
    [string]$RunId = "bt_v42",
    [int]$Limit = 0,
    [switch]$WriteSheets
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src_eval").Path + ";" + (Resolve-Path ".\src").Path

$argsList = @(
    ".\scripts\run_eval_backtest_full_v42.py",
    "--field", $Field,
    "--frequency", $Frequency,
    "--start", $Start,
    "--end", $End,
    "--universe-csv", $UniverseCsv,
    "--run-id", $RunId
)
if ($Limit -gt 0) { $argsList += @("--limit", [string]$Limit) }
if ($WriteSheets) { $argsList += "--write-sheets" }

python @argsList
