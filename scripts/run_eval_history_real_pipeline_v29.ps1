param(
  [string]$Field = "반도체",
  [ValidateSet("monthly","daily")]
  [string]$Frequency = "monthly",
  [string]$Start = "2025-01",
  [string]$End = "2026-01",
  [string]$UniverseCsv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",
  [string]$RunId = "eval_monthly_real_2025_2026_v29",
  [int]$Limit = 0,
  [int]$TimeoutSec = 900,
  [string]$Agents = "data-intake,finance,valuation,tech,market,issue,macro,auditor,chair",
  [switch]$WriteSheets,
  [switch]$StopOnError,
  [switch]$SkipRealPipeline
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$root = Resolve-Path "."
$env:PYTHONPATH = (Resolve-Path ".\src_eval").Path + ";" + (Resolve-Path ".\src").Path

$argsList = @(
  ".\scripts\run_eval_history_real_pipeline_v29.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--timeout-sec", "$TimeoutSec",
  "--agents", $Agents
)
if ($Limit -gt 0) { $argsList += @("--limit", "$Limit") }
if ($WriteSheets) { $argsList += "--write-sheets" }
if ($StopOnError) { $argsList += "--stop-on-error" }
if ($SkipRealPipeline) { $argsList += "--skip-real-pipeline" }

python @argsList
