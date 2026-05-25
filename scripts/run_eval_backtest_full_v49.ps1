param(
  [string]$Field = "반도체",
  [string]$Frequency = "monthly",
  [string]$Start = "2025-01",
  [string]$End = "2026-01",
  [string]$UniverseCsv = "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv",
  [string]$RunId = "bt_2025_2026_v49",
  [string]$RunStamp = "",
  [int]$TimeoutSec = 900,
  [string]$HoldPolicy = "reject_option_directional_argmax",
  [int]$Limit = 0,
  [switch]$StopOnError,
  [switch]$WriteSheets,
  [switch]$SkipRealPipeline,
  [switch]$KeepLocalOutputs
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$srcPath = Resolve-Path ".\src"
$env:PYTHONPATH = "$srcPath"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:ALPHAPROVE_EVAL_HISTORY = "1"
$env:ALPHAPROVE_FIELD = $Field
$env:ALPHAPROVE_DATA_FIELD = $Field
$env:ALPHAPROVE_EVAL_FREQUENCY = $Frequency
$env:ALPHAPROVE_HISTORY_BACKEND = "local"
$env:ALPHAPROVE_DISABLE_GOOGLE_SHEETS = "1"
$env:ALPHAPROVE_CHAIR_OUTPUT_BACKEND = "local"
$env:CHAIR_FORCE_LOCAL_OUTPUT = "1"

$argsList = @(
  ".\scripts\run_eval_backtest_full_v49.py",
  "--field", $Field,
  "--frequency", $Frequency,
  "--start", $Start,
  "--end", $End,
  "--universe-csv", $UniverseCsv,
  "--run-id", $RunId,
  "--timeout-sec", "$TimeoutSec",
  "--hold-policy", $HoldPolicy
)

if ($RunStamp -ne "") {
  $argsList += @("--run-stamp", $RunStamp)
}

if ($Limit -gt 0) {
  $argsList += @("--limit", "$Limit")
}

if ($StopOnError) {
  $argsList += "--stop-on-error"
}

if ($WriteSheets) {
  $argsList += "--write-sheets"
}

if ($SkipRealPipeline) {
  $argsList += "--skip-real-pipeline"
}

if ($KeepLocalOutputs) {
  $argsList += "--keep-local-outputs"
}

Write-Host "[v49/local] repoRoot=$repoRoot"
Write-Host "[v49/local] PYTHONPATH=$env:PYTHONPATH"
Write-Host "[v49/local] python $($argsList -join ' ')"

python @argsList
exit $LASTEXITCODE
