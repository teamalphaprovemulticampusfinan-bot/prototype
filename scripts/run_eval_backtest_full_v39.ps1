param(
  [string]$Field = "반도체",
  [string]$Frequency = "monthly",
  [Parameter(Mandatory=$true)][string]$Start,
  [Parameter(Mandatory=$true)][string]$End,
  [Parameter(Mandatory=$true)][string]$UniverseCsv,
  [string]$RunId = "bt_v39",
  [string]$RunStamp = "",
  [int]$TimeoutSec = 900,
  [string]$Agents = "data-intake,finance,valuation,tech,market,issue,macro,auditor,chair",
  [int]$Limit = 0,
  [switch]$WriteSheets,
  [switch]$SkipRealPipeline,
  [switch]$KeepLocalOutputs,
  [switch]$StopOnError,
  [string]$HoldPolicy = "directional_argmax"
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Resolve-Path ".\src_eval").Path + ";" + (Resolve-Path ".\src").Path

$argsList = @(
  ".\scripts\run_eval_backtest_full_v39.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--agents", $Agents,
  "--timeout-sec", "$TimeoutSec",
  "--hold-policy", $HoldPolicy
)

if ($RunStamp -ne "") { $argsList += @("--run-stamp", $RunStamp) }
if ($Limit -gt 0) { $argsList += @("--limit", "$Limit") }
if ($WriteSheets) { $argsList += "--write-sheets" }
if ($SkipRealPipeline) { $argsList += "--skip-real-pipeline" }
if ($KeepLocalOutputs) { $argsList += "--keep-local-outputs" }
if ($StopOnError) { $argsList += "--stop-on-error" }

python @argsList
